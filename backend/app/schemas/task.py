from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Priority, TaskStatus


class TaskBase(BaseModel):
    shipment_id: int
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_date: Optional[date] = None
    priority: Priority = "info"
    status: TaskStatus = "open"


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_date: Optional[date] = None
    priority: Optional[Priority] = None
    status: Optional[TaskStatus] = None


class TaskRead(TaskBase):
    id: int
    auto_generated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
