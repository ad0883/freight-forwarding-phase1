from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


EventValidationStatus = Literal[
    "not_checked",
    "passed",
    "warning",
    "failed",
    "manual_review_required",
]

EventSource = Literal[
    "user",
    "system",
    "gmail",
    "ai",
    "scheduler",
    "workflow",
    "finance",
    "notification",
]


class OperationalEventRead(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: Optional[int] = None
    entity_label: Optional[str] = None
    shipment_id: Optional[int] = None
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    source: EventSource
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    previous_state_json: Optional[dict[str, Any]] = None
    new_state_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    validation_status: EventValidationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
