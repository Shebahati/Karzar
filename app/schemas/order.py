"""Order API schemas for admin management, customer history, and tracking."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Optional[str] = None


class OrderSummary(BaseModel):
    id: int
    tracking_code: str
    mode: str
    status: str
    status_label: str
    payment_status: str
    payment_status_label: str
    estimated_total: Optional[str] = None
    customer_full_name: str
    customer_phone: str
    company_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderDetailResponse(OrderSummary):
    customer_is_guest: bool
    note: Optional[str] = None
    shipping: Optional[dict[str, Any]] = None
    user_id: Optional[int] = None
    items: List[OrderItemResponse] = Field(default_factory=list)
    allowed_next_statuses: List[str] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    data: List[OrderSummary]
    meta: PaginationMeta


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target canonical order status code")
    note: Optional[str] = Field(None, max_length=500)


class OrderTrackingResponse(BaseModel):
    """Minimal, non-sensitive projection for public order tracking."""

    tracking_code: str
    mode: str
    status: str
    status_label: str
    estimated_total: Optional[str] = None
    created_at: datetime
