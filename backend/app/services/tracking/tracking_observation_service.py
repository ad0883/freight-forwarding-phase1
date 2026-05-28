"""Tracking observation service — create and query observations."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.tracking import (
    TrackingActivityLog,
    TrackingEvent,
    TrackingObservation,
    TrackingWatchItem,
)
from app.services.tracking.tracking_normalization_service import (
    map_observation_to_event_key,
    normalize_location,
    normalize_tracking_status,
)


def create_manual_observation(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TrackingObservation:
    """Create a manual tracking observation."""
    now = datetime.utcnow()
    raw_status = data.get("raw_status", "")
    normalized = normalize_tracking_status(raw_status, data.get("provider_type", "manual"))

    obs = TrackingObservation(
        tracking_watch_item_id=data.get("tracking_watch_item_id"),
        tracking_provider_id=data.get("tracking_provider_id"),
        shipment_id=data.get("shipment_id"),
        container_id=data.get("container_id"),
        transport_job_id=data.get("transport_job_id"),
        observation_type=data.get("observation_type", "container_status"),
        source="manual",
        raw_status=raw_status,
        normalized_status=normalized,
        status_time=data.get("status_time"),
        location_text=normalize_location(data.get("location_text")),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        eta=data.get("eta"),
        etd=data.get("etd"),
        vessel_name=data.get("vessel_name"),
        voyage_no=data.get("voyage_no"),
        confidence=data.get("confidence", 0.8),
        is_customer_visible=data.get("is_customer_visible", False),
        observed_at=data.get("observed_at", now),
        received_at=now,
    )
    db.add(obs)
    db.flush()

    # Update watch item last_observation_at
    if obs.tracking_watch_item_id:
        wi = db.query(TrackingWatchItem).filter(TrackingWatchItem.id == obs.tracking_watch_item_id).first()
        if wi:
            wi.last_observation_at = now
            wi.updated_at = now

    # Create tracking event
    event = TrackingEvent(
        tracking_observation_id=obs.id,
        shipment_id=obs.shipment_id,
        container_id=obs.container_id,
        transport_job_id=obs.transport_job_id,
        event_key=map_observation_to_event_key(normalized),
        event_label=normalized.replace("_", " ").title(),
        event_time=obs.status_time or now,
        location_text=obs.location_text,
        confidence=obs.confidence,
        match_status="new_information",
        created_at=now,
    )
    db.add(event)

    # Activity log
    db.add(TrackingActivityLog(
        shipment_id=obs.shipment_id,
        container_id=obs.container_id,
        transport_job_id=obs.transport_job_id,
        tracking_provider_id=obs.tracking_provider_id,
        activity_type="manual_observation",
        safe_summary=f"Manual observation: {normalized} at {obs.location_text or 'unknown'}",
        created_by_user_id=user.id,
        created_by_name=user.name,
        created_at=now,
    ))

    db.commit()
    db.refresh(obs)
    return obs


def create_observation_from_adapter(db: Session, data: dict[str, Any], source: str, user: Optional[AuthenticatedUser] = None) -> TrackingObservation:
    """Create an observation from an adapter (mock or real)."""
    now = datetime.utcnow()
    raw_status = data.get("raw_status", "")
    normalized = normalize_tracking_status(raw_status, data.get("provider_type", "other"))

    obs = TrackingObservation(
        tracking_watch_item_id=data.get("tracking_watch_item_id"),
        tracking_provider_id=data.get("tracking_provider_id"),
        shipment_id=data.get("shipment_id"),
        container_id=data.get("container_id"),
        transport_job_id=data.get("transport_job_id"),
        observation_type=data.get("observation_type", "container_status"),
        source=source,
        raw_status=raw_status,
        normalized_status=normalized,
        status_time=data.get("status_time"),
        location_text=normalize_location(data.get("location_text")),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        eta=data.get("eta"),
        etd=data.get("etd"),
        vessel_name=data.get("vessel_name"),
        voyage_no=data.get("voyage_no"),
        confidence=data.get("confidence", 0.5),
        is_customer_visible=data.get("is_customer_visible", False),
        observed_at=data.get("observed_at", now),
        received_at=now,
    )
    db.add(obs)
    db.flush()

    # Update watch item
    if obs.tracking_watch_item_id:
        wi = db.query(TrackingWatchItem).filter(TrackingWatchItem.id == obs.tracking_watch_item_id).first()
        if wi:
            wi.last_observation_at = now
            wi.last_sync_at = now
            wi.updated_at = now

    # Create tracking event
    event = TrackingEvent(
        tracking_observation_id=obs.id,
        shipment_id=obs.shipment_id,
        container_id=obs.container_id,
        transport_job_id=obs.transport_job_id,
        event_key=map_observation_to_event_key(normalized),
        event_label=normalized.replace("_", " ").title(),
        event_time=obs.status_time or now,
        location_text=obs.location_text,
        confidence=obs.confidence,
        match_status="new_information",
        created_at=now,
    )
    db.add(event)

    db.commit()
    db.refresh(obs)
    return obs


def list_observations(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    watch_item_id: Optional[int] = None,
    observation_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TrackingObservation]:
    q = db.query(TrackingObservation)
    if shipment_id:
        q = q.filter(TrackingObservation.shipment_id == shipment_id)
    if watch_item_id:
        q = q.filter(TrackingObservation.tracking_watch_item_id == watch_item_id)
    if observation_type:
        q = q.filter(TrackingObservation.observation_type == observation_type)
    return q.order_by(TrackingObservation.received_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def list_tracking_events(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    container_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TrackingEvent]:
    q = db.query(TrackingEvent)
    if shipment_id:
        q = q.filter(TrackingEvent.shipment_id == shipment_id)
    if container_id:
        q = q.filter(TrackingEvent.container_id == container_id)
    return q.order_by(TrackingEvent.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()
