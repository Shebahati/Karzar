"""Admin user management schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse


class AdminUserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    email: Optional[str] = None
    order_count: int = 0
    created_at: Optional[datetime] = None
    note: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class AdminUserListResponse(PaginatedResponse[AdminUserResponse]):
    pass


class AdminUserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
