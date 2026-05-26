"""Phase 9 event recording service.

Recording an operational event must never break the original business action.
Metadata is sanitized via an allowlist style (sensitive keys redacted) before
being persisted.
"""
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.operational_event import OperationalEvent
from app.models.validation_issue import ValidationIssue


logger = logging.getLogger(__name__)


class OperationalEventType(str, Enum):
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_UPDATED = "shipment.updated"
    SHIPMENT_ARCHIVED = "shipment.archived"
    SHIPMENT_RESTORED = "shipment.restored"
    SHIPMENT_WORKFLOW_STATUS_UPDATED = "shipment.workflow_status_updated"

    PARTY_CREATED = "party.created"
    PARTY_UPDATED = "party.updated"
    PARTY_DEACTIVATED = "party.deactivated"
    PARTY_REACTIVATED = "party.reactivated"
    PARTY_DELETED = "party.deleted"

    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_CANCELLED = "task.cancelled"
    TASK_RESTORED = "task.restored"
    TASK_DELETED = "task.deleted"

    CHARGE_CREATED = "charge.created"
    CHARGE_UPDATED = "charge.updated"
    CHARGE_CANCELLED = "charge.cancelled"
    CHARGE_MARKED_PAID = "charge.marked_paid"
    CHARGE_MARKED_RECEIVED = "charge.marked_received"

    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_VERSION_UPLOADED = "document.version_uploaded"
    DOCUMENT_VERSION_APPROVED = "document.version_approved"
    DOCUMENT_VERSION_REJECTED = "document.version_rejected"
    DOCUMENT_VERSION_ARCHIVED = "document.version_archived"
    DOCUMENT_VERSION_ROLLBACK = "document.version_rollback"
    DOCUMENT_FILE_DOWNLOADED = "document.file_downloaded"
    DOCUMENT_INTELLIGENCE_RUN_STARTED = "document_intelligence.run_started"
    DOCUMENT_INTELLIGENCE_RUN_COMPLETED = "document_intelligence.run_completed"
    DOCUMENT_INTELLIGENCE_RUN_FAILED = "document_intelligence.run_failed"
    DOCUMENT_INTELLIGENCE_MISMATCH_FOUND = "document_intelligence.mismatch_found"
    DOCUMENT_INTELLIGENCE_SUGGESTION_CREATED = "document_intelligence.suggestion_created"
    DOCUMENT_INTELLIGENCE_SUGGESTION_APPROVED = "document_intelligence.suggestion_approved"
    DOCUMENT_INTELLIGENCE_SUGGESTION_REJECTED = "document_intelligence.suggestion_rejected"
    DOCUMENT_INTELLIGENCE_SUGGESTION_APPLIED = "document_intelligence.suggestion_applied"
    BL_MANAGEMENT_UPDATED = "bl.updated"
    DEMURRAGE_UPDATED = "demurrage.updated"

    EMAIL_SUGGESTION_APPLIED = "email_suggestion.apply"
    EMAIL_SUGGESTION_REJECTED = "email_suggestion.reject"

    NOTIFICATION_CHECKS_RUN = "notification.run_checks"


SENSITIVE_KEY_FRAGMENTS = {
    "access_token",
    "api_key",
    "authorization",
    "auth_code",
    "client_secret",
    "code_verifier",
    "cookie",
    "database_url",
    "env",
    "gmail_token",
    "hashed_password",
    "jwt",
    "oauth_code",
    "password",
    "refresh_token",
    "secret",
    "token",
}

ALLOWED_VALIDATION_STATUSES = {
    "not_checked",
    "passed",
    "warning",
    "failed",
    "manual_review_required",
}


def record_operational_event(
    db: Session,
    event_type: str,
    entity_type: str,
    *,
    entity_id: Optional[int] = None,
    entity_label: Optional[str] = None,
    shipment_id: Optional[int] = None,
    actor_user: Any = None,
    source: str = "user",
    previous_state: Optional[dict[str, Any]] = None,
    new_state: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    correlation_id: Optional[str] = None,
    run_validation: bool = True,
) -> Optional[OperationalEvent]:
    """Record an operational event and optionally trigger validation.

    Errors here must never propagate to the caller; the original business
    action takes precedence.
    """
    try:
        event = OperationalEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=_truncate(entity_label, 250),
            shipment_id=shipment_id,
            actor_user_id=getattr(actor_user, "id", None),
            actor_name=getattr(actor_user, "name", None),
            actor_email=getattr(actor_user, "email", None),
            actor_role=getattr(actor_user, "role", None),
            source=source if source in _allowed_sources() else "system",
            correlation_id=correlation_id or _request_correlation_id(request),
            request_id=_request_id(request),
            previous_state_json=_safe_json(previous_state),
            new_state_json=_safe_json(new_state),
            metadata_json=_safe_json(metadata),
            validation_status="not_checked",
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.flush()
    except Exception:
        logger.exception(
            "Unable to record operational event event_type=%s entity_type=%s",
            event_type,
            entity_type,
        )
        try:
            db.rollback()
        except Exception:
            pass
        return None

    if not run_validation:
        try:
            db.commit()
        except Exception:
            logger.exception("Unable to commit operational event without validation")
            db.rollback()
            return None
        return event

    try:
        # Imported lazily to avoid circular imports between services.
        from app.services.validation_engine import (
            create_validation_issues_from_results,
            run_validation_for_event,
            summarize_validation_status,
        )
        from app.services.validation_issue_service import (
            create_critical_notifications_for_issues,
        )

        results = run_validation_for_event(db, event)
        issues = create_validation_issues_from_results(db, event, results)
        event.validation_status = summarize_validation_status(results)
        if event.validation_status not in ALLOWED_VALIDATION_STATUSES:
            event.validation_status = "warning"
        db.flush()
        if issues:
            create_critical_notifications_for_issues(db, issues)
        db.commit()
    except Exception:
        logger.exception(
            "Validation pipeline failed for operational event event_type=%s",
            event_type,
        )
        try:
            db.rollback()
        except Exception:
            pass
        # Re-attempt to persist the bare event without validation outcome
        # so the operational trail remains intact.
        try:
            event = OperationalEvent(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_label=_truncate(entity_label, 250),
                shipment_id=shipment_id,
                actor_user_id=getattr(actor_user, "id", None),
                actor_name=getattr(actor_user, "name", None),
                actor_email=getattr(actor_user, "email", None),
                actor_role=getattr(actor_user, "role", None),
                source=source if source in _allowed_sources() else "system",
                correlation_id=correlation_id,
                request_id=_request_id(request),
                previous_state_json=_safe_json(previous_state),
                new_state_json=_safe_json(new_state),
                metadata_json=_safe_json(metadata),
                validation_status="not_checked",
                created_at=datetime.utcnow(),
            )
            db.add(event)
            db.commit()
        except Exception:
            logger.exception("Unable to fall back to bare event recording")
            db.rollback()
            return None
    return event


def list_operational_events(
    db: Session,
    *,
    event_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    source: Optional[str] = None,
    validation_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[OperationalEvent]:
    query = db.query(OperationalEvent)
    if event_type:
        query = query.filter(OperationalEvent.event_type == event_type)
    if entity_type:
        query = query.filter(OperationalEvent.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(OperationalEvent.entity_id == entity_id)
    if shipment_id is not None:
        query = query.filter(OperationalEvent.shipment_id == shipment_id)
    if source:
        query = query.filter(OperationalEvent.source == source)
    if validation_status:
        query = query.filter(OperationalEvent.validation_status == validation_status)
    if date_from:
        query = query.filter(OperationalEvent.created_at >= date_from)
    if date_to:
        query = query.filter(OperationalEvent.created_at <= date_to)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (OperationalEvent.entity_label.ilike(pattern))
            | (OperationalEvent.event_type.ilike(pattern))
        )
    return (
        query.order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
        .limit(min(max(limit, 1), 200))
        .offset(max(offset, 0))
        .all()
    )


def get_operational_event(db: Session, event_id: int) -> Optional[OperationalEvent]:
    return db.query(OperationalEvent).filter(OperationalEvent.id == event_id).first()


def diff_state(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for key, value in after.items():
        if key not in before:
            changed.append(key)
            continue
        if _safe_value(before[key]) != _safe_value(value):
            changed.append(key)
    return sorted(changed)


def _allowed_sources() -> set[str]:
    return {
        "user",
        "system",
        "gmail",
        "ai",
        "scheduler",
        "workflow",
        "finance",
        "notification",
    }


def _safe_json(value: Any) -> Optional[Any]:
    if value is None:
        return None
    return _safe_value(value)


def _safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _safe_dict(value)
    if isinstance(value, list):
        return [_safe_value(item) for item in value[:50]]
    if isinstance(value, tuple):
        return [_safe_value(item) for item in list(value)[:50]]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > 500:
            return f"{value[:500]}..."
        return value
    return str(value)


def _safe_dict(values: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in values.items():
        safe_key = str(key)
        if _is_sensitive_key(safe_key):
            sanitized[safe_key] = "[redacted]"
            continue
        sanitized[safe_key] = _safe_value(value)
    return sanitized


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _truncate(value: Optional[str], length: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= length else f"{text[: length - 3]}..."


def _request_correlation_id(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    for header in ("x-correlation-id", "x-request-id"):
        value = request.headers.get(header)
        if value:
            return _truncate(value, 120)
    return None


def _request_id(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    value = request.headers.get("x-request-id") or uuid.uuid4().hex
    return _truncate(value, 120)


def safe_metadata(values: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    return _safe_dict(dict(values))
