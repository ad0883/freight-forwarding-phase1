from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


ValidationIssueStatus = Literal["open", "acknowledged", "resolved", "dismissed"]
ValidationIssueSeverity = Literal["info", "warning", "critical"]


class ValidationIssueRead(BaseModel):
    id: int
    event_id: Optional[int] = None
    rule_key: str
    entity_type: str
    entity_id: Optional[int] = None
    entity_label: Optional[str] = None
    shipment_id: Optional[int] = None
    severity: ValidationIssueSeverity
    status: ValidationIssueStatus
    message: str
    recommended_action: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
