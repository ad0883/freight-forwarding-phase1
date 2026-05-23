from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.charge import Charge
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.charge import (
    DashboardFinancialSummary,
    MonthlyReportSummary,
    PendingChargeReportRow,
    ShipmentPLReportRow,
    ShipmentPLSummary,
)


COMPLETED_STATUSES = {"completed", "Completed"}
DEFAULT_CURRENCY = "INR"


def _money(value: Optional[Decimal]) -> Decimal:
    return value or Decimal("0")


def _active(charges: Iterable[Charge]) -> list[Charge]:
    return [charge for charge in charges if charge.status != "cancelled"]


def _currency_for(charges: Iterable[Charge]) -> tuple[str, bool]:
    currencies = sorted({charge.currency or DEFAULT_CURRENCY for charge in charges})
    if not currencies:
        return DEFAULT_CURRENCY, False
    if len(currencies) == 1:
        return currencies[0], False
    return "MIXED", True


def _charge_report_date(charge: Charge) -> date:
    if charge.date:
        return charge.date
    return charge.created_at.date()


def _shipment_pnl_from_charges(shipment: Shipment, charges: list[Charge]) -> ShipmentPLSummary:
    active_charges = _active(charges)
    total_payable = sum((_money(charge.amount) for charge in active_charges if charge.direction == "payable"), Decimal("0"))
    total_receivable = sum((_money(charge.amount) for charge in active_charges if charge.direction == "receivable"), Decimal("0"))
    total_paid = sum(
        (_money(charge.amount) for charge in active_charges if charge.direction == "payable" and charge.status == "paid"),
        Decimal("0"),
    )
    total_received = sum(
        (_money(charge.amount) for charge in active_charges if charge.direction == "receivable" and charge.status == "received"),
        Decimal("0"),
    )
    pending_payable = sum(
        (_money(charge.amount) for charge in active_charges if charge.direction == "payable" and charge.status == "pending"),
        Decimal("0"),
    )
    pending_receivable = sum(
        (_money(charge.amount) for charge in active_charges if charge.direction == "receivable" and charge.status == "pending"),
        Decimal("0"),
    )
    currency, multiple_currencies = _currency_for(active_charges)
    return ShipmentPLSummary(
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        currency=currency,
        total_payable=total_payable,
        total_receivable=total_receivable,
        total_paid=total_paid,
        total_received=total_received,
        pending_payable=pending_payable,
        pending_receivable=pending_receivable,
        net_profit=total_receivable - total_payable,
        charge_count=len(active_charges),
        multiple_currencies=multiple_currencies,
    )


def calculate_shipment_pnl(db: Session, shipment_id: int) -> Optional[ShipmentPLSummary]:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        return None
    charges = db.query(Charge).filter(Charge.shipment_id == shipment_id).all()
    return _shipment_pnl_from_charges(shipment, charges)


def calculate_dashboard_financials(db: Session, today: Optional[date] = None) -> DashboardFinancialSummary:
    today = today or date.today()
    charges = db.query(Charge).filter(Charge.status != "cancelled").all()
    month_charges = [
        charge
        for charge in charges
        if _charge_report_date(charge).year == today.year and _charge_report_date(charge).month == today.month
    ]
    pending_receivables = sum(
        (_money(charge.amount) for charge in charges if charge.direction == "receivable" and charge.status == "pending"),
        Decimal("0"),
    )
    pending_payables = sum(
        (_money(charge.amount) for charge in charges if charge.direction == "payable" and charge.status == "pending"),
        Decimal("0"),
    )
    this_month_receivables = sum(
        (_money(charge.amount) for charge in month_charges if charge.direction == "receivable"),
        Decimal("0"),
    )
    this_month_payables = sum(
        (_money(charge.amount) for charge in month_charges if charge.direction == "payable"),
        Decimal("0"),
    )
    currency, multiple_currencies = _currency_for(charges)
    return DashboardFinancialSummary(
        pending_receivables=pending_receivables,
        pending_payables=pending_payables,
        this_month_receivables=this_month_receivables,
        this_month_payables=this_month_payables,
        this_month_profit=this_month_receivables - this_month_payables,
        currency=currency,
        multiple_currencies=multiple_currencies,
    )


def calculate_monthly_report(
    db: Session, year: Optional[int] = None, month: Optional[int] = None, today: Optional[date] = None
) -> MonthlyReportSummary:
    today = today or date.today()
    year = year or today.year
    month = month or today.month
    charges = [
        charge
        for charge in db.query(Charge).filter(Charge.status != "cancelled").all()
        if _charge_report_date(charge).year == year and _charge_report_date(charge).month == month
    ]
    shipments = (
        db.query(Shipment)
        .filter(Shipment.created_at >= datetime(year, month, 1))
        .all()
    )
    shipments = [
        shipment
        for shipment in shipments
        if shipment.created_at.year == year and shipment.created_at.month == month
    ]
    total_receivable = sum(
        (_money(charge.amount) for charge in charges if charge.direction == "receivable"),
        Decimal("0"),
    )
    total_payable = sum(
        (_money(charge.amount) for charge in charges if charge.direction == "payable"),
        Decimal("0"),
    )
    pending_receivable = sum(
        (_money(charge.amount) for charge in charges if charge.direction == "receivable" and charge.status == "pending"),
        Decimal("0"),
    )
    pending_payable = sum(
        (_money(charge.amount) for charge in charges if charge.direction == "payable" and charge.status == "pending"),
        Decimal("0"),
    )
    currency, multiple_currencies = _currency_for(charges)
    return MonthlyReportSummary(
        month=month,
        year=year,
        shipment_count=len(shipments),
        completed_shipments=sum(1 for shipment in shipments if shipment.status in COMPLETED_STATUSES),
        total_receivable=total_receivable,
        total_payable=total_payable,
        net_profit=total_receivable - total_payable,
        pending_receivable=pending_receivable,
        pending_payable=pending_payable,
        currency=currency,
        multiple_currencies=multiple_currencies,
    )


def _pending_charges(db: Session, direction: str) -> list[PendingChargeReportRow]:
    charges = (
        db.query(Charge)
        .options(joinedload(Charge.shipment), joinedload(Charge.party))
        .filter(Charge.direction == direction, Charge.status == "pending")
        .order_by(Charge.date.asc().nullslast(), Charge.created_at.asc())
        .all()
    )
    return [
        PendingChargeReportRow(
            charge_id=charge.id,
            shipment_id=charge.shipment_id,
            shipment_code=charge.shipment.shipment_code,
            party_name=charge.party.name if charge.party else None,
            amount=charge.amount,
            currency=charge.currency,
            invoice_no=charge.invoice_no,
            date=charge.date,
            notes=charge.notes,
        )
        for charge in charges
    ]


def list_pending_receivables(db: Session) -> list[PendingChargeReportRow]:
    return _pending_charges(db, "receivable")


def list_pending_payables(db: Session) -> list[PendingChargeReportRow]:
    return _pending_charges(db, "payable")


def list_shipment_pnl(db: Session) -> list[ShipmentPLReportRow]:
    shipments = (
        db.query(Shipment)
        .options(joinedload(Shipment.charges))
        .order_by(Shipment.created_at.desc())
        .all()
    )
    rows = []
    for shipment in shipments:
        summary = _shipment_pnl_from_charges(shipment, list(shipment.charges))
        rows.append(
            ShipmentPLReportRow(
                shipment_id=shipment.id,
                shipment_code=shipment.shipment_code,
                type=shipment.type,
                status=shipment.status,
                total_receivable=summary.total_receivable,
                total_payable=summary.total_payable,
                net_profit=summary.net_profit,
                pending_receivable=summary.pending_receivable,
                pending_payable=summary.pending_payable,
                currency=summary.currency,
                multiple_currencies=summary.multiple_currencies,
            )
        )
    return rows
