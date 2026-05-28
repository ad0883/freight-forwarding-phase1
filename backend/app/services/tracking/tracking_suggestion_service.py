"""Tracking suggestion service — create and manage suggested updates."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.tracking import TrackingMismatch, TrackingObservation, TrackingSuggestedUpdate


def create_suggestion(db: Session, data: dict[str, Any], user: Optional[AuthenticatedUser] = None) -> TrackingSuggestedUpdate:
    """Create a tracking suggested update."""
    now = datetime.utcnow()
    suggestion = TrackingSuggestedUpdate(
        tracking_observation_id=data.get("tracking_observation_id"),
        tracking_event_id=data.get("tracking_event_id"),
        shipment_id=data.get("shipment_id"),
        container_id=data.get("container_id"),
        transport_job_id=data.get("transport_job_id"),
        suggestion_type=data.get("suggestion_type", "manual_review"),
        target_entity_type=data.get("target_entity_type", "shipment"),
        target_entity_id=data.get("target_entity_id"),
        target_field=data.get("target_field", "status"),
        current_value=data.get("current_value"),
        suggested_value=data.get("suggested_value"),
        confidence=data.get("confidence", 0.5),
        risk_level=data.get("risk_level", "low"),
        status="pending_review",
        created_at=now,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def list_suggestions(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    shipment_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TrackingSuggestedUpdate]:
    q = db.query(TrackingSuggestedUpdate)
    if status_filter:
        q = q.filter(TrackingSuggestedUpdate.status == status_filter)
    if shipment_id:
        q = q.filter(TrackingSuggestedUpdate.shipment_id == shipment_id)
    return q.order_by(TrackingSuggestedUpdate.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def approve_suggestion(db: Session, suggestion_id: int, user: AuthenticatedUser) -> TrackingSuggestedUpdate:
    s = db.query(TrackingSuggestedUpdate).filter(TrackingSuggestedUpdate.id == suggestion_id).first()
    if not s:
        raise ValueError("Suggestion not found")
    s.status = "approved"
    s.reviewed_at = datetime.utcnow()
    s.reviewed_by_user_id = user.id
    s.reviewed_by_name = user.name
    db.commit()
    db.refresh(s)
    return s


def reject_suggestion(db: Session, suggestion_id: int, user: AuthenticatedUser, reason: Optional[str] = None) -> TrackingSuggestedUpdate:
    s = db.query(TrackingSuggestedUpdate).filter(TrackingSuggestedUpdate.id == suggestion_id).first()
    if not s:
        raise ValueError("Suggestion not found")
    s.status = "rejected"
    s.reviewed_at = datetime.utcnow()
    s.reviewed_by_user_id = user.id
    s.reviewed_by_name = user.name
    db.commit()
    db.refresh(s)
    return s


def dismiss_suggestion(db: Session, suggestion_id: int, user: AuthenticatedUser, reason: Optional[str] = None) -> TrackingSuggestedUpdate:
    s = db.query(TrackingSuggestedUpdate).filter(TrackingSuggestedUpdate.id == suggestion_id).first()
    if not s:
        raise ValueError("Suggestion not found")
    s.status = "dismissed"
    s.reviewed_at = datetime.utcnow()
    s.reviewed_by_user_id = user.id
    s.reviewed_by_name = user.name
    db.commit()
    db.refresh(s)
    return s


# --- Mismatches ---

def create_mismatch(db: Session, data: dict[str, Any], user: Optional[AuthenticatedUser] = None) -> TrackingMismatch:
    mm = TrackingMismatch(
        tracking_observation_id=data.get("tracking_observation_id"),
        shipment_id=data.get("shipment_id"),
        container_id=data.get("container_id"),
        transport_job_id=data.get("transport_job_id"),
        mismatch_type=data.get("mismatch_type", "other"),
        severity=data.get("severity", "medium"),
        title=data["title"],
        description=data.get("description"),
        status="open",
        created_at=datetime.utcnow(),
    )
    db.add(mm)
    db.commit()
    db.refresh(mm)
    return mm


def list_mismatches(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    shipment_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TrackingMismatch]:
    q = db.query(TrackingMismatch)
    if status_filter:
        q = q.filter(TrackingMismatch.status == status_filter)
    if shipment_id:
        q = q.filter(TrackingMismatch.shipment_id == shipment_id)
    return q.order_by(TrackingMismatch.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def resolve_mismatch(db: Session, mismatch_id: int, user: AuthenticatedUser) -> TrackingMismatch:
    mm = db.query(TrackingMismatch).filter(TrackingMismatch.id == mismatch_id).first()
    if not mm:
        raise ValueError("Mismatch not found")
    mm.status = "resolved"
    mm.resolved_at = datetime.utcnow()
    mm.resolved_by_user_id = user.id
    mm.resolved_by_name = user.name
    db.commit()
    db.refresh(mm)
    return mm
