"""Phase 15 exception engine API routes."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.exception_case import (
    ExceptionCase,
    ExceptionCaseComment,
    ExceptionCaseLink,
    ExceptionCaseSlaPolicy,
    ExceptionCaseStatusHistory,
)
from app.schemas.exception_case import (
    ExceptionCaseAssignRequest,
    ExceptionCaseCommentCreate,
    ExceptionCaseCommentRead,
    ExceptionCaseCreate,
    ExceptionCaseDismissRequest,
    ExceptionCaseEscalateRequest,
    ExceptionCaseEscalationRead,
    ExceptionCaseLinkCreate,
    ExceptionCaseLinkRead,
    ExceptionCaseRead,
    ExceptionCaseReopenRequest,
    ExceptionCaseResolveRequest,
    ExceptionCaseSlaPolicyRead,
    ExceptionCaseSlaPolicyUpdate,
    ExceptionCaseStatusHistoryRead,
    ExceptionCaseUpdate,
    ExceptionSummary,
)
from app.services.audit_service import record_audit_log
from app.services.exception_detection_service import run_exception_detection
from app.services.exception_service import (
    acknowledge_exception_case,
    add_exception_comment,
    assign_exception_case,
    create_exception_case,
    dismiss_exception_case,
    escalate_exception_case,
    get_exception_case,
    get_exception_summary,
    link_exception_entity,
    list_exception_cases,
    reopen_exception_case,
    resolve_exception_case,
)
from app.services.manual_review_service import (
    get_manual_review_queue,
    get_manual_review_summary,
    get_my_review_items,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exceptions", tags=["exceptions"])
shipment_exception_router = APIRouter(prefix="/shipments", tags=["shipment-exceptions"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


# ---------------------------------------------------------------------------
# List / Summary
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ExceptionCaseRead])
def list_exceptions(
    category: Optional[str] = None,
    source: Optional[str] = None,
    severity: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = Query(default=None, alias="status"),
    assigned_to_user_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    party_id: Optional[int] = None,
    overdue: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseRead]:
    cases = list_exception_cases(
        db,
        category=category,
        source=source,
        severity=severity,
        priority=priority,
        status_filter=status,
        assigned_to_user_id=assigned_to_user_id,
        shipment_id=shipment_id,
        party_id=party_id,
        overdue=overdue,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [ExceptionCaseRead.model_validate(c) for c in cases]


@router.get("/summary", response_model=ExceptionSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> ExceptionSummary:
    data = get_exception_summary(db, current_user)
    return ExceptionSummary(**data)


@router.get("/manual-review", response_model=list[ExceptionCaseRead])
def manual_review_queue(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseRead]:
    cases = get_manual_review_queue(
        db, category=category, severity=severity, priority=priority,
        limit=limit, offset=offset,
    )
    return [ExceptionCaseRead.model_validate(c) for c in cases]


@router.get("/my-queue", response_model=list[ExceptionCaseRead])
def my_queue(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> list[ExceptionCaseRead]:
    cases = get_my_review_items(db, current_user, limit=limit)
    return [ExceptionCaseRead.model_validate(c) for c in cases]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


@router.post("/run-detection")
def trigger_detection(
    request: Request,
    scope: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> dict:
    results = run_exception_detection(db, current_user, scope=scope)
    record_audit_log(
        db, current_user, "exception.detection_run", "exception",
        description="Exception detection run triggered.",
        metadata={"results": results, "scope": scope},
        request=request,
    )
    return {"status": "ok", "results": results}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post("", response_model=ExceptionCaseRead, status_code=201)
def create_exception(
    body: ExceptionCaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseRead:
    case = create_exception_case(db, body.model_dump(), current_user)
    record_audit_log(
        db, current_user, "exception.create", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description=f"Exception case created: {case.title[:100]}",
        metadata={"category": case.category, "severity": case.severity},
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


# ---------------------------------------------------------------------------
# Detail / Update
# ---------------------------------------------------------------------------


@router.get("/{case_id}", response_model=ExceptionCaseRead)
def get_exception_detail(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> ExceptionCaseRead:
    case = get_exception_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    return ExceptionCaseRead.model_validate(case)


@router.patch("/{case_id}", response_model=ExceptionCaseRead)
def update_exception(
    case_id: int,
    body: ExceptionCaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseRead:
    case = get_exception_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(case, key, value)
    from datetime import datetime
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    record_audit_log(
        db, current_user, "exception.update", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description="Exception case updated.",
        metadata={"fields": list(updates.keys())},
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


# ---------------------------------------------------------------------------
# Lifecycle actions
# ---------------------------------------------------------------------------


@router.post("/{case_id}/acknowledge", response_model=ExceptionCaseRead)
def acknowledge(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseRead:
    try:
        case = acknowledge_exception_case(db, case_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.acknowledge", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description="Exception case acknowledged.",
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


@router.post("/{case_id}/assign", response_model=ExceptionCaseRead)
def assign(
    case_id: int,
    body: ExceptionCaseAssignRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> ExceptionCaseRead:
    try:
        case = assign_exception_case(
            db, case_id,
            assignee_user_id=body.assigned_to_user_id,
            assignee_role=body.assigned_to_role,
            user=current_user,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.assign", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description=f"Exception assigned to user_id={body.assigned_to_user_id} role={body.assigned_to_role}",
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


@router.post("/{case_id}/resolve", response_model=ExceptionCaseRead)
def resolve(
    case_id: int,
    body: ExceptionCaseResolveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseRead:
    try:
        case = resolve_exception_case(db, case_id, current_user, body.resolution_notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.resolve", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description="Exception case resolved.",
        metadata={"resolution_notes": body.resolution_notes[:200]},
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


@router.post("/{case_id}/dismiss", response_model=ExceptionCaseRead)
def dismiss(
    case_id: int,
    body: ExceptionCaseDismissRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> ExceptionCaseRead:
    try:
        case = dismiss_exception_case(db, case_id, current_user, body.dismissal_reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.dismiss", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description="Exception case dismissed.",
        metadata={"dismissal_reason": body.dismissal_reason[:200]},
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


@router.post("/{case_id}/reopen", response_model=ExceptionCaseRead)
def reopen(
    case_id: int,
    body: ExceptionCaseReopenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseRead:
    try:
        case = reopen_exception_case(db, case_id, current_user, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.reopen", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description="Exception case reopened.",
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


@router.post("/{case_id}/escalate", response_model=ExceptionCaseRead)
def escalate(
    case_id: int,
    body: ExceptionCaseEscalateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> ExceptionCaseRead:
    try:
        case = escalate_exception_case(
            db, case_id, current_user,
            severity=body.severity,
            priority=body.priority,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.escalate", "exception",
        entity_id=case.id, entity_label=case.case_number,
        description=f"Exception escalated: {body.reason[:100]}",
        metadata={"severity": body.severity, "priority": body.priority},
        request=request,
    )
    return ExceptionCaseRead.model_validate(case)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.get("/{case_id}/comments", response_model=list[ExceptionCaseCommentRead])
def list_comments(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseCommentRead]:
    case = get_exception_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    comments = (
        db.query(ExceptionCaseComment)
        .filter(ExceptionCaseComment.exception_case_id == case_id)
        .order_by(ExceptionCaseComment.created_at.asc())
        .all()
    )
    return [ExceptionCaseCommentRead.model_validate(c) for c in comments]


@router.post("/{case_id}/comments", response_model=ExceptionCaseCommentRead, status_code=201)
def create_comment(
    case_id: int,
    body: ExceptionCaseCommentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseCommentRead:
    try:
        comment = add_exception_comment(
            db, case_id, current_user, body.comment_text, body.is_internal,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    record_audit_log(
        db, current_user, "exception.comment", "exception",
        entity_id=case_id,
        description="Comment added to exception case.",
        request=request,
    )
    return ExceptionCaseCommentRead.model_validate(comment)


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------


@router.get("/{case_id}/links", response_model=list[ExceptionCaseLinkRead])
def list_links(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseLinkRead]:
    case = get_exception_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    links = (
        db.query(ExceptionCaseLink)
        .filter(ExceptionCaseLink.exception_case_id == case_id)
        .order_by(ExceptionCaseLink.created_at.desc())
        .all()
    )
    return [ExceptionCaseLinkRead.model_validate(link) for link in links]


@router.post("/{case_id}/links", response_model=ExceptionCaseLinkRead, status_code=201)
def create_link(
    case_id: int,
    body: ExceptionCaseLinkCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ExceptionCaseLinkRead:
    case = get_exception_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    link = link_exception_entity(
        db, case_id, body.linked_type, body.linked_id,
        body.relationship_type, body.linked_label, body.metadata_json,
    )
    return ExceptionCaseLinkRead.model_validate(link)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get("/{case_id}/history", response_model=list[ExceptionCaseStatusHistoryRead])
def get_history(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseStatusHistoryRead]:
    case = get_exception_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Exception case not found")
    history = (
        db.query(ExceptionCaseStatusHistory)
        .filter(ExceptionCaseStatusHistory.exception_case_id == case_id)
        .order_by(ExceptionCaseStatusHistory.created_at.asc())
        .all()
    )
    return [ExceptionCaseStatusHistoryRead.model_validate(h) for h in history]


# ---------------------------------------------------------------------------
# SLA Policies
# ---------------------------------------------------------------------------


@router.get("/sla-policies", response_model=list[ExceptionCaseSlaPolicyRead])
def list_sla_policies(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseSlaPolicyRead]:
    policies = db.query(ExceptionCaseSlaPolicy).order_by(ExceptionCaseSlaPolicy.id).all()
    return [ExceptionCaseSlaPolicyRead.model_validate(p) for p in policies]


@router.patch("/sla-policies/{policy_id}", response_model=ExceptionCaseSlaPolicyRead)
def update_sla_policy(
    policy_id: int,
    body: ExceptionCaseSlaPolicyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> ExceptionCaseSlaPolicyRead:
    policy = db.query(ExceptionCaseSlaPolicy).filter(ExceptionCaseSlaPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(policy, key, value)
    from datetime import datetime
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    record_audit_log(
        db, current_user, "exception.sla_policy_update", "exception_sla_policy",
        entity_id=policy.id,
        description="SLA policy updated.",
        metadata={"fields": list(updates.keys())},
        request=request,
    )
    return ExceptionCaseSlaPolicyRead.model_validate(policy)


# ---------------------------------------------------------------------------
# Shipment-specific routes
# ---------------------------------------------------------------------------


@shipment_exception_router.get("/{shipment_id}/exceptions", response_model=list[ExceptionCaseRead])
def get_shipment_exceptions(
    shipment_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseRead]:
    cases = list_exception_cases(db, shipment_id=shipment_id, limit=limit, offset=offset)
    return [ExceptionCaseRead.model_validate(c) for c in cases]


@shipment_exception_router.get("/{shipment_id}/manual-review", response_model=list[ExceptionCaseRead])
def get_shipment_manual_review(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
) -> list[ExceptionCaseRead]:
    from app.services.exception_service import ACTIVE_STATUSES
    cases = (
        db.query(ExceptionCase)
        .filter(
            ExceptionCase.shipment_id == shipment_id,
            ExceptionCase.status.in_(ACTIVE_STATUSES),
        )
        .order_by(ExceptionCase.priority.asc(), ExceptionCase.risk_score.desc())
        .all()
    )
    return [ExceptionCaseRead.model_validate(c) for c in cases]
