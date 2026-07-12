"""Storefront content and commerce response schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import PHONE_PATTERN

BlogBlock = (
    dict[Literal["type"], Literal["paragraph"]]
    | dict[Literal["type"], Literal["heading"]]
    | dict[Literal["type"], Literal["list"]]
)


class ArticleTeaser(BaseModel):
    id: int
    slug: str
    title: str
    excerpt: str
    cover_image: str
    published_at: datetime
    reading_minutes: int

    model_config = ConfigDict(from_attributes=True)


class BlogPostResponse(ArticleTeaser):
    author: str
    tags: list[str] = Field(default_factory=list)
    related_product_ids: list[int] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)


class ArticleListResponse(BaseModel):
    data: list[ArticleTeaser]


class HeroSlideResponse(BaseModel):
    id: int
    title: str
    subtitle: str = ""
    cta_label: str = ""
    cta_href: str = ""
    image: str
    accent: str

    model_config = ConfigDict(from_attributes=True)


class HeroSlideListResponse(BaseModel):
    data: list[HeroSlideResponse]


class ProductCommentResponse(BaseModel):
    id: int
    product_id: int
    author_name: str
    rating: int
    body: str
    created_at: datetime
    is_verified_buyer: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCommentListResponse(BaseModel):
    data: list[ProductCommentResponse]


class ProductCommentCreateRequest(BaseModel):
    author_name: str = Field(..., min_length=2, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    body: str = Field(..., min_length=3)
    is_verified_buyer: bool = False


class RelatedProductsResponse(BaseModel):
    data: list[Any]


class ContactRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class ContactResponse(BaseModel):
    ok: bool = True
    ticket: str


class CheckoutLineInput(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)


class CheckoutCustomer(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str
    is_guest: bool = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class ShippingAddress(BaseModel):
    province: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    postal_code: str
    address_line: str = Field(..., min_length=10)

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit() or len(normalized) != 10:
            raise ValueError("postal_code must be exactly 10 digits")
        return normalized


class CheckoutRequest(BaseModel):
    mode: Literal["purchase", "inquiry"]
    customer: CheckoutCustomer
    items: list[CheckoutLineInput] = Field(..., min_length=1)
    note: str | None = Field(None, max_length=500)
    shipping: ShippingAddress | None = None
    company_name: str | None = Field(None, max_length=120)


class CheckoutResponse(BaseModel):
    order_id: int
    tracking_code: str
    mode: Literal["purchase", "inquiry"]
    status: str
    status_label: str
    estimated_total: str | None = None
    created_at: datetime
    payment_url: str | None = None
    authority: str | None = None
