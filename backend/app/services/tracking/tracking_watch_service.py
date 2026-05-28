"""Tracking watch item management service."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.tracking import TrackingWatchItem


def create_watch_item(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TrackingWatchItem:
    now = datetime.utcnow()
    item = TrackingWatchItem(
        tracking_provider_id=data.get("tracking_provider_id"),
        shipment_id=data.get("shipment_id"),
        container_id=data.get("container_id"),
        transport_job_id=data.get("transport_job_id"),
        customs_case_id=data.get("customs_case_id"),
        watch_type=data.get("watch_type", "container"),
        tracking_identifier=data["tracking_identifier"],
        secondary_identifier=data.get("secondary_identifier"),
        status="active",
        created_by_user_id=user.id,
        created_by_name=user.name,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_watch_items(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    watch_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[TrackingWatchItem]:
    q = db.query(TrackingWatchItem)
    if shipment_id:
        q = q.filter(TrackingWatchItem.shipment_id == shipment_id)
    if status_filter:
        q = q.filter(TrackingWatchItem.status == status_filter)
    if watch_type:
        q = q.filter(TrackingWatchItem.watch_type == watch_type)
    return q.order_by(TrackingWatchItem.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def get_watch_item(db: Session, watch_item_id: int) -> Optional[TrackingWatchItem]:
    return db.query(TrackingWatchItem).filter(TrackingWatchItem.id == watch_item_id).first()


def pause_watch_item(db: Session, watch_item_id: int, user: AuthenticatedUser) -> TrackingWatchItem:
    item = get_watch_item(db, watch_item_id)
    if not item:
        raise ValueError("Watch item not found")
    item.status = "paused"
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def resume_watch_item(db: Session, watch_item_id: int, user: AuthenticatedUser) -> TrackingWatchItem:
    item = get_watch_item(db, watch_item_id)
    if not item:
        raise ValueError("Watch item not found")
    item.status = "active"
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def complete_watch_item(db: Session, watch_item_id: int, user: AuthenticatedUser) -> TrackingWatchItem:
    item = get_watch_item(db, watch_item_id)
    if not item:
        raise ValueError("Watch item not found")
    item.status = "completed"
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item
