"""Admin user management schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class AdminUserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: Optional[str] = None
    role: str
    is_active: bool


class AdminUserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None
