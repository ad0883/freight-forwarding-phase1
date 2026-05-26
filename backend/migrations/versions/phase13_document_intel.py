"""Phase 13 document intelligence OCR foundation.

Revision ID: phase13_doc_intel
Revises: phase12_document_versions
Create Date: 2026-05-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "phase13_doc_intel"
down_revision: Union[str, None] = "phase12_document_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "document_intelligence_runs" not in tables:
        op.create_table(
            "document_intelligence_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("document_version_id", sa.Integer(), nullable=False),
            sa.Column("document_file_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("document_type", sa.String(length=80), nullable=True),
            sa.Column("run_type", sa.String(length=40), nullable=False, server_default="full"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
            sa.Column("ocr_engine", sa.String(length=80), nullable=True),
            sa.Column("classification_engine", sa.String(length=80), nullable=True),
            sa.Column("extraction_engine", sa.String(length=80), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("triggered_by_user_id", sa.Integer(), nullable=True),
            sa.Column("triggered_by_name", sa.String(length=150), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_doc_intel_runs_version"),
            sa.ForeignKeyConstraint(["document_file_id"], ["document_files.id"], name="fk_doc_intel_runs_file"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_doc_intel_runs_shipment"),
            sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], name="fk_doc_intel_runs_user"),
        )
    _create_index("ix_document_intelligence_runs_document_version_id", "document_intelligence_runs", "document_version_id")
    _create_index("ix_document_intelligence_runs_document_file_id", "document_intelligence_runs", "document_file_id")
    _create_index("ix_document_intelligence_runs_shipment_id", "document_intelligence_runs", "shipment_id")
    _create_index("ix_document_intelligence_runs_status", "document_intelligence_runs", "status")
    _create_index("ix_document_intelligence_runs_started_at", "document_intelligence_runs", "started_at")

    tables = set(inspector.get_table_names())
    if "document_extractions" not in tables:
        op.create_table(
            "document_extractions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("document_version_id", sa.Integer(), nullable=False),
            sa.Column("document_file_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("document_type", sa.String(length=80), nullable=False),
            sa.Column("detected_document_type", sa.String(length=80), nullable=True),
            sa.Column("classification_confidence", sa.Float(), nullable=True),
            sa.Column("ocr_text_preview", sa.Text(), nullable=True),
            sa.Column("ocr_text_hash", sa.String(length=64), nullable=True),
            sa.Column("ocr_char_count", sa.Integer(), nullable=True),
            sa.Column("ocr_page_count", sa.Integer(), nullable=True),
            sa.Column("overall_confidence", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="extracted"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["document_intelligence_runs.id"], name="fk_doc_extractions_run"),
            sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_doc_extractions_version"),
            sa.ForeignKeyConstraint(["document_file_id"], ["document_files.id"], name="fk_doc_extractions_file"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_doc_extractions_shipment"),
        )
    _create_index("ix_document_extractions_run_id", "document_extractions", "run_id")
    _create_index("ix_document_extractions_document_version_id", "document_extractions", "document_version_id")
    _create_index("ix_document_extractions_document_file_id", "document_extractions", "document_file_id")
    _create_index("ix_document_extractions_shipment_id", "document_extractions", "shipment_id")
    _create_index("ix_document_extractions_status", "document_extractions", "status")
    _create_index("ix_document_extractions_overall_confidence", "document_extractions", "overall_confidence")

    tables = set(inspector.get_table_names())
    if "document_extracted_fields" not in tables:
        op.create_table(
            "document_extracted_fields",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("extraction_id", sa.Integer(), nullable=False),
            sa.Column("field_key", sa.String(length=80), nullable=False),
            sa.Column("field_value", sa.Text(), nullable=False),
            sa.Column("normalized_value", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("source_text", sa.Text(), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="candidate"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], name="fk_doc_extracted_fields_extraction"),
        )
    _create_index("ix_document_extracted_fields_extraction_id", "document_extracted_fields", "extraction_id")
    _create_index("ix_document_extracted_fields_field_key", "document_extracted_fields", "field_key")
    _create_index("ix_document_extracted_fields_status", "document_extracted_fields", "status")

    tables = set(inspector.get_table_names())
    if "document_mismatch_results" not in tables:
        op.create_table(
            "document_mismatch_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("extraction_id", sa.Integer(), nullable=False),
            sa.Column("document_version_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("rule_key", sa.String(length=120), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="warning"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
            sa.Column("field_key", sa.String(length=80), nullable=True),
            sa.Column("system_value", sa.Text(), nullable=True),
            sa.Column("extracted_value", sa.Text(), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("recommended_action", sa.Text(), nullable=True),
            sa.Column("validation_issue_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], name="fk_doc_mismatches_extraction"),
            sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_doc_mismatches_version"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_doc_mismatches_shipment"),
            sa.ForeignKeyConstraint(["validation_issue_id"], ["validation_issues.id"], name="fk_doc_mismatches_issue"),
            sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], name="fk_doc_mismatches_resolved_by"),
        )
    _create_index("ix_document_mismatch_results_extraction_id", "document_mismatch_results", "extraction_id")
    _create_index("ix_document_mismatch_results_document_version_id", "document_mismatch_results", "document_version_id")
    _create_index("ix_document_mismatch_results_shipment_id", "document_mismatch_results", "shipment_id")
    _create_index("ix_document_mismatch_results_rule_key", "document_mismatch_results", "rule_key")
    _create_index("ix_document_mismatch_results_severity", "document_mismatch_results", "severity")
    _create_index("ix_document_mismatch_results_status", "document_mismatch_results", "status")

    tables = set(inspector.get_table_names())
    if "document_intelligence_suggestions" not in tables:
        op.create_table(
            "document_intelligence_suggestions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("extraction_id", sa.Integer(), nullable=False),
            sa.Column("document_version_id", sa.Integer(), nullable=False),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("suggestion_type", sa.String(length=80), nullable=False),
            sa.Column("target_entity_type", sa.String(length=80), nullable=False),
            sa.Column("target_entity_id", sa.Integer(), nullable=True),
            sa.Column("suggested_action", sa.String(length=120), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
            sa.Column("payload_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_by_name", sa.String(length=150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], name="fk_doc_intel_suggestions_extraction"),
            sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_doc_intel_suggestions_version"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_doc_intel_suggestions_shipment"),
            sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], name="fk_doc_intel_suggestions_reviewer"),
        )
    _create_index("ix_document_intelligence_suggestions_extraction_id", "document_intelligence_suggestions", "extraction_id")
    _create_index("ix_document_intelligence_suggestions_document_version_id", "document_intelligence_suggestions", "document_version_id")
    _create_index("ix_document_intelligence_suggestions_shipment_id", "document_intelligence_suggestions", "shipment_id")
    _create_index("ix_document_intelligence_suggestions_status", "document_intelligence_suggestions", "status")
    _create_index("ix_document_intelligence_suggestions_type", "document_intelligence_suggestions", "suggestion_type")


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        return
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    for table in (
        "document_intelligence_suggestions",
        "document_mismatch_results",
        "document_extracted_fields",
        "document_extractions",
        "document_intelligence_runs",
    ):
        if table in tables:
            op.drop_table(table)


def _create_index(index_name: str, table_name: str, column_name: str) -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})")
