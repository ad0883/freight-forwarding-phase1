from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import Role


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    role: Role = "STAFF"
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class AdminPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class UserRead(UserBase):
    id: int
    created_at: datetime
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
