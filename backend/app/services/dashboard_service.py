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
_cache_dict = {}  # Format: {org_id: {"expires_at": float, "value": DashboardSummary}}


def invalidate_dashboard_cache(organization_id: Optional[int] = None) -> None:
    global _cache_dict
    with _cache_lock:
        if organization_id and organization_id in _cache_dict:
            del _cache_dict[organization_id]
        elif not organization_id:
            _cache_dict.clear()


def get_dashboard_summary(db: Session, organization_id: int) -> DashboardSummary:
    global _cache_dict
    now = monotonic()
    with _cache_lock:
        cache_entry = _cache_dict.get(organization_id)
        if cache_entry and now < cache_entry["expires_at"]:
            return cache_entry["value"]

    summary = _build_dashboard_summary(db, organization_id)
    with _cache_lock:
        _cache_dict[organization_id] = {
            "value": summary,
            "expires_at": monotonic() + DASHBOARD_CACHE_TTL_SECONDS
        }
    return summary


def warm_dashboard_cache(db: Session) -> None:
    pass # Cannot warm globally without knowing orgs


def _build_dashboard_summary(db: Session, organization_id: int) -> DashboardSummary:
    today = date.today()
    month_start = datetime(today.year, today.month, 1)
    day_start = datetime(today.year, today.month, today.day)

    counts = db.query(
        select(func.count(Shipment.id))
        .where(Shipment.is_archived.is_(False), ~Shipment.status.in_(COMPLETED_STATUSES + CANCELLED_STATUSES), Shipment.organization_id == organization_id)
        .scalar_subquery(),
        select(func.count(Task.id))
        .join(Shipment, Shipment.id == Task.shipment_id)
        .where(Task.status == "open", Shipment.is_archived.is_(False), Shipment.organization_id == organization_id)
        .scalar_subquery(),
        select(func.count(Shipment.id))
        .where(
            and_(
                Shipment.is_archived.is_(False),
                ~Shipment.status.in_(COMPLETED_STATUSES + CANCELLED_STATUSES),
                Shipment.etd.isnot(None),
                Shipment.etd >= today,
                Shipment.organization_id == organization_id
            )
        )
        .scalar_subquery(),
        select(func.count(Alert.id))
        .join(Shipment, Shipment.id == Alert.shipment_id)
        .where(Alert.created_at >= day_start, Shipment.is_archived.is_(False), Shipment.organization_id == organization_id)
        .scalar_subquery(),
        select(func.count(Shipment.id))
        .where(
            and_(
                Shipment.is_archived.is_(False),
                Shipment.status.in_(COMPLETED_STATUSES),
                Shipment.created_at >= month_start,
                Shipment.organization_id == organization_id
            )
        )
        .scalar_subquery(),
    ).one()

    shipments = (
        db.query(Shipment)
        .options(joinedload(Shipment.exporter), joinedload(Shipment.importer))
        .filter(Shipment.is_archived.is_(False), Shipment.organization_id == organization_id)
        .order_by(Shipment.created_at.desc())
        .limit(8)
        .all()
    )
    recent_alerts = (
        db.query(Alert)
        .join(Shipment, Shipment.id == Alert.shipment_id)
        .filter(Alert.priority == "critical", Shipment.is_archived.is_(False), Shipment.organization_id == organization_id)
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
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(Task.status == "open", Shipment.is_archived.is_(False), Shipment.organization_id == organization_id)
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
