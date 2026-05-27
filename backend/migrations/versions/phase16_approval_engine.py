"""Phase 16 approval engine + HOD bot governance.

Revision ID: phase16_approval_engine
Revises: phase15_exception_engine
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase16_approval_engine"
down_revision: Union[str, None] = "phase15_exception_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ci(name: str, table: str, col: str) -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "approval_requests" not in tables:
        op.create_table("approval_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("approval_number", sa.String(60), nullable=False, unique=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("approval_type", sa.String(60), nullable=False),
            sa.Column("source", sa.String(60), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("priority", sa.String(10), nullable=False, server_default="p3"),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True),
            sa.Column("requested_action", sa.String(255), nullable=False),
            sa.Column("requested_payload_json", sa.JSON(), nullable=True),
            sa.Column("safe_summary_json", sa.JSON(), nullable=True),
            sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("requested_by_name", sa.String(150), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_to_name", sa.String(150), nullable=True),
            sa.Column("assigned_to_role", sa.String(30), nullable=True),
            sa.Column("current_step_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("required_steps", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("rejected_at", sa.DateTime(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("final_decision_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("final_decision_by_name", sa.String(150), nullable=True),
            sa.Column("final_decision_notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "approval_steps" not in tables:
        op.create_table("approval_steps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=False),
            sa.Column("step_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("approver_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approver_name", sa.String(150), nullable=True),
            sa.Column("approver_role", sa.String(30), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("decision", sa.String(30), nullable=True),
            sa.Column("decision_notes", sa.Text(), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "approval_policies" not in tables:
        op.create_table("approval_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("approval_type", sa.String(60), nullable=False),
            sa.Column("risk_level", sa.String(20), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("required_approver_role", sa.String(30), nullable=False, server_default="ADMIN"),
            sa.Column("required_steps", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("maker_checker_required", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("admin_override_allowed", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("auto_expire_hours", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "approval_policy_rules" not in tables:
        op.create_table("approval_policy_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("approval_policy_id", sa.Integer(), sa.ForeignKey("approval_policies.id"), nullable=False),
            sa.Column("rule_key", sa.String(120), nullable=False),
            sa.Column("condition_json", sa.JSON(), nullable=True),
            sa.Column("effect", sa.String(40), nullable=False, server_default="require_approval"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "approval_request_evidence" not in tables:
        op.create_table("approval_request_evidence",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=False),
            sa.Column("evidence_type", sa.String(60), nullable=False),
            sa.Column("linked_type", sa.String(80), nullable=True),
            sa.Column("linked_id", sa.Integer(), nullable=True),
            sa.Column("label", sa.String(255), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "approval_action_locks" not in tables:
        op.create_table("approval_action_locks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("entity_type", sa.String(80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("action_key", sa.String(120), nullable=False),
            sa.Column("lock_reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            sa.Column("released_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("released_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "approval_delegations" not in tables:
        op.create_table("approval_delegations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("delegator_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("delegate_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role_scope", sa.String(30), nullable=True),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("ends_at", sa.DateTime(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "approval_overrides" not in tables:
        op.create_table("approval_overrides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("action_key", sa.String(120), nullable=False),
            sa.Column("override_reason", sa.Text(), nullable=False),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("overridden_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("overridden_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "bot_governance_actions" not in tables:
        op.create_table("bot_governance_actions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_name", sa.String(120), nullable=True),
            sa.Column("action_type", sa.String(60), nullable=False),
            sa.Column("source", sa.String(60), nullable=False, server_default="system"),
            sa.Column("status", sa.String(30), nullable=False, server_default="proposed"),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("proposed_payload_json", sa.JSON(), nullable=True),
            sa.Column("safe_summary_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # Indexes
    _ci("ix_approval_requests_number", "approval_requests", "approval_number")
    _ci("ix_approval_requests_type", "approval_requests", "approval_type")
    _ci("ix_approval_requests_status", "approval_requests", "status")
    _ci("ix_approval_requests_risk", "approval_requests", "risk_level")
    _ci("ix_approval_requests_shipment", "approval_requests", "shipment_id")
    _ci("ix_approval_requests_assigned", "approval_requests", "assigned_to_user_id")
    _ci("ix_approval_requests_due", "approval_requests", "due_at")
    _ci("ix_approval_steps_request", "approval_steps", "approval_request_id")
    _ci("ix_approval_policies_type", "approval_policies", "approval_type")
    _ci("ix_approval_policies_risk", "approval_policies", "risk_level")
    _ci("ix_approval_policy_rules_policy", "approval_policy_rules", "approval_policy_id")
    _ci("ix_approval_evidence_request", "approval_request_evidence", "approval_request_id")
    _ci("ix_approval_locks_entity", "approval_action_locks", "entity_type")
    _ci("ix_approval_locks_status", "approval_action_locks", "status")
    _ci("ix_approval_locks_action", "approval_action_locks", "action_key")
    _ci("ix_approval_delegations_delegator", "approval_delegations", "delegator_user_id")
    _ci("ix_approval_overrides_request", "approval_overrides", "approval_request_id")
    _ci("ix_bot_governance_status", "bot_governance_actions", "status")
    _ci("ix_bot_governance_type", "bot_governance_actions", "action_type")
    _ci("ix_bot_governance_shipment", "bot_governance_actions", "shipment_id")


def downgrade() -> None:
    op.drop_table("bot_governance_actions")
    op.drop_table("approval_overrides")
    op.drop_table("approval_delegations")
    op.drop_table("approval_action_locks")
    op.drop_table("approval_request_evidence")
    op.drop_table("approval_policy_rules")
    op.drop_table("approval_policies")
    op.drop_table("approval_steps")
    op.drop_table("approval_requests")
