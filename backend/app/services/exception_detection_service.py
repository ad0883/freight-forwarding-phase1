"""Phase 15 exception detection service.

Scans existing data sources (validation issues, document mismatches, finance
holds/risks, workflow logs, container risks, Gmail suggestions, overdue tasks)
and creates/updates exception cases.  Detection is idempotent and deduped.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.services.exception_service import create_or_update_exception_from_source, link_exception_entity

logger = logging.getLogger(__name__)


def run_exception_detection(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
    scope: Optional[str] = None,
) -> dict[str, int]:
    """Run all detection sources and return counts of created/updated cases."""
    results: dict[str, int] = {}

    detectors = [
        ("validation_issues", detect_from_validation_issues),
        ("document_mismatches", detect_from_document_mismatches),
        ("finance_holds", detect_from_finance_holds),
        ("finance_risks", detect_from_finance_risks),
        ("workflow_logs", detect_from_workflow_logs),
        ("container_risks", detect_from_container_risks),
        ("gmail_suggestions", detect_from_gmail_suggestions),
        ("overdue_tasks", detect_from_overdue_tasks),
    ]

    for name, detector in detectors:
        if scope and scope != name:
            continue
        try:
            count = detector(db, user)
            results[name] = count
        except Exception:
            logger.exception("Exception detection failed for %s", name)
            results[name] = 0

    return results


def detect_from_validation_issues(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from critical/blocking validation issues."""
    from app.models.validation_issue import ValidationIssue

    issues = (
        db.query(ValidationIssue)
        .filter(
            ValidationIssue.status.in_(["open", "acknowledged"]),
            ValidationIssue.severity.in_(["critical", "warning"]),
        )
        .all()
    )

    count = 0
    for issue in issues:
        # Only create exceptions for critical issues or warnings that are old
        if issue.severity == "warning":
            age = (datetime.utcnow() - issue.created_at).days if issue.created_at else 0
            if age < 3:
                continue

        dedupe_key = f"validation_issue:{issue.id}"
        severity = "high" if issue.severity == "critical" else "medium"
        priority = "p1" if issue.severity == "critical" else "p2"

        data = {
            "title": f"Validation: {issue.message[:200]}",
            "description": issue.message,
            "category": "validation",
            "source": "validation_issue",
            "severity": severity,
            "priority": priority,
            "dedupe_key": dedupe_key,
            "entity_type": issue.entity_type,
            "entity_id": issue.entity_id,
            "shipment_id": issue.shipment_id,
            "risk_score": 80 if issue.severity == "critical" else 50,
            "metadata_json": {
                "rule_key": issue.rule_key,
                "entity_label": issue.entity_label,
                "recommended_action": issue.recommended_action,
            },
        }
        case = create_or_update_exception_from_source(db, "validation_issue", issue.id, data, user)
        link_exception_entity(db, case.id, "validation_issue", issue.id, "source", issue.entity_label)
        if issue.shipment_id:
            link_exception_entity(db, case.id, "shipment", issue.shipment_id, "related")
        count += 1

    return count


def detect_from_document_mismatches(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from document mismatch results."""
    try:
        from app.models.document_intelligence import DocumentMismatchResult
    except (ImportError, Exception):
        return 0

    mismatches = (
        db.query(DocumentMismatchResult)
        .filter(
            DocumentMismatchResult.status.in_(["open", "unresolved"]),
            DocumentMismatchResult.severity.in_(["critical", "high"]),
        )
        .all()
    )

    count = 0
    for mismatch in mismatches:
        dedupe_key = f"document_mismatch:{mismatch.id}"
        severity = "high" if mismatch.severity == "critical" else "medium"
        priority = "p1" if mismatch.severity == "critical" else "p2"

        title = f"Document mismatch: {getattr(mismatch, 'rule_key', 'unknown')}"
        if hasattr(mismatch, 'message') and mismatch.message:
            title = f"Document mismatch: {mismatch.message[:200]}"

        data = {
            "title": title,
            "category": "document",
            "source": "document_mismatch",
            "severity": severity,
            "priority": priority,
            "dedupe_key": dedupe_key,
            "shipment_id": getattr(mismatch, "shipment_id", None),
            "risk_score": 75 if mismatch.severity == "critical" else 55,
            "metadata_json": {
                "rule_key": getattr(mismatch, "rule_key", None),
                "extraction_id": getattr(mismatch, "extraction_id", None),
            },
        }
        case = create_or_update_exception_from_source(db, "document_mismatch", mismatch.id, data, user)
        link_exception_entity(db, case.id, "document_mismatch", mismatch.id, "source")
        if getattr(mismatch, "shipment_id", None):
            link_exception_entity(db, case.id, "shipment", mismatch.shipment_id, "related")
        count += 1

    return count


def detect_from_finance_holds(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from active finance/credit holds."""
    try:
        from app.models.finance_control import CreditHoldRecord
    except (ImportError, Exception):
        return 0

    holds = (
        db.query(CreditHoldRecord)
        .filter(CreditHoldRecord.status == "active")
        .all()
    )

    count = 0
    for hold in holds:
        dedupe_key = f"finance_hold:{hold.id}"
        severity_map = {"critical": "critical", "warning": "high", "info": "medium"}
        hold_severity = getattr(hold, "severity", "warning")
        severity = severity_map.get(hold_severity, "high")
        priority = "p0" if severity == "critical" else "p1"

        data = {
            "title": f"Finance hold: {getattr(hold, 'hold_type', 'unknown')}",
            "description": getattr(hold, "reason", None),
            "category": "finance",
            "source": "finance_hold",
            "severity": severity,
            "priority": priority,
            "dedupe_key": dedupe_key,
            "shipment_id": getattr(hold, "shipment_id", None),
            "party_id": getattr(hold, "party_id", None),
            "risk_score": 90 if severity == "critical" else 70,
            "metadata_json": {
                "hold_type": getattr(hold, "hold_type", None),
                "blocked_action": getattr(hold, "blocked_action", None),
            },
        }
        case = create_or_update_exception_from_source(db, "finance_hold", hold.id, data, user)
        link_exception_entity(db, case.id, "credit_hold", hold.id, "source")
        if getattr(hold, "shipment_id", None):
            link_exception_entity(db, case.id, "shipment", hold.shipment_id, "related")
        if getattr(hold, "party_id", None):
            link_exception_entity(db, case.id, "party", hold.party_id, "related")
        count += 1

    return count


def detect_from_finance_risks(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from open finance risk records."""
    try:
        from app.models.finance_control import FinanceRiskRecord
    except (ImportError, Exception):
        return 0

    risks = (
        db.query(FinanceRiskRecord)
        .filter(FinanceRiskRecord.status.in_(["open", "acknowledged"]))
        .all()
    )

    count = 0
    for risk in risks:
        dedupe_key = f"finance_risk:{risk.id}"
        risk_severity = getattr(risk, "severity", "medium")
        severity_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
        severity = severity_map.get(risk_severity, "medium")
        priority = "p1" if severity in ("critical", "high") else "p2"

        data = {
            "title": f"Finance risk: {getattr(risk, 'risk_type', 'unknown')}",
            "description": getattr(risk, "description", None),
            "category": "finance",
            "source": "finance_risk",
            "severity": severity,
            "priority": priority,
            "dedupe_key": dedupe_key,
            "shipment_id": getattr(risk, "shipment_id", None),
            "party_id": getattr(risk, "party_id", None),
            "risk_score": 70,
            "metadata_json": {
                "risk_type": getattr(risk, "risk_type", None),
            },
        }
        case = create_or_update_exception_from_source(db, "finance_risk", risk.id, data, user)
        link_exception_entity(db, case.id, "finance_risk", risk.id, "source")
        count += 1

    return count


def detect_from_workflow_logs(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from blocked workflow transitions."""
    try:
        from app.models.operational_event import OperationalEvent
    except (ImportError, Exception):
        return 0

    # Look for blocked/manual_review workflow events
    events = (
        db.query(OperationalEvent)
        .filter(
            OperationalEvent.event_type == "workflow.transition_requested",
        )
        .order_by(OperationalEvent.created_at.desc())
        .limit(100)
        .all()
    )

    count = 0
    for event in events:
        meta = event.metadata_json or {}
        outcome = meta.get("outcome", "")
        if outcome not in ("blocked", "manual_review_required"):
            continue

        dedupe_key = f"workflow_blocked:{event.id}"
        data = {
            "title": f"Workflow blocked: {meta.get('transition', 'unknown')}",
            "description": meta.get("reason", "Workflow transition blocked"),
            "category": "workflow",
            "source": "workflow_transition",
            "severity": "high",
            "priority": "p1",
            "dedupe_key": dedupe_key,
            "shipment_id": event.shipment_id,
            "entity_type": "operational_event",
            "entity_id": event.id,
            "risk_score": 65,
            "metadata_json": {
                "transition": meta.get("transition"),
                "outcome": outcome,
                "reason": meta.get("reason"),
            },
        }
        case = create_or_update_exception_from_source(db, "workflow_transition", event.id, data, user)
        link_exception_entity(db, case.id, "operational_event", event.id, "source")
        if event.shipment_id:
            link_exception_entity(db, case.id, "shipment", event.shipment_id, "related")
        count += 1

    return count


def detect_from_container_risks(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from container risk conditions."""
    try:
        from app.models.container import Container
    except (ImportError, Exception):
        return 0

    now = datetime.utcnow()

    # Containers with overdue empty return
    containers = (
        db.query(Container)
        .filter(
            Container.empty_return_deadline.isnot(None),
            Container.empty_return_deadline < now,
            Container.current_status.notin_(["returned", "closed"]),
        )
        .all()
    )

    count = 0
    for container in containers:
        dedupe_key = f"container_empty_return_overdue:{container.id}"
        days_overdue = (now - container.empty_return_deadline).days if container.empty_return_deadline else 0
        severity = "critical" if days_overdue > 5 else "high"
        priority = "p0" if days_overdue > 5 else "p1"

        data = {
            "title": f"Container empty return overdue: {container.container_number}",
            "description": f"Container {container.container_number} empty return is {days_overdue} days overdue",
            "category": "container",
            "source": "container_risk",
            "severity": severity,
            "priority": priority,
            "dedupe_key": dedupe_key,
            "shipment_id": container.shipment_id,
            "entity_type": "container",
            "entity_id": container.id,
            "risk_score": min(95, 60 + days_overdue * 5),
            "metadata_json": {
                "container_number": container.container_number,
                "days_overdue": days_overdue,
                "deadline": container.empty_return_deadline.isoformat() if container.empty_return_deadline else None,
            },
        }
        case = create_or_update_exception_from_source(db, "container_risk", container.id, data, user)
        link_exception_entity(db, case.id, "container", container.id, "source", container.container_number)
        if container.shipment_id:
            link_exception_entity(db, case.id, "shipment", container.shipment_id, "related")
        count += 1

    return count


def detect_from_gmail_suggestions(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from low-confidence Gmail suggestions."""
    try:
        from app.models.email import EmailSuggestion
    except (ImportError, Exception):
        return 0

    suggestions = (
        db.query(EmailSuggestion)
        .filter(EmailSuggestion.status == "manual_review")
        .all()
    )

    count = 0
    for suggestion in suggestions:
        dedupe_key = f"gmail_low_confidence:{suggestion.id}"
        data = {
            "title": f"Gmail suggestion needs review: {getattr(suggestion, 'suggestion_type', 'unknown')}",
            "category": "gmail",
            "source": "gmail_suggestion",
            "severity": "low",
            "priority": "p3",
            "dedupe_key": dedupe_key,
            "shipment_id": getattr(suggestion, "shipment_id", None),
            "entity_type": "email_suggestion",
            "entity_id": suggestion.id,
            "risk_score": 30,
            "metadata_json": {
                "suggestion_type": getattr(suggestion, "suggestion_type", None),
            },
        }
        case = create_or_update_exception_from_source(db, "gmail_suggestion", suggestion.id, data, user)
        link_exception_entity(db, case.id, "gmail_suggestion", suggestion.id, "source")
        count += 1

    return count


def detect_from_overdue_tasks(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> int:
    """Create exceptions from overdue high-priority tasks."""
    try:
        from app.models.task import Task
    except (ImportError, Exception):
        return 0

    now = datetime.utcnow()

    tasks = (
        db.query(Task)
        .filter(
            Task.status == "open",
            Task.due_date.isnot(None),
            Task.due_date < now.date(),
            Task.priority.in_(["critical", "warning"]),
        )
        .all()
    )

    count = 0
    for task in tasks:
        dedupe_key = f"task_overdue:{task.id}"
        is_critical = task.priority == "critical"
        severity = "high" if is_critical else "medium"
        priority = "p1" if is_critical else "p2"

        data = {
            "title": f"Overdue task: {task.title[:200]}",
            "description": f"Task '{task.title}' is overdue (due: {task.due_date})",
            "category": "sla",
            "source": "system_check",
            "severity": severity,
            "priority": priority,
            "dedupe_key": dedupe_key,
            "shipment_id": task.shipment_id,
            "entity_type": "task",
            "entity_id": task.id,
            "risk_score": 60 if is_critical else 40,
            "metadata_json": {
                "task_title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            },
        }
        case = create_or_update_exception_from_source(db, "system_check", task.id, data, user)
        link_exception_entity(db, case.id, "task", task.id, "source", task.title)
        if task.shipment_id:
            link_exception_entity(db, case.id, "shipment", task.shipment_id, "related")
        count += 1

    return count
