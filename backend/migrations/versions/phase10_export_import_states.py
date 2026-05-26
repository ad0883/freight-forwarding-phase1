"""Add Phase 10 export/import workflow state-machine foundation.

Revision ID: phase10_export_import_states
Revises: phase9_event_validation
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "phase10_export_import_states"
down_revision: Union[str, None] = "phase9_event_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SHIPMENT_COLUMNS = [
    ("workflow_state", sa.String(length=80), True, None),
    ("workflow_state_updated_at", sa.DateTime(), True, None),
    ("workflow_state_reason", sa.Text(), True, None),
    ("manual_review_required", sa.Boolean(), False, sa.false()),
    ("manual_review_reason", sa.Text(), True, None),
]


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "workflow_state_definitions" not in table_names:
        op.create_table(
            "workflow_state_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("flow_type", sa.String(length=20), nullable=False),
            sa.Column("state_key", sa.String(length=80), nullable=False),
            sa.Column("state_label", sa.String(length=180), nullable=False),
            sa.Column("state_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_initial", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "flow_type", "state_key", name="uq_workflow_state_def_flow_state"
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_state_def_flow_type "
        "ON workflow_state_definitions (flow_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_state_def_state_key "
        "ON workflow_state_definitions (state_key)"
    )

    if "workflow_transition_definitions" not in table_names:
        op.create_table(
            "workflow_transition_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("flow_type", sa.String(length=20), nullable=False),
            sa.Column("transition_key", sa.String(length=160), nullable=False),
            sa.Column("from_state", sa.String(length=80), nullable=True),
            sa.Column("to_state", sa.String(length=80), nullable=False),
            sa.Column("label", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("requires_reason", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "flow_type", "transition_key", name="uq_workflow_transition_def_key"
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_transition_def_flow_type "
        "ON workflow_transition_definitions (flow_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_transition_def_from_state "
        "ON workflow_transition_definitions (from_state)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_transition_def_to_state "
        "ON workflow_transition_definitions (to_state)"
    )

    if "workflow_transition_logs" not in table_names:
        op.create_table(
            "workflow_transition_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("shipment_id", sa.Integer(), nullable=False),
            sa.Column("flow_type", sa.String(length=20), nullable=False),
            sa.Column("transition_key", sa.String(length=160), nullable=True),
            sa.Column("from_state", sa.String(length=80), nullable=True),
            sa.Column("to_state", sa.String(length=80), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=150), nullable=True),
            sa.Column("actor_email", sa.String(length=255), nullable=True),
            sa.Column("actor_role", sa.String(length=30), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="user"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="requested"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column(
                "validation_status",
                sa.String(length=40),
                nullable=False,
                server_default="not_checked",
            ),
            sa.Column("event_id", sa.Integer(), nullable=True),
            sa.Column("validation_issue_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["shipment_id"], ["shipments.id"], name="fk_workflow_logs_shipment"
            ),
            sa.ForeignKeyConstraint(
                ["actor_user_id"], ["users.id"], name="fk_workflow_logs_actor"
            ),
            sa.ForeignKeyConstraint(
                ["event_id"], ["operational_events.id"], name="fk_workflow_logs_event"
            ),
            sa.ForeignKeyConstraint(
                ["validation_issue_id"],
                ["validation_issues.id"],
                name="fk_workflow_logs_issue",
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_logs_shipment_id "
        "ON workflow_transition_logs (shipment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_logs_flow_type "
        "ON workflow_transition_logs (flow_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_logs_status "
        "ON workflow_transition_logs (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_logs_to_state "
        "ON workflow_transition_logs (to_state)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_logs_created_at "
        "ON workflow_transition_logs (created_at)"
    )

    if "shipments" in table_names:
        existing_columns = {column["name"] for column in inspector.get_columns("shipments")}
        for name, column_type, nullable, default in SHIPMENT_COLUMNS:
            if name in existing_columns:
                continue
            op.add_column(
                "shipments",
                sa.Column(name, column_type, nullable=nullable, server_default=default),
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_shipments_workflow_state "
            "ON shipments (workflow_state)"
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    if connection.dialect.name == "sqlite":
        return
    if "workflow_transition_logs" in table_names:
        op.drop_table("workflow_transition_logs")
    if "workflow_transition_definitions" in table_names:
        op.drop_table("workflow_transition_definitions")
    if "workflow_state_definitions" in table_names:
        op.drop_table("workflow_state_definitions")
    if "shipments" in table_names:
        existing_columns = {column["name"] for column in inspector.get_columns("shipments")}
        for name, _column_type, _nullable, _default in SHIPMENT_COLUMNS:
            if name in existing_columns:
                op.drop_column("shipments", name)
