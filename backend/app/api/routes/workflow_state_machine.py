"""Phase 10 workflow state-machine API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.models.shipment import Shipment
from app.schemas.workflow import (
    WorkflowAvailableTransition,
    WorkflowAvailableTransitionsResponse,
    WorkflowShipmentStateRead,
    WorkflowStateRead,
    WorkflowTimelineResponse,
    WorkflowTransitionLogRead,
    WorkflowTransitionRead,
    WorkflowTransitionRequest,
    WorkflowTransitionResponse,
)
from app.services.workflow_state_machine_service import (
    WorkflowError,
    get_flow_type,
    get_or_infer_state,
    list_available_transitions,
    list_states,
    list_transitions,
    list_workflow_logs,
    request_workflow_transition,
)


router = APIRouter(prefix="/workflow", tags=["workflow"])


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.get("/states", response_model=list[WorkflowStateRead])
def get_states(
    flow_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
):
    return list_states(db, flow_type=flow_type)


@router.get("/transitions", response_model=list[WorkflowTransitionRead])
def get_transitions(
    flow_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
):
    return list_transitions(db, flow_type=flow_type)


@router.get(
    "/shipments/{shipment_id}/state",
    response_model=WorkflowShipmentStateRead,
)
def get_shipment_state(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> WorkflowShipmentStateRead:
    shipment = _get_shipment(db, shipment_id)
    flow_type = get_flow_type(shipment)
    state, was_inferred = get_or_infer_state(db, shipment)
    label = None
    if state:
        from app.services.workflow_state_machine_service import get_state_definition

        definition = get_state_definition(db, flow_type, state)
        label = definition.state_label if definition else state.replace("_", " ").title()
    return WorkflowShipmentStateRead(
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        flow_type=flow_type,
        workflow_state=state,
        workflow_state_label=label,
        workflow_state_updated_at=shipment.workflow_state_updated_at,
        workflow_state_reason=shipment.workflow_state_reason,
        manual_review_required=bool(shipment.manual_review_required),
        manual_review_reason=shipment.manual_review_reason,
        inferred=bool(was_inferred and not shipment.workflow_state),
        is_archived=bool(shipment.is_archived),
    )


@router.get(
    "/shipments/{shipment_id}/available-transitions",
    response_model=WorkflowAvailableTransitionsResponse,
)
def get_shipment_available_transitions(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WorkflowAvailableTransitionsResponse:
    shipment = _get_shipment(db, shipment_id)
    flow_type = get_flow_type(shipment)
    current_state, rows = list_available_transitions(db, shipment, current_user)
    return WorkflowAvailableTransitionsResponse(
        shipment_id=shipment.id,
        flow_type=flow_type,
        current_state=current_state,
        transitions=[
            WorkflowAvailableTransition(
                transition_key=transition.transition_key,
                to_state=transition.to_state,
                to_state_label=target.state_label,
                label=transition.label,
                description=transition.description,
                requires_reason=transition.requires_reason,
                requires_confirmation=transition.requires_confirmation,
                requires_manual_review=transition.requires_manual_review,
                is_sensitive=transition.is_sensitive,
                permitted=permitted,
                permission_reason=permission_reason,
            )
            for transition, target, permitted, permission_reason in rows
        ],
    )


@router.post(
    "/shipments/{shipment_id}/transition",
    response_model=WorkflowTransitionResponse,
)
def post_shipment_transition(
    shipment_id: int,
    payload: WorkflowTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WorkflowTransitionResponse:
    shipment = _get_shipment(db, shipment_id)
    flow_type = get_flow_type(shipment)
    try:
        result = request_workflow_transition(
            db,
            shipment,
            payload.to_state,
            current_user,
            reason=payload.reason,
            confirm_sensitive=payload.confirm_sensitive,
            source="user",
            request=request,
        )
    except WorkflowError as exc:
        raise exc
    return WorkflowTransitionResponse(
        shipment_id=shipment.id,
        flow_type=flow_type,
        from_state=result["from_state"],
        to_state=result["to_state"],
        status=result["status"],
        manual_review_required=result["manual_review_required"],
        validation_status=result["validation_status"],
        reason=result.get("reason"),
        log_id=result.get("log_id"),
        event_id=result.get("event_id"),
        validation_issue_id=result.get("validation_issue_id"),
        detail=result.get("detail"),
    )


@router.get(
    "/shipments/{shipment_id}/timeline",
    response_model=WorkflowTimelineResponse,
)
def get_shipment_workflow_timeline(
    shipment_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> WorkflowTimelineResponse:
    shipment = _get_shipment(db, shipment_id)
    flow_type = get_flow_type(shipment)
    state, _was_inferred = get_or_infer_state(db, shipment)
    logs = list_workflow_logs(db, shipment.id, limit=limit)
    return WorkflowTimelineResponse(
        shipment_id=shipment.id,
        flow_type=flow_type,
        current_state=state,
        entries=[WorkflowTransitionLogRead.model_validate(row) for row in logs],
    )
