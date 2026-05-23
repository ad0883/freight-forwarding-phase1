from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import BLType


class BLManagementRead(BaseModel):
    id: int
    shipment_id: int
    bl_type: BLType
    draft_received: Optional[date] = None
    corrections: Optional[str] = None
    approval_date: Optional[date] = None
    final_bl_date: Optional[date] = None
    surrender_done: bool
    telex_release: bool
    file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BLManagementUpdate(BaseModel):
    bl_type: Optional[BLType] = None
    draft_received: Optional[date] = None
    corrections: Optional[str] = None
    approval_date: Optional[date] = None
    final_bl_date: Optional[date] = None
    surrender_done: Optional[bool] = None
    telex_release: Optional[bool] = None
    file_url: Optional[str] = None
