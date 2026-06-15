# app/schemas/product.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

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
    category_slug: str
    brand: str
    base_price: float
    stock_quantity: int
    is_active: bool = True
    specifications: Specifications

class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True)