"""Phase 12 document upload and versioning foundation.

Revision ID: phase12_document_versions
Revises: phase11_main_merge
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "phase12_document_versions"
down_revision: Union[str, None] = "phase11_main_merge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "document_files" not in tables:
        op.create_table(
            "document_files",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("document_id", sa.Integer(), nullable=True),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("sanitized_filename", sa.String(length=255), nullable=False),
            sa.Column("content_type", sa.String(length=120), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("storage_backend", sa.String(length=30), nullable=False, server_default="database"),
            sa.Column("storage_key", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("uploaded_by", sa.Integer(), nullable=True),
            sa.Column("uploaded_by_name", sa.String(length=150), nullable=True),
            sa.Column(
                "uploaded_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_document_files_org"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_document_files_shipment"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_files_document"),
            sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name="fk_document_files_uploaded_by"),
        )
    _create_index("ix_document_files_organization_id", "document_files", "organization_id")
    _create_index("ix_document_files_shipment_id", "document_files", "shipment_id")
    _create_index("ix_document_files_document_id", "document_files", "document_id")
    _create_index("ix_document_files_sha256", "document_files", "sha256")
    _create_index("ix_document_files_status", "document_files", "status")
    _create_index("ix_document_files_uploaded_at", "document_files", "uploaded_at")

    tables = set(inspector.get_table_names())
    if "document_file_blobs" not in tables:
        op.create_table(
            "document_file_blobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_file_id", sa.Integer(), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["document_file_id"], ["document_files.id"], name="fk_document_file_blobs_file"
            ),
            sa.UniqueConstraint("document_file_id", name="uq_document_file_blobs_file_id"),
        )
    _create_index("ix_document_file_blobs_document_file_id", "document_file_blobs", "document_file_id")

    tables = set(inspector.get_table_names())
    if "document_versions" not in tables:
        op.create_table(
            "document_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=True),
            sa.Column("document_type", sa.String(length=80), nullable=False),
            sa.Column("document_file_id", sa.Integer(), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("version_label", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("review_status", sa.String(length=30), nullable=False, server_default="pending_review"),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("replaces_version_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_by_name", sa.String(length=150), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
            sa.Column("reviewed_by_name", sa.String(length=150), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("review_notes", sa.Text(), nullable=True),
            sa.Column("archived_by", sa.Integer(), nullable=True),
            sa.Column("archived_by_name", sa.String(length=150), nullable=True),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.Column("archive_reason", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_document_versions_org"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_document_versions_shipment"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_versions_document"),
            sa.ForeignKeyConstraint(
                ["document_file_id"], ["document_files.id"], name="fk_document_versions_file"
            ),
            sa.ForeignKeyConstraint(
                ["replaces_version_id"], ["document_versions.id"], name="fk_document_versions_replaces"
            ),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_document_versions_created_by"),
            sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_document_versions_reviewed_by"),
            sa.ForeignKeyConstraint(["archived_by"], ["users.id"], name="fk_document_versions_archived_by"),
            sa.UniqueConstraint(
                "shipment_id",
                "document_id",
                "document_type",
                "version_no",
                name="uq_document_versions_version_no",
            ),
        )
    _create_index("ix_document_versions_organization_id", "document_versions", "organization_id")
    _create_index("ix_document_versions_shipment_id", "document_versions", "shipment_id")
    _create_index("ix_document_versions_document_id", "document_versions", "document_id")
    _create_index("ix_document_versions_document_type", "document_versions", "document_type")
    _create_index("ix_document_versions_document_file_id", "document_versions", "document_file_id")
    _create_index("ix_document_versions_status", "document_versions", "status")
    _create_index("ix_document_versions_review_status", "document_versions", "review_status")
    _create_index("ix_document_versions_is_current", "document_versions", "is_current")
    _create_index("ix_document_versions_created_at", "document_versions", "created_at")

    _add_document_columns(connection)

    tables = set(inspector.get_table_names())
    if "document_version_events" not in tables:
        op.create_table(
            "document_version_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_version_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=150), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["document_version_id"], ["document_versions.id"], name="fk_document_version_events_version"
            ),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_document_version_events_shipment"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_version_events_document"),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_document_version_events_actor"),
        )
    _create_index("ix_document_version_events_document_version_id", "document_version_events", "document_version_id")
    _create_index("ix_document_version_events_shipment_id", "document_version_events", "shipment_id")
    _create_index("ix_document_version_events_event_type", "document_version_events", "event_type")
    _create_index("ix_document_version_events_created_at", "document_version_events", "created_at")

    tables = set(inspector.get_table_names())
    if "document_access_logs" not in tables:
        op.create_table(
            "document_access_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_file_id", sa.Integer(), nullable=False),
            sa.Column("document_version_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=150), nullable=True),
            sa.Column("action", sa.String(length=40), nullable=False, server_default="download"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["document_file_id"], ["document_files.id"], name="fk_document_access_logs_file"),
            sa.ForeignKeyConstraint(
                ["document_version_id"], ["document_versions.id"], name="fk_document_access_logs_version"
            ),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_document_access_logs_shipment"),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_document_access_logs_actor"),
        )
    _create_index("ix_document_access_logs_document_file_id", "document_access_logs", "document_file_id")
    _create_index("ix_document_access_logs_document_version_id", "document_access_logs", "document_version_id")
    _create_index("ix_document_access_logs_shipment_id", "document_access_logs", "shipment_id")
    _create_index("ix_document_access_logs_action", "document_access_logs", "action")
    _create_index("ix_document_access_logs_created_at", "document_access_logs", "created_at")


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        return
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    for table in (
        "document_access_logs",
        "document_version_events",
        "document_versions",
        "document_file_blobs",
        "document_files",
    ):
        if table in tables:
            op.drop_table(table)
    if "documents" in tables:
        columns = {column["name"] for column in inspector.get_columns("documents")}
        for column_name in ("latest_uploaded_at", "uploaded_file_count", "current_version_id"):
            if column_name in columns:
                op.drop_column("documents", column_name)


def _add_document_columns(connection) -> None:
    inspector = inspect(connection)
    if "documents" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("documents")}
    if "current_version_id" not in columns:
        op.add_column("documents", sa.Column("current_version_id", sa.Integer(), nullable=True))
    if "uploaded_file_count" not in columns:
        op.add_column(
            "documents",
            sa.Column("uploaded_file_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if "latest_uploaded_at" not in columns:
        op.add_column("documents", sa.Column("latest_uploaded_at", sa.DateTime(), nullable=True))
    _create_index("ix_documents_current_version_id", "documents", "current_version_id")


def _create_index(index_name: str, table_name: str, column_name: str) -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})"
    )
