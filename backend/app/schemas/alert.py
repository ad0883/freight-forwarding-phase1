from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Priority


class AlertRead(BaseModel):
    id: int
    shipment_id: int
    task_id: Optional[int] = None
    title: str
    message: str
    priority: Priority
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None
