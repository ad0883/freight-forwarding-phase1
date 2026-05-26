from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


FlowType = Literal["export", "import"]
TransitionStatus = Literal[
    "requested",
    "applied",
    "blocked",
    "manual_review_required",
    "failed",
]
TransitionSource = Literal[
    "user",
    "system",
    "gmail",
    "ai",
    "workflow",
    "scheduler",
]
ValidationStatus = Literal[
    "not_checked",
    "passed",
    "warning",
    "failed",
    "manual_review_required",
]


class WorkflowStateRead(BaseModel):
    id: int
    flow_type: FlowType
    state_key: str
    state_label: str
    state_order: int
    description: Optional[str] = None
    is_initial: bool
    is_terminal: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class WorkflowTransitionRead(BaseModel):
    id: int
    flow_type: FlowType
    transition_key: str
    from_state: Optional[str] = None
    to_state: str
    label: str
    description: Optional[str] = None
    requires_reason: bool
    requires_confirmation: bool
    requires_manual_review: bool
    is_sensitive: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class WorkflowTransitionLogRead(BaseModel):
    id: int
    shipment_id: int
    flow_type: FlowType
    transition_key: Optional[str] = None
    from_state: Optional[str] = None
    to_state: str
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    source: TransitionSource
    status: TransitionStatus
    reason: Optional[str] = None
    validation_status: ValidationStatus
    event_id: Optional[int] = None
    validation_issue_id: Optional[int] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowShipmentStateRead(BaseModel):
    shipment_id: int
    shipment_code: str
    flow_type: FlowType
    workflow_state: Optional[str] = None
    workflow_state_label: Optional[str] = None
    workflow_state_updated_at: Optional[datetime] = None
    workflow_state_reason: Optional[str] = None
    manual_review_required: bool = False
    manual_review_reason: Optional[str] = None
    inferred: bool = False
    is_archived: bool = False


class WorkflowAvailableTransition(BaseModel):
    transition_key: str
    to_state: str
    to_state_label: str
    label: str
    description: Optional[str] = None
    requires_reason: bool
    requires_confirmation: bool
    requires_manual_review: bool
    is_sensitive: bool
    permitted: bool
    permission_reason: Optional[str] = None


class WorkflowAvailableTransitionsResponse(BaseModel):
    shipment_id: int
    flow_type: FlowType
    current_state: Optional[str] = None
    transitions: list[WorkflowAvailableTransition] = Field(default_factory=list)


class WorkflowTransitionRequest(BaseModel):
    to_state: str = Field(min_length=1, max_length=80)
    reason: Optional[str] = Field(default=None, max_length=500)
    confirm_sensitive: bool = False


class WorkflowTransitionResponse(BaseModel):
    shipment_id: int
    flow_type: FlowType
    from_state: Optional[str] = None
    to_state: str
    status: TransitionStatus
    manual_review_required: bool
    validation_status: ValidationStatus
    reason: Optional[str] = None
    log_id: Optional[int] = None
    event_id: Optional[int] = None
    validation_issue_id: Optional[int] = None
    detail: Optional[str] = None


class WorkflowTimelineResponse(BaseModel):
    shipment_id: int
    flow_type: FlowType
    current_state: Optional[str] = None
    entries: list[WorkflowTransitionLogRead] = Field(default_factory=list)
