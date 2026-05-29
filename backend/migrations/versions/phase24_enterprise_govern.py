"""Phase 24 Enterprise Scaling + Governance.

Revision ID: phase24_enterprise_govern
Revises: phase23_predictive_intel
Create Date: 2026-05-29
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase24_enterprise_govern"
down_revision: Union[str, None] = "phase23_predictive_intel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ci(n, t, c):
    op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "organization_settings" not in tables:
        op.create_table("organization_settings", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("setting_key", sa.String(80), nullable=False), sa.Column("setting_value_json", sa.JSON(), nullable=True), sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default="false"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "organization_memberships" not in tables:
        op.create_table("organization_memberships", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("membership_status", sa.String(20), nullable=False, server_default="active"), sa.Column("member_type", sa.String(30), nullable=False, server_default="internal_user"), sa.Column("role_key", sa.String(40), nullable=False, server_default="STAFF"), sa.Column("branch_id", sa.Integer(), nullable=True), sa.Column("department_id", sa.Integer(), nullable=True), sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "organization_roles" not in tables:
        op.create_table("organization_roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("role_key", sa.String(40), nullable=False), sa.Column("role_name", sa.String(100), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("scope", sa.String(20), nullable=False, server_default="organization"), sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default="true"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "role_permission_policies" not in tables:
        op.create_table("role_permission_policies", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("role_key", sa.String(40), nullable=False), sa.Column("resource_key", sa.String(40), nullable=False), sa.Column("action_key", sa.String(30), nullable=False), sa.Column("effect", sa.String(20), nullable=False, server_default="allow"), sa.Column("conditions_json", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "organization_branches" not in tables:
        op.create_table("organization_branches", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("branch_name", sa.String(150), nullable=False), sa.Column("branch_code", sa.String(30), nullable=False), sa.Column("city", sa.String(100), nullable=True), sa.Column("country", sa.String(60), nullable=True), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "organization_departments" not in tables:
        op.create_table("organization_departments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("department_name", sa.String(100), nullable=False), sa.Column("department_code", sa.String(30), nullable=False), sa.Column("branch_id", sa.Integer(), sa.ForeignKey("organization_branches.id"), nullable=True), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "enterprise_audit_exports" not in tables:
        op.create_table("enterprise_audit_exports", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("export_number", sa.String(60), nullable=False), sa.Column("export_type", sa.String(30), nullable=False, server_default="full"), sa.Column("status", sa.String(20), nullable=False, server_default="pending"), sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("requested_by_name", sa.String(150), nullable=True), sa.Column("filters_json", sa.JSON(), nullable=True), sa.Column("file_path", sa.String(500), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("completed_at", sa.DateTime(), nullable=True), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "enterprise_security_events" not in tables:
        op.create_table("enterprise_security_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("event_type", sa.String(60), nullable=False), sa.Column("severity", sa.String(20), nullable=False, server_default="info"), sa.Column("source", sa.String(40), nullable=False, server_default="system"), sa.Column("safe_summary", sa.Text(), nullable=False), sa.Column("ip_address_hash", sa.String(64), nullable=True), sa.Column("user_agent_summary", sa.String(255), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "enterprise_data_retention_policies" not in tables:
        op.create_table("enterprise_data_retention_policies", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False), sa.Column("resource_key", sa.String(40), nullable=False), sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"), sa.Column("archive_after_days", sa.Integer(), nullable=True), sa.Column("delete_after_days", sa.Integer(), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "enterprise_health_snapshots" not in tables:
        op.create_table("enterprise_health_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("snapshot_key", sa.String(60), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="ok"), sa.Column("summary_json", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    _ci("ix_org_settings_org", "organization_settings", "organization_id")
    _ci("ix_org_settings_key", "organization_settings", "setting_key")
    _ci("ix_org_memberships_org", "organization_memberships", "organization_id")
    _ci("ix_org_memberships_user", "organization_memberships", "user_id")
    _ci("ix_org_memberships_status", "organization_memberships", "membership_status")
    _ci("ix_org_roles_key", "organization_roles", "role_key")
    _ci("ix_role_perms_role", "role_permission_policies", "role_key")
    _ci("ix_role_perms_resource", "role_permission_policies", "resource_key")
    _ci("ix_org_branches_org", "organization_branches", "organization_id")
    _ci("ix_org_depts_org", "organization_departments", "organization_id")
    _ci("ix_ent_audit_exports_num", "enterprise_audit_exports", "export_number")
    _ci("ix_ent_security_type", "enterprise_security_events", "event_type")
    _ci("ix_ent_security_user", "enterprise_security_events", "user_id")
    _ci("ix_ent_retention_org", "enterprise_data_retention_policies", "organization_id")
    _ci("ix_ent_health_key", "enterprise_health_snapshots", "snapshot_key")


def downgrade() -> None:
    for t in ["enterprise_health_snapshots", "enterprise_data_retention_policies", "enterprise_security_events", "enterprise_audit_exports", "organization_departments", "organization_branches", "role_permission_policies", "organization_roles", "organization_memberships", "organization_settings"]:
        op.drop_table(t)
