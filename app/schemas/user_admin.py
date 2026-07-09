"""Admin user management schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse


class AdminUserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: Optional[str] = None
    role: str
    is_active: bool


class AdminUserListResponse(PaginatedResponse[AdminUserResponse]):
    pass


class AdminUserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None
