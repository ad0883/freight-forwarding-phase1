"""Phase 14 finance + credit-control foundation.

Revision ID: phase14_finance_credit
Revises: phase13_doc_intel
Create Date: 2026-05-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "phase14_finance_credit"
down_revision: Union[str, None] = "phase13_doc_intel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index(index_name: str, table_name: str, column_name: str) -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})"
    )


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "finance_invoices" not in tables:
        op.create_table(
            "finance_invoices",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("party_id", sa.Integer(), nullable=True),
            sa.Column("invoice_number", sa.String(length=120), nullable=True),
            sa.Column("invoice_type", sa.String(length=40), nullable=False, server_default="customer_invoice"),
            sa.Column("direction", sa.String(length=20), nullable=False, server_default="receivable"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("subtotal_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("outstanding_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("invoice_date", sa.Date(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("credit_days", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="manual"),
            sa.Column("linked_charge_id", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_name", sa.String(length=150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_finance_invoices_org"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_finance_invoices_shipment"),
            sa.ForeignKeyConstraint(["party_id"], ["parties.id"], name="fk_finance_invoices_party"),
            sa.ForeignKeyConstraint(["linked_charge_id"], ["charges.id"], name="fk_finance_invoices_charge"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_finance_invoices_user"),
        )
    _create_index("ix_finance_invoices_organization_id", "finance_invoices", "organization_id")
    _create_index("ix_finance_invoices_shipment_id", "finance_invoices", "shipment_id")
    _create_index("ix_finance_invoices_party_id", "finance_invoices", "party_id")
    _create_index("ix_finance_invoices_invoice_number", "finance_invoices", "invoice_number")
    _create_index("ix_finance_invoices_status", "finance_invoices", "status")
    _create_index("ix_finance_invoices_direction", "finance_invoices", "direction")
    _create_index("ix_finance_invoices_due_date", "finance_invoices", "due_date")

    tables = set(inspector.get_table_names())
    if "finance_invoice_lines" not in tables:
        op.create_table(
            "finance_invoice_lines",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), nullable=False),
            sa.Column("charge_id", sa.Integer(), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="1"),
            sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("tax_code", sa.String(length=40), nullable=True),
            sa.Column("tax_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["invoice_id"], ["finance_invoices.id"], name="fk_finance_invoice_lines_invoice"),
            sa.ForeignKeyConstraint(["charge_id"], ["charges.id"], name="fk_finance_invoice_lines_charge"),
        )
    _create_index("ix_finance_invoice_lines_invoice_id", "finance_invoice_lines", "invoice_id")
    _create_index("ix_finance_invoice_lines_charge_id", "finance_invoice_lines", "charge_id")

    tables = set(inspector.get_table_names())
    if "finance_payments" not in tables:
        op.create_table(
            "finance_payments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("party_id", sa.Integer(), nullable=True),
            sa.Column("payment_type", sa.String(length=40), nullable=False, server_default="receipt"),
            sa.Column("direction", sa.String(length=20), nullable=False, server_default="inbound"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="posted"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("unallocated_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("payment_date", sa.Date(), nullable=True),
            sa.Column("reference_number", sa.String(length=120), nullable=True),
            sa.Column("method", sa.String(length=40), nullable=True),
            sa.Column("bank_name", sa.String(length=120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_name", sa.String(length=150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_finance_payments_org"),
            sa.ForeignKeyConstraint(["party_id"], ["parties.id"], name="fk_finance_payments_party"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_finance_payments_user"),
        )
    _create_index("ix_finance_payments_organization_id", "finance_payments", "organization_id")
    _create_index("ix_finance_payments_party_id", "finance_payments", "party_id")
    _create_index("ix_finance_payments_status", "finance_payments", "status")
    _create_index("ix_finance_payments_direction", "finance_payments", "direction")

    tables = set(inspector.get_table_names())
    if "finance_payment_allocations" not in tables:
        op.create_table(
            "finance_payment_allocations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("payment_id", sa.Integer(), nullable=False),
            sa.Column("invoice_id", sa.Integer(), nullable=True),
            sa.Column("charge_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("allocated_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("allocated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("allocated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("allocated_by_name", sa.String(length=150), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["payment_id"], ["finance_payments.id"], name="fk_finance_alloc_payment"),
            sa.ForeignKeyConstraint(["invoice_id"], ["finance_invoices.id"], name="fk_finance_alloc_invoice"),
            sa.ForeignKeyConstraint(["charge_id"], ["charges.id"], name="fk_finance_alloc_charge"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_finance_alloc_shipment"),
            sa.ForeignKeyConstraint(["allocated_by_user_id"], ["users.id"], name="fk_finance_alloc_user"),
        )
    _create_index("ix_finance_payment_allocations_payment_id", "finance_payment_allocations", "payment_id")
    _create_index("ix_finance_payment_allocations_invoice_id", "finance_payment_allocations", "invoice_id")
    _create_index("ix_finance_payment_allocations_charge_id", "finance_payment_allocations", "charge_id")
    _create_index("ix_finance_payment_allocations_shipment_id", "finance_payment_allocations", "shipment_id")

    tables = set(inspector.get_table_names())
    if "party_credit_profiles" not in tables:
        op.create_table(
            "party_credit_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("party_id", sa.Integer(), nullable=False),
            sa.Column("credit_limit", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("credit_currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("credit_days", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_credit_allowed", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("hold_on_overdue", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("hold_on_limit_exceeded", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("warning_threshold_percent", sa.Integer(), nullable=False, server_default="80"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_party_credit_profile_org"),
            sa.ForeignKeyConstraint(["party_id"], ["parties.id"], name="fk_party_credit_profile_party"),
        )
    _create_index("ix_party_credit_profiles_party_id", "party_credit_profiles", "party_id")
    _create_index("ix_party_credit_profiles_status", "party_credit_profiles", "status")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_party_credit_profiles_party "
        "ON party_credit_profiles (party_id)"
    )

    tables = set(inspector.get_table_names())
    if "credit_hold_records" not in tables:
        op.create_table(
            "credit_hold_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("party_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("hold_type", sa.String(length=60), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="warning"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("trigger_source", sa.String(length=60), nullable=False, server_default="system"),
            sa.Column("current_outstanding", sa.Numeric(14, 2), nullable=True),
            sa.Column("credit_limit", sa.Numeric(14, 2), nullable=True),
            sa.Column("overdue_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("blocked_action", sa.String(length=60), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_name", sa.String(length=150), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("resolved_by_name", sa.String(length=150), nullable=True),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["party_id"], ["parties.id"], name="fk_credit_hold_party"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_credit_hold_shipment"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_credit_hold_created_by"),
            sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], name="fk_credit_hold_resolved_by"),
        )
    _create_index("ix_credit_hold_records_party_id", "credit_hold_records", "party_id")
    _create_index("ix_credit_hold_records_shipment_id", "credit_hold_records", "shipment_id")
    _create_index("ix_credit_hold_records_hold_type", "credit_hold_records", "hold_type")
    _create_index("ix_credit_hold_records_status", "credit_hold_records", "status")
    _create_index("ix_credit_hold_records_blocked_action", "credit_hold_records", "blocked_action")

    tables = set(inspector.get_table_names())
    if "finance_aging_snapshots" not in tables:
        op.create_table(
            "finance_aging_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("party_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("direction", sa.String(length=20), nullable=False, server_default="receivable"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("not_due_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("bucket_0_30", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("bucket_31_60", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("bucket_61_90", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("bucket_90_plus", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("total_outstanding", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("overdue_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["party_id"], ["parties.id"], name="fk_finance_aging_party"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_finance_aging_shipment"),
        )
    _create_index("ix_finance_aging_snapshots_party_id", "finance_aging_snapshots", "party_id")
    _create_index("ix_finance_aging_snapshots_shipment_id", "finance_aging_snapshots", "shipment_id")
    _create_index("ix_finance_aging_snapshots_direction", "finance_aging_snapshots", "direction")
    _create_index("ix_finance_aging_snapshots_snapshot_date", "finance_aging_snapshots", "snapshot_date")

    tables = set(inspector.get_table_names())
    if "fx_rate_snapshots" not in tables:
        op.create_table(
            "fx_rate_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("base_currency", sa.String(length=10), nullable=False),
            sa.Column("quote_currency", sa.String(length=10), nullable=False),
            sa.Column("rate", sa.Numeric(18, 6), nullable=False),
            sa.Column("rate_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=60), nullable=False, server_default="manual"),
            sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_name", sa.String(length=150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_fx_rate_user"),
        )
    _create_index("ix_fx_rate_snapshots_base_currency", "fx_rate_snapshots", "base_currency")
    _create_index("ix_fx_rate_snapshots_quote_currency", "fx_rate_snapshots", "quote_currency")
    _create_index("ix_fx_rate_snapshots_rate_date", "fx_rate_snapshots", "rate_date")

    tables = set(inspector.get_table_names())
    if "finance_risk_records" not in tables:
        op.create_table(
            "finance_risk_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("party_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("risk_type", sa.String(length=60), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="warning"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("recommended_action", sa.Text(), nullable=True),
            sa.Column("related_invoice_id", sa.Integer(), nullable=True),
            sa.Column("related_payment_id", sa.Integer(), nullable=True),
            sa.Column("related_hold_id", sa.Integer(), nullable=True),
            sa.Column("dedupe_key", sa.String(length=180), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("resolved_by_name", sa.String(length=150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["party_id"], ["parties.id"], name="fk_finance_risk_party"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_finance_risk_shipment"),
            sa.ForeignKeyConstraint(["related_invoice_id"], ["finance_invoices.id"], name="fk_finance_risk_invoice"),
            sa.ForeignKeyConstraint(["related_payment_id"], ["finance_payments.id"], name="fk_finance_risk_payment"),
            sa.ForeignKeyConstraint(["related_hold_id"], ["credit_hold_records.id"], name="fk_finance_risk_hold"),
            sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], name="fk_finance_risk_resolved_by"),
        )
    _create_index("ix_finance_risk_records_party_id", "finance_risk_records", "party_id")
    _create_index("ix_finance_risk_records_shipment_id", "finance_risk_records", "shipment_id")
    _create_index("ix_finance_risk_records_risk_type", "finance_risk_records", "risk_type")
    _create_index("ix_finance_risk_records_status", "finance_risk_records", "status")
    _create_index("ix_finance_risk_records_severity", "finance_risk_records", "severity")
    _create_index("ix_finance_risk_records_dedupe_key", "finance_risk_records", "dedupe_key")

    tables = set(inspector.get_table_names())
    if "finance_adjustments" not in tables:
        op.create_table(
            "finance_adjustments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), nullable=True),
            sa.Column("charge_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), nullable=True),
            sa.Column("adjustment_type", sa.String(length=40), nullable=False),
            sa.Column("direction", sa.String(length=20), nullable=False, server_default="receivable"),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_name", sa.String(length=150), nullable=True),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_by_name", sa.String(length=150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["invoice_id"], ["finance_invoices.id"], name="fk_finance_adjustment_invoice"),
            sa.ForeignKeyConstraint(["charge_id"], ["charges.id"], name="fk_finance_adjustment_charge"),
            sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], name="fk_finance_adjustment_shipment"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_finance_adjustment_created_by"),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], name="fk_finance_adjustment_approved_by"),
        )
    _create_index("ix_finance_adjustments_invoice_id", "finance_adjustments", "invoice_id")
    _create_index("ix_finance_adjustments_charge_id", "finance_adjustments", "charge_id")
    _create_index("ix_finance_adjustments_shipment_id", "finance_adjustments", "shipment_id")
    _create_index("ix_finance_adjustments_status", "finance_adjustments", "status")


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        return
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    for table in (
        "finance_adjustments",
        "finance_risk_records",
        "fx_rate_snapshots",
        "finance_aging_snapshots",
        "credit_hold_records",
        "party_credit_profiles",
        "finance_payment_allocations",
        "finance_payments",
        "finance_invoice_lines",
        "finance_invoices",
    ):
        if table in tables:
            op.drop_table(table)
