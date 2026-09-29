"""Pydantic contracts for the Emalls read-only product extraction adapter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmallsProductsRequest(BaseModel):
    """POST body matching the observed Emalls WooCommerce extraction plugin."""

    model_config = ConfigDict(extra="ignore")

    token: str = Field(..., min_length=1, description="Token supplied by Emalls")
    page: int = Field(default=1, ge=1, description="1-based page index")
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Page size (default 50, hard cap 100)",
    )
    variation: Any = Field(
        default=None,
        description="WooCommerce compatibility field; accepted and ignored by Karzar",
    )

    @field_validator("token")
    @classmethod
    def _strip_token(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("token must not be empty")
        return stripped


class EmallsProduct(BaseModel):
    """Single product payload for Emalls consumption."""

    model_config = ConfigDict(extra="forbid")

    title: str
    subtitle: str = ""
    parent_id: int = 0
    page_unique: int
    current_price: str
    old_price: str
    availability: str
    category_name: str
    image_link: str
    image_links: list[str]
    page_url: str
    short_desc: str
    spec: list[dict[str, str]]
    date_added: str
    date_updated: str
    product_type: str = "simple"
    registry: str = ""
    guarantee: str = ""


class EmallsProductsResponse(BaseModel):
    """Root Emalls extraction response."""

    model_config = ConfigDict(extra="forbid")

    count: int
    max_pages: int
    products: list[EmallsProduct]
    Version: str
    NeedSession: bool = False
