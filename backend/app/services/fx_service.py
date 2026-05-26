"""Phase 14 FX rate snapshot service.

Manual FX rate snapshots. Live rate fetching is intentionally not implemented
in this phase; missing rates surface as finance risks/validation issues.
"""
from datetime import date as Date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.finance_control import FxRateSnapshot
from app.schemas.finance_control import FxRateCreate, FxRateRead


def _to_read(rate: FxRateSnapshot) -> FxRateRead:
    return FxRateRead(
        id=rate.id,
        base_currency=rate.base_currency,
        quote_currency=rate.quote_currency,
        rate=rate.rate,
        rate_date=rate.rate_date,
        source=rate.source,
        is_manual=bool(rate.is_manual),
        created_by_user_id=rate.created_by_user_id,
        created_by_name=rate.created_by_name,
        created_at=rate.created_at,
    )


def create_fx_rate_snapshot(
    db: Session, payload: FxRateCreate, user: Optional[AuthenticatedUser]
) -> FxRateRead:
    rate = FxRateSnapshot(
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate=payload.rate,
        rate_date=payload.rate_date,
        source=payload.source or "manual",
        is_manual=bool(payload.is_manual),
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else None,
        created_at=datetime.utcnow(),
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return _to_read(rate)


def list_fx_rates(
    db: Session,
    *,
    base_currency: Optional[str] = None,
    quote_currency: Optional[str] = None,
    limit: int = 100,
) -> list[FxRateRead]:
    query = db.query(FxRateSnapshot)
    if base_currency:
        query = query.filter(FxRateSnapshot.base_currency == base_currency.upper())
    if quote_currency:
        query = query.filter(FxRateSnapshot.quote_currency == quote_currency.upper())
    rows = (
        query.order_by(desc(FxRateSnapshot.rate_date), desc(FxRateSnapshot.id))
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return [_to_read(row) for row in rows]


def get_fx_rate(
    db: Session,
    base_currency: str,
    quote_currency: str,
    rate_date: Optional[Date] = None,
) -> Optional[FxRateSnapshot]:
    base = base_currency.upper()
    quote = quote_currency.upper()
    if base == quote:
        return None
    query = db.query(FxRateSnapshot).filter(
        FxRateSnapshot.base_currency == base,
        FxRateSnapshot.quote_currency == quote,
    )
    if rate_date is not None:
        query = query.filter(FxRateSnapshot.rate_date <= rate_date)
    return query.order_by(desc(FxRateSnapshot.rate_date), desc(FxRateSnapshot.id)).first()


def convert_amount(
    db: Session,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    rate_date: Optional[Date] = None,
) -> Optional[Decimal]:
    if not amount:
        return Decimal("0")
    from_cur = (from_currency or "").upper()
    to_cur = (to_currency or "").upper()
    if not from_cur or not to_cur or from_cur == to_cur:
        return Decimal(amount)
    rate = get_fx_rate(db, from_cur, to_cur, rate_date)
    if rate is not None:
        return Decimal(amount) * Decimal(rate.rate)
    inverse = get_fx_rate(db, to_cur, from_cur, rate_date)
    if inverse is not None and inverse.rate:
        return Decimal(amount) / Decimal(inverse.rate)
    return None
