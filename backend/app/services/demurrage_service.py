from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.demurrage import Demurrage
from app.models.shipment import Shipment
from app.schemas.demurrage import DemurrageRead


def get_or_create_demurrage(db: Session, shipment: Shipment) -> Demurrage:
    record = db.query(Demurrage).filter(Demurrage.shipment_id == shipment.id).first()
    if record:
        return record
    record = Demurrage(shipment_id=shipment.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def calculate_demurrage(
    record: Demurrage, today: Optional[date] = None, persist_status: bool = True
) -> DemurrageRead:
    today = today or date.today()
    free_days_end_date = None
    days_used = 0
    days_remaining = None
    is_running = False
    total_due = Decimal("0")
    status = "not_started"

    if record.start_date and record.free_days is not None:
        free_days_end_date = record.start_date + timedelta(days=record.free_days)
        days_used = max((today - record.start_date).days, 0)
        days_remaining = (free_days_end_date - today).days
        if days_remaining <= 0:
            status = "running"
            is_running = True
            overdue_days = abs(days_remaining)
            rate = record.rate_per_day or Decimal("0")
            total_due = rate * record.container_count * overdue_days
        elif days_remaining <= record.alert_at_days:
            status = "expiring_soon"
        else:
            status = "within_free_days"

    if persist_status:
        record.status = status
    return DemurrageRead(
        id=record.id,
        shipment_id=record.shipment_id,
        free_days=record.free_days,
        start_date=record.start_date,
        rate_per_day=record.rate_per_day,
        currency=record.currency,
        alert_at_days=record.alert_at_days,
        container_count=record.container_count,
        status=status,
        free_days_end_date=free_days_end_date,
        days_used=days_used,
        days_remaining=days_remaining,
        is_demurrage_running=is_running,
        total_demurrage_due=total_due,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
