"""Phase 9 validation issue management."""
import logging
from datetime import date, datetime
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.validation_issue import ValidationIssue


logger = logging.getLogger(__name__)


def list_validation_issues(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    rule_key: Optional[str] = None,
    entity_type: Optional[str] = None,
    shipment_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ValidationIssue]:
    query = db.query(ValidationIssue)
    if status_filter:
        query = query.filter(ValidationIssue.status == status_filter)
    if severity:
        query = query.filter(ValidationIssue.severity == severity)
    if rule_key:
        query = query.filter(ValidationIssue.rule_key == rule_key)
    if entity_type:
        query = query.filter(ValidationIssue.entity_type == entity_type)
    if shipment_id is not None:
        query = query.filter(ValidationIssue.shipment_id == shipment_id)
    if date_from:
        query = query.filter(ValidationIssue.created_at >= date_from)
    if date_to:
        query = query.filter(ValidationIssue.created_at <= date_to)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            ValidationIssue.message.ilike(pattern)
            | ValidationIssue.entity_label.ilike(pattern)
        )
    return (
        query.order_by(ValidationIssue.created_at.desc(), ValidationIssue.id.desc())
        .limit(min(max(limit, 1), 200))
        .offset(max(offset, 0))
        .all()
    )


def get_validation_issue(db: Session, issue_id: int) -> ValidationIssue:
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation issue not found")
    return issue


def acknowledge_issue(db: Session, issue_id: int, user: AuthenticatedUser) -> ValidationIssue:
    issue = get_validation_issue(db, issue_id)
    issue.status = "acknowledged"
    issue.acknowledged_at = datetime.utcnow()
    issue.acknowledged_by = user.id
    db.commit()
    db.refresh(issue)
    return issue


def resolve_issue(db: Session, issue_id: int, user: AuthenticatedUser) -> ValidationIssue:
    issue = get_validation_issue(db, issue_id)
    now = datetime.utcnow()
    issue.status = "resolved"
    issue.resolved_at = now
    issue.resolved_by = user.id
    if issue.acknowledged_at is None:
        issue.acknowledged_at = now
        issue.acknowledged_by = user.id
    db.commit()
    db.refresh(issue)
    return issue


def dismiss_issue(db: Session, issue_id: int, user: AuthenticatedUser) -> ValidationIssue:
    issue = get_validation_issue(db, issue_id)
    issue.status = "dismissed"
    if issue.acknowledged_at is None:
        issue.acknowledged_at = datetime.utcnow()
        issue.acknowledged_by = user.id
    db.commit()
    db.refresh(issue)
    return issue


def create_critical_notifications_for_issues(
    db: Session, issues: Iterable[ValidationIssue]
) -> int:
    """Create deduped critical notifications for severity=critical issues."""
    try:
        from app.services.notification_service import create_notification
    except Exception:
        logger.exception("Notification service unavailable for validation issue dedupe")
        return 0

    created = 0
    today = date.today().isoformat()
    for issue in issues:
        if issue.severity != "critical":
            continue
        entity_id = issue.entity_id if issue.entity_id is not None else "none"
        dedupe_key = f"validation_issue:{issue.rule_key}:{issue.entity_type}:{entity_id}"
        action_url = "/validation-issues"
        try:
            _, was_created = create_notification(
                db,
                title="Manual review required",
                message=issue.message,
                category="system",
                priority="critical",
                target_role="ADMIN",
                entity_type="validation_issue",
                entity_id=issue.id,
                entity_label=issue.entity_label,
                action_url=action_url,
                dedupe_key=dedupe_key,
                source="system",
                metadata={
                    "rule_key": issue.rule_key,
                    "entity_type": issue.entity_type,
                    "entity_id": issue.entity_id,
                    "shipment_id": issue.shipment_id,
                    "date": today,
                },
            )
            if was_created:
                created += 1
        except Exception:
            logger.exception(
                "Could not create dedupe notification for validation issue rule_key=%s",
                issue.rule_key,
            )
    return created


def count_issues_by_status(db: Session) -> dict[str, int]:
    rows = (
        db.query(ValidationIssue.status, ValidationIssue.severity)
        .all()
    )
    counts: dict[str, int] = {"open": 0, "acknowledged": 0, "resolved": 0, "dismissed": 0}
    for status_value, _severity in rows:
        if status_value in counts:
            counts[status_value] += 1
    return counts
