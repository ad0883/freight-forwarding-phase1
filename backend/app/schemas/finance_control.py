"""Phase 14 finance + credit-control Pydantic schemas."""
from datetime import date as Date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

InvoiceType = Literal[
    "customer_invoice",
    "vendor_invoice",
    "freight_invoice",
    "demurrage_invoice",
    "detention_invoice",
    "debit_note",
    "credit_note",
    "reimbursement",
    "other",
]
InvoiceDirection = Literal["receivable", "payable"]
InvoiceStatus = Literal[
    "draft",
    "issued",
    "partially_paid",
    "paid",
    "overdue",
    "cancelled",
    "disputed",
    "on_hold",
]
PaymentType = Literal["receipt", "vendor_payment", "adjustment", "refund", "advance", "other"]
PaymentDirection = Literal["inbound", "outbound"]
PaymentStatus = Literal[
    "draft",
    "posted",
    "partially_allocated",
    "allocated",
    "cancelled",
    "reversed",
]
HoldType = Literal[
    "credit_limit_exceeded",
    "overdue_payment",
    "manual_finance_hold",
    "document_release_hold",
    "do_release_hold",
    "obl_release_hold",
    "shipment_completion_hold",
]
HoldStatus = Literal["active", "acknowledged", "resolved", "waived", "dismissed"]
HoldSeverity = Literal["info", "warning", "critical"]
RiskType = Literal[
    "receivable_overdue",
    "payable_overdue",
    "credit_limit_warning",
    "credit_limit_exceeded",
    "unallocated_payment",
    "invoice_dispute",
    "margin_negative",
    "missing_fx_rate",
    "release_blocked",
]
RiskStatus = Literal["open", "acknowledged", "resolved", "dismissed"]
CreditProfileStatus = Literal["active", "suspended", "manual_review", "inactive"]


# ---------------------------------------------------------------------------
# Invoice schemas
# ---------------------------------------------------------------------------


class FinanceInvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(default=Decimal("1"), ge=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=1, max_length=10)
    charge_id: Optional[int] = None
    tax_code: Optional[str] = None
    tax_amount: Optional[Decimal] = Field(default=None, ge=0)


class FinanceInvoiceLineRead(BaseModel):
    id: int
    invoice_id: int
    charge_id: Optional[int] = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    currency: str
    tax_code: Optional[str] = None
    tax_amount: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinanceInvoiceCreate(BaseModel):
    shipment_id: Optional[int] = None
    party_id: Optional[int] = None
    invoice_number: Optional[str] = Field(default=None, max_length=120)
    invoice_type: InvoiceType = "customer_invoice"
    direction: InvoiceDirection = "receivable"
    status: InvoiceStatus = "draft"
    currency: str = Field(default="INR", min_length=1, max_length=10)
    invoice_date: Optional[Date] = None
    due_date: Optional[Date] = None
    credit_days: Optional[int] = Field(default=None, ge=0, le=3650)
    source: Optional[str] = "manual"
    linked_charge_id: Optional[int] = None
    lines: list[FinanceInvoiceLineCreate] = Field(default_factory=list)
    tax_amount: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_currency(self):
        if self.currency:
            self.currency = self.currency.upper()
        return self


class FinanceInvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = Field(default=None, max_length=120)
    invoice_type: Optional[InvoiceType] = None
    direction: Optional[InvoiceDirection] = None
    status: Optional[InvoiceStatus] = None
    currency: Optional[str] = Field(default=None, min_length=1, max_length=10)
    invoice_date: Optional[Date] = None
    due_date: Optional[Date] = None
    credit_days: Optional[int] = Field(default=None, ge=0, le=3650)
    party_id: Optional[int] = None
    notes: Optional[str] = None
    tax_amount: Optional[Decimal] = Field(default=None, ge=0)


class FinanceInvoiceRead(BaseModel):
    id: int
    organization_id: Optional[int] = None
    shipment_id: Optional[int] = None
    shipment_code: Optional[str] = None
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_type: str
    direction: str
    status: str
    currency: str
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    invoice_date: Optional[Date] = None
    due_date: Optional[Date] = None
    credit_days: Optional[int] = None
    source: str
    linked_charge_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    lines: list[FinanceInvoiceLineRead] = Field(default_factory=list)
    metadata_json: Optional[dict[str, Any]] = None


class FinanceInvoiceCancel(BaseModel):
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class FinancePaymentCreate(BaseModel):
    party_id: Optional[int] = None
    payment_type: PaymentType = "receipt"
    direction: Optional[PaymentDirection] = None
    status: PaymentStatus = "posted"
    currency: str = Field(default="INR", min_length=1, max_length=10)
    amount: Decimal = Field(gt=0)
    payment_date: Optional[Date] = None
    reference_number: Optional[str] = Field(default=None, max_length=120)
    method: Optional[str] = Field(default=None, max_length=40)
    bank_name: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_currency(self):
        if self.currency:
            self.currency = self.currency.upper()
        return self


class FinancePaymentAllocationItem(BaseModel):
    invoice_id: Optional[int] = None
    charge_id: Optional[int] = None
    shipment_id: Optional[int] = None
    allocated_amount: Decimal = Field(gt=0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def require_target(self):
        if not (self.invoice_id or self.charge_id or self.shipment_id):
            raise ValueError("At least one of invoice_id, charge_id, or shipment_id is required")
        return self


class FinancePaymentAllocateRequest(BaseModel):
    allocations: list[FinancePaymentAllocationItem] = Field(min_length=1)


class FinancePaymentAllocationRead(BaseModel):
    id: int
    payment_id: int
    invoice_id: Optional[int] = None
    charge_id: Optional[int] = None
    shipment_id: Optional[int] = None
    allocated_amount: Decimal
    currency: str
    allocated_at: datetime
    allocated_by_user_id: Optional[int] = None
    allocated_by_name: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FinancePaymentRead(BaseModel):
    id: int
    organization_id: Optional[int] = None
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    payment_type: str
    direction: str
    status: str
    currency: str
    amount: Decimal
    unallocated_amount: Decimal
    payment_date: Optional[Date] = None
    reference_number: Optional[str] = None
    method: Optional[str] = None
    bank_name: Optional[str] = None
    notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    allocations: list[FinancePaymentAllocationRead] = Field(default_factory=list)


class FinancePaymentCancel(BaseModel):
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Credit profile / holds
# ---------------------------------------------------------------------------


class PartyCreditProfileUpdate(BaseModel):
    credit_limit: Optional[Decimal] = Field(default=None, ge=0)
    credit_currency: Optional[str] = Field(default=None, min_length=1, max_length=10)
    credit_days: Optional[int] = Field(default=None, ge=0, le=3650)
    is_credit_allowed: Optional[bool] = None
    hold_on_overdue: Optional[bool] = None
    hold_on_limit_exceeded: Optional[bool] = None
    warning_threshold_percent: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[CreditProfileStatus] = None


class PartyCreditProfileRead(BaseModel):
    id: int
    organization_id: Optional[int] = None
    party_id: int
    party_name: Optional[str] = None
    credit_limit: Decimal
    credit_currency: str
    credit_days: int
    is_credit_allowed: bool
    hold_on_overdue: bool
    hold_on_limit_exceeded: bool
    warning_threshold_percent: int
    status: str
    current_outstanding: Optional[Decimal] = None
    overdue_amount: Optional[Decimal] = None
    available_credit: Optional[Decimal] = None
    active_holds: int = 0
    created_at: datetime
    updated_at: datetime


class CreditHoldRead(BaseModel):
    id: int
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    shipment_id: Optional[int] = None
    shipment_code: Optional[str] = None
    hold_type: str
    severity: str
    status: str
    reason: Optional[str] = None
    trigger_source: str
    current_outstanding: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    overdue_amount: Optional[Decimal] = None
    blocked_action: Optional[str] = None
    created_at: datetime
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolution_notes: Optional[str] = None


class CreditHoldResolutionRequest(BaseModel):
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Aging
# ---------------------------------------------------------------------------


class FinanceAgingBuckets(BaseModel):
    not_due: Decimal = Decimal("0")
    bucket_0_30: Decimal = Decimal("0")
    bucket_31_60: Decimal = Decimal("0")
    bucket_61_90: Decimal = Decimal("0")
    bucket_90_plus: Decimal = Decimal("0")
    total_outstanding: Decimal = Decimal("0")
    overdue_amount: Decimal = Decimal("0")


class PartyAgingRead(BaseModel):
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    direction: str
    currency: str
    snapshot_date: Date
    buckets: FinanceAgingBuckets


class FinanceAgingSummary(BaseModel):
    direction: str
    currency: str
    snapshot_date: Date
    buckets: FinanceAgingBuckets
    parties: list[PartyAgingRead] = Field(default_factory=list)


class FinanceAgingSnapshotRead(BaseModel):
    id: int
    party_id: Optional[int] = None
    shipment_id: Optional[int] = None
    direction: str
    currency: str
    snapshot_date: Date
    not_due_amount: Decimal
    bucket_0_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_90_plus: Decimal
    total_outstanding: Decimal
    overdue_amount: Decimal
    created_at: datetime


# ---------------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------------


class FxRateCreate(BaseModel):
    base_currency: str = Field(min_length=1, max_length=10)
    quote_currency: str = Field(min_length=1, max_length=10)
    rate: Decimal = Field(gt=0)
    rate_date: Date
    source: Optional[str] = "manual"
    is_manual: bool = True

    @model_validator(mode="after")
    def normalize_currency(self):
        self.base_currency = self.base_currency.upper()
        self.quote_currency = self.quote_currency.upper()
        return self


class FxRateRead(BaseModel):
    id: int
    base_currency: str
    quote_currency: str
    rate: Decimal
    rate_date: Date
    source: str
    is_manual: bool
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Risks
# ---------------------------------------------------------------------------


class FinanceRiskRead(BaseModel):
    id: int
    party_id: Optional[int] = None
    party_name: Optional[str] = None
    shipment_id: Optional[int] = None
    shipment_code: Optional[str] = None
    risk_type: str
    severity: str
    status: str
    message: str
    recommended_action: Optional[str] = None
    related_invoice_id: Optional[int] = None
    related_payment_id: Optional[int] = None
    related_hold_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[int] = None
    resolved_by_name: Optional[str] = None


class FinanceRiskResolutionRequest(BaseModel):
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Shipment finance summary & release checks
# ---------------------------------------------------------------------------


class ShipmentFinanceSummary(BaseModel):
    shipment_id: int
    shipment_code: str
    currency: str
    receivable_total: Decimal
    receivable_paid: Decimal
    receivable_outstanding: Decimal
    payable_total: Decimal
    payable_paid: Decimal
    payable_outstanding: Decimal
    invoice_count: int
    payment_count: int
    pnl_net_profit: Decimal
    pnl_currency: str
    active_holds: list[CreditHoldRead] = Field(default_factory=list)
    open_risks: list[FinanceRiskRead] = Field(default_factory=list)
    margin_negative: bool


class ReleaseCheckRequest(BaseModel):
    action_key: str = Field(min_length=1, max_length=60)


class ReleaseCheckResult(BaseModel):
    action_key: str
    allowed: bool
    blocked_by: list[CreditHoldRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str


# ---------------------------------------------------------------------------
# Finance overview
# ---------------------------------------------------------------------------


class FinanceOverviewSummary(BaseModel):
    receivable_total: Decimal
    receivable_overdue: Decimal
    payable_total: Decimal
    payable_overdue: Decimal
    active_holds: int
    credit_limit_warnings: int
    unallocated_payments: Decimal
    open_risks: int
    negative_margin_shipments: int
    currency: str
