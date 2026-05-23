from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DemurrageStatus


class DemurrageRead(BaseModel):
    id: int
    shipment_id: int
    free_days: Optional[int] = None
    start_date: Optional[date] = None
    rate_per_day: Optional[Decimal] = None
    currency: str
    alert_at_days: int
    container_count: int
    status: DemurrageStatus
    free_days_end_date: Optional[date] = None
    days_used: int
    days_remaining: Optional[int] = None
    is_demurrage_running: bool
    total_demurrage_due: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DemurrageUpdate(BaseModel):
    free_days: Optional[int] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    rate_per_day: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = None
    alert_at_days: Optional[int] = Field(default=None, ge=0)
    container_count: Optional[int] = Field(default=None, ge=1)
