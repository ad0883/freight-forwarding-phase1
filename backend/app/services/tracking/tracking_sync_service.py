"""Tracking sync service — run mock/manual adapters and record sync runs."""
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.tracking import (
    TrackingActivityLog,
    TrackingObservation,
    TrackingProvider,
    TrackingSyncRun,
    TrackingWatchItem,
)
from app.services.tracking.tracking_observation_service import create_observation_from_adapter
from app.services.tracking.tracking_suggestion_service import create_mismatch, create_suggestion

logger = logging.getLogger(__name__)

# Mock data for simulated tracking
MOCK_SHIPPING_LINE_EVENTS = [
    {"raw_status": "Gate In", "location_text": "JNPT, Mumbai", "observation_type": "container_status"},
    {"raw_status": "Loaded on Vessel", "location_text": "JNPT, Mumbai", "observation_type": "container_status"},
    {"raw_status": "Vessel Departed", "location_text": "JNPT, Mumbai", "observation_type": "vessel_status"},
    {"raw_status": "In Transit", "location_text": "Arabian Sea", "observation_type": "container_status"},
    {"raw_status": "Vessel Arrived", "location_text": "Jebel Ali, Dubai", "observation_type": "vessel_status"},
    {"raw_status": "Discharged", "location_text": "Jebel Ali, Dubai", "observation_type": "container_status"},
]

MOCK_VESSEL_EVENTS = [
    {"raw_status": "Departed", "vessel_name": "MSC ANNA", "voyage_no": "VA2601", "location_text": "JNPT"},
    {"raw_status": "In Transit", "vessel_name": "MSC ANNA", "voyage_no": "VA2601", "location_text": "Arabian Sea"},
    {"raw_status": "Arrived", "vessel_name": "MSC ANNA", "voyage_no": "VA2601", "location_text": "Jebel Ali"},
]

MOCK_TERMINAL_EVENTS = [
    {"raw_status": "Gate In", "location_text": "JNPT Terminal 3", "observation_type": "terminal_status"},
    {"raw_status": "Loaded", "location_text": "JNPT Terminal 3", "observation_type": "terminal_status"},
    {"raw_status": "Gate Out", "location_text": "JNPT Terminal 3", "observation_type": "terminal_status"},
]

MOCK_GPS_EVENTS = [
    {"raw_status": "In Transit", "location_text": "NH4 near Panvel", "latitude": 18.99, "longitude": 73.12},
    {"raw_status": "In Transit", "location_text": "Pune-Mumbai Expressway", "latitude": 18.75, "longitude": 73.40},
    {"raw_status": "Delivered", "location_text": "JNPT Gate 4", "latitude": 18.95, "longitude": 72.95},
]


def run_tracking_sync(
    db: Session,
    scope: str = "manual",
    user: Optional[AuthenticatedUser] = None,
    provider_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    watch_item_id: Optional[int] = None,
) -> TrackingSyncRun:
    """Run a tracking sync. For Phase 21, only mock/manual adapters are supported."""
    now = datetime.utcnow()
    sync_run = TrackingSyncRun(
        tracking_provider_id=provider_id,
        started_at=now,
        status="running",
        scope=scope,
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else None,
    )
    db.add(sync_run)
    db.flush()

    try:
        # Determine watch items to process
        q = db.query(TrackingWatchItem).filter(TrackingWatchItem.status == "active")
        if watch_item_id:
            q = q.filter(TrackingWatchItem.id == watch_item_id)
        elif shipment_id:
            q = q.filter(TrackingWatchItem.shipment_id == shipment_id)
        elif provider_id:
            q = q.filter(TrackingWatchItem.tracking_provider_id == provider_id)

        watch_items = q.all()
        observations_created = 0
        suggestions_created = 0
        mismatches_created = 0

        for wi in watch_items:
            # Get provider
            provider = None
            if wi.tracking_provider_id:
                provider = db.query(TrackingProvider).filter(TrackingProvider.id == wi.tracking_provider_id).first()

            if provider and provider.is_mock:
                obs = _run_mock_adapter(db, wi, provider, user)
                if obs:
                    observations_created += 1
                    # Create a suggestion if confidence is high enough
                    if obs.confidence >= 0.7:
                        create_suggestion(db, {
                            "tracking_observation_id": obs.id,
                            "shipment_id": obs.shipment_id,
                            "container_id": obs.container_id,
                            "transport_job_id": obs.transport_job_id,
                            "suggestion_type": "container_status_change" if obs.observation_type == "container_status" else "manual_review",
                            "target_entity_type": "container" if obs.container_id else "shipment",
                            "target_entity_id": obs.container_id or obs.shipment_id,
                            "target_field": "status",
                            "suggested_value": obs.normalized_status,
                            "confidence": obs.confidence,
                            "risk_level": "medium" if obs.confidence < 0.9 else "low",
                        })
                        suggestions_created += 1

            wi.last_sync_at = now
            wi.updated_at = now

        sync_run.watch_items_processed = len(watch_items)
        sync_run.observations_created = observations_created
        sync_run.suggestions_created = suggestions_created
        sync_run.mismatches_created = mismatches_created
        sync_run.status = "completed"
        sync_run.completed_at = datetime.utcnow()

    except Exception as e:
        logger.error(f"Tracking sync failed: {e}")
        sync_run.status = "failed"
        sync_run.error_message = str(e)[:500]
        sync_run.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(sync_run)
    return sync_run


def _run_mock_adapter(
    db: Session,
    watch_item: TrackingWatchItem,
    provider: TrackingProvider,
    user: Optional[AuthenticatedUser] = None,
) -> Optional[TrackingObservation]:
    """Run a mock adapter to generate a simulated observation."""
    events = []
    source = "mock_adapter"

    if provider.provider_key == "mock_shipping_line":
        events = MOCK_SHIPPING_LINE_EVENTS
        source = "shipping_line_adapter"
    elif provider.provider_key == "mock_vessel_schedule":
        events = MOCK_VESSEL_EVENTS
        source = "vessel_schedule_adapter"
    elif provider.provider_key == "mock_terminal":
        events = MOCK_TERMINAL_EVENTS
        source = "terminal_adapter"
    elif provider.provider_key == "mock_transport_gps":
        events = MOCK_GPS_EVENTS
        source = "transport_gps_adapter"

    if not events:
        return None

    # Pick a random event from the mock data
    event_data = random.choice(events)
    now = datetime.utcnow()

    obs_data = {
        "tracking_watch_item_id": watch_item.id,
        "tracking_provider_id": provider.id,
        "shipment_id": watch_item.shipment_id,
        "container_id": watch_item.container_id,
        "transport_job_id": watch_item.transport_job_id,
        "observation_type": event_data.get("observation_type", "container_status"),
        "raw_status": event_data["raw_status"],
        "location_text": event_data.get("location_text"),
        "latitude": event_data.get("latitude"),
        "longitude": event_data.get("longitude"),
        "vessel_name": event_data.get("vessel_name"),
        "voyage_no": event_data.get("voyage_no"),
        "status_time": now - timedelta(minutes=random.randint(5, 120)),
        "confidence": round(random.uniform(0.6, 0.95), 2),
        "provider_type": provider.provider_type,
    }

    return create_observation_from_adapter(db, obs_data, source, user)


def list_sync_runs(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    provider_id: Optional[int] = None,
    limit: int = 50,
) -> list[TrackingSyncRun]:
    q = db.query(TrackingSyncRun)
    if status_filter:
        q = q.filter(TrackingSyncRun.status == status_filter)
    if provider_id:
        q = q.filter(TrackingSyncRun.tracking_provider_id == provider_id)
    return q.order_by(TrackingSyncRun.started_at.desc()).limit(limit).all()


def get_tracking_summary(db: Session) -> dict[str, Any]:
    """Get tracking dashboard summary."""
    active_watches = db.query(TrackingWatchItem).filter(TrackingWatchItem.status == "active").count()
    pending_suggestions = db.query(TrackingObservation).count()  # total observations
    from app.models.tracking import TrackingSuggestedUpdate, TrackingMismatch
    pending_sugg = db.query(TrackingSuggestedUpdate).filter(TrackingSuggestedUpdate.status == "pending_review").count()
    open_mismatches = db.query(TrackingMismatch).filter(TrackingMismatch.status == "open").count()
    failed_syncs = db.query(TrackingSyncRun).filter(TrackingSyncRun.status == "failed").count()

    # Stale tracking: watch items not synced in 24h
    stale_cutoff = datetime.utcnow() - timedelta(hours=24)
    stale_count = db.query(TrackingWatchItem).filter(
        TrackingWatchItem.status == "active",
        (TrackingWatchItem.last_sync_at < stale_cutoff) | (TrackingWatchItem.last_sync_at.is_(None))
    ).count()

    return {
        "active_watch_items": active_watches,
        "total_observations": pending_suggestions,
        "pending_suggestions": pending_sugg,
        "open_mismatches": open_mismatches,
        "failed_sync_runs": failed_syncs,
        "stale_tracking": stale_count,
    }


def build_customer_safe_tracking_summary(db: Session, shipment_id: int) -> list[dict[str, Any]]:
    """Build portal-safe tracking summary. Hides provider internals."""
    observations = db.query(TrackingObservation).filter(
        TrackingObservation.shipment_id == shipment_id,
        TrackingObservation.is_customer_visible.is_(True),
    ).order_by(TrackingObservation.observed_at.desc()).limit(20).all()

    result = []
    for obs in observations:
        result.append({
            "status": obs.normalized_status,
            "location": obs.location_text,
            "time": obs.status_time.isoformat() if obs.status_time else obs.observed_at.isoformat(),
            "eta": obs.eta.isoformat() if obs.eta else None,
            "vessel_name": obs.vessel_name,
            "voyage_no": obs.voyage_no,
            # Intentionally omit: provider details, confidence, raw_status, metadata
        })
    return result
