"""Phase 16 approval engine core service."""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.approval import (
    ApprovalActionLock,
    ApprovalPolicy,
    ApprovalRequest,
    ApprovalRequestEvidence,
    ApprovalStep,
)

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("draft", "pending", "in_review", "changes_requested")
TERMINAL_STATUSES = ("approved", "rejected", "cancelled", "expired", "executed", "failed_execution")

SENSITIVE_KEYS = {
    "password", "jwt", "api_key", "gmail_token", "oauth_code",
    "database_url", "secret", "token", "bank_account", "card_number", "upi_secret",
}


def _generate_approval_number() -> str:
    now = datetime.utcnow()
    short_id = uuid.uuid4().hex[:6].upper()
    return f"APR-{now.strftime('%Y%m%d')}-{short_id}"


def _sanitize(metadata: Optional[dict]) -> Optional[dict]:
    if not metadata:
        return metadata
    return {k: v for k, v in metadata.items() if k.lower() not in SENSITIVE_KEYS}


def create_approval_request(
    db: Session, data: dict[str, Any], user: Optional[AuthenticatedUser] = None,
) -> ApprovalRequest:
    now = datetime.utcnow()
    # Match policy
    policy = match_approval_policy(db, data.get("approval_type", "other"), data.get("risk_level", "medium"))
    required_steps = policy.required_steps if policy else 1
    approver_role = policy.required_approver_role if policy else "ADMIN"

    req = ApprovalRequest(
        approval_number=_generate_approval_number(),
        title=data["title"],
        description=data.get("description"),
        approval_type=data.get("approval_type", "other"),
        source=data.get("source", "manual"),
        status="draft",
        risk_level=data.get("risk_level", "medium"),
        priority=data.get("priority", "p3"),
        entity_type=data.get("entity_type"),
        entity_id=data.get("entity_id"),
        shipment_id=data.get("shipment_id"),
        party_id=data.get("party_id"),
        exception_case_id=data.get("exception_case_id"),
        requested_action=data["requested_action"],
        requested_payload_json=_sanitize(data.get("requested_payload_json")),
        safe_summary_json=data.get("safe_summary_json"),
        requested_by_user_id=user.id if user else None,
        requested_by_name=user.name if user else None,
        assigned_to_role=approver_role,
        current_step_no=1,
        required_steps=required_steps,
        metadata_json=_sanitize(data.get("metadata_json")),
        created_at=now,
        updated_at=now,
    )
    db.add(req)
    db.flush()

    # Create approval steps
    for step_no in range(1, required_steps + 1):
        step = ApprovalStep(
            approval_request_id=req.id,
            step_no=step_no,
            approver_role=approver_role,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        db.add(step)

    db.commit()
    db.refresh(req)
    return req


def submit_approval_request(
    db: Session, approval_id: int, user: AuthenticatedUser,
) -> ApprovalRequest:
    req = get_approval_request(db, approval_id)
    if not req:
        raise ValueError("Approval request not found")
    if req.status != "draft":
        raise ValueError("Only draft approvals can be submitted")
    now = datetime.utcnow()
    req.status = "pending"
    req.submitted_at = now
    req.updated_at = now
    # Set due_at based on policy
    policy = match_approval_policy(db, req.approval_type, req.risk_level)
    if policy and policy.auto_expire_hours:
        req.due_at = now + timedelta(hours=policy.auto_expire_hours)
    db.commit()
    db.refresh(req)
    return req


def get_approval_request(db: Session, approval_id: int) -> Optional[ApprovalRequest]:
    return db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()


def list_approval_requests(
    db: Session, *,
    approval_type: Optional[str] = None,
    source: Optional[str] = None,
    status_filter: Optional[str] = None,
    risk_level: Optional[str] = None,
    assigned_to_user_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    overdue: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50, offset: int = 0,
) -> list[ApprovalRequest]:
    query = db.query(ApprovalRequest)
    if approval_type:
        query = query.filter(ApprovalRequest.approval_type == approval_type)
    if source:
        query = query.filter(ApprovalRequest.source == source)
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter)
    if risk_level:
        query = query.filter(ApprovalRequest.risk_level == risk_level)
    if assigned_to_user_id is not None:
        query = query.filter(ApprovalRequest.assigned_to_user_id == assigned_to_user_id)
    if shipment_id is not None:
        query = query.filter(ApprovalRequest.shipment_id == shipment_id)
    if overdue:
        now = datetime.utcnow()
        query = query.filter(
            ApprovalRequest.due_at.isnot(None),
            ApprovalRequest.due_at < now,
            ApprovalRequest.status.in_(ACTIVE_STATUSES),
        )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            ApprovalRequest.title.ilike(pattern) | ApprovalRequest.approval_number.ilike(pattern)
        )
    return (
        query.order_by(ApprovalRequest.created_at.desc())
        .limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()
    )


def approve_step(
    db: Session, approval_id: int, user: AuthenticatedUser, notes: Optional[str] = None,
) -> ApprovalRequest:
    req = get_approval_request(db, approval_id)
    if not req:
        raise ValueError("Approval request not found")
    if req.status not in ("pending", "in_review", "changes_requested"):
        raise ValueError("Approval is not in a reviewable state")

    # Maker-checker: requester cannot approve their own high-risk request
    policy = match_approval_policy(db, req.approval_type, req.risk_level)
    if policy and policy.maker_checker_required and req.requested_by_user_id == user.id:
        raise ValueError("Maker-checker policy: you cannot approve your own request")

    now = datetime.utcnow()
    step = _get_current_step(db, req)
    if step:
        step.approver_user_id = user.id
        step.approver_name = user.name
        step.status = "approved"
        step.decision = "approve"
        step.decision_notes = notes
        step.decided_at = now
        step.updated_at = now

    if req.current_step_no >= req.required_steps:
        req.status = "approved"
        req.approved_at = now
        req.final_decision_by_user_id = user.id
        req.final_decision_by_name = user.name
        req.final_decision_notes = notes
    else:
        req.current_step_no += 1
        req.status = "in_review"

    req.updated_at = now
    db.commit()
    db.refresh(req)
    return req


def reject_step(
    db: Session, approval_id: int, user: AuthenticatedUser, notes: Optional[str] = None,
) -> ApprovalRequest:
    req = get_approval_request(db, approval_id)
    if not req:
        raise ValueError("Approval request not found")
    if req.status not in ("pending", "in_review", "changes_requested"):
        raise ValueError("Approval is not in a reviewable state")
    now = datetime.utcnow()
    step = _get_current_step(db, req)
    if step:
        step.approver_user_id = user.id
        step.approver_name = user.name
        step.status = "rejected"
        step.decision = "reject"
        step.decision_notes = notes
        step.decided_at = now
        step.updated_at = now
    req.status = "rejected"
    req.rejected_at = now
    req.final_decision_by_user_id = user.id
    req.final_decision_by_name = user.name
    req.final_decision_notes = notes
    req.updated_at = now
    db.commit()
    db.refresh(req)
    return req


def request_changes(
    db: Session, approval_id: int, user: AuthenticatedUser, notes: Optional[str] = None,
) -> ApprovalRequest:
    req = get_approval_request(db, approval_id)
    if not req:
        raise ValueError("Approval request not found")
    if req.status not in ("pending", "in_review"):
        raise ValueError("Approval is not in a reviewable state")
    now = datetime.utcnow()
    step = _get_current_step(db, req)
    if step:
        step.approver_user_id = user.id
        step.approver_name = user.name
        step.status = "changes_requested"
        step.decision = "request_changes"
        step.decision_notes = notes
        step.decided_at = now
        step.updated_at = now
    req.status = "changes_requested"
    req.updated_at = now
    db.commit()
    db.refresh(req)
    return req


def cancel_approval_request(
    db: Session, approval_id: int, user: AuthenticatedUser, reason: Optional[str] = None,
) -> ApprovalRequest:
    req = get_approval_request(db, approval_id)
    if not req:
        raise ValueError("Approval request not found")
    if req.status in TERMINAL_STATUSES:
        raise ValueError("Cannot cancel a terminal approval")
    now = datetime.utcnow()
    req.status = "cancelled"
    req.cancelled_at = now
    req.final_decision_notes = reason
    req.updated_at = now
    db.commit()
    db.refresh(req)
    return req


def execute_approved_action(
    db: Session, approval_id: int, user: AuthenticatedUser,
) -> ApprovalRequest:
    """Mark an approved request as executed and release any action locks."""
    req = get_approval_request(db, approval_id)
    if not req:
        raise ValueError("Approval request not found")
    if req.status != "approved":
        raise ValueError("Only approved requests can be executed")
    now = datetime.utcnow()
    req.status = "executed"
    req.completed_at = now
    req.updated_at = now
    # Release associated action locks
    locks = (
        db.query(ApprovalActionLock)
        .filter(ApprovalActionLock.approval_request_id == req.id, ApprovalActionLock.status == "active")
        .all()
    )
    for lock in locks:
        lock.status = "released"
        lock.released_at = now
        lock.released_by_user_id = user.id
        lock.released_by_name = user.name
    db.commit()
    db.refresh(req)
    return req


def get_approval_summary(db: Session, user: Optional[AuthenticatedUser] = None) -> dict[str, Any]:
    now = datetime.utcnow()
    active = db.query(ApprovalRequest).filter(ApprovalRequest.status.in_(ACTIVE_STATUSES)).all()
    from app.models.approval import BotGovernanceAction
    bot_pending = db.query(BotGovernanceAction).filter(BotGovernanceAction.status.in_(("proposed", "pending_approval"))).count()

    total_pending = len(active)
    total_high_risk = sum(1 for a in active if a.risk_level in ("high", "critical"))
    total_overdue = sum(1 for a in active if a.due_at and a.due_at < now)
    total_assigned_to_me = 0
    if user:
        total_assigned_to_me = sum(1 for a in active if a.assigned_to_user_id == user.id)

    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for a in active:
        by_type[a.approval_type] = by_type.get(a.approval_type, 0) + 1
        by_status[a.status] = by_status.get(a.status, 0) + 1
        by_risk[a.risk_level] = by_risk.get(a.risk_level, 0) + 1

    return {
        "total_pending": total_pending,
        "total_assigned_to_me": total_assigned_to_me,
        "total_high_risk": total_high_risk,
        "total_overdue": total_overdue,
        "total_bot_pending": bot_pending,
        "by_type": by_type,
        "by_status": by_status,
        "by_risk": by_risk,
    }


def match_approval_policy(
    db: Session, approval_type: str, risk_level: str,
) -> Optional[ApprovalPolicy]:
    return (
        db.query(ApprovalPolicy)
        .filter(
            ApprovalPolicy.approval_type == approval_type,
            ApprovalPolicy.risk_level == risk_level,
            ApprovalPolicy.is_active.is_(True),
        )
        .first()
    )


def _get_current_step(db: Session, req: ApprovalRequest) -> Optional[ApprovalStep]:
    return (
        db.query(ApprovalStep)
        .filter(
            ApprovalStep.approval_request_id == req.id,
            ApprovalStep.step_no == req.current_step_no,
        )
        .first()
    )


# --- Action Locks ---

def create_action_lock(
    db: Session, entity_type: str, entity_id: int, action_key: str,
    approval_request_id: Optional[int] = None, reason: Optional[str] = None,
) -> ApprovalActionLock:
    lock = ApprovalActionLock(
        approval_request_id=approval_request_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action_key=action_key,
        lock_reason=reason,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(lock)
    db.commit()
    db.refresh(lock)
    return lock


def check_action_allowed(
    db: Session, entity_type: str, entity_id: int, action_key: str,
) -> dict[str, Any]:
    lock = (
        db.query(ApprovalActionLock)
        .filter(
            ApprovalActionLock.entity_type == entity_type,
            ApprovalActionLock.entity_id == entity_id,
            ApprovalActionLock.action_key == action_key,
            ApprovalActionLock.status == "active",
        )
        .first()
    )
    if lock:
        return {"allowed": False, "lock_id": lock.id, "lock_reason": lock.lock_reason, "approval_request_id": lock.approval_request_id}
    return {"allowed": True, "lock_id": None, "lock_reason": None, "approval_request_id": None}


def release_action_lock(
    db: Session, lock_id: int, user: AuthenticatedUser, reason: Optional[str] = None,
) -> ApprovalActionLock:
    lock = db.query(ApprovalActionLock).filter(ApprovalActionLock.id == lock_id).first()
    if not lock:
        raise ValueError("Action lock not found")
    if lock.status != "active":
        raise ValueError("Lock is not active")
    now = datetime.utcnow()
    lock.status = "released"
    lock.released_at = now
    lock.released_by_user_id = user.id
    lock.released_by_name = user.name
    db.commit()
    db.refresh(lock)
    return lock
