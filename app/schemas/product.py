"""Product request/response Pydantic schemas for the catalog API."""

from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal

from app.core.constants import DEFAULT_TAX_PERCENT
from app.db.models.product import StockUnitEnum
from app.schemas.common import PaginatedResponse

StockUnitValue = Literal["piece", "kg", "meter", "pack"]
VALID_STOCK_UNITS = {unit.value for unit in StockUnitEnum}


class CategoryBrief(BaseModel):
    id: int
    name: str
    breadcrumb: List[str] = Field(default_factory=list)
    hierarchy_label: Optional[str] = None


class BrandBrief(BaseModel):
    id: int
    name: str
    country: Optional[str] = None


class ProductImageResponse(BaseModel):
    id: int
    url: str
    is_primary: bool

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Validated payload for creating a new product."""

    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    # Intentionally Optional: admin UI requires category_id, but PATCH may omit it.
    category_id: Optional[int] = None
    brand_id: Optional[int] = None

    base_price: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    stock_quantity: Decimal = Field(default=Decimal("0.0"), max_digits=12, decimal_places=2)
    stock_unit: StockUnitValue = "piece"

    warranty_text: Optional[str] = None
    weight_grams: Optional[Decimal] = None
    is_original: bool = True
    tax_percent: Decimal = Field(
        default=Decimal(str(DEFAULT_TAX_PERCENT)), ge=0, le=100
    )
    is_active: bool = True
    pdf_catalog_url: Optional[str] = None
    description: Optional[str] = None
    original_price: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)

    specifications: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("base_price", "weight_grams", "stock_quantity")
    @classmethod
    def check_non_negative(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
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
    set to null to move a product to uncategorized.
    """

    sku: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    base_price: Optional[Decimal] = None
    stock_quantity: Optional[Decimal] = None
    stock_unit: Optional[StockUnitValue] = None
    warranty_text: Optional[str] = None
    weight_grams: Optional[Decimal] = None
    is_original: Optional[bool] = None
    tax_percent: Optional[Decimal] = None
    is_active: Optional[bool] = None
    pdf_catalog_url: Optional[str] = None
    description: Optional[str] = None
    original_price: Optional[Decimal] = None
    specifications: Optional[Dict[str, Any]] = None

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
    def validate_stock_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STOCK_UNITS:
            raise ValueError(f"stock_unit must be one of: {', '.join(sorted(VALID_STOCK_UNITS))}")
        return v



class ProductSummaryResponse(BaseModel):
    """PLP card shape returned by GET /products."""

    id: int
    sku: str
    name: str
    thumbnail: Optional[str] = None
    base_price: Optional[str] = None
    original_price: Optional[str] = None
    discount_percent: Optional[int] = None
    stock_status: str
    availability: bool = False
    is_original: bool = True
    category: Optional[CategoryBrief] = None
    brand: Optional[BrandBrief] = None

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(BaseModel):
    """Full PDP shape including images, specifications, and computed stock fields."""

    id: int
    sku: str
    name: str
    category_id: Optional[int] = None
    brand_id: Optional[int]
    category: Optional[CategoryBrief] = None
    brand: Optional[BrandBrief] = None
    base_price: Optional[str] = None
    original_price: Optional[str] = None
    discount_percent: Optional[int] = None
    stock_quantity: str
    stock_unit: str
    stock_status: str
    low_stock: bool
    availability: bool
    warranty_text: Optional[str]
    weight_grams: Optional[str] = None
    is_original: bool
    tax_percent: str
    is_active: bool
    pdf_catalog_url: Optional[str]
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    images: List[ProductImageResponse] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ProductImageCreate(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=500)
    is_primary: bool = False


class ProductImageReorderRequest(BaseModel):
    image_ids: List[int] = Field(..., min_length=1)


class ProductImageSetPrimaryResponse(BaseModel):
    product_id: int
    image_id: int
    is_primary: bool = True


class ProductListResponse(PaginatedResponse[ProductSummaryResponse]):
    pass


class StockStatusResponse(BaseModel):
    product_id: int
    sku: str
    stock_quantity: Decimal
    stock_status: str
