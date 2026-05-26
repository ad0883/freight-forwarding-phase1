"""Phase 11 container lifecycle + demurrage/detention tables.

Revision ID: phase11_container_lifecycle
Revises: phase9_event_validation
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "phase11_container_lifecycle"
down_revision: Union[str, None] = "phase9_event_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "containers" not in tables:
        op.create_table(
            "containers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("shipment_id", sa.Integer(), nullable=False),
            sa.Column("container_number", sa.String(length=20), nullable=False),
            sa.Column("container_size", sa.String(length=10), nullable=True),
            sa.Column("container_type", sa.String(length=20), nullable=True),
            sa.Column("soc_coc", sa.String(length=10), nullable=True),
            sa.Column("seal_number", sa.String(length=40), nullable=True),
            sa.Column("gross_weight", sa.Numeric(12, 2), nullable=True),
            sa.Column("tare_weight", sa.Numeric(12, 2), nullable=True),
            sa.Column("package_count", sa.Integer(), nullable=True),
            sa.Column(
                "current_status",
                sa.String(length=60),
                nullable=False,
                server_default="CONTAINER_PLANNED",
            ),
            sa.Column("current_location", sa.String(length=150), nullable=True),
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
            sa.Column("planned_date", sa.Date(), nullable=True),
            sa.Column("empty_release_date", sa.Date(), nullable=True),
            sa.Column("empty_pickup_date", sa.Date(), nullable=True),
            sa.Column("factory_arrival_date", sa.Date(), nullable=True),
            sa.Column("stuffing_start_date", sa.Date(), nullable=True),
            sa.Column("stuffing_completed_date", sa.Date(), nullable=True),
            sa.Column("sealed_date", sa.Date(), nullable=True),
            sa.Column("gate_in_date", sa.Date(), nullable=True),
            sa.Column("loaded_on_vessel_date", sa.Date(), nullable=True),
            sa.Column("departed_date", sa.Date(), nullable=True),
            sa.Column("expected_arrival_date", sa.Date(), nullable=True),
            sa.Column("discharge_date", sa.Date(), nullable=True),
            sa.Column("do_received_date", sa.Date(), nullable=True),
            sa.Column("gate_out_date", sa.Date(), nullable=True),
            sa.Column("delivery_date", sa.Date(), nullable=True),
            sa.Column("empty_return_deadline", sa.Date(), nullable=True),
            sa.Column("empty_return_date", sa.Date(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("demurrage_free_days", sa.Integer(), nullable=True),
            sa.Column("detention_free_days", sa.Integer(), nullable=True),
            sa.Column("demurrage_start_date", sa.Date(), nullable=True),
            sa.Column("demurrage_end_date", sa.Date(), nullable=True),
            sa.Column("detention_start_date", sa.Date(), nullable=True),
            sa.Column("detention_end_date", sa.Date(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(
                ["shipment_id"], ["shipments.id"], name="fk_containers_shipment"
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_containers_shipment_id "
        "ON containers (shipment_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_containers_container_number "
        "ON containers (container_number)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_containers_current_status "
        "ON containers (current_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_containers_empty_return_deadline "
        "ON containers (empty_return_deadline)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_containers_discharge_date "
        "ON containers (discharge_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_containers_delivery_date "
        "ON containers (delivery_date)"
    )

    if "container_events" not in tables:
        op.create_table(
            "container_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("container_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=60), nullable=False),
            sa.Column("event_date", sa.Date(), nullable=True),
            sa.Column("location", sa.String(length=150), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="user"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["container_id"], ["containers.id"], name="fk_container_events_container"
            ),
            sa.ForeignKeyConstraint(
                ["shipment_id"], ["shipments.id"], name="fk_container_events_shipment"
            ),
            sa.ForeignKeyConstraint(
                ["actor_user_id"], ["users.id"], name="fk_container_events_actor"
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_container_events_container_id "
        "ON container_events (container_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_container_events_event_type "
        "ON container_events (event_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_container_events_event_date "
        "ON container_events (event_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_container_events_created_at "
        "ON container_events (created_at)"
    )

    if "demurrage_detention_rules" not in tables:
        op.create_table(
            "demurrage_detention_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("rule_type", sa.String(length=20), nullable=False),
            sa.Column("shipment_direction", sa.String(length=20), nullable=True),
            sa.Column("container_size", sa.String(length=10), nullable=True),
            sa.Column("container_type", sa.String(length=20), nullable=True),
            sa.Column("free_days", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("rate_per_day", sa.Numeric(12, 2), nullable=True),
            sa.Column("slab_json", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(length=60), nullable=True),
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
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_demurrage_detention_rules_rule_type "
        "ON demurrage_detention_rules (rule_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_demurrage_detention_rules_is_active "
        "ON demurrage_detention_rules (is_active)"
    )

    for table in ("container_demurrage_records", "container_detention_records"):
        if table not in tables:
            op.create_table(
                table,
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column("container_id", sa.Integer(), nullable=False),
                sa.Column("shipment_id", sa.Integer(), nullable=False),
                sa.Column("start_date", sa.Date(), nullable=True),
                sa.Column("end_date", sa.Date(), nullable=True),
                sa.Column("free_days", sa.Integer(), nullable=False, server_default="0"),
                sa.Column("days_used", sa.Integer(), nullable=False, server_default="0"),
                sa.Column(
                    "chargeable_days", sa.Integer(), nullable=False, server_default="0"
                ),
                sa.Column(
                    "currency", sa.String(length=10), nullable=False, server_default="INR"
                ),
                sa.Column(
                    "estimated_amount",
                    sa.Numeric(12, 2),
                    nullable=False,
                    server_default="0",
                ),
                sa.Column(
                    "status", sa.String(length=30), nullable=False, server_default="estimated"
                ),
                sa.Column("source", sa.String(length=60), nullable=True),
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
                sa.ForeignKeyConstraint(
                    ["container_id"], ["containers.id"], name=f"fk_{table}_container"
                ),
                sa.ForeignKeyConstraint(
                    ["shipment_id"], ["shipments.id"], name=f"fk_{table}_shipment"
                ),
            )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_container_id "
            f"ON {table} (container_id)"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_status "
            f"ON {table} (status)"
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        return
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    for table in (
        "container_detention_records",
        "container_demurrage_records",
        "demurrage_detention_rules",
        "container_events",
        "containers",
    ):
        if table in tables:
            op.drop_table(table)
