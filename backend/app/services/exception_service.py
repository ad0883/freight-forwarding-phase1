"""Phase 15 exception engine core service.

Manages exception case lifecycle: create, dedupe, assign, acknowledge,
resolve, dismiss, reopen, escalate, comment, link.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.exception_case import (
    ExceptionCase,
    ExceptionCaseAssignment,
    ExceptionCaseComment,
    ExceptionCaseEscalation,
    ExceptionCaseLink,
    ExceptionCaseStatusHistory,
    ExceptionCaseWatcher,
)

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = (
    "open", "acknowledged", "in_review", "reopened",
    "waiting_on_party", "waiting_on_document", "waiting_on_finance",
    "waiting_on_customer", "waiting_on_vendor", "escalated",
)

TERMINAL_STATUSES = ("resolved", "dismissed")


def _generate_case_number() -> str:
    """Generate a unique case number."""
    now = datetime.utcnow()
    short_id = uuid.uuid4().hex[:6].upper()
    return f"EXC-{now.strftime('%Y%m%d')}-{short_id}"


def _sanitize_metadata(metadata: Optional[dict]) -> Optional[dict]:
    """Remove sensitive keys from metadata."""
    if not metadata:
        return metadata
    sensitive_keys = {
        "password", "jwt", "api_key", "gmail_token", "oauth_code",
        "database_url", "secret", "token", "bank_account", "card_number",
        "upi_secret", "raw_email_body", "raw_file_bytes",
    }
    return {
        k: v for k, v in metadata.items()
        if k.lower() not in sensitive_keys
    }


def create_exception_case(
    db: Session,
    data: dict[str, Any],
    user: Optional[AuthenticatedUser] = None,
) -> ExceptionCase:
    """Create a new exception case."""
    now = datetime.utcnow()
    case = ExceptionCase(
        case_number=_generate_case_number(),
        title=data["title"],
        description=data.get("description"),
        category=data.get("category", "other"),
        source=data.get("source", "manual"),
        severity=data.get("severity", "medium"),
        priority=data.get("priority", "p3"),
        status="open",
        risk_score=data.get("risk_score", 0),
        dedupe_key=data.get("dedupe_key"),
        entity_type=data.get("entity_type"),
        entity_id=data.get("entity_id"),
        shipment_id=data.get("shipment_id"),
        party_id=data.get("party_id"),
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else None,
        due_at=data.get("due_at"),
        first_seen_at=now,
        last_seen_at=now,
        metadata_json=_sanitize_metadata(data.get("metadata_json")),
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    db.flush()

    # Record initial status history
    history = ExceptionCaseStatusHistory(
        exception_case_id=case.id,
        old_status=None,
        new_status="open",
        changed_by_user_id=user.id if user else None,
        changed_by_name=user.name if user else None,
        reason="Exception case created",
        created_at=now,
    )
    db.add(history)
    db.commit()
    db.refresh(case)
    return case


def create_or_update_exception_from_source(
    db: Session,
    source_type: str,
    source_id: int,
    data: dict[str, Any],
    user: Optional[AuthenticatedUser] = None,
) -> ExceptionCase:
    """Create or update an exception case from a detection source (deduped)."""
    dedupe_key = data.get("dedupe_key") or f"{source_type}:{source_id}"
    now = datetime.utcnow()

    # Check for existing active case with same dedupe_key
    existing = (
        db.query(ExceptionCase)
        .filter(
            ExceptionCase.dedupe_key == dedupe_key,
            ExceptionCase.status.in_(ACTIVE_STATUSES),
        )
        .first()
    )

    if existing:
        existing.last_seen_at = now
        existing.updated_at = now
        if data.get("severity") and data["severity"] != existing.severity:
            existing.severity = data["severity"]
        if data.get("risk_score") and data["risk_score"] > existing.risk_score:
            existing.risk_score = data["risk_score"]
        if data.get("metadata_json"):
            merged = dict(existing.metadata_json or {})
            merged.update(_sanitize_metadata(data["metadata_json"]) or {})
            existing.metadata_json = merged
        db.commit()
        db.refresh(existing)
        return existing

    # Create new case
    data["dedupe_key"] = dedupe_key
    data["source"] = source_type
    return create_exception_case(db, data, user)


def get_exception_case(db: Session, case_id: int) -> Optional[ExceptionCase]:
    """Get a single exception case by ID."""
    return db.query(ExceptionCase).filter(ExceptionCase.id == case_id).first()


def list_exception_cases(
    db: Session,
    *,
    category: Optional[str] = None,
    source: Optional[str] = None,
    severity: Optional[str] = None,
    priority: Optional[str] = None,
    status_filter: Optional[str] = None,
    assigned_to_user_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    party_id: Optional[int] = None,
    overdue: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ExceptionCase]:
    """List exception cases with filters."""
    query = db.query(ExceptionCase)
    if category:
        query = query.filter(ExceptionCase.category == category)
    if source:
        query = query.filter(ExceptionCase.source == source)
    if severity:
        query = query.filter(ExceptionCase.severity == severity)
    if priority:
        query = query.filter(ExceptionCase.priority == priority)
    if status_filter:
        query = query.filter(ExceptionCase.status == status_filter)
    if assigned_to_user_id is not None:
        query = query.filter(ExceptionCase.assigned_to_user_id == assigned_to_user_id)
    if shipment_id is not None:
        query = query.filter(ExceptionCase.shipment_id == shipment_id)
    if party_id is not None:
        query = query.filter(ExceptionCase.party_id == party_id)
    if overdue:
        now = datetime.utcnow()
        query = query.filter(
            ExceptionCase.due_at.isnot(None),
            ExceptionCase.due_at < now,
            ExceptionCase.status.in_(ACTIVE_STATUSES),
        )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            ExceptionCase.title.ilike(pattern)
            | ExceptionCase.case_number.ilike(pattern)
            | ExceptionCase.description.ilike(pattern)
        )
    return (
        query.order_by(ExceptionCase.created_at.desc(), ExceptionCase.id.desc())
        .limit(min(max(limit, 1), 200))
        .offset(max(offset, 0))
        .all()
    )


def _change_status(
    db: Session,
    case: ExceptionCase,
    new_status: str,
    user: Optional[AuthenticatedUser],
    reason: Optional[str] = None,
) -> None:
    """Record a status change."""
    old_status = case.status
    case.status = new_status
    case.updated_at = datetime.utcnow()
    history = ExceptionCaseStatusHistory(
        exception_case_id=case.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=user.id if user else None,
        changed_by_name=user.name if user else None,
        reason=reason,
        created_at=datetime.utcnow(),
    )
    db.add(history)


def acknowledge_exception_case(
    db: Session,
    case_id: int,
    user: AuthenticatedUser,
    notes: Optional[str] = None,
) -> ExceptionCase:
    """Acknowledge an exception case."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")
    _change_status(db, case, "acknowledged", user, notes or "Acknowledged")
    db.commit()
    db.refresh(case)
    return case


def assign_exception_case(
    db: Session,
    case_id: int,
    assignee_user_id: Optional[int] = None,
    assignee_role: Optional[str] = None,
    user: Optional[AuthenticatedUser] = None,
    notes: Optional[str] = None,
) -> ExceptionCase:
    """Assign an exception case to a user or role."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")

    now = datetime.utcnow()

    # Resolve assignee name
    assignee_name = None
    if assignee_user_id:
        from app.models import User
        target_user = db.query(User).filter(User.id == assignee_user_id).first()
        if target_user:
            assignee_name = target_user.name
            assignee_role = assignee_role or target_user.role

    case.assigned_to_user_id = assignee_user_id
    case.assigned_to_name = assignee_name
    case.assigned_to_role = assignee_role
    case.updated_at = now

    assignment = ExceptionCaseAssignment(
        exception_case_id=case.id,
        assigned_to_user_id=assignee_user_id,
        assigned_to_name=assignee_name,
        assigned_to_role=assignee_role,
        assigned_by_user_id=user.id if user else None,
        assigned_by_name=user.name if user else None,
        assigned_at=now,
        notes=notes,
    )
    db.add(assignment)
    db.commit()
    db.refresh(case)
    return case


def resolve_exception_case(
    db: Session,
    case_id: int,
    user: AuthenticatedUser,
    resolution_notes: str,
) -> ExceptionCase:
    """Resolve an exception case."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")
    now = datetime.utcnow()
    _change_status(db, case, "resolved", user, resolution_notes)
    case.resolved_at = now
    case.resolved_by_user_id = user.id
    case.resolved_by_name = user.name
    case.resolution_notes = resolution_notes
    db.commit()
    db.refresh(case)
    return case


def dismiss_exception_case(
    db: Session,
    case_id: int,
    user: AuthenticatedUser,
    dismissal_reason: str,
) -> ExceptionCase:
    """Dismiss an exception case."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")
    now = datetime.utcnow()
    _change_status(db, case, "dismissed", user, dismissal_reason)
    case.dismissed_at = now
    case.dismissed_by_user_id = user.id
    case.dismissed_by_name = user.name
    case.dismissal_reason = dismissal_reason
    db.commit()
    db.refresh(case)
    return case


def reopen_exception_case(
    db: Session,
    case_id: int,
    user: AuthenticatedUser,
    reason: Optional[str] = None,
) -> ExceptionCase:
    """Reopen a resolved or dismissed exception case."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")
    _change_status(db, case, "reopened", user, reason or "Reopened")
    case.resolved_at = None
    case.resolved_by_user_id = None
    case.resolved_by_name = None
    case.resolution_notes = None
    case.dismissed_at = None
    case.dismissed_by_user_id = None
    case.dismissed_by_name = None
    case.dismissal_reason = None
    case.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    return case


def escalate_exception_case(
    db: Session,
    case_id: int,
    user: AuthenticatedUser,
    severity: Optional[str] = None,
    priority: Optional[str] = None,
    reason: str = "",
) -> ExceptionCase:
    """Escalate an exception case."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")

    now = datetime.utcnow()
    from_severity = case.severity
    from_priority = case.priority

    if severity:
        case.severity = severity
    if priority:
        case.priority = priority

    _change_status(db, case, "escalated", user, reason)

    escalation = ExceptionCaseEscalation(
        exception_case_id=case.id,
        from_severity=from_severity,
        to_severity=case.severity,
        from_priority=from_priority,
        to_priority=case.priority,
        escalation_reason=reason,
        escalated_by_user_id=user.id,
        escalated_by_name=user.name,
        escalated_at=now,
    )
    db.add(escalation)
    db.commit()
    db.refresh(case)
    return case


def add_exception_comment(
    db: Session,
    case_id: int,
    user: AuthenticatedUser,
    comment_text: str,
    is_internal: bool = True,
) -> ExceptionCaseComment:
    """Add a comment to an exception case."""
    case = get_exception_case(db, case_id)
    if not case:
        raise ValueError("Exception case not found")

    comment = ExceptionCaseComment(
        exception_case_id=case.id,
        author_user_id=user.id,
        author_name=user.name,
        comment_text=comment_text,
        is_internal=is_internal,
        created_at=datetime.utcnow(),
    )
    db.add(comment)
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return comment


def link_exception_entity(
    db: Session,
    case_id: int,
    linked_type: str,
    linked_id: int,
    relationship_type: str = "related",
    linked_label: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> ExceptionCaseLink:
    """Link an entity to an exception case."""
    # Avoid duplicate links
    existing = (
        db.query(ExceptionCaseLink)
        .filter(
            ExceptionCaseLink.exception_case_id == case_id,
            ExceptionCaseLink.linked_type == linked_type,
            ExceptionCaseLink.linked_id == linked_id,
            ExceptionCaseLink.relationship_type == relationship_type,
        )
        .first()
    )
    if existing:
        return existing

    link = ExceptionCaseLink(
        exception_case_id=case_id,
        linked_type=linked_type,
        linked_id=linked_id,
        linked_label=linked_label,
        relationship_type=relationship_type,
        created_at=datetime.utcnow(),
        metadata_json=_sanitize_metadata(metadata),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_exception_summary(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> dict[str, Any]:
    """Get summary counts for the manual review dashboard."""
    now = datetime.utcnow()
    all_active = (
        db.query(ExceptionCase)
        .filter(ExceptionCase.status.in_(ACTIVE_STATUSES))
        .all()
    )

    total_open = len(all_active)
    total_critical = sum(1 for c in all_active if c.severity == "critical")
    total_overdue = sum(1 for c in all_active if c.due_at and c.due_at < now)
    total_assigned_to_me = 0
    if user:
        total_assigned_to_me = sum(
            1 for c in all_active if c.assigned_to_user_id == user.id
        )

    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for c in all_active:
        by_category[c.category] = by_category.get(c.category, 0) + 1
        by_severity[c.severity] = by_severity.get(c.severity, 0) + 1
        by_status[c.status] = by_status.get(c.status, 0) + 1
        by_source[c.source] = by_source.get(c.source, 0) + 1

    return {
        "total_open": total_open,
        "total_critical": total_critical,
        "total_assigned_to_me": total_assigned_to_me,
        "total_overdue": total_overdue,
        "by_category": by_category,
        "by_severity": by_severity,
        "by_status": by_status,
        "by_source": by_source,
    }
