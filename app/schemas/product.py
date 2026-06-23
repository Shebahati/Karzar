from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal

from app.db.models.product import StockUnitEnum
from app.schemas.common import PaginatedResponse

StockUnitValue = Literal["piece", "kg", "meter", "pack"]
VALID_STOCK_UNITS = {unit.value for unit in StockUnitEnum}


class CategoryBrief(BaseModel):
    id: int
    name: str


class BrandBrief(BaseModel):
    id: int
    name: str


class ProductImageResponse(BaseModel):
    id: int
    url: str
    is_primary: bool


class ProductCreate(BaseModel):
    sku: str
    name: str
    category_id: int
    brand_id: Optional[int] = None

    base_price: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    stock_quantity: Decimal = Field(default=Decimal("0.0"), max_digits=12, decimal_places=2)
    stock_unit: StockUnitValue = "piece"

    warranty_text: Optional[str] = None
    weight_grams: Optional[Decimal] = None
    is_original: bool = True
    tax_percent: Decimal = Field(default=Decimal("0.0"), ge=0, le=100)
    is_active: bool = True
    pdf_catalog_url: Optional[str] = None

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

    @field_validator("sku")
    @classmethod
    def clean_sku(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("stock_unit")
    @classmethod
    def validate_stock_unit(cls, v: str) -> str:
        if v not in VALID_STOCK_UNITS:
            raise ValueError(f"stock_unit must be one of: {', '.join(sorted(VALID_STOCK_UNITS))}")
        return v


class ProductUpdate(BaseModel):
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
    specifications: Optional[Dict[str, Any]] = None

    @field_validator("sku")
    @classmethod
    def clean_sku(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.strip().upper()

    @field_validator("stock_unit")
    @classmethod
    def validate_stock_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STOCK_UNITS:
            raise ValueError(f"stock_unit must be one of: {', '.join(sorted(VALID_STOCK_UNITS))}")
        return v


class ProductResponse(BaseModel):
    """Admin create/update response — full product record."""

    id: int
    sku: str
    name: str
    category_id: int
    brand_id: Optional[int]
    base_price: Optional[Decimal]
    stock_quantity: Decimal
    stock_unit: str
    warranty_text: Optional[str]
    weight_grams: Optional[Decimal]
    is_original: bool
    tax_percent: Decimal
    is_active: bool
    pdf_catalog_url: Optional[str]
    specifications: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductSummaryResponse(BaseModel):
    id: int
    sku: str
    name: str
    thumbnail: Optional[str] = None
    base_price: Optional[Decimal]
    stock_status: str
    category: Optional[CategoryBrief] = None
    brand: Optional[BrandBrief] = None

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(BaseModel):
    id: int
    sku: str
    name: str
    category_id: int
    brand_id: Optional[int]
    category: Optional[CategoryBrief] = None
    brand: Optional[BrandBrief] = None
    base_price: Optional[Decimal]
    stock_quantity: Decimal
    stock_unit: str
    stock_status: str
    low_stock: bool
    availability: bool
    warranty_text: Optional[str]
    weight_grams: Optional[Decimal]
    is_original: bool
    tax_percent: Decimal
    is_active: bool
    pdf_catalog_url: Optional[str]
    thumbnail: Optional[str] = None
    images: List[ProductImageResponse] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ProductListResponse(PaginatedResponse[ProductSummaryResponse]):
    pass


class StockStatusResponse(BaseModel):
    product_id: int
    sku: str
    stock_quantity: Decimal
    stock_status: str
