"""Phase 14 finance aging service.

Computes aging buckets for receivables/payables based on due date.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.finance_control import FinanceAgingSnapshot, FinanceInvoice
from app.models.party import Party
from app.schemas.finance_control import (
    FinanceAgingBuckets,
    FinanceAgingSnapshotRead,
    FinanceAgingSummary,
    PartyAgingRead,
)


_OPEN_STATUSES = ("draft", "issued", "partially_paid", "overdue", "disputed", "on_hold")


def _money(value: Optional[Decimal]) -> Decimal:
    return Decimal(value) if value is not None else Decimal("0")


def _bucket_for(due_date: Optional[date], today: date) -> str:
    if due_date is None:
        return "not_due"
    days = (today - due_date).days
    if days < 0:
        return "not_due"
    if days <= 30:
        return "bucket_0_30"
    if days <= 60:
        return "bucket_31_60"
    if days <= 90:
        return "bucket_61_90"
    return "bucket_90_plus"


def _empty_buckets() -> dict[str, Decimal]:
    return {
        "not_due": Decimal("0"),
        "bucket_0_30": Decimal("0"),
        "bucket_31_60": Decimal("0"),
        "bucket_61_90": Decimal("0"),
        "bucket_90_plus": Decimal("0"),
    }


def _buckets_to_summary(buckets: dict[str, Decimal]) -> FinanceAgingBuckets:
    not_due = buckets["not_due"]
    overdue = (
        buckets["bucket_0_30"]
        + buckets["bucket_31_60"]
        + buckets["bucket_61_90"]
        + buckets["bucket_90_plus"]
    )
    return FinanceAgingBuckets(
        not_due=not_due,
        bucket_0_30=buckets["bucket_0_30"],
        bucket_31_60=buckets["bucket_31_60"],
        bucket_61_90=buckets["bucket_61_90"],
        bucket_90_plus=buckets["bucket_90_plus"],
        total_outstanding=not_due + overdue,
        overdue_amount=overdue,
    )


def calculate_aging_for_party(
    db: Session,
    party_id: int,
    direction: str = "receivable",
    *,
    as_of_date: Optional[date] = None,
    currency: Optional[str] = None,
) -> FinanceAgingBuckets:
    today = as_of_date or date.today()
    query = db.query(FinanceInvoice).filter(
        FinanceInvoice.party_id == party_id,
        FinanceInvoice.direction == direction,
        FinanceInvoice.status.in_(_OPEN_STATUSES),
    )
    if currency:
        query = query.filter(FinanceInvoice.currency == currency.upper())
    buckets = _empty_buckets()
    for invoice in query.all():
        outstanding = _money(invoice.outstanding_amount)
        if outstanding <= Decimal("0"):
            continue
        bucket = _bucket_for(invoice.due_date, today)
        buckets[bucket] += outstanding
    return _buckets_to_summary(buckets)


def calculate_aging_summary(
    db: Session,
    direction: str = "receivable",
    *,
    as_of_date: Optional[date] = None,
    currency: Optional[str] = None,
) -> FinanceAgingSummary:
    today = as_of_date or date.today()
    base_currency = (currency or "INR").upper()
    party_buckets: dict[Optional[int], dict[str, Decimal]] = {}
    party_names: dict[int, str] = {}

    query = db.query(FinanceInvoice).filter(
        FinanceInvoice.direction == direction,
        FinanceInvoice.status.in_(_OPEN_STATUSES),
    )
    if currency:
        query = query.filter(FinanceInvoice.currency == currency.upper())
    invoices = query.all()
    if invoices:
        names = (
            db.query(Party.id, Party.name)
            .filter(Party.id.in_({invoice.party_id for invoice in invoices if invoice.party_id}))
            .all()
        )
        party_names = {row[0]: row[1] for row in names}

    overall = _empty_buckets()
    for invoice in invoices:
        outstanding = _money(invoice.outstanding_amount)
        if outstanding <= Decimal("0"):
            continue
        bucket = _bucket_for(invoice.due_date, today)
        overall[bucket] += outstanding
        bucket_map = party_buckets.setdefault(invoice.party_id, _empty_buckets())
        bucket_map[bucket] += outstanding

    parties = []
    for party_id, bucket_map in party_buckets.items():
        parties.append(
            PartyAgingRead(
                party_id=party_id,
                party_name=party_names.get(party_id) if party_id else None,
                direction=direction,
                currency=base_currency,
                snapshot_date=today,
                buckets=_buckets_to_summary(bucket_map),
            )
        )
    parties.sort(
        key=lambda row: row.buckets.total_outstanding,
        reverse=True,
    )
    return FinanceAgingSummary(
        direction=direction,
        currency=base_currency,
        snapshot_date=today,
        buckets=_buckets_to_summary(overall),
        parties=parties,
    )


def create_aging_snapshot(
    db: Session,
    *,
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    direction: str = "receivable",
    currency: str = "INR",
) -> FinanceAgingSnapshotRead:
    today = date.today()
    if party_id is not None:
        buckets = calculate_aging_for_party(db, party_id, direction, currency=currency)
    else:
        summary = calculate_aging_summary(db, direction=direction, currency=currency)
        buckets = summary.buckets
    snapshot = FinanceAgingSnapshot(
        party_id=party_id,
        shipment_id=shipment_id,
        direction=direction,
        currency=currency.upper(),
        snapshot_date=today,
        not_due_amount=buckets.not_due,
        bucket_0_30=buckets.bucket_0_30,
        bucket_31_60=buckets.bucket_31_60,
        bucket_61_90=buckets.bucket_61_90,
        bucket_90_plus=buckets.bucket_90_plus,
        total_outstanding=buckets.total_outstanding,
        overdue_amount=buckets.overdue_amount,
        created_at=datetime.utcnow(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return FinanceAgingSnapshotRead(
        id=snapshot.id,
        party_id=snapshot.party_id,
        shipment_id=snapshot.shipment_id,
        direction=snapshot.direction,
        currency=snapshot.currency,
        snapshot_date=snapshot.snapshot_date,
        not_due_amount=_money(snapshot.not_due_amount),
        bucket_0_30=_money(snapshot.bucket_0_30),
        bucket_31_60=_money(snapshot.bucket_31_60),
        bucket_61_90=_money(snapshot.bucket_61_90),
        bucket_90_plus=_money(snapshot.bucket_90_plus),
        total_outstanding=_money(snapshot.total_outstanding),
        overdue_amount=_money(snapshot.overdue_amount),
        created_at=snapshot.created_at,
    )
