from datetime import date, datetime
from threading import Lock
from time import monotonic
from typing import Optional

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.alert import Alert
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.shipment import DashboardSummary


DASHBOARD_CACHE_TTL_SECONDS = 15
COMPLETED_STATUSES = ["completed", "Completed"]
CANCELLED_STATUSES = ["cancelled", "Cancelled"]

_cache_lock = Lock()
_cache_expires_at = 0.0
_cache_value: Optional[DashboardSummary] = None


def invalidate_dashboard_cache() -> None:
    global _cache_expires_at, _cache_value
    with _cache_lock:
        _cache_expires_at = 0.0
        _cache_value = None


def get_dashboard_summary(db: Session) -> DashboardSummary:
    global _cache_expires_at, _cache_value
    now = monotonic()
    with _cache_lock:
        if _cache_value is not None and now < _cache_expires_at:
            return _cache_value

    summary = _build_dashboard_summary(db)
    with _cache_lock:
        _cache_value = summary
        _cache_expires_at = monotonic() + DASHBOARD_CACHE_TTL_SECONDS
    return summary


def warm_dashboard_cache(db: Session) -> None:
    get_dashboard_summary(db)


def _build_dashboard_summary(db: Session) -> DashboardSummary:
    today = date.today()
    month_start = datetime(today.year, today.month, 1)
    day_start = datetime(today.year, today.month, today.day)

    counts = db.query(
        select(func.count(Shipment.id))
        .where(~Shipment.status.in_(COMPLETED_STATUSES + CANCELLED_STATUSES))
        .scalar_subquery(),
        select(func.count(Task.id)).where(Task.status == "open").scalar_subquery(),
        select(func.count(Shipment.id))
        .where(
            and_(
                ~Shipment.status.in_(COMPLETED_STATUSES + CANCELLED_STATUSES),
                Shipment.etd.isnot(None),
                Shipment.etd >= today,
            )
        )
        .scalar_subquery(),
        select(func.count(Alert.id))
        .where(Alert.created_at >= day_start)
        .scalar_subquery(),
        select(func.count(Shipment.id))
        .where(
            and_(
                Shipment.status.in_(COMPLETED_STATUSES),
                Shipment.created_at >= month_start,
            )
        )
        .scalar_subquery(),
    ).one()

    shipments = (
        db.query(Shipment)
        .options(joinedload(Shipment.exporter), joinedload(Shipment.importer))
        .order_by(Shipment.created_at.desc())
        .limit(8)
        .all()
    )
    recent_alerts = (
        db.query(Alert)
        .filter(Alert.priority == "critical")
        .order_by(Alert.is_read.asc(), Alert.created_at.desc())
        .limit(6)
        .all()
    )
    priority_order = case(
        (Task.priority == "critical", 0),
        (Task.priority == "warning", 1),
        else_=2,
    )
    urgent_tasks = (
        db.query(Task)
        .filter(Task.status == "open")
        .order_by(priority_order.asc(), Task.due_date.asc().nullslast(), Task.created_at.desc())
        .limit(8)
        .all()
    )

    return DashboardSummary(
        live_shipments=counts[0],
        pending_tasks=counts[1],
        future_bookings=counts[2],
        alerts_today=counts[3],
        completed_this_month=counts[4],
        shipments=shipments,
        recent_alerts=recent_alerts,
        urgent_tasks=urgent_tasks,
    )
