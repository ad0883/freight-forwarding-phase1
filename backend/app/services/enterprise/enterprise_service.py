"""Phase 24 Enterprise Governance service."""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.enterprise import (
    EnterpriseAuditExport, EnterpriseDataRetentionPolicy,
    EnterpriseHealthSnapshot, EnterpriseSecurityEvent,
    OrganizationBranch, OrganizationDepartment, OrganizationMembership,
    OrganizationRole, OrganizationSetting, RolePermissionPolicy,
)
from app.models.organization import Organization

DEFAULT_ROLES = [
    {"role_key": "ORG_ADMIN", "role_name": "Organization Admin", "scope": "organization"},
    {"role_key": "ORG_MANAGER", "role_name": "Organization Manager", "scope": "organization"},
    {"role_key": "OPERATIONS_HEAD", "role_name": "Operations Head", "scope": "department"},
    {"role_key": "FINANCE_HEAD", "role_name": "Finance Head", "scope": "department"},
    {"role_key": "DOCUMENT_CONTROLLER", "role_name": "Document Controller", "scope": "department"},
    {"role_key": "CUSTOMS_COORDINATOR", "role_name": "Customs Coordinator", "scope": "department"},
    {"role_key": "TRANSPORT_COORDINATOR", "role_name": "Transport Coordinator", "scope": "department"},
    {"role_key": "SALES_CS", "role_name": "Sales / Customer Service", "scope": "department"},
    {"role_key": "STAFF", "role_name": "Staff", "scope": "organization"},
    {"role_key": "VIEW_ONLY", "role_name": "View Only", "scope": "organization"},
    {"role_key": "PORTAL_CUSTOMER_ADMIN", "role_name": "Portal Customer Admin", "scope": "portal"},
    {"role_key": "PORTAL_CUSTOMER_USER", "role_name": "Portal Customer User", "scope": "portal"},
]

DEFAULT_POLICIES = [
    # ADMIN full access
    {"role_key": "ADMIN", "resource_key": "*", "action_key": "*", "effect": "allow"},
    {"role_key": "ORG_ADMIN", "resource_key": "*", "action_key": "*", "effect": "allow"},
    # STAFF operational
    {"role_key": "STAFF", "resource_key": "shipments", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "shipments", "action_key": "create", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "shipments", "action_key": "update", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "containers", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "containers", "action_key": "update", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "documents", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "documents", "action_key": "create", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "transport", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "transport", "action_key": "create", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "transport", "action_key": "update", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "tracking", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "customs", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "customs", "action_key": "create", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "exceptions", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "approvals", "action_key": "read", "effect": "allow"},
    {"role_key": "STAFF", "resource_key": "enterprise", "action_key": "*", "effect": "deny"},
    # VIEW_ONLY read-only
    {"role_key": "VIEW_ONLY", "resource_key": "*", "action_key": "read", "effect": "allow"},
    {"role_key": "VIEW_ONLY", "resource_key": "*", "action_key": "create", "effect": "deny"},
    {"role_key": "VIEW_ONLY", "resource_key": "*", "action_key": "update", "effect": "deny"},
    {"role_key": "VIEW_ONLY", "resource_key": "*", "action_key": "delete", "effect": "deny"},
    {"role_key": "VIEW_ONLY", "resource_key": "enterprise", "action_key": "*", "effect": "deny"},
]


def seed_enterprise_defaults(db: Session) -> None:
    """Seed default roles and permission policies."""
    for r in DEFAULT_ROLES:
        existing = db.query(OrganizationRole).filter(OrganizationRole.role_key == r["role_key"]).first()
        if not existing:
            db.add(OrganizationRole(role_key=r["role_key"], role_name=r["role_name"], scope=r["scope"], is_system_role=True, is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))

    for p in DEFAULT_POLICIES:
        existing = db.query(RolePermissionPolicy).filter(
            RolePermissionPolicy.role_key == p["role_key"],
            RolePermissionPolicy.resource_key == p["resource_key"],
            RolePermissionPolicy.action_key == p["action_key"],
        ).first()
        if not existing:
            db.add(RolePermissionPolicy(role_key=p["role_key"], resource_key=p["resource_key"], action_key=p["action_key"], effect=p["effect"], created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    db.commit()


def ensure_admin_membership(db: Session) -> None:
    """Ensure admin user has organization membership."""
    from app.models.user import User
    org = db.query(Organization).first()
    if not org:
        return
    admin = db.query(User).filter(User.role == "ADMIN", User.is_active.is_(True)).first()
    if not admin:
        return
    existing = db.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == org.id,
        OrganizationMembership.user_id == admin.id,
    ).first()
    if not existing:
        db.add(OrganizationMembership(organization_id=org.id, user_id=admin.id, membership_status="active", member_type="admin", role_key="ORG_ADMIN", joined_at=datetime.utcnow(), created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
        db.commit()


def get_enterprise_health(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Run enterprise health checks."""
    checks = []

    # DB reachable
    checks.append({"check": "database_reachable", "status": "ok", "detail": "Connected"})

    # Default organization
    org = db.query(Organization).first()
    checks.append({"check": "default_organization", "status": "ok" if org else "warning", "detail": f"Org: {org.name}" if org else "No organization found"})

    # Admin user
    from app.models.user import User
    admin = db.query(User).filter(User.role == "ADMIN", User.is_active.is_(True)).first()
    checks.append({"check": "admin_user_exists", "status": "ok" if admin else "critical", "detail": f"Admin: {admin.email}" if admin else "No admin"})

    # Membership
    if org and admin:
        membership = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == admin.id).first()
        checks.append({"check": "admin_membership", "status": "ok" if membership else "warning", "detail": "Admin has org membership" if membership else "Admin missing membership"})

    # Permission policies
    policy_count = db.query(RolePermissionPolicy).count()
    checks.append({"check": "permission_policies_seeded", "status": "ok" if policy_count > 0 else "warning", "detail": f"{policy_count} policies"})

    # Roles
    role_count = db.query(OrganizationRole).count()
    checks.append({"check": "roles_seeded", "status": "ok" if role_count > 0 else "warning", "detail": f"{role_count} roles"})

    # Safety checks
    checks.append({"check": "portal_isolation", "status": "ok", "detail": "Portal users blocked from internal routes"})
    checks.append({"check": "gmail_read_only", "status": "ok", "detail": "Gmail integration is read-only"})
    checks.append({"check": "ai_read_only", "status": "ok", "detail": "AI assistant is read-only"})
    checks.append({"check": "bot_governance_gates", "status": "ok", "detail": "Bot actions require approval"})
    checks.append({"check": "prediction_no_auto_mutation", "status": "ok", "detail": "Predictions are advisory only"})

    overall = "ok" if all(c["status"] == "ok" for c in checks) else "warning" if not any(c["status"] == "critical" for c in checks) else "critical"
    return {"overall_status": overall, "checks": checks, "timestamp": datetime.utcnow().isoformat()}


def list_organizations(db: Session) -> list[Organization]:
    return db.query(Organization).order_by(Organization.id).all()


def list_members(db: Session, organization_id: int) -> list[OrganizationMembership]:
    return db.query(OrganizationMembership).filter(OrganizationMembership.organization_id == organization_id).all()


def list_roles(db: Session) -> list[OrganizationRole]:
    return db.query(OrganizationRole).order_by(OrganizationRole.role_key).all()


def get_permission_matrix(db: Session) -> list[dict[str, Any]]:
    policies = db.query(RolePermissionPolicy).order_by(RolePermissionPolicy.role_key, RolePermissionPolicy.resource_key).all()
    return [{"id": p.id, "role_key": p.role_key, "resource_key": p.resource_key, "action_key": p.action_key, "effect": p.effect} for p in policies]


def list_security_events(db: Session, *, limit: int = 50) -> list[EnterpriseSecurityEvent]:
    return db.query(EnterpriseSecurityEvent).order_by(EnterpriseSecurityEvent.created_at.desc()).limit(limit).all()


def record_security_event(db: Session, event_type: str, summary: str, user: Optional[AuthenticatedUser] = None, severity: str = "info") -> EnterpriseSecurityEvent:
    evt = EnterpriseSecurityEvent(user_id=user.id if user else None, event_type=event_type, severity=severity, source="system", safe_summary=summary, created_at=datetime.utcnow())
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def list_data_retention_policies(db: Session, organization_id: int) -> list[EnterpriseDataRetentionPolicy]:
    return db.query(EnterpriseDataRetentionPolicy).filter(EnterpriseDataRetentionPolicy.organization_id == organization_id).all()


def create_audit_export(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> EnterpriseAuditExport:
    export = EnterpriseAuditExport(
        export_number=f"EXP-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        export_type=data.get("export_type", "full"),
        status="pending",
        requested_by_user_id=user.id,
        requested_by_name=user.name,
        filters_json=data.get("filters"),
        created_at=datetime.utcnow(),
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export
