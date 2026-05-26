"""Add Phase 9 event validation foundation.

Revision ID: phase9_event_validation
Revises: phase8_organization_foundation
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "phase9_event_validation"
down_revision: Union[str, None] = "phase8_organization_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "operational_events" not in table_names:
        op.create_table(
            "operational_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("entity_label", sa.String(length=255), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=150), nullable=True),
            sa.Column("actor_email", sa.String(length=255), nullable=True),
            sa.Column("actor_role", sa.String(length=30), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="user"),
            sa.Column("correlation_id", sa.String(length=120), nullable=True),
            sa.Column("request_id", sa.String(length=120), nullable=True),
            sa.Column("previous_state_json", sa.JSON(), nullable=True),
            sa.Column("new_state_json", sa.JSON(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column(
                "validation_status",
                sa.String(length=40),
                nullable=False,
                server_default="not_checked",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["shipment_id"], ["shipments.id"], name="fk_operational_events_shipment"
            ),
            sa.ForeignKeyConstraint(
                ["actor_user_id"], ["users.id"], name="fk_operational_events_actor"
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_event_type "
        "ON operational_events (event_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_entity_type "
        "ON operational_events (entity_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_entity_id "
        "ON operational_events (entity_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_shipment_id "
        "ON operational_events (shipment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_actor_user_id "
        "ON operational_events (actor_user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_source "
        "ON operational_events (source)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_correlation_id "
        "ON operational_events (correlation_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_validation_status "
        "ON operational_events (validation_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_operational_events_created_at "
        "ON operational_events (created_at)"
    )

    if "rule_definitions" not in table_names:
        op.create_table(
            "rule_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rule_key", sa.String(length=120), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("entity_type", sa.String(length=80), nullable=True),
            sa.Column("event_type", sa.String(length=120), nullable=True),
            sa.Column(
                "severity", sa.String(length=20), nullable=False, server_default="warning"
            ),
            sa.Column(
                "is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column(
                "is_blocking", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
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
            sa.UniqueConstraint("rule_key", name="uq_rule_definitions_rule_key"),
        )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_rule_definitions_rule_key "
        "ON rule_definitions (rule_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rule_definitions_entity_type "
        "ON rule_definitions (entity_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rule_definitions_event_type "
        "ON rule_definitions (event_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_rule_definitions_is_enabled "
        "ON rule_definitions (is_enabled)"
    )

    if "validation_issues" not in table_names:
        op.create_table(
            "validation_issues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.Integer(), nullable=True),
            sa.Column("rule_key", sa.String(length=120), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("entity_label", sa.String(length=255), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column(
                "severity", sa.String(length=20), nullable=False, server_default="warning"
            ),
            sa.Column(
                "status", sa.String(length=20), nullable=False, server_default="open"
            ),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("recommended_action", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_by", sa.Integer(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["event_id"], ["operational_events.id"], name="fk_validation_issues_event"
            ),
            sa.ForeignKeyConstraint(
                ["shipment_id"], ["shipments.id"], name="fk_validation_issues_shipment"
            ),
            sa.ForeignKeyConstraint(
                ["acknowledged_by"], ["users.id"], name="fk_validation_issues_ack_by"
            ),
            sa.ForeignKeyConstraint(
                ["resolved_by"], ["users.id"], name="fk_validation_issues_resolved_by"
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_event_id "
        "ON validation_issues (event_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_rule_key "
        "ON validation_issues (rule_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_entity_type "
        "ON validation_issues (entity_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_entity_id "
        "ON validation_issues (entity_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_shipment_id "
        "ON validation_issues (shipment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_severity "
        "ON validation_issues (severity)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_status "
        "ON validation_issues (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_validation_issues_created_at "
        "ON validation_issues (created_at)"
    )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    if connection.dialect.name == "sqlite":
        return
    if "validation_issues" in table_names:
        op.drop_table("validation_issues")
    if "rule_definitions" in table_names:
        op.drop_table("rule_definitions")
    if "operational_events" in table_names:
        op.drop_table("operational_events")
