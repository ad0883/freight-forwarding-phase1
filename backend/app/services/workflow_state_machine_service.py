"""Phase 10 workflow state-machine service.

Coordinates available transitions, transition validation, event creation,
validation issue creation, manual-review notifications, and shipment state
updates. Errors do not corrupt shipment data: transitions are only applied
when explicitly allowed.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.operational_event import OperationalEvent
from app.models.shipment import Shipment
from app.models.validation_issue import ValidationIssue
from app.models.workflow_state_machine import (
    WorkflowStateDefinition,
    WorkflowTransitionDefinition,
    WorkflowTransitionLog,
)
from app.services.audit_service import record_audit_log
from app.services.event_service import record_operational_event
from app.services.notification_service import create_notification
from app.services.workflow_definitions import seed_workflow_definitions
from app.services.workflow_state_mapper import infer_workflow_state_for_shipment


logger = logging.getLogger(__name__)


SENSITIVE_AUDIT_ACTIONS = {
    "applied": "workflow.transition_applied",
    "blocked": "workflow.transition_blocked",
    "manual_review_required": "workflow.manual_review_required",
    "failed": "workflow.transition_failed",
    "requested": "workflow.transition_requested",
}


class WorkflowError(HTTPException):
    """Workflow domain error returned to API callers."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


def get_flow_type(shipment: Shipment) -> str:
    flow = (shipment.type or "").lower()
    if flow not in {"export", "import"}:
        raise WorkflowError(
            status.HTTP_400_BAD_REQUEST,
            "Shipment type is not import or export.",
        )
    return flow


def get_or_infer_state(db: Session, shipment: Shipment) -> tuple[Optional[str], bool]:
    """Return (state_key, was_inferred). Inference does not persist."""
    if shipment.workflow_state:
        return shipment.workflow_state, False
    inferred = infer_workflow_state_for_shipment(shipment)
    return inferred, inferred is not None


def list_states(db: Session, flow_type: Optional[str] = None) -> list[WorkflowStateDefinition]:
    query = db.query(WorkflowStateDefinition).filter(WorkflowStateDefinition.is_active.is_(True))
    if flow_type:
        query = query.filter(WorkflowStateDefinition.flow_type == flow_type)
    return query.order_by(
        WorkflowStateDefinition.flow_type.asc(),
        WorkflowStateDefinition.state_order.asc(),
    ).all()


def list_transitions(
    db: Session, flow_type: Optional[str] = None
) -> list[WorkflowTransitionDefinition]:
    query = db.query(WorkflowTransitionDefinition).filter(
        WorkflowTransitionDefinition.is_active.is_(True)
    )
    if flow_type:
        query = query.filter(WorkflowTransitionDefinition.flow_type == flow_type)
    return query.order_by(
        WorkflowTransitionDefinition.flow_type.asc(),
        WorkflowTransitionDefinition.from_state.asc().nullsfirst(),
        WorkflowTransitionDefinition.to_state.asc(),
    ).all()


def get_state_definition(
    db: Session, flow_type: str, state_key: str
) -> Optional[WorkflowStateDefinition]:
    return (
        db.query(WorkflowStateDefinition)
        .filter(
            WorkflowStateDefinition.flow_type == flow_type,
            WorkflowStateDefinition.state_key == state_key,
        )
        .first()
    )


def get_transition_definition(
    db: Session,
    flow_type: str,
    from_state: Optional[str],
    to_state: str,
) -> Optional[WorkflowTransitionDefinition]:
    query = db.query(WorkflowTransitionDefinition).filter(
        WorkflowTransitionDefinition.flow_type == flow_type,
        WorkflowTransitionDefinition.to_state == to_state,
        WorkflowTransitionDefinition.is_active.is_(True),
    )
    if from_state is None:
        match = query.filter(WorkflowTransitionDefinition.from_state.is_(None)).first()
        if match:
            return match
    else:
        match = query.filter(WorkflowTransitionDefinition.from_state == from_state).first()
        if match:
            return match
    # Fallback: a transition with no required from_state acts as a wildcard.
    return query.filter(WorkflowTransitionDefinition.from_state.is_(None)).first()


def role_can_transition(role: Optional[str], transition: WorkflowTransitionDefinition) -> bool:
    if role is None:
        return False
    if role == "VIEW_ONLY":
        return False
    if transition.is_sensitive and role != "ADMIN":
        return False
    return True


def list_available_transitions(
    db: Session, shipment: Shipment, user: AuthenticatedUser
) -> tuple[Optional[str], list[tuple[WorkflowTransitionDefinition, WorkflowStateDefinition, bool, Optional[str]]]]:
    flow_type = get_flow_type(shipment)
    current_state, _ = get_or_infer_state(db, shipment)
    transitions = (
        db.query(WorkflowTransitionDefinition)
        .filter(
            WorkflowTransitionDefinition.flow_type == flow_type,
            WorkflowTransitionDefinition.is_active.is_(True),
        )
        .filter(
            (WorkflowTransitionDefinition.from_state == current_state)
            | (WorkflowTransitionDefinition.from_state.is_(None))
        )
        .all()
    )
    state_lookup = {
        state.state_key: state
        for state in db.query(WorkflowStateDefinition)
        .filter(WorkflowStateDefinition.flow_type == flow_type)
        .all()
    }
    rows: list[
        tuple[WorkflowTransitionDefinition, WorkflowStateDefinition, bool, Optional[str]]
    ] = []
    for transition in transitions:
        target_state = state_lookup.get(transition.to_state)
        if target_state is None:
            continue
        permitted = role_can_transition(user.role, transition)
        permission_reason = None
        if not permitted:
            if user.role == "VIEW_ONLY":
                permission_reason = "View-only users cannot transition workflow state."
            elif transition.is_sensitive and user.role != "ADMIN":
                permission_reason = "Sensitive transitions require ADMIN."
        rows.append((transition, target_state, permitted, permission_reason))
    return current_state, rows


def list_workflow_logs(
    db: Session, shipment_id: int, limit: int = 100
) -> list[WorkflowTransitionLog]:
    return (
        db.query(WorkflowTransitionLog)
        .filter(WorkflowTransitionLog.shipment_id == shipment_id)
        .order_by(WorkflowTransitionLog.created_at.desc(), WorkflowTransitionLog.id.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )


def request_workflow_transition(
    db: Session,
    shipment: Shipment,
    to_state: str,
    user: AuthenticatedUser,
    *,
    reason: Optional[str] = None,
    confirm_sensitive: bool = False,
    source: str = "user",
    request: Optional[Request] = None,
) -> dict[str, Any]:
    flow_type = get_flow_type(shipment)
    current_state, was_inferred = get_or_infer_state(db, shipment)

    target_state = get_state_definition(db, flow_type, to_state)
    if target_state is None:
        return _block(
            db,
            shipment,
            flow_type,
            current_state,
            to_state,
            user,
            source,
            reason,
            request,
            detail="Target state is not defined for this flow.",
            rule_key="workflow_invalid_transition",
        )

    transition = get_transition_definition(db, flow_type, current_state, to_state)
    if transition is None or not transition.is_active:
        return _block(
            db,
            shipment,
            flow_type,
            current_state,
            to_state,
            user,
            source,
            reason,
            request,
            detail=(
                f"No active transition is defined from "
                f"{current_state or 'unset'} to {to_state}."
            ),
            rule_key="workflow_invalid_transition",
        )

    # Permission check.
    if user.role == "VIEW_ONLY":
        raise WorkflowError(
            status.HTTP_403_FORBIDDEN,
            "View-only users cannot transition workflow state.",
        )
    if transition.is_sensitive and user.role != "ADMIN":
        raise WorkflowError(
            status.HTTP_403_FORBIDDEN,
            "Sensitive transitions require ADMIN.",
        )

    # Archived shipments are blocked outright.
    if shipment.is_archived:
        return _block(
            db,
            shipment,
            flow_type,
            current_state,
            to_state,
            user,
            source,
            reason,
            request,
            transition=transition,
            detail="Archived shipments cannot transition workflow state.",
            rule_key="workflow_archived_shipment_transition_block",
            severity="critical",
        )

    # Sensitive transitions need explicit confirmation.
    if transition.is_sensitive and not confirm_sensitive:
        return _manual_review(
            db,
            shipment,
            flow_type,
            current_state,
            to_state,
            user,
            source,
            reason,
            request,
            transition=transition,
            detail="Sensitive transition requires explicit confirmation.",
            rule_key="workflow_sensitive_transition_requires_confirmation",
        )

    # Reason requirement.
    if transition.requires_reason and not (reason and reason.strip()):
        return _block(
            db,
            shipment,
            flow_type,
            current_state,
            to_state,
            user,
            source,
            reason,
            request,
            transition=transition,
            detail="Transition requires a reason.",
            rule_key="workflow_missing_required_state_data",
        )

    # Workflows that need manual review for non-sensitive cases.
    if transition.requires_manual_review:
        return _manual_review(
            db,
            shipment,
            flow_type,
            current_state,
            to_state,
            user,
            source,
            reason,
            request,
            transition=transition,
            detail="Transition requires manual review.",
            rule_key="workflow_sensitive_transition_requires_confirmation",
        )

    # All checks passed: apply the transition.
    return _apply(
        db,
        shipment,
        flow_type,
        current_state,
        to_state,
        user,
        source,
        reason,
        request,
        transition=transition,
        was_inferred=was_inferred,
        target_state=target_state,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _persist_log(
    db: Session,
    *,
    shipment_id: int,
    flow_type: str,
    transition: Optional[WorkflowTransitionDefinition],
    from_state: Optional[str],
    to_state: str,
    user: AuthenticatedUser,
    source: str,
    status_value: str,
    reason: Optional[str],
    validation_status: str,
    event_id: Optional[int] = None,
    validation_issue_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> WorkflowTransitionLog:
    log = WorkflowTransitionLog(
        shipment_id=shipment_id,
        flow_type=flow_type,
        transition_key=transition.transition_key if transition else None,
        from_state=from_state,
        to_state=to_state,
        actor_user_id=user.id if user else None,
        actor_name=user.name if user else None,
        actor_email=user.email if user else None,
        actor_role=user.role if user else None,
        source=source,
        status=status_value,
        reason=(reason or None),
        validation_status=validation_status,
        event_id=event_id,
        validation_issue_id=validation_issue_id,
        metadata_json=metadata or None,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    return log


def _record_event(
    db: Session,
    *,
    event_type: str,
    shipment: Shipment,
    user: AuthenticatedUser,
    source: str,
    from_state: Optional[str],
    to_state: str,
    transition: Optional[WorkflowTransitionDefinition],
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    run_validation: bool = False,
) -> Optional[OperationalEvent]:
    payload_metadata = {
        "from_state": from_state,
        "to_state": to_state,
        "flow_type": shipment.type,
    }
    if transition is not None:
        payload_metadata["transition_key"] = transition.transition_key
        payload_metadata["is_sensitive"] = transition.is_sensitive
    if metadata:
        payload_metadata.update(metadata)
    return record_operational_event(
        db,
        event_type,
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        shipment_id=shipment.id,
        actor_user=user,
        source=source if source in {"user", "system", "gmail", "ai", "scheduler", "workflow", "finance", "notification"} else "workflow",
        previous_state={"workflow_state": from_state},
        new_state={"workflow_state": to_state},
        metadata=payload_metadata,
        request=request,
        run_validation=run_validation,
    )


def _create_validation_issue(
    db: Session,
    *,
    rule_key: str,
    severity: str,
    message: str,
    shipment: Shipment,
    event_id: Optional[int],
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[ValidationIssue]:
    try:
        issue = ValidationIssue(
            event_id=event_id,
            rule_key=rule_key,
            entity_type="shipment",
            entity_id=shipment.id,
            entity_label=shipment.shipment_code,
            shipment_id=shipment.id,
            severity=severity,
            status="open",
            message=message,
            recommended_action=None,
            metadata_json=metadata or None,
            created_at=datetime.utcnow(),
        )
        db.add(issue)
        db.flush()
        return issue
    except Exception:
        logger.exception("Unable to create workflow validation issue rule_key=%s", rule_key)
        return None


def _create_manual_review_notification(
    db: Session,
    *,
    shipment: Shipment,
    rule_key: str,
    issue_id: Optional[int],
    message: str,
) -> None:
    try:
        entity_id = issue_id if issue_id is not None else shipment.id
        dedupe_key = f"workflow_manual_review:{rule_key}:shipment:{shipment.id}"
        create_notification(
            db,
            title="Manual review required",
            message=message,
            category="system",
            priority="critical",
            target_role="ADMIN",
            entity_type="validation_issue" if issue_id else "shipment",
            entity_id=entity_id,
            entity_label=shipment.shipment_code,
            action_url="/validation-issues",
            dedupe_key=dedupe_key,
            source="workflow",
            metadata={
                "rule_key": rule_key,
                "shipment_id": shipment.id,
            },
        )
    except Exception:
        logger.exception(
            "Unable to create manual-review notification rule_key=%s shipment_id=%s",
            rule_key,
            shipment.id,
        )


def _audit_workflow(
    db: Session,
    *,
    shipment: Shipment,
    user: AuthenticatedUser,
    status_value: str,
    from_state: Optional[str],
    to_state: str,
    reason: Optional[str],
    request: Optional[Request] = None,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> None:
    action = SENSITIVE_AUDIT_ACTIONS.get(status_value, "workflow.transition_event")
    metadata: dict[str, Any] = {
        "shipment_id": shipment.id,
        "from_state": from_state,
        "to_state": to_state,
        "reason_present": bool(reason),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    record_audit_log(
        db,
        user,
        action,
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        description=f"Workflow {status_value}: {from_state or '-'} -> {to_state}",
        metadata=metadata,
        request=request,
    )


def _apply(
    db: Session,
    shipment: Shipment,
    flow_type: str,
    from_state: Optional[str],
    to_state: str,
    user: AuthenticatedUser,
    source: str,
    reason: Optional[str],
    request: Optional[Request],
    *,
    transition: WorkflowTransitionDefinition,
    was_inferred: bool,
    target_state: WorkflowStateDefinition,
) -> dict[str, Any]:
    requested_event = _record_event(
        db,
        event_type="workflow.transition_requested",
        shipment=shipment,
        user=user,
        source=source,
        from_state=from_state,
        to_state=to_state,
        transition=transition,
        request=request,
        run_validation=False,
    )

    shipment.workflow_state = to_state
    shipment.workflow_state_updated_at = datetime.utcnow()
    shipment.workflow_state_reason = reason or None
    if target_state.is_terminal and (
        to_state in {"EXPORT_COMPLETED", "IMPORT_COMPLETED"}
    ):
        shipment.manual_review_required = False
        shipment.manual_review_reason = None
    db.flush()

    applied_event = _record_event(
        db,
        event_type="workflow.transition_applied",
        shipment=shipment,
        user=user,
        source=source,
        from_state=from_state,
        to_state=to_state,
        transition=transition,
        metadata={"was_inferred": was_inferred},
        request=request,
        run_validation=False,
    )

    log = _persist_log(
        db,
        shipment_id=shipment.id,
        flow_type=flow_type,
        transition=transition,
        from_state=from_state,
        to_state=to_state,
        user=user,
        source=source,
        status_value="applied",
        reason=reason,
        validation_status="passed",
        event_id=applied_event.id if applied_event else None,
        metadata={"was_inferred": was_inferred},
    )
    db.commit()

    _audit_workflow(
        db,
        shipment=shipment,
        user=user,
        status_value="applied",
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        request=request,
        extra_metadata={"transition_key": transition.transition_key},
    )

    return {
        "status": "applied",
        "from_state": from_state,
        "to_state": to_state,
        "validation_status": "passed",
        "manual_review_required": False,
        "log_id": log.id,
        "event_id": applied_event.id if applied_event else (requested_event.id if requested_event else None),
        "validation_issue_id": None,
        "detail": None,
        "reason": reason,
    }


def _block(
    db: Session,
    shipment: Shipment,
    flow_type: str,
    from_state: Optional[str],
    to_state: str,
    user: AuthenticatedUser,
    source: str,
    reason: Optional[str],
    request: Optional[Request],
    *,
    transition: Optional[WorkflowTransitionDefinition] = None,
    detail: str,
    rule_key: str,
    severity: str = "warning",
) -> dict[str, Any]:
    event = _record_event(
        db,
        event_type="workflow.transition_requested",
        shipment=shipment,
        user=user,
        source=source,
        from_state=from_state,
        to_state=to_state,
        transition=transition,
        metadata={"outcome": "blocked", "rule_key": rule_key, "detail": detail},
        request=request,
        run_validation=False,
    )
    issue = _create_validation_issue(
        db,
        rule_key=rule_key,
        severity=severity,
        message=detail,
        shipment=shipment,
        event_id=event.id if event else None,
        metadata={"from_state": from_state, "to_state": to_state},
    )
    log = _persist_log(
        db,
        shipment_id=shipment.id,
        flow_type=flow_type,
        transition=transition,
        from_state=from_state,
        to_state=to_state,
        user=user,
        source=source,
        status_value="blocked",
        reason=reason,
        validation_status="failed",
        event_id=event.id if event else None,
        validation_issue_id=issue.id if issue else None,
        metadata={"rule_key": rule_key, "detail": detail},
    )
    db.commit()

    _audit_workflow(
        db,
        shipment=shipment,
        user=user,
        status_value="blocked",
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        request=request,
        extra_metadata={"rule_key": rule_key},
    )

    return {
        "status": "blocked",
        "from_state": from_state,
        "to_state": to_state,
        "validation_status": "failed",
        "manual_review_required": False,
        "log_id": log.id,
        "event_id": event.id if event else None,
        "validation_issue_id": issue.id if issue else None,
        "detail": detail,
        "reason": reason,
    }


def _manual_review(
    db: Session,
    shipment: Shipment,
    flow_type: str,
    from_state: Optional[str],
    to_state: str,
    user: AuthenticatedUser,
    source: str,
    reason: Optional[str],
    request: Optional[Request],
    *,
    transition: WorkflowTransitionDefinition,
    detail: str,
    rule_key: str,
) -> dict[str, Any]:
    event = _record_event(
        db,
        event_type="workflow.transition_requested",
        shipment=shipment,
        user=user,
        source=source,
        from_state=from_state,
        to_state=to_state,
        transition=transition,
        metadata={"outcome": "manual_review_required", "rule_key": rule_key, "detail": detail},
        request=request,
        run_validation=False,
    )
    issue = _create_validation_issue(
        db,
        rule_key=rule_key,
        severity="critical",
        message=detail,
        shipment=shipment,
        event_id=event.id if event else None,
        metadata={
            "from_state": from_state,
            "to_state": to_state,
            "transition_key": transition.transition_key,
        },
    )
    if issue:
        _create_manual_review_notification(
            db,
            shipment=shipment,
            rule_key=rule_key,
            issue_id=issue.id,
            message=detail,
        )
    log = _persist_log(
        db,
        shipment_id=shipment.id,
        flow_type=flow_type,
        transition=transition,
        from_state=from_state,
        to_state=to_state,
        user=user,
        source=source,
        status_value="manual_review_required",
        reason=reason,
        validation_status="manual_review_required",
        event_id=event.id if event else None,
        validation_issue_id=issue.id if issue else None,
        metadata={"rule_key": rule_key, "detail": detail},
    )
    shipment.manual_review_required = True
    shipment.manual_review_reason = detail
    db.commit()

    _audit_workflow(
        db,
        shipment=shipment,
        user=user,
        status_value="manual_review_required",
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        request=request,
        extra_metadata={"rule_key": rule_key, "transition_key": transition.transition_key},
    )

    return {
        "status": "manual_review_required",
        "from_state": from_state,
        "to_state": to_state,
        "validation_status": "manual_review_required",
        "manual_review_required": True,
        "log_id": log.id,
        "event_id": event.id if event else None,
        "validation_issue_id": issue.id if issue else None,
        "detail": detail,
        "reason": reason,
    }


__all__ = [
    "WorkflowError",
    "get_flow_type",
    "get_or_infer_state",
    "list_states",
    "list_transitions",
    "list_available_transitions",
    "list_workflow_logs",
    "request_workflow_transition",
    "seed_workflow_definitions",
]
