from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Role


NotificationCategory = Literal[
    "task",
    "shipment",
    "document",
    "bl",
    "demurrage",
    "finance",
    "gmail",
    "ai",
    "system",
]
NotificationPriority = Literal["critical", "warning", "info", "none"]
NotificationStatus = Literal["unread", "read", "dismissed"]
NotificationSource = Literal["system", "scheduler", "manual", "gmail", "workflow", "finance"]


class NotificationRead(BaseModel):
    id: int
    title: str
    message: str
    category: NotificationCategory
    priority: NotificationPriority
    status: NotificationStatus
    target_role: Optional[Role] = None
    target_user_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    entity_label: Optional[str] = None
    action_url: Optional[str] = None
    dedupe_key: Optional[str] = None
    source: NotificationSource
    created_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None


class NotificationUnreadCount(BaseModel):
    unread_count: int


class NotificationActionResponse(BaseModel):
    notification: NotificationRead


class NotificationBulkActionResponse(BaseModel):
    updated: int


class NotificationRuleRead(BaseModel):
    id: int
    rule_key: str
    name: str
    description: Optional[str] = None
    category: NotificationCategory
    priority: NotificationPriority
    is_enabled: bool
    threshold_days: Optional[int] = None
    target_role: Optional[Role] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationRuleUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    threshold_days: Optional[int] = Field(default=None, ge=0, le=365)
    priority: Optional[NotificationPriority] = None
    target_role: Optional[Role] = None


class NotificationRunChecksResponse(BaseModel):
    created: int
    checked_rules: list[str]
    skipped_rules: list[str]


class DailySummaryTotals(BaseModel):
    open_tasks: int
    overdue_tasks: int
    shipments_needing_attention: int
    demurrage_risks: int
    pending_bl_approvals: int
    pending_receivables_total: Decimal
    pending_payables_total: Decimal
    pending_gmail_suggestions: int
    unread_notifications: int
    currency: str
    multiple_currencies: bool = False


class DailySummaryItem(BaseModel):
    title: str
    message: str
    category: NotificationCategory
    priority: NotificationPriority
    action_url: Optional[str] = None
    entity_label: Optional[str] = None
    due_date: Optional[date] = None


class DailySummaryRead(BaseModel):
    generated_at: datetime
    totals: DailySummaryTotals
    top_urgent_items: list[DailySummaryItem] = Field(default_factory=list)
