"""Pydantic contracts for the direct Emalls PDF product-feed adapter.

Authoritative source: Emalls PDF «راهنمای ایجاد صفحه معرفی محصولات به ایمالز».
Intentionally separate from the WordPress-compatible `/products` adapter.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EmallsPdfProduct(BaseModel):
    """Single product row for the Emalls PDF feed contract."""

    model_config = ConfigDict(extra="forbid")

    title: str
    id: str
    price: int
    old_price: int | None = None
    category: str
    image: str
    color: str = ""
    guarantee: str = ""
    is_available: bool
    url: str


class EmallsPdfFeedResponse(BaseModel):
    """Root PDF feed response (exact field names from the Emalls PDF)."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    products: list[EmallsPdfProduct]
    total_items: int
    pages_count: int
    item_per_page: int
    page_num: int


# Query defaults / Karzar operational safety (not specified by the PDF).
EMALLS_PDF_DEFAULT_PAGE = 1
EMALLS_PDF_DEFAULT_ITEM_PER_PAGE = 50
EMALLS_PDF_MAX_ITEM_PER_PAGE = 100
