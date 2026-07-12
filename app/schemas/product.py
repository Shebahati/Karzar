"""Product request/response Pydantic schemas for the catalog API."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DEFAULT_TAX_PERCENT
from app.db.models.product import StockUnitEnum
from app.schemas.common import PaginatedResponse, PaginationMeta

StockUnitValue = Literal["piece", "kg", "meter", "pack"]
VALID_STOCK_UNITS = {unit.value for unit in StockUnitEnum}


class CategoryBrief(BaseModel):
    id: int
    name: str
    breadcrumb: list[str] = Field(default_factory=list)
    hierarchy_label: str | None = None


class BrandBrief(BaseModel):
    id: int
    name: str
    country: str | None = None


class ProductImageResponse(BaseModel):
    id: int
    url: str
    is_primary: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Validated payload for creating a new product."""

    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    category_id: int = Field(..., ge=1, description="Required selectable (depth-3 leaf) category")
    brand_id: int | None = None

    base_price: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)
    stock_quantity: Decimal = Field(default=Decimal("0.0"), max_digits=12, decimal_places=2)
    stock_unit: StockUnitValue = "piece"

    warranty_text: str | None = None
    weight_grams: Decimal | None = None
    is_original: bool = True
    tax_percent: Decimal = Field(
        default=Decimal(str(DEFAULT_TAX_PERCENT)), ge=0, le=100
    )
    is_active: bool = True
    pdf_catalog_url: str | None = None
    description: str | None = None
    original_price: Decimal | None = Field(default=None, max_digits=15, decimal_places=2)

    specifications: dict[str, Any] = Field(default_factory=dict)

    @field_validator("base_price", "weight_grams", "stock_quantity")
    @classmethod
    def check_non_negative(cls, v: Decimal | None, info) -> Decimal | None:
        if v is not None and v < Decimal("0.0"):
            raise ValueError(f"{info.field_name} cannot be negative")
        return v

    @field_validator("tax_percent")
    @classmethod
    def check_tax_percent(cls, v: Decimal) -> Decimal:
        if v < Decimal("0.0") or v > Decimal("100.0"):
            raise ValueError("tax_percent must be between 0 and 100")
        return v

    @field_validator("sku", mode="before")
    @classmethod
    def clean_sku(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        stripped = v.strip().upper()
        if not stripped:
            raise ValueError("sku cannot be empty or whitespace")
        return stripped

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be empty or whitespace")
        return stripped

    @field_validator("stock_unit")
    @classmethod
    def validate_stock_unit(cls, v: str) -> str:
        if v not in VALID_STOCK_UNITS:
            raise ValueError(f"stock_unit must be one of: {', '.join(sorted(VALID_STOCK_UNITS))}")
        return v


class ProductUpdate(BaseModel):
    """Partial update payload; omitted fields are left unchanged.

    Explicit null on required string columns (sku, name) is rejected
    to prevent IntegrityError at the database layer. category_id may be
    omitted on PATCH (leave unchanged) but cannot be cleared to null.
    """

    sku: str | None = None
    name: str | None = None
    category_id: int | None = Field(None, ge=1)
    brand_id: int | None = None
    base_price: Decimal | None = None
    stock_quantity: Decimal | None = None
    stock_unit: StockUnitValue | None = None
    warranty_text: str | None = None
    weight_grams: Decimal | None = None
    is_original: bool | None = None
    tax_percent: Decimal | None = None
    is_active: bool | None = None
    pdf_catalog_url: str | None = None
    description: str | None = None
    original_price: Decimal | None = None
    specifications: dict[str, Any] | None = None

    @field_validator("sku", "name", mode="before")
    @classmethod
    def check_not_null_and_clean(cls, v: Any, info) -> Any:
        """Reject explicit null and whitespace-only values on required string fields."""
        if v is None:
            raise ValueError(f"{info.field_name} cannot be explicitly set to null")
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")
        if info.field_name == "sku":
            return stripped.upper()
        return stripped

    @field_validator("stock_unit")
    @classmethod
    def validate_stock_unit(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STOCK_UNITS:
            raise ValueError(f"stock_unit must be one of: {', '.join(sorted(VALID_STOCK_UNITS))}")
        return v



class ProductSummaryResponse(BaseModel):
    """PLP card shape returned by GET /products."""

    id: int
    sku: str
    name: str
    thumbnail: str | None = None
    base_price: str | None = None
    original_price: str | None = None
    discount_percent: int | None = None
    stock_status: str
    availability: bool = False
    is_original: bool = True
    category: CategoryBrief | None = None
    brand: BrandBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(BaseModel):
    """Full PDP shape including images, specifications, and computed stock fields."""

    id: int
    sku: str
    name: str
    category_id: int | None = None
    brand_id: int | None
    category: CategoryBrief | None = None
    brand: BrandBrief | None = None
    base_price: str | None = None
    original_price: str | None = None
    discount_percent: int | None = None
    stock_quantity: str
    stock_unit: str
    stock_status: str
    low_stock: bool
    availability: bool
    warranty_text: str | None
    weight_grams: str | None = None
    is_original: bool
    tax_percent: str
    is_active: bool
    pdf_catalog_url: str | None
    description: str | None = None
    thumbnail: str | None = None
    images: list[ProductImageResponse] = Field(default_factory=list)
    specifications: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ProductImageCreate(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)
    is_primary: bool = False


class ProductImageReorderRequest(BaseModel):
    image_ids: list[int] = Field(..., min_length=1)


class ProductImageSetPrimaryResponse(BaseModel):
    product_id: int
    image_id: int
    is_primary: bool = True


class ProductImageUploadResponse(BaseModel):
    id: int
    url: str
    is_primary: bool


class ProductStatisticsResponse(BaseModel):
    total_products: int
    active_products: int
    total_stock_value: str
    total_stock_quantity: str
    categories: int
    brands: int


class ProductListResponse(PaginatedResponse[ProductSummaryResponse]):
    pass


class StockStatusResponse(BaseModel):
    """Admin stock snapshot. stock_status uses English codes: in_stock | low_stock | out_of_stock."""

    product_id: int
    sku: str
    stock_quantity: Decimal
    stock_status: str


class BulkStockAdjustItem(BaseModel):
    product_id: int = Field(..., ge=1)
    quantity_delta: Decimal
    reason: str | None = Field(None, max_length=255)


class BulkStockAdjustRequest(BaseModel):
    items: list[BulkStockAdjustItem] = Field(..., min_length=1, max_length=100)


class BulkStockAdjustResponse(BaseModel):
    updated_product_ids: list[int]


class ProductChangeLogEntry(BaseModel):
    id: int
    product_id: int
    field_name: str
    old_value: str | None = None
    new_value: str | None = None
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductChangeLogListResponse(BaseModel):
    data: list[ProductChangeLogEntry]
    meta: PaginationMeta
