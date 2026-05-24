from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import AdminPasswordResetRequest, UserCreate, UserRead, UserUpdate
from app.services.audit_service import changed_fields, record_audit_log


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), _: AuthenticatedUser = Depends(require_roles("ADMIN"))
) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> User:
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=user_in.name,
        email=str(user_in.email),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_log(
        db,
        current_user,
        "user.create",
        "user",
        entity_id=user.id,
        entity_label=user.email,
        description="User created by admin.",
        metadata={"role": user.role, "is_active": user.is_active},
        request=request,
    )
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> User:
    user = _get_user(db, user_id)
    data = user_in.model_dump(exclude_unset=True)
    if not data:
        return user
    if "email" in data:
        data["email"] = str(data["email"])
        existing = db.query(User).filter(User.email == data["email"], User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    next_role = data.get("role", user.role)
    next_is_active = data.get("is_active", user.is_active)
    _validate_admin_guardrails(db, user, current_user, next_role=next_role, next_is_active=next_is_active)
    before = _user_audit_snapshot(user)
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    after = _user_audit_snapshot(user)
    fields_changed = changed_fields(before, after)
    record_audit_log(
        db,
        current_user,
        "user.update",
        "user",
        entity_id=user.id,
        entity_label=user.email,
        description="User updated by admin.",
        metadata={"fields_changed": fields_changed},
        request=request,
    )
    if before["role"] != after["role"]:
        record_audit_log(
            db,
            current_user,
            "user.role_change",
            "user",
            entity_id=user.id,
            entity_label=user.email,
            description="User role changed by admin.",
            metadata={"from_role": before["role"], "to_role": after["role"]},
            request=request,
        )
    return user


@router.patch("/{user_id}/password-reset", response_model=UserRead)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> User:
    user = _get_user(db, user_id)
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    db.refresh(user)
    record_audit_log(
        db,
        current_user,
        "user.password_reset",
        "user",
        entity_id=user.id,
        entity_label=user.email,
        description="User password reset by admin.",
        metadata={"target_user_id": user.id},
        request=request,
    )
    return user


@router.patch("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> User:
    user = _get_user(db, user_id)
    _validate_admin_guardrails(db, user, current_user, next_role=user.role, next_is_active=False)
    user.is_active = False
    db.commit()
    db.refresh(user)
    record_audit_log(
        db,
        current_user,
        "user.deactivate",
        "user",
        entity_id=user.id,
        entity_label=user.email,
        description="User deactivated by admin.",
        metadata={"target_user_id": user.id, "target_role": user.role},
        request=request,
    )
    return user


@router.patch("/{user_id}/reactivate", response_model=UserRead)
def reactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> User:
    user = _get_user(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    record_audit_log(
        db,
        current_user,
        "user.reactivate",
        "user",
        entity_id=user.id,
        entity_label=user.email,
        description="User reactivated by admin.",
        metadata={"target_user_id": user.id, "target_role": user.role},
        request=request,
    )
    return user


def _get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _validate_admin_guardrails(
    db: Session,
    target_user: User,
    current_user: AuthenticatedUser,
    next_role: str,
    next_is_active: bool,
) -> None:
    if target_user.id == current_user.id and (next_role != "ADMIN" or not next_is_active):
        raise HTTPException(status_code=400, detail="Admins cannot remove their own admin access")
    if target_user.role == "ADMIN" and target_user.is_active and (next_role != "ADMIN" or not next_is_active):
        other_admin = (
            db.query(User.id)
            .filter(User.id != target_user.id, User.role == "ADMIN", User.is_active.is_(True))
            .first()
        )
        if not other_admin:
            raise HTTPException(status_code=400, detail="At least one active admin must remain")


def _user_audit_snapshot(user: User) -> dict[str, object]:
    return {
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }
