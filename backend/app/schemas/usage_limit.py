from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class UsageLimitBase(BaseModel):
    usage_key: str
    limit_value: Optional[int]
    period: str
    enforcement_mode: str
    warning_threshold_percent: int
    is_active: bool


class UsageLimitRead(UsageLimitBase):
    id: int
    plan_id: int
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class UsageLimitUpdate(BaseModel):
    limit_value: Optional[int]
    enforcement_mode: Optional[str]
    warning_threshold_percent: Optional[int]


class UsageCounterRead(BaseModel):
    id: int
    organization_id: int
    usage_key: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    used_value: int
    last_calculated_at: Optional[datetime]
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UsageEventRead(BaseModel):
    id: int
    organization_id: int
    subscription_id: Optional[int]
    usage_key: str
    event_type: str
    used_value: int
    limit_value: Optional[int]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    safe_summary: str
    created_by_user_id: Optional[int]
    created_by_name: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class UsageCheckResult(BaseModel):
    usage_key: str
    allowed: bool
    used: int
    limit: Optional[int]
    remaining: Optional[int]
    percent_used: Optional[int]
    warning: bool
    blocked: bool
    message: str


class UsageSummaryRead(BaseModel):
    organization_id: int
    counters: Dict[str, UsageCheckResult]


class UsageRecountRequest(BaseModel):
    usage_key: Optional[str] = None


class UsageRecountResult(BaseModel):
    organization_id: int
    keys_recounted: List[str]
    message: str
