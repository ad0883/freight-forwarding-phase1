"""Phase 16 approval engine Pydantic schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ApprovalType = Literal[
    "workflow_transition", "document_approval", "document_intelligence_apply",
    "gmail_suggestion_apply", "finance_hold_waiver", "finance_adjustment",
    "payment_allocation", "credit_limit_override", "release_action",
    "container_exception_override", "manual_exception_resolution", "bot_action", "other",
]
ApprovalSource = Literal[
    "manual", "exception_case", "workflow", "document_intelligence",
    "gmail_suggestion", "finance_control", "release_control", "ai_assistant", "system_rule",
]
ApprovalStatus = Literal[
    "draft", "pending", "in_review", "changes_requested",
    "approved", "rejected", "cancelled", "expired", "executed", "failed_execution",
]
RiskLevel = Literal["low", "medium", "high", "critical"]
StepStatus = Literal["pending", "in_review", "approved", "rejected", "changes_requested", "skipped", "expired"]
StepDecision = Literal["approve", "reject", "request_changes", "escalate", "skip"]


class ApprovalRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    approval_type: ApprovalType = "other"
    source: ApprovalSource = "manual"
    risk_level: RiskLevel = "medium"
    priority: Optional[str] = "p3"
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    shipment_id: Optional[int] = None
    party_id: Optional[int] = None
    exception_case_id: Optional[int] = None
    requested_action: str = Field(min_length=1, max_length=255)
    requested_payload_json: Optional[dict[str, Any]] = None
    safe_summary_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None


class ApprovalRequestUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    priority: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    assigned_to_role: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class ApprovalRequestRead(BaseModel):
    id: int
    organization_id: Optional[int] = None
    approval_number: str
    title: str
    description: Optional[str] = None
    approval_type: str
    source: str
    status: str
    risk_level: str
    priority: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    shipment_id: Optional[int] = None
    party_id: Optional[int] = None
    exception_case_id: Optional[int] = None
    requested_action: str
    requested_payload_json: Optional[dict[str, Any]] = None
    safe_summary_json: Optional[dict[str, Any]] = None
    requested_by_user_id: Optional[int] = None
    requested_by_name: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_to_role: Optional[str] = None
    current_step_no: int
    required_steps: int
    due_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    final_decision_by_user_id: Optional[int] = None
    final_decision_by_name: Optional[str] = None
    final_decision_notes: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApprovalStepRead(BaseModel):
    id: int
    approval_request_id: int
    step_no: int
    approver_user_id: Optional[int] = None
    approver_name: Optional[str] = None
    approver_role: Optional[str] = None
    status: str
    decision: Optional[str] = None
    decision_notes: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


class ApprovalDecisionRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)


class ApprovalPolicyRead(BaseModel):
    id: int
    name: str
    approval_type: str
    risk_level: str
    is_active: bool
    required_approver_role: str
    required_steps: int
    maker_checker_required: bool
    admin_override_allowed: bool
    auto_expire_hours: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


class ApprovalPolicyUpdate(BaseModel):
    is_active: Optional[bool] = None
    required_approver_role: Optional[str] = None
    required_steps: Optional[int] = Field(default=None, ge=1, le=5)
    maker_checker_required: Optional[bool] = None
    admin_override_allowed: Optional[bool] = None
    auto_expire_hours: Optional[int] = Field(default=None, ge=1)


class ApprovalEvidenceCreate(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=60)
    linked_type: Optional[str] = None
    linked_id: Optional[int] = None
    label: Optional[str] = None
    summary: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class ApprovalEvidenceRead(BaseModel):
    id: int
    approval_request_id: int
    evidence_type: str
    linked_type: Optional[str] = None
    linked_id: Optional[int] = None
    label: Optional[str] = None
    summary: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ActionLockCheckRequest(BaseModel):
    entity_type: str
    entity_id: int
    action_key: str


class ActionLockCheckResponse(BaseModel):
    allowed: bool
    lock_id: Optional[int] = None
    lock_reason: Optional[str] = None
    approval_request_id: Optional[int] = None


class ActionLockRead(BaseModel):
    id: int
    approval_request_id: Optional[int] = None
    entity_type: str
    entity_id: int
    action_key: str
    lock_reason: Optional[str] = None
    status: str
    created_at: datetime
    released_at: Optional[datetime] = None
    released_by_user_id: Optional[int] = None
    released_by_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class BotGovernanceActionRead(BaseModel):
    id: int
    bot_name: Optional[str] = None
    action_type: str
    source: str
    status: str
    risk_level: str
    confidence: Optional[Decimal] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    shipment_id: Optional[int] = None
    approval_request_id: Optional[int] = None
    proposed_payload_json: Optional[dict[str, Any]] = None
    safe_summary_json: Optional[dict[str, Any]] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)


class ApprovalSummary(BaseModel):
    total_pending: int = 0
    total_assigned_to_me: int = 0
    total_high_risk: int = 0
    total_overdue: int = 0
    total_bot_pending: int = 0
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_risk: dict[str, int] = {}
