"""Phase 22 Control Tower Dashboard.

Revision ID: phase22_control_tower
Revises: phase21_tracking_adapters
Create Date: 2026-05-28
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase22_control_tower"
down_revision: Union[str, None] = "phase21_tracking_adapters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ci(n, t, c):
    op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "control_tower_saved_views" not in tables:
        op.create_table(
            "control_tower_saved_views",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
            sa.Column("filters_json", sa.JSON(), nullable=True),
            sa.Column("layout_json", sa.JSON(), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "control_tower_snapshots" not in tables:
        op.create_table(
            "control_tower_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("snapshot_key", sa.String(60), nullable=False),
            sa.Column("period_start", sa.DateTime(), nullable=True),
            sa.Column("period_end", sa.DateTime(), nullable=True),
            sa.Column("scope", sa.String(30), nullable=False, server_default="global"),
            sa.Column("summary_json", sa.JSON(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "control_tower_widget_preferences" not in tables:
        op.create_table(
            "control_tower_widget_preferences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("widget_key", sa.String(60), nullable=False),
            sa.Column("is_visible", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("position_index", sa.Integer(), nullable=True),
            sa.Column("settings_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "control_tower_activity_logs" not in tables:
        op.create_table(
            "control_tower_activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("activity_type", sa.String(60), nullable=False),
            sa.Column("safe_summary", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    _ci("ix_ct_saved_views_user", "control_tower_saved_views", "user_id")
    _ci("ix_ct_snapshots_key", "control_tower_snapshots", "snapshot_key")
    _ci("ix_ct_snapshots_scope", "control_tower_snapshots", "scope")
    _ci("ix_ct_widget_prefs_user", "control_tower_widget_preferences", "user_id")
    _ci("ix_ct_activity_user", "control_tower_activity_logs", "user_id")


def downgrade() -> None:
    for t in ["control_tower_activity_logs", "control_tower_widget_preferences",
              "control_tower_snapshots", "control_tower_saved_views"]:
        op.drop_table(t)
