from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import PartyType


class PartyBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: PartyType
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    gstin: Optional[str] = None


class PartyCreate(PartyBase):
    pass


class PartyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    type: Optional[PartyType] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    gstin: Optional[str] = None


class PartyRead(PartyBase):
    id: int
    is_active: bool = True
    deactivated_at: Optional[datetime] = None
    deactivated_by: Optional[int] = None
    deactivation_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartyDeactivationRequest(BaseModel):
    reason: Optional[str] = None
