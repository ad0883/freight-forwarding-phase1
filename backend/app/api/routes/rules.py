from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.rule_definition import RuleDefinition
from app.schemas.rule import RuleDefinitionRead, RuleDefinitionUpdate
from app.services.audit_service import changed_fields, record_audit_log


router = APIRouter(prefix="/rules", tags=["rules"])

ReadUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


@router.get("", response_model=list[RuleDefinitionRead])
def list_rules(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = ReadUser,
) -> list[RuleDefinition]:
    return (
        db.query(RuleDefinition)
        .order_by(
            RuleDefinition.entity_type.asc().nullslast(),
            RuleDefinition.rule_key.asc(),
        )
        .all()
    )


@router.patch("/{rule_id}", response_model=RuleDefinitionRead)
def update_rule(
    rule_id: int,
    payload: RuleDefinitionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> RuleDefinition:
    rule = db.query(RuleDefinition).filter(RuleDefinition.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    data = payload.model_dump(exclude_unset=True)
    if "rule_key" in data:
        data.pop("rule_key", None)
    before = {field: getattr(rule, field, None) for field in data}
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    record_audit_log(
        db,
        current_user,
        "rule.update",
        "rule_definition",
        entity_id=rule.id,
        entity_label=rule.rule_key,
        description="Validation rule updated.",
        metadata={
            "fields_changed": changed_fields(
                before, {field: getattr(rule, field, None) for field in data}
            ),
            "rule_key": rule.rule_key,
            "is_blocking": rule.is_blocking,
            "is_enabled": rule.is_enabled,
        },
        request=request,
    )
    return rule
