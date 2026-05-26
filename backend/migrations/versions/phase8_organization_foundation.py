"""Add Phase 8 organization foundation.

Revision ID: phase8_organization_foundation
Revises: phase8_baseline
Create Date: 2026-05-26
"""

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = "phase8_organization_foundation"
down_revision: Union[str, None] = "phase8_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORGANIZATION_NAME = "Default Freight Organization"
DEFAULT_ORGANIZATION_SLUG = "default-freight-organization"
DEFAULT_ORGANIZATION_TYPE = "freight_forwarder"


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "organizations" not in table_names:
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("org_type", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("slug", name="uq_organizations_slug"),
        )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_slug ON organizations (slug)")

    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "organization_id" not in user_columns:
            op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
            if connection.dialect.name != "sqlite":
                op.create_foreign_key(
                    "fk_users_organization_id_organizations",
                    "users",
                    "organizations",
                    ["organization_id"],
                    ["id"],
                )
        op.execute("CREATE INDEX IF NOT EXISTS ix_users_organization_id ON users (organization_id)")

    default_org_id = _ensure_default_organization(connection)
    if "users" in table_names:
        connection.execute(
            text(
                "UPDATE users "
                "SET organization_id = :organization_id "
                "WHERE organization_id IS NULL"
            ),
            {"organization_id": default_org_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    if "users" in table_names:
        op.execute("DROP INDEX IF EXISTS ix_users_organization_id")
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if connection.dialect.name != "sqlite" and "organization_id" in user_columns:
            op.drop_column("users", "organization_id")
    if "organizations" in table_names and connection.dialect.name != "sqlite":
        op.drop_table("organizations")


def _ensure_default_organization(connection) -> int:
    now = datetime.utcnow()
    connection.execute(
        text(
            "INSERT INTO organizations (name, slug, org_type, is_active, created_at, updated_at) "
            "SELECT :name, :slug, :org_type, :is_active, :created_at, :updated_at "
            "WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE slug = :slug)"
        ),
        {
            "name": DEFAULT_ORGANIZATION_NAME,
            "slug": DEFAULT_ORGANIZATION_SLUG,
            "org_type": DEFAULT_ORGANIZATION_TYPE,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    default_org_id = connection.execute(
        text("SELECT id FROM organizations WHERE slug = :slug"),
        {"slug": DEFAULT_ORGANIZATION_SLUG},
    ).scalar_one()
    return int(default_org_id)
