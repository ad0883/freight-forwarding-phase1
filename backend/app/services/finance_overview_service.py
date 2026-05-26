"""Phase 14 finance overview helpers.

Aggregates totals for the finance dashboard and shipment finance summary,
without altering the existing Phase 3 charges/P&L logic.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.finance_control import (
    CreditHoldRecord,
    FinanceInvoice,
    FinancePayment,
    FinanceRiskRecord,
)
from app.models.shipment import Shipment
from app.schemas.finance_control import (
    CreditHoldRead,
    FinanceOverviewSummary,
    FinanceRiskRead,
    ShipmentFinanceSummary,
)
from app.services.credit_control_service import (
    expose_credit_hold_read,
    get_active_holds_for_party,
    get_active_holds_for_shipment,
)
from app.services.finance_risk_service import (
    get_open_risks_for_party,
    get_open_risks_for_shipment,
)
from app.services.finance_service import calculate_shipment_pnl


_OPEN_INVOICE_STATUSES = ("draft", "issued", "partially_paid", "overdue", "disputed", "on_hold")


def _money(value: Optional[Decimal]) -> Decimal:
    return Decimal(value) if value is not None else Decimal("0")


def build_finance_overview(db: Session, currency: str = "INR") -> FinanceOverviewSummary:
    today = date.today()
    receivable_total = Decimal("0")
    receivable_overdue = Decimal("0")
    payable_total = Decimal("0")
    payable_overdue = Decimal("0")
    invoices = (
        db.query(FinanceInvoice)
        .filter(FinanceInvoice.status.in_(_OPEN_INVOICE_STATUSES))
        .all()
    )
    for invoice in invoices:
        outstanding = _money(invoice.outstanding_amount)
        if outstanding <= Decimal("0"):
            continue
        is_overdue = invoice.due_date is not None and invoice.due_date < today
        if invoice.direction == "receivable":
            receivable_total += outstanding
            if is_overdue:
                receivable_overdue += outstanding
        elif invoice.direction == "payable":
            payable_total += outstanding
            if is_overdue:
                payable_overdue += outstanding

    active_holds = (
        db.query(CreditHoldRecord)
        .filter(CreditHoldRecord.status == "active")
        .count()
    )
    credit_warnings = (
        db.query(FinanceRiskRecord)
        .filter(
            FinanceRiskRecord.risk_type == "credit_limit_warning",
            FinanceRiskRecord.status.in_(["open", "acknowledged"]),
        )
        .count()
    )
    unallocated_payments = (
        db.query(FinancePayment)
        .filter(
            FinancePayment.status.notin_(["cancelled", "reversed"]),
            FinancePayment.unallocated_amount > 0,
        )
        .all()
    )
    unallocated_total = sum(
        (_money(payment.unallocated_amount) for payment in unallocated_payments),
        Decimal("0"),
    )
    open_risks = (
        db.query(FinanceRiskRecord)
        .filter(FinanceRiskRecord.status.in_(["open", "acknowledged"]))
        .count()
    )
    negative_margin = (
        db.query(FinanceRiskRecord)
        .filter(
            FinanceRiskRecord.risk_type == "margin_negative",
            FinanceRiskRecord.status.in_(["open", "acknowledged"]),
        )
        .count()
    )
    return FinanceOverviewSummary(
        receivable_total=receivable_total,
        receivable_overdue=receivable_overdue,
        payable_total=payable_total,
        payable_overdue=payable_overdue,
        active_holds=active_holds,
        credit_limit_warnings=credit_warnings,
        unallocated_payments=unallocated_total,
        open_risks=open_risks,
        negative_margin_shipments=negative_margin,
        currency=currency.upper(),
    )


def build_shipment_finance_summary(db: Session, shipment_id: int) -> ShipmentFinanceSummary:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    invoices = (
        db.query(FinanceInvoice)
        .filter(FinanceInvoice.shipment_id == shipment_id)
        .all()
    )
    receivable_total = Decimal("0")
    receivable_paid = Decimal("0")
    receivable_outstanding = Decimal("0")
    payable_total = Decimal("0")
    payable_paid = Decimal("0")
    payable_outstanding = Decimal("0")
    currencies: set[str] = set()
    for invoice in invoices:
        if invoice.status == "cancelled":
            continue
        currencies.add(invoice.currency)
        total = _money(invoice.total_amount)
        paid = _money(invoice.paid_amount)
        outstanding = _money(invoice.outstanding_amount)
        if invoice.direction == "receivable":
            receivable_total += total
            receivable_paid += paid
            receivable_outstanding += outstanding
        else:
            payable_total += total
            payable_paid += paid
            payable_outstanding += outstanding
    from app.models.finance_control import FinancePaymentAllocation as _Allocation

    payment_ids = {
        row[0]
        for row in db.query(_Allocation.payment_id)
        .filter(_Allocation.shipment_id == shipment_id)
        .all()
        if row[0] is not None
    }
    invoice_ids = [invoice.id for invoice in invoices]
    if invoice_ids:
        rows = (
            db.query(_Allocation.payment_id)
            .filter(_Allocation.invoice_id.in_(invoice_ids))
            .all()
        )
        for row in rows:
            if row[0] is not None:
                payment_ids.add(row[0])
    payment_count = len(payment_ids)

    pnl = calculate_shipment_pnl(db, shipment_id)
    pnl_currency = pnl.currency if pnl else "INR"
    pnl_net = pnl.net_profit if pnl else Decimal("0")

    invoice_currency = next(iter(currencies)) if len(currencies) == 1 else (pnl_currency or "INR")

    holds = [expose_credit_hold_read(db, hold) for hold in get_active_holds_for_shipment(db, shipment_id)]
    party_id = shipment.exporter_id or shipment.importer_id
    if party_id:
        for hold in get_active_holds_for_party(db, party_id):
            existing = {entry.id for entry in holds}
            if hold.id not in existing:
                holds.append(expose_credit_hold_read(db, hold))

    risks: list[FinanceRiskRead] = []
    from app.services.finance_risk_service import _to_read as risk_to_read

    for risk in get_open_risks_for_shipment(db, shipment_id):
        risks.append(risk_to_read(db, risk))
    if party_id:
        seen_ids = {row.id for row in risks}
        for risk in get_open_risks_for_party(db, party_id):
            if risk.id in seen_ids:
                continue
            risks.append(risk_to_read(db, risk))

    margin_negative = bool(pnl and pnl.net_profit is not None and Decimal(pnl.net_profit) < Decimal("0"))

    return ShipmentFinanceSummary(
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        currency=invoice_currency,
        receivable_total=receivable_total,
        receivable_paid=receivable_paid,
        receivable_outstanding=receivable_outstanding,
        payable_total=payable_total,
        payable_paid=payable_paid,
        payable_outstanding=payable_outstanding,
        invoice_count=len([inv for inv in invoices if inv.status != "cancelled"]),
        payment_count=int(payment_count),
        pnl_net_profit=Decimal(pnl_net or 0),
        pnl_currency=pnl_currency,
        active_holds=holds,
        open_risks=risks,
        margin_negative=margin_negative,
    )
