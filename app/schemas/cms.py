"""CMS admin request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse
from app.schemas.storefront import ArticleTeaser, HeroSlideResponse, ProductCommentResponse


class ArticleAdminResponse(ArticleTeaser):
    author: str
    tags: list[str] = Field(default_factory=list)
    related_product_ids: list[int] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    is_published: bool = True


class ArticleCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=255)
    excerpt: str = Field(..., min_length=1)
    cover_image: str | None = Field(None, max_length=500)
    published_at: datetime
    reading_minutes: int = Field(default=5, ge=1)
    author: str = Field(default="تیم فنی کارزار", max_length=100)
    tags: list[str] = Field(default_factory=list)
    related_product_ids: list[int] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    is_published: bool = True


class ArticleUpdateRequest(BaseModel):
    slug: str | None = Field(None, min_length=1, max_length=200)
    title: str | None = Field(None, min_length=1, max_length=255)
    excerpt: str | None = Field(None, min_length=1)
    cover_image: str | None = Field(None, max_length=500)
    published_at: datetime | None = None
    reading_minutes: int | None = Field(None, ge=1)
    author: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    related_product_ids: list[int] | None = None
    blocks: list[dict[str, Any]] | None = None
    is_published: bool | None = None


class ArticleAdminListResponse(PaginatedResponse[ArticleAdminResponse]):
    pass


class HeroSlideCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=500)
    cta_label: str | None = Field(None, max_length=100)
    cta_href: str | None = Field(None, max_length=500)
    image: str = Field(..., min_length=1, max_length=500)
    accent: str = Field(default="#C22026", max_length=20)
    sort_order: int = 0
    is_active: bool = True


class HeroSlideUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=500)
    cta_label: str | None = Field(None, max_length=100)
    cta_href: str | None = Field(None, max_length=500)
    image: str | None = Field(None, min_length=1, max_length=500)
    accent: str | None = Field(None, max_length=20)
    sort_order: int | None = None
    is_active: bool | None = None


class HeroSlideAdminListResponse(BaseModel):
    data: list[HeroSlideResponse]


class ProductCommentCreateRequest(BaseModel):
    author_name: str = Field(..., min_length=2, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    body: str = Field(..., min_length=3)
    is_verified_buyer: bool = False


class ProductCommentAdminListResponse(PaginatedResponse[ProductCommentResponse]):
    pass


class ContactSubmissionResponse(BaseModel):
    id: int
    ticket_code: str
    full_name: str
    phone: str
    subject: str
    message: str
    created_at: datetime


class ContactSubmissionListResponse(PaginatedResponse[ContactSubmissionResponse]):
    pass
