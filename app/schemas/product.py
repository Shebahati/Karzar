from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal

from app.db.models.product import StockUnitEnum

StockUnitValue = Literal["piece", "kg", "meter", "pack"]
VALID_STOCK_UNITS = {unit.value for unit in StockUnitEnum}


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

    @field_validator("stock_unit")
    @classmethod
    def validate_stock_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STOCK_UNITS:
            raise ValueError(f"stock_unit must be one of: {', '.join(sorted(VALID_STOCK_UNITS))}")
        return v


class ProductResponse(BaseModel):
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
    specifications: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductSummaryResponse(BaseModel):
    id: int
    sku: str
    name: str
    base_price: Optional[Decimal]
    stock_status: str

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    total_count: int
    skip: int
    limit: int
    has_next: bool


class ProductListResponse(BaseModel):
    data: List[ProductSummaryResponse]
    meta: PaginationMeta
