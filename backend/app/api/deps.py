from dataclasses import dataclass
from datetime import datetime
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user_from_token_payload(payload: dict) -> Optional[AuthenticatedUser]:
    required_claims = ["uid", "name", "role", "is_active", "created_at"]
    if not all(claim in payload for claim in required_claims):
        return None
    return AuthenticatedUser(
        id=int(payload["uid"]),
        name=payload["name"],
        email=payload["sub"],
        role=payload["role"],
        is_active=bool(payload["is_active"]),
        created_at=datetime.fromisoformat(payload["created_at"]),
        organization_id=payload.get("organization_id"),
        organization_name=payload.get("organization_name"),
    )


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AuthenticatedUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
    except ValueError:
        raise credentials_exception
    if not email:
        raise credentials_exception
    token_user = _user_from_token_payload(payload)
    if token_user and token_user.is_active and token_user.organization_id is not None:
        return token_user
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise credentials_exception
    return AuthenticatedUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        organization_id=user.organization_id,
        organization_name=user.organization_name,
    )


def require_roles(*roles: str):
    def dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return dependency


def require_write_access(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if current_user.role == "VIEW_ONLY":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="View-only users cannot modify records",
        )
    return current_user


def require_feature(feature_key: str):
    def dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> AuthenticatedUser:
        # Import dynamically to avoid circular import issues if they exist
        from app.services.subscription_service import require_feature_access
        
        # We need a proper User object to pass to the service, or we can just pass the current_user 
        # since it shares similar attributes (like role and organization_id)
        # We'll fetch the actual user object or adapt the service to accept AuthenticatedUser.
        # Since subscription_service expects `user: User`, and uses `user.organization_id`, `user.role`
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            
        require_feature_access(db, user, feature_key)
        return current_user

    return dependency
