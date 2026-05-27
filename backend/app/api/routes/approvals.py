"""Phase 16 approval engine API routes."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.approval import (
    ApprovalActionLock, ApprovalPolicy, ApprovalRequest,
    ApprovalRequestEvidence, ApprovalStep, BotGovernanceAction,
)
from app.schemas.approval import (
    ActionLockCheckRequest, ActionLockCheckResponse, ActionLockRead,
    ApprovalDecisionRequest, ApprovalEvidenceCreate, ApprovalEvidenceRead,
    ApprovalPolicyRead, ApprovalPolicyUpdate, ApprovalRequestCreate,
    ApprovalRequestRead, ApprovalRequestUpdate, ApprovalStepRead,
    ApprovalSummary, BotGovernanceActionRead,
)
from app.services.approval_service import (
    approve_step, cancel_approval_request, check_action_allowed,
    create_action_lock, create_approval_request, execute_approved_action,
    get_approval_request, get_approval_summary, list_approval_requests,
    reject_step, release_action_lock, request_changes, submit_approval_request,
)
from app.services.audit_service import record_audit_log
from app.services.bot_governance_service import (
    approve_bot_action, list_bot_actions, reject_bot_action,
    submit_bot_action_for_approval,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])
shipment_approval_router = APIRouter(prefix="/shipments", tags=["shipment-approvals"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


@router.get("", response_model=list[ApprovalRequestRead])
def list_approvals(
    approval_type: Optional[str] = None, source: Optional[str] = None,
    status: Optional[str] = Query(default=None), risk_level: Optional[str] = None,
    assigned_to_user_id: Optional[int] = None, shipment_id: Optional[int] = None,
    overdue: Optional[bool] = None, search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser,
) -> list[ApprovalRequestRead]:
    items = list_approval_requests(
        db, approval_type=approval_type, source=source, status_filter=status,
        risk_level=risk_level, assigned_to_user_id=assigned_to_user_id,
        shipment_id=shipment_id, overdue=overdue, search=search, limit=limit, offset=offset,
    )
    return [ApprovalRequestRead.model_validate(i) for i in items]


@router.get("/summary", response_model=ApprovalSummary)
def summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return ApprovalSummary(**get_approval_summary(db, current_user))


@router.get("/my-queue", response_model=list[ApprovalRequestRead])
def my_queue(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser,
):
    items = list_approval_requests(db, assigned_to_user_id=current_user.id, limit=limit)
    return [ApprovalRequestRead.model_validate(i) for i in items]


@router.get("/pending", response_model=list[ApprovalRequestRead])
def pending(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser,
):
    items = list_approval_requests(db, status_filter="pending", limit=limit)
    return [ApprovalRequestRead.model_validate(i) for i in items]


@router.post("", response_model=ApprovalRequestRead, status_code=201)
def create_approval(
    body: ApprovalRequestCreate, request: Request,
    db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser,
):
    req = create_approval_request(db, body.model_dump(), current_user)
    record_audit_log(db, current_user, "approval.create", "approval", entity_id=req.id, entity_label=req.approval_number, description=f"Approval created: {req.title[:100]}", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.get("/{approval_id}", response_model=ApprovalRequestRead)
def get_detail(approval_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    req = get_approval_request(db, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalRequestRead.model_validate(req)


@router.patch("/{approval_id}", response_model=ApprovalRequestRead)
def update_approval(
    approval_id: int, body: ApprovalRequestUpdate, request: Request,
    db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser,
):
    req = get_approval_request(db, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    from datetime import datetime
    updates = body.model_dump(exclude_unset=True)
    if "assigned_to_user_id" in updates and updates["assigned_to_user_id"]:
        from app.models import User
        target = db.query(User).filter(User.id == updates["assigned_to_user_id"]).first()
        if target:
            req.assigned_to_name = target.name
            req.assigned_to_user_id = target.id
        updates.pop("assigned_to_user_id", None)
    for k, v in updates.items():
        if hasattr(req, k):
            setattr(req, k, v)
    req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(req)
    record_audit_log(db, current_user, "approval.update", "approval", entity_id=req.id, entity_label=req.approval_number, description="Approval updated.", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.post("/{approval_id}/submit", response_model=ApprovalRequestRead)
def submit(approval_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try:
        req = submit_approval_request(db, approval_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.submit", "approval", entity_id=req.id, entity_label=req.approval_number, description="Approval submitted.", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.post("/{approval_id}/approve", response_model=ApprovalRequestRead)
def approve(approval_id: int, body: ApprovalDecisionRequest, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        req = approve_step(db, approval_id, current_user, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.approve", "approval", entity_id=req.id, entity_label=req.approval_number, description="Approval approved.", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.post("/{approval_id}/reject", response_model=ApprovalRequestRead)
def reject(approval_id: int, body: ApprovalDecisionRequest, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        req = reject_step(db, approval_id, current_user, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.reject", "approval", entity_id=req.id, entity_label=req.approval_number, description="Approval rejected.", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.post("/{approval_id}/request-changes", response_model=ApprovalRequestRead)
def req_changes(approval_id: int, body: ApprovalDecisionRequest, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        req = request_changes(db, approval_id, current_user, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.request_changes", "approval", entity_id=req.id, entity_label=req.approval_number, description="Changes requested.", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.post("/{approval_id}/cancel", response_model=ApprovalRequestRead)
def cancel(approval_id: int, body: ApprovalDecisionRequest, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try:
        req = cancel_approval_request(db, approval_id, current_user, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.cancel", "approval", entity_id=req.id, entity_label=req.approval_number, description="Approval cancelled.", request=request)
    return ApprovalRequestRead.model_validate(req)


@router.post("/{approval_id}/execute", response_model=ApprovalRequestRead)
def execute(approval_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        req = execute_approved_action(db, approval_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.execute", "approval", entity_id=req.id, entity_label=req.approval_number, description="Approved action executed.", request=request)
    return ApprovalRequestRead.model_validate(req)


# --- Steps & Evidence ---

@router.get("/{approval_id}/steps", response_model=list[ApprovalStepRead])
def get_steps(approval_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    req = get_approval_request(db, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    steps = db.query(ApprovalStep).filter(ApprovalStep.approval_request_id == approval_id).order_by(ApprovalStep.step_no).all()
    return [ApprovalStepRead.model_validate(s) for s in steps]


@router.get("/{approval_id}/evidence", response_model=list[ApprovalEvidenceRead])
def get_evidence(approval_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    items = db.query(ApprovalRequestEvidence).filter(ApprovalRequestEvidence.approval_request_id == approval_id).order_by(ApprovalRequestEvidence.created_at.desc()).all()
    return [ApprovalEvidenceRead.model_validate(e) for e in items]


@router.post("/{approval_id}/evidence", response_model=ApprovalEvidenceRead, status_code=201)
def add_evidence(approval_id: int, body: ApprovalEvidenceCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    req = get_approval_request(db, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    from datetime import datetime
    ev = ApprovalRequestEvidence(
        approval_request_id=approval_id, evidence_type=body.evidence_type,
        linked_type=body.linked_type, linked_id=body.linked_id,
        label=body.label, summary=body.summary, metadata_json=body.metadata_json,
        created_at=datetime.utcnow(),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ApprovalEvidenceRead.model_validate(ev)


# --- Policies ---

@router.get("/policies", response_model=list[ApprovalPolicyRead])
def list_policies(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    policies = db.query(ApprovalPolicy).order_by(ApprovalPolicy.id).all()
    return [ApprovalPolicyRead.model_validate(p) for p in policies]


@router.patch("/policies/{policy_id}", response_model=ApprovalPolicyRead)
def update_policy(policy_id: int, body: ApprovalPolicyUpdate, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    policy = db.query(ApprovalPolicy).filter(ApprovalPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    from datetime import datetime
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(policy, k, v)
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    record_audit_log(db, current_user, "approval.policy_update", "approval_policy", entity_id=policy.id, description="Approval policy updated.", request=request)
    return ApprovalPolicyRead.model_validate(policy)


# --- Action Locks ---

@router.get("/action-locks", response_model=list[ActionLockRead])
def list_locks(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    locks = db.query(ApprovalActionLock).filter(ApprovalActionLock.status == "active").order_by(ApprovalActionLock.created_at.desc()).limit(100).all()
    return [ActionLockRead.model_validate(l) for l in locks]


@router.post("/action-locks/check", response_model=ActionLockCheckResponse)
def check_lock(body: ActionLockCheckRequest, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    result = check_action_allowed(db, body.entity_type, body.entity_id, body.action_key)
    return ActionLockCheckResponse(**result)


@router.post("/action-locks/{lock_id}/release", response_model=ActionLockRead)
def release_lock(lock_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        lock = release_action_lock(db, lock_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "approval.lock_release", "action_lock", entity_id=lock.id, description="Action lock released.", request=request)
    return ActionLockRead.model_validate(lock)


# --- Bot Governance ---

@router.get("/bot-actions", response_model=list[BotGovernanceActionRead])
def list_bot(status: Optional[str] = None, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    items = list_bot_actions(db, status_filter=status, limit=limit)
    return [BotGovernanceActionRead.model_validate(i) for i in items]


@router.post("/bot-actions/{bot_action_id}/submit", response_model=BotGovernanceActionRead)
def submit_bot(bot_action_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try:
        action = submit_bot_action_for_approval(db, bot_action_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "bot_action.submit", "bot_governance_action", entity_id=action.id, description="Bot action submitted for approval.", request=request)
    return BotGovernanceActionRead.model_validate(action)


@router.post("/bot-actions/{bot_action_id}/approve", response_model=BotGovernanceActionRead)
def approve_bot(bot_action_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        action = approve_bot_action(db, bot_action_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "bot_action.approve", "bot_governance_action", entity_id=action.id, description="Bot action approved.", request=request)
    return BotGovernanceActionRead.model_validate(action)


@router.post("/bot-actions/{bot_action_id}/reject", response_model=BotGovernanceActionRead)
def reject_bot(bot_action_id: int, body: ApprovalDecisionRequest, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try:
        action = reject_bot_action(db, bot_action_id, current_user, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    record_audit_log(db, current_user, "bot_action.reject", "bot_governance_action", entity_id=action.id, description="Bot action rejected.", request=request)
    return BotGovernanceActionRead.model_validate(action)


# --- Shipment-specific ---

@shipment_approval_router.get("/{shipment_id}/approvals", response_model=list[ApprovalRequestRead])
def shipment_approvals(shipment_id: int, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    items = list_approval_requests(db, shipment_id=shipment_id, limit=limit)
    return [ApprovalRequestRead.model_validate(i) for i in items]
