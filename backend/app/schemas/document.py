from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DocumentStatus


class DocumentRead(BaseModel):
    id: int
    shipment_id: int
    doc_type: str
    status: DocumentStatus
    date_received: Optional[date] = None
    date_sent: Optional[date] = None
    file_url: Optional[str] = None
    notes: Optional[str] = None
    is_required: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    status: Optional[DocumentStatus] = None
    date_received: Optional[date] = None
    date_sent: Optional[date] = None
    file_url: Optional[str] = None
    notes: Optional[str] = None
    is_required: Optional[bool] = None
