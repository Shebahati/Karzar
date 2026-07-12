"""Admin user management schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse


class AdminUserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: str | None = None
    role: str
    is_active: bool
    email: str | None = None
    order_count: int = 0
    created_at: datetime
    note: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class AdminUserListResponse(PaginatedResponse[AdminUserResponse]):
    pass


class AdminUserUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    role: str | None = None
    is_active: bool | None = None
    email: str | None = Field(None, max_length=255)
    note: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=50)
    tags: list[str] | None = None
