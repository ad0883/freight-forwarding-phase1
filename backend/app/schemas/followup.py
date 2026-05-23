from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import FollowUpChannel, FollowUpStatus
from app.schemas.party import PartyRead
from app.schemas.user import UserRead


class FollowUpCreate(BaseModel):
    party_id: Optional[int] = None
    channel: FollowUpChannel
    summary: str = Field(min_length=1)
    next_action: Optional[str] = None
    status: FollowUpStatus = "open"
    date: date


class FollowUpUpdate(BaseModel):
    party_id: Optional[int] = None
    channel: Optional[FollowUpChannel] = None
    summary: Optional[str] = Field(default=None, min_length=1)
    next_action: Optional[str] = None
    status: Optional[FollowUpStatus] = None
    date: Optional[date] = None


class FollowUpRead(BaseModel):
    id: int
    shipment_id: int
    party_id: Optional[int] = None
    channel: FollowUpChannel
    summary: str
    next_action: Optional[str] = None
    status: FollowUpStatus
    logged_by: int
    date: date
    party: Optional[PartyRead] = None
    logger: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)
