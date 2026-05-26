"""Phase 14 finance + credit-control models.

These tables sit beside the existing ``charges`` table and capture stronger
finance signals (invoices, payments, allocations, credit profiles, holds,
aging snapshots, FX snapshots, risks, and adjustments).  They never mutate
the historical charge based P&L; finance control is advisory and auditable.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class FinanceInvoice(Base):
    __tablename__ = "finance_invoices"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    invoice_number = Column(String(120), nullable=True, index=True)
    invoice_type = Column(String(40), nullable=False, default="customer_invoice", index=True)
    direction = Column(String(20), nullable=False, default="receivable", index=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    currency = Column(String(10), nullable=False, default="INR")
    subtotal_amount = Column(Numeric(14, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(14, 2), nullable=False, default=0)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(14, 2), nullable=False, default=0)
    outstanding_amount = Column(Numeric(14, 2), nullable=False, default=0)
    invoice_date = Column(Date, nullable=True, index=True)
    due_date = Column(Date, nullable=True, index=True)
    credit_days = Column(Integer, nullable=True)
    source = Column(String(40), nullable=False, default="manual")
    linked_charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    lines = relationship(
        "FinanceInvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    allocations = relationship(
        "FinancePaymentAllocation",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class FinanceInvoiceLine(Base):
    __tablename__ = "finance_invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("finance_invoices.id"), nullable=False, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True, index=True)
    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False, default=1)
    unit_price = Column(Numeric(14, 2), nullable=False, default=0)
    amount = Column(Numeric(14, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    tax_code = Column(String(40), nullable=True)
    tax_amount = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    invoice = relationship("FinanceInvoice", back_populates="lines")


class FinancePayment(Base):
    __tablename__ = "finance_payments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    payment_type = Column(String(40), nullable=False, default="receipt", index=True)
    direction = Column(String(20), nullable=False, default="inbound", index=True)
    status = Column(String(30), nullable=False, default="posted", index=True)
    currency = Column(String(10), nullable=False, default="INR")
    amount = Column(Numeric(14, 2), nullable=False, default=0)
    unallocated_amount = Column(Numeric(14, 2), nullable=False, default=0)
    payment_date = Column(Date, nullable=True, index=True)
    reference_number = Column(String(120), nullable=True)
    method = Column(String(40), nullable=True)
    bank_name = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    allocations = relationship(
        "FinancePaymentAllocation",
        back_populates="payment",
        cascade="all, delete-orphan",
    )


class FinancePaymentAllocation(Base):
    __tablename__ = "finance_payment_allocations"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("finance_payments.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("finance_invoices.id"), nullable=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    allocated_amount = Column(Numeric(14, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    allocated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    allocated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    allocated_by_name = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    payment = relationship("FinancePayment", back_populates="allocations")
    invoice = relationship("FinanceInvoice", back_populates="allocations")


class PartyCreditProfile(Base):
    __tablename__ = "party_credit_profiles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, unique=True, index=True)
    credit_limit = Column(Numeric(14, 2), nullable=False, default=0)
    credit_currency = Column(String(10), nullable=False, default="INR")
    credit_days = Column(Integer, nullable=False, default=0)
    is_credit_allowed = Column(Boolean, nullable=False, default=True)
    hold_on_overdue = Column(Boolean, nullable=False, default=True)
    hold_on_limit_exceeded = Column(Boolean, nullable=False, default=True)
    warning_threshold_percent = Column(Integer, nullable=False, default=80)
    status = Column(String(30), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CreditHoldRecord(Base):
    __tablename__ = "credit_hold_records"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    hold_type = Column(String(60), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="warning", index=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    reason = Column(Text, nullable=True)
    trigger_source = Column(String(60), nullable=False, default="system")
    current_outstanding = Column(Numeric(14, 2), nullable=True)
    credit_limit = Column(Numeric(14, 2), nullable=True)
    overdue_amount = Column(Numeric(14, 2), nullable=True)
    blocked_action = Column(String(60), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class FinanceAgingSnapshot(Base):
    __tablename__ = "finance_aging_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    direction = Column(String(20), nullable=False, default="receivable", index=True)
    currency = Column(String(10), nullable=False, default="INR")
    snapshot_date = Column(Date, nullable=False, index=True)
    not_due_amount = Column(Numeric(14, 2), nullable=False, default=0)
    bucket_0_30 = Column(Numeric(14, 2), nullable=False, default=0)
    bucket_31_60 = Column(Numeric(14, 2), nullable=False, default=0)
    bucket_61_90 = Column(Numeric(14, 2), nullable=False, default=0)
    bucket_90_plus = Column(Numeric(14, 2), nullable=False, default=0)
    total_outstanding = Column(Numeric(14, 2), nullable=False, default=0)
    overdue_amount = Column(Numeric(14, 2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class FxRateSnapshot(Base):
    __tablename__ = "fx_rate_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    base_currency = Column(String(10), nullable=False, index=True)
    quote_currency = Column(String(10), nullable=False, index=True)
    rate = Column(Numeric(18, 6), nullable=False)
    rate_date = Column(Date, nullable=False, index=True)
    source = Column(String(60), nullable=False, default="manual")
    is_manual = Column(Boolean, nullable=False, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class FinanceRiskRecord(Base):
    __tablename__ = "finance_risk_records"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    risk_type = Column(String(60), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="warning", index=True)
    status = Column(String(30), nullable=False, default="open", index=True)
    message = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    related_invoice_id = Column(Integer, ForeignKey("finance_invoices.id"), nullable=True, index=True)
    related_payment_id = Column(Integer, ForeignKey("finance_payments.id"), nullable=True, index=True)
    related_hold_id = Column(Integer, ForeignKey("credit_hold_records.id"), nullable=True, index=True)
    dedupe_key = Column(String(180), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class FinanceAdjustment(Base):
    __tablename__ = "finance_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("finance_invoices.id"), nullable=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    adjustment_type = Column(String(40), nullable=False, index=True)
    direction = Column(String(20), nullable=False, default="receivable")
    amount = Column(Numeric(14, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    reason = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)
