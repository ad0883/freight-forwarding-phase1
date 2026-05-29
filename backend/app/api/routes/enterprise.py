"""Phase 24 Enterprise Scaling + Governance API routes."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.services.enterprise.enterprise_service import (
    create_audit_export, get_enterprise_health, get_permission_matrix,
    list_data_retention_policies, list_members, list_organizations,
    list_roles, list_security_events, record_security_event,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])
AdminUser = Depends(require_roles("ADMIN"))


class SecurityEventRead(BaseModel):
    id: int; event_type: str; severity: str; source: str; safe_summary: str; created_at: datetime
    class Config:
        from_attributes = True

class OrgRead(BaseModel):
    id: int; name: str; status: str = "active"; organization_type: Optional[str] = None; created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_org(cls, org) -> "OrgRead":
        return cls(
            id=org.id,
            name=org.name,
            status="active" if getattr(org, "is_active", True) else "inactive",
            organization_type=getattr(org, "org_type", None),
            created_at=org.created_at,
        )

class MemberRead(BaseModel):
    id: int; organization_id: int; user_id: int; membership_status: str; member_type: str; role_key: str
    class Config:
        from_attributes = True

class RoleRead(BaseModel):
    id: int; role_key: str; role_name: str; scope: str; is_system_role: bool; is_active: bool
    class Config:
        from_attributes = True


@router.get("/health")
def enterprise_health(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return get_enterprise_health(db, current_user)


@router.post("/health/run")
def run_health_check(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return get_enterprise_health(db, current_user)


@router.get("/organizations", response_model=list[OrgRead])
def orgs(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return [OrgRead.from_org(o) for o in list_organizations(db)]


@router.get("/organizations/{organization_id}/members", response_model=list[MemberRead])
def org_members(organization_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return [MemberRead.model_validate(m) for m in list_members(db, organization_id)]


@router.get("/roles", response_model=list[RoleRead])
def roles(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return [RoleRead.model_validate(r) for r in list_roles(db)]


@router.get("/permissions")
def permissions(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return get_permission_matrix(db)


@router.get("/permissions/matrix")
def permission_matrix(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return get_permission_matrix(db)


@router.get("/security-events", response_model=list[SecurityEventRead])
def security_events(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return [SecurityEventRead.model_validate(e) for e in list_security_events(db, limit=limit)]


@router.get("/data-retention")
def data_retention(organization_id: int = Query(1), db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    return [{"id": p.id, "resource_key": p.resource_key, "retention_days": p.retention_days, "is_active": p.is_active} for p in list_data_retention_policies(db, organization_id)]


@router.post("/audit-exports", status_code=201)
def create_export(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    export = create_audit_export(db, {"export_type": "full"}, current_user)
    return {"id": export.id, "export_number": export.export_number, "status": export.status}
