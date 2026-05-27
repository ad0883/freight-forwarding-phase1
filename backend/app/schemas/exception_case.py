"""Phase 15 exception engine Pydantic schemas."""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ExceptionCategory = Literal[
    "workflow", "document", "container", "finance", "gmail", "ai",
    "validation", "notification", "sla", "party", "shipment",
    "system", "security", "other",
]
ExceptionSource = Literal[
    "validation_issue", "operational_event", "notification",
    "document_mismatch", "finance_hold", "finance_risk",
    "workflow_transition", "container_risk", "gmail_suggestion",
    "ai_low_confidence", "manual", "system_check",
]
ExceptionSeverity = Literal["info", "low", "medium", "high", "critical"]
ExceptionPriority = Literal["p4", "p3", "p2", "p1", "p0"]
ExceptionStatus = Literal[
    "open", "acknowledged", "in_review",
    "waiting_on_party", "waiting_on_document", "waiting_on_finance",
    "waiting_on_customer", "waiting_on_vendor",
    "escalated", "resolved", "dismissed", "reopened",
]


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------

class ExceptionCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    category: ExceptionCategory = "other"
    source: ExceptionSource = "manual"
    severity: ExceptionSeverity = "medium"
    priority: ExceptionPriority = "p3"
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    shipment_id: Optional[int] = None
    party_id: Optional[int] = None
    dedupe_key: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class ExceptionCaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    description: Optional[str] = None
    severity: Optional[ExceptionSeverity] = None
    priority: Optional[ExceptionPriority] = None
    status: Optional[ExceptionStatus] = None
    metadata_json: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

class ExceptionCaseRead(BaseModel):
    id: int
    organization_id: Optional[int] = None
    case_number: str
    title: str
    description: Optional[str] = None
    category: str
    source: str
    severity: str
    priority: str
    status: str
    risk_score: int
    dedupe_key: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    shipment_id: Optional[int] = None
    party_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_to_role: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    due_at: Optional[datetime] = None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolution_notes: Optional[str] = None
    dismissed_at: Optional[datetime] = None
    dismissed_by_user_id: Optional[int] = None
    dismissed_by_name: Optional[str] = None
    dismissal_reason: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExceptionCaseLinkRead(BaseModel):
    id: int
    exception_case_id: int
    linked_type: str
    linked_id: int
    linked_label: Optional[str] = None
    relationship_type: str
    created_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ExceptionCaseLinkCreate(BaseModel):
    linked_type: str = Field(min_length=1, max_length=80)
    linked_id: int
    linked_label: Optional[str] = None
    relationship_type: str = "related"
    metadata_json: Optional[dict[str, Any]] = None


class ExceptionCaseCommentRead(BaseModel):
    id: int
    exception_case_id: int
    author_user_id: Optional[int] = None
    author_name: Optional[str] = None
    comment_text: str
    is_internal: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ExceptionCaseCommentCreate(BaseModel):
    comment_text: str = Field(min_length=1, max_length=5000)
    is_internal: bool = True


class ExceptionCaseStatusHistoryRead(BaseModel):
    id: int
    exception_case_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by_user_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ExceptionCaseAssignRequest(BaseModel):
    assigned_to_user_id: Optional[int] = None
    assigned_to_role: Optional[str] = None
    notes: Optional[str] = None


class ExceptionCaseResolveRequest(BaseModel):
    resolution_notes: str = Field(min_length=1, max_length=2000)


class ExceptionCaseDismissRequest(BaseModel):
    dismissal_reason: str = Field(min_length=1, max_length=2000)


class ExceptionCaseReopenRequest(BaseModel):
    reason: Optional[str] = None


class ExceptionCaseEscalateRequest(BaseModel):
    severity: Optional[ExceptionSeverity] = None
    priority: Optional[ExceptionPriority] = None
    reason: str = Field(min_length=1, max_length=2000)


class ExceptionCaseEscalationRead(BaseModel):
    id: int
    exception_case_id: int
    from_severity: Optional[str] = None
    to_severity: str
    from_priority: Optional[str] = None
    to_priority: str
    escalation_reason: str
    escalated_by_user_id: Optional[int] = None
    escalated_by_name: Optional[str] = None
    escalated_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ExceptionCaseSlaPolicyRead(BaseModel):
    id: int
    category: str
    severity: str
    priority: str
    response_minutes: int
    resolution_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ExceptionCaseSlaPolicyUpdate(BaseModel):
    response_minutes: Optional[int] = Field(default=None, ge=1)
    resolution_minutes: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class ExceptionSummary(BaseModel):
    total_open: int = 0
    total_critical: int = 0
    total_assigned_to_me: int = 0
    total_overdue: int = 0
    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
