"""Phase 18 exporter/importer portal.

Revision ID: phase18_customer_portal
Revises: phase17_bot_learning
Create Date: 2026-05-28
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase18_customer_portal"
down_revision: Union[str, None] = "phase17_bot_learning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _ci(n, t, c): op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")

def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "portal_accounts" not in tables:
        op.create_table("portal_accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=False),
            sa.Column("account_type", sa.String(30), nullable=False, server_default="exporter"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("company_name", sa.String(255), nullable=True),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_party_links" not in tables:
        op.create_table("portal_party_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=False),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=False),
            sa.Column("relationship_type", sa.String(40), nullable=False, server_default="customer"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_shipment_access" not in tables:
        op.create_table("portal_shipment_access",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=False),
            sa.Column("access_level", sa.String(30), nullable=False, server_default="view_only"),
            sa.Column("can_view_documents", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("can_upload_documents", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("can_view_finance", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("can_raise_requests", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("can_comment", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("granted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("granted_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_document_access" not in tables:
        op.create_table("portal_document_access",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=False),
            sa.Column("document_version_id", sa.Integer(), sa.ForeignKey("document_versions.id"), nullable=True),
            sa.Column("document_type", sa.String(80), nullable=True),
            sa.Column("access_type", sa.String(20), nullable=False, server_default="view"),
            sa.Column("can_download", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("can_upload_new_version", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("visible_to_customer", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("granted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("granted_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_requests" not in tables:
        op.create_table("portal_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("request_number", sa.String(60), nullable=False, unique=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("request_type", sa.String(40), nullable=False, server_default="other"),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(10), nullable=False, server_default="p3"),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_to_name", sa.String(150), nullable=True),
            sa.Column("linked_exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True),
            sa.Column("linked_approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("resolved_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_request_comments" not in tables:
        op.create_table("portal_request_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_request_id", sa.Integer(), sa.ForeignKey("portal_requests.id"), nullable=False),
            sa.Column("author_type", sa.String(20), nullable=False, server_default="portal_user"),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("author_name", sa.String(150), nullable=True),
            sa.Column("comment_text", sa.Text(), nullable=False),
            sa.Column("visible_to_customer", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_notifications" not in tables:
        op.create_table("portal_notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("notification_type", sa.String(40), nullable=False, server_default="system"),
            sa.Column("status", sa.String(20), nullable=False, server_default="unread"),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_activity_logs" not in tables:
        op.create_table("portal_activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("activity_type", sa.String(60), nullable=False),
            sa.Column("safe_summary", sa.Text(), nullable=False),
            sa.Column("ip_address_hash", sa.String(64), nullable=True),
            sa.Column("user_agent_summary", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "portal_preferences" not in tables:
        op.create_table("portal_preferences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("portal_account_id", sa.Integer(), sa.ForeignKey("portal_accounts.id"), nullable=False),
            sa.Column("preference_key", sa.String(120), nullable=False),
            sa.Column("preference_value_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    _ci("ix_portal_accounts_email", "portal_accounts", "email")
    _ci("ix_portal_accounts_user_id", "portal_accounts", "user_id")
    _ci("ix_portal_accounts_status", "portal_accounts", "status")
    _ci("ix_portal_party_links_account", "portal_party_links", "portal_account_id")
    _ci("ix_portal_party_links_party", "portal_party_links", "party_id")
    _ci("ix_portal_shipment_access_account", "portal_shipment_access", "portal_account_id")
    _ci("ix_portal_shipment_access_shipment", "portal_shipment_access", "shipment_id")
    _ci("ix_portal_document_access_shipment", "portal_document_access", "shipment_id")
    _ci("ix_portal_requests_account", "portal_requests", "portal_account_id")
    _ci("ix_portal_requests_shipment", "portal_requests", "shipment_id")
    _ci("ix_portal_requests_status", "portal_requests", "status")
    _ci("ix_portal_request_comments_request", "portal_request_comments", "portal_request_id")
    _ci("ix_portal_notifications_account", "portal_notifications", "portal_account_id")
    _ci("ix_portal_notifications_status", "portal_notifications", "status")
    _ci("ix_portal_activity_logs_account", "portal_activity_logs", "portal_account_id")
    _ci("ix_portal_preferences_account", "portal_preferences", "portal_account_id")

def downgrade() -> None:
    for t in ["portal_preferences", "portal_activity_logs", "portal_notifications", "portal_request_comments", "portal_requests", "portal_document_access", "portal_shipment_access", "portal_party_links", "portal_accounts"]:
        op.drop_table(t)
