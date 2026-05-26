from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


RuleSeverity = Literal["info", "warning", "critical"]


class RuleDefinitionRead(BaseModel):
    id: int
    rule_key: str
    name: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    event_type: Optional[str] = None
    severity: RuleSeverity
    is_enabled: bool
    is_blocking: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleDefinitionUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    is_blocking: Optional[bool] = None
    severity: Optional[RuleSeverity] = None
    description: Optional[str] = None
