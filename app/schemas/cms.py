"""CMS admin request/response schemas."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse
from app.schemas.storefront import ArticleTeaser, HeroSlideResponse, ProductCommentResponse


class ArticleAdminResponse(ArticleTeaser):
    author: str
    tags: List[str] = Field(default_factory=list)
    related_product_ids: List[int] = Field(default_factory=list)
    blocks: List[dict[str, Any]] = Field(default_factory=list)
    is_published: bool = True


class ArticleCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=255)
    excerpt: str = Field(..., min_length=1)
    cover_image: Optional[str] = Field(None, max_length=500)
    published_at: datetime
    reading_minutes: int = Field(default=5, ge=1)
    author: str = Field(default="تیم فنی کارزار", max_length=100)
    tags: List[str] = Field(default_factory=list)
    related_product_ids: List[int] = Field(default_factory=list)
    blocks: List[dict[str, Any]] = Field(default_factory=list)
    is_published: bool = True


class ArticleUpdateRequest(BaseModel):
    slug: Optional[str] = Field(None, min_length=1, max_length=200)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    excerpt: Optional[str] = Field(None, min_length=1)
    cover_image: Optional[str] = Field(None, max_length=500)
    published_at: Optional[datetime] = None
    reading_minutes: Optional[int] = Field(None, ge=1)
    author: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    related_product_ids: Optional[List[int]] = None
    blocks: Optional[List[dict[str, Any]]] = None
    is_published: Optional[bool] = None


class ArticleAdminListResponse(PaginatedResponse[ArticleAdminResponse]):
    pass


class HeroSlideCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    cta_label: Optional[str] = Field(None, max_length=100)
    cta_href: Optional[str] = Field(None, max_length=500)
    image: str = Field(..., min_length=1, max_length=500)
    accent: str = Field(default="#C22026", max_length=20)
    sort_order: int = 0
    is_active: bool = True


class HeroSlideUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(None, max_length=500)
    cta_label: Optional[str] = Field(None, max_length=100)
    cta_href: Optional[str] = Field(None, max_length=500)
    image: Optional[str] = Field(None, min_length=1, max_length=500)
    accent: Optional[str] = Field(None, max_length=20)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class HeroSlideAdminListResponse(BaseModel):
    data: List[HeroSlideResponse]


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
