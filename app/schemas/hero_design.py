"""Pydantic DTOs for Hero Studio PR1 APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

EXPECTED_R0_SHA256 = "1d4e7aa46f2d6f3aa04578be67af18bbb9672e337ef1b1ad8eeaa16acbdae674"
REBORN_FIVE_DOCK_KEYS = (
    "discounts",
    "metrology",
    "inserts",
    "endmills",
    "industrial-machines",
)


class HeroValidationErrorItem(BaseModel):
    field: str
    message: str


class HeroValidateRequest(BaseModel):
    pack_json: dict[str, Any]


class HeroValidateResponse(BaseModel):
    valid: bool
    errors: list[HeroValidationErrorItem] = Field(default_factory=list)


class HeroPublishRequest(BaseModel):
    expected_parent_revision_id: str | None = None
    publish_comment: str | None = Field(default=None, max_length=2000)


class HeroRollbackRequest(BaseModel):
    revision_id: str = Field(min_length=36, max_length=36)


class HeroRevisionSummary(BaseModel):
    id: str
    status: str
    pack_sha256: str
    created_at: datetime
    created_by: int | None = None
    publish_comment: str | None = None


class HeroRevisionListResponse(BaseModel):
    items: list[HeroRevisionSummary]
    total: int


class HeroDesignedPackResponse(BaseModel):
    revision_id: str
    etag: str
    profile: str
    schema_version: int
    published_at: datetime
    pack: dict[str, Any]
    published_by: int | None = None
    pack_sha256: str | None = None


class HeroPublishResult(BaseModel):
    revision_id: str
    etag: str
    published_at: datetime


class HeroDraftReadResponse(BaseModel):
    base_revision_id: str | None
    draft_json: dict[str, Any]
    lock_version: int
    updated_at: datetime
