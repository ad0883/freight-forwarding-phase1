"""Phase 24 Enterprise Scaling + Multi-Organization Governance models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class OrganizationSetting(Base):
    __tablename__ = "organization_settings"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    setting_key = Column(String(80), nullable=False, index=True)
    setting_value_json = Column(JSON, nullable=True)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    membership_status = Column(String(20), nullable=False, default="active", index=True)
    member_type = Column(String(30), nullable=False, default="internal_user")
    role_key = Column(String(40), nullable=False, default="STAFF")
    branch_id = Column(Integer, nullable=True)
    department_id = Column(Integer, nullable=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class OrganizationRole(Base):
    __tablename__ = "organization_roles"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    role_key = Column(String(40), nullable=False, index=True)
    role_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(20), nullable=False, default="organization")
    is_system_role = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class RolePermissionPolicy(Base):
    __tablename__ = "role_permission_policies"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    role_key = Column(String(40), nullable=False, index=True)
    resource_key = Column(String(40), nullable=False, index=True)
    action_key = Column(String(30), nullable=False)
    effect = Column(String(20), nullable=False, default="allow")
    conditions_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class OrganizationBranch(Base):
    __tablename__ = "organization_branches"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    branch_name = Column(String(150), nullable=False)
    branch_code = Column(String(30), nullable=False)
    city = Column(String(100), nullable=True)
    country = Column(String(60), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class OrganizationDepartment(Base):
    __tablename__ = "organization_departments"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    department_name = Column(String(100), nullable=False)
    department_code = Column(String(30), nullable=False)
    branch_id = Column(Integer, ForeignKey("organization_branches.id"), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class EnterpriseAuditExport(Base):
    __tablename__ = "enterprise_audit_exports"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    export_number = Column(String(60), nullable=False, index=True)
    export_type = Column(String(30), nullable=False, default="full")
    status = Column(String(20), nullable=False, default="pending")
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    requested_by_name = Column(String(150), nullable=True)
    filters_json = Column(JSON, nullable=True)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class EnterpriseSecurityEvent(Base):
    __tablename__ = "enterprise_security_events"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(60), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info")
    source = Column(String(40), nullable=False, default="system")
    safe_summary = Column(Text, nullable=False)
    ip_address_hash = Column(String(64), nullable=True)
    user_agent_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class EnterpriseDataRetentionPolicy(Base):
    __tablename__ = "enterprise_data_retention_policies"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    resource_key = Column(String(40), nullable=False)
    retention_days = Column(Integer, nullable=False, default=365)
    archive_after_days = Column(Integer, nullable=True)
    delete_after_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class EnterpriseHealthSnapshot(Base):
    __tablename__ = "enterprise_health_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    snapshot_key = Column(String(60), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="ok")
    summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
