"""Cart API schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CartItemResponse(BaseModel):
    product_id: int
    quantity: int
    product_name: str
    base_price: Optional[str] = None
    stock_quantity: Optional[float] = None


class CartResponse(BaseModel):
    lane: str
    items: List[CartItemResponse]
    item_count: int = 0


class CartItemUpsertRequest(BaseModel):
    lane: str = Field(..., pattern="^(purchase|inquiry)$")
    product_id: int
    quantity: int = Field(..., ge=0, le=999)


class CartMergeRequest(BaseModel):
    guest_token: str = Field(..., min_length=8, max_length=64)
    lane: Optional[str] = Field(None, pattern="^(purchase|inquiry)$")
