"""Phase 15 exception engine + manual review center.

Revision ID: phase15_exception_engine
Revises: phase14_finance_credit
Create Date: 2026-05-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "phase15_exception_engine"
down_revision: Union[str, None] = "phase14_finance_credit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    # --- exception_cases ---
    if "exception_cases" not in tables:
        op.create_table(
            "exception_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("case_number", sa.String(60), nullable=False, unique=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("source", sa.String(60), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("priority", sa.String(10), nullable=False, server_default="p3"),
            sa.Column("status", sa.String(40), nullable=False, server_default="open"),
            sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("dedupe_key", sa.String(255), nullable=True),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_to_name", sa.String(150), nullable=True),
            sa.Column("assigned_to_role", sa.String(30), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("first_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("resolved_by_name", sa.String(150), nullable=True),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column("dismissed_at", sa.DateTime(), nullable=True),
            sa.Column("dismissed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("dismissed_by_name", sa.String(150), nullable=True),
            sa.Column("dismissal_reason", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # --- exception_case_links ---
    if "exception_case_links" not in tables:
        op.create_table(
            "exception_case_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=False),
            sa.Column("linked_type", sa.String(80), nullable=False),
            sa.Column("linked_id", sa.Integer(), nullable=False),
            sa.Column("linked_label", sa.String(255), nullable=True),
            sa.Column("relationship_type", sa.String(40), nullable=False, server_default="related"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- exception_case_comments ---
    if "exception_case_comments" not in tables:
        op.create_table(
            "exception_case_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=False),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("author_name", sa.String(150), nullable=True),
            sa.Column("comment_text", sa.Text(), nullable=False),
            sa.Column("is_internal", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- exception_case_assignments ---
    if "exception_case_assignments" not in tables:
        op.create_table(
            "exception_case_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=False),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_to_name", sa.String(150), nullable=True),
            sa.Column("assigned_to_role", sa.String(30), nullable=True),
            sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_by_name", sa.String(150), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("unassigned_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- exception_case_status_history ---
    if "exception_case_status_history" not in tables:
        op.create_table(
            "exception_case_status_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=False),
            sa.Column("old_status", sa.String(40), nullable=True),
            sa.Column("new_status", sa.String(40), nullable=False),
            sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("changed_by_name", sa.String(150), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- exception_case_escalations ---
    if "exception_case_escalations" not in tables:
        op.create_table(
            "exception_case_escalations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=False),
            sa.Column("from_severity", sa.String(20), nullable=True),
            sa.Column("to_severity", sa.String(20), nullable=False),
            sa.Column("from_priority", sa.String(10), nullable=True),
            sa.Column("to_priority", sa.String(10), nullable=False),
            sa.Column("escalation_reason", sa.Text(), nullable=False),
            sa.Column("escalated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("escalated_by_name", sa.String(150), nullable=True),
            sa.Column("escalated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- exception_case_sla_policies ---
    if "exception_case_sla_policies" not in tables:
        op.create_table(
            "exception_case_sla_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("priority", sa.String(10), nullable=False),
            sa.Column("response_minutes", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("resolution_minutes", sa.Integer(), nullable=False, server_default="480"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- exception_case_watchers ---
    if "exception_case_watchers" not in tables:
        op.create_table(
            "exception_case_watchers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("role", sa.String(30), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # --- Indexes ---
    _create_index("ix_exception_cases_case_number", "exception_cases", "case_number")
    _create_index("ix_exception_cases_category", "exception_cases", "category")
    _create_index("ix_exception_cases_source", "exception_cases", "source")
    _create_index("ix_exception_cases_severity", "exception_cases", "severity")
    _create_index("ix_exception_cases_priority", "exception_cases", "priority")
    _create_index("ix_exception_cases_status", "exception_cases", "status")
    _create_index("ix_exception_cases_dedupe_key", "exception_cases", "dedupe_key")
    _create_index("ix_exception_cases_shipment_id", "exception_cases", "shipment_id")
    _create_index("ix_exception_cases_party_id", "exception_cases", "party_id")
    _create_index("ix_exception_cases_assigned_to_user_id", "exception_cases", "assigned_to_user_id")
    _create_index("ix_exception_cases_due_at", "exception_cases", "due_at")
    _create_index("ix_exception_cases_created_at", "exception_cases", "created_at")
    _create_index("ix_exception_case_links_case_id", "exception_case_links", "exception_case_id")
    _create_index("ix_exception_case_links_linked_type", "exception_case_links", "linked_type")
    _create_index("ix_exception_case_comments_case_id", "exception_case_comments", "exception_case_id")
    _create_index("ix_exception_case_assignments_case_id", "exception_case_assignments", "exception_case_id")
    _create_index("ix_exception_case_status_history_case_id", "exception_case_status_history", "exception_case_id")
    _create_index("ix_exception_case_escalations_case_id", "exception_case_escalations", "exception_case_id")
    _create_index("ix_exception_case_watchers_case_id", "exception_case_watchers", "exception_case_id")
    _create_index("ix_exception_case_sla_policies_category", "exception_case_sla_policies", "category")
    _create_index("ix_exception_case_sla_policies_severity", "exception_case_sla_policies", "severity")


def _create_index(index_name: str, table_name: str, column_name: str) -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})"
    )


def downgrade() -> None:
    op.drop_table("exception_case_watchers")
    op.drop_table("exception_case_sla_policies")
    op.drop_table("exception_case_escalations")
    op.drop_table("exception_case_status_history")
    op.drop_table("exception_case_assignments")
    op.drop_table("exception_case_comments")
    op.drop_table("exception_case_links")
    op.drop_table("exception_cases")
