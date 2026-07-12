"""Cart API schemas."""


from pydantic import BaseModel, Field


class CartItemResponse(BaseModel):
    product_id: int
    quantity: int
    product_name: str
    base_price: str | None = None
    stock_quantity: float | None = None


class CartResponse(BaseModel):
    lane: str
    items: list[CartItemResponse]
    item_count: int = 0


class CartItemUpsertRequest(BaseModel):
    lane: str = Field(..., pattern="^(purchase|inquiry)$")
    product_id: int
    quantity: int = Field(..., ge=0, le=999)


class CartMergeRequest(BaseModel):
    guest_token: str = Field(..., min_length=8, max_length=64)
    lane: str | None = Field(None, pattern="^(purchase|inquiry)$")
