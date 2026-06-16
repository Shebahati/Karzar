# app/schemas/product.py
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import UUID


class CategorySlug(str, Enum):
    """Enum for product categories."""
    DIGITAL_CALIPERS = "digital-calipers"
    MEASURING_TOOLS = "measuring-tools"
    CUTTING_TOOLS = "cutting-tools"
    PRECISION_INSTRUMENTS = "precision-instruments"
    OTHER = "other"


class TechnicalSpecs(BaseModel):
    range: str
    accuracy: str
    resolution: str
    material: str
    standard: str
    battery_type: str


class Features(BaseModel):
    waterproof: bool
    data_output: bool
    auto_power_off: bool
    buttons: List[str]
    certification: str


class Dimensions(BaseModel):
    L_mm: float
    a_mm: float
    b_mm: float
    c_mm: float
    d_mm: float


class Specifications(BaseModel):
    technical_specs: TechnicalSpecs
    features: Features
    dimensions: Dimensions
    optional_accessories: List[str]


class ProductCreate(BaseModel):
    sku: str
    name: str
    category_slug: CategorySlug
    brand: str
    base_price: float
    stock_quantity: int
    is_active: bool = True
    specifications: Specifications
    model_config = ConfigDict(use_enum_values=True)

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("SKU cannot be empty")
        if len(v) > 50:
            raise ValueError("SKU must be 50 characters or less")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Name cannot be empty")
        if len(v) > 255:
            raise ValueError("Name must be 255 characters or less")
        return v.strip()

    @field_validator("brand")
    @classmethod
    def validate_brand(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Brand cannot be empty")
        if len(v) > 100:
            raise ValueError("Brand must be 100 characters or less")
        return v.strip()

    @field_validator("base_price")
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        return round(float(v), 2)

    @field_validator("stock_quantity")
    @classmethod
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError("Stock quantity cannot be negative")
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_slug: Optional[CategorySlug] = None
    brand: Optional[str] = None
    base_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    specifications: Optional[Specifications] = None
    model_config = ConfigDict(use_enum_values=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Name cannot be empty")
            if len(v) > 255:
                raise ValueError("Name must be 255 characters or less")
            return v.strip()
        return v

    @field_validator("brand")
    @classmethod
    def validate_brand(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Brand cannot be empty")
            if len(v) > 100:
                raise ValueError("Brand must be 100 characters or less")
            return v.strip()
        return v

    @field_validator("base_price")
    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return round(float(v), 2) if v is not None else None

    @field_validator("stock_quantity")
    @classmethod
    def validate_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError("Stock quantity cannot be negative")
        return v


class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    category_slug: CategorySlug
    brand: str
    base_price: float
    stock_quantity: int
    is_active: bool
    specifications: Specifications
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[ProductResponse]

    model_config = ConfigDict(from_attributes=True)
