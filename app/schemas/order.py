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


class OrderInvoiceResponse(BaseModel):
    invoice_number: str
    issued_at: datetime
    valid_until: Optional[datetime] = None
    total: str
    note: Optional[str] = None


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
    admin_note: Optional[str] = None
    shipping: Optional[dict[str, Any]] = None
    user_id: Optional[int] = None
    postal_tracking_code: Optional[str] = None
    delivery_eta: Optional[datetime] = None
    invoice: Optional[OrderInvoiceResponse] = None
    items: List[OrderItemResponse] = Field(default_factory=list)
    allowed_next_statuses: List[str] = Field(default_factory=list)
    timeline: List["OrderTrackingEvent"] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    data: List[OrderSummary]
    meta: PaginationMeta


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target canonical order status code")
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="Admin annotation stored in admin_note (does not overwrite customer note)",
    )
    postal_tracking_code: Optional[str] = Field(None, max_length=64)
    delivery_eta: Optional[datetime] = None


class IssueQuoteLineItem(BaseModel):
    product_id: int
    unit_price: str
    quantity: int = Field(..., ge=1)


class IssueQuoteRequest(BaseModel):
    items: List[IssueQuoteLineItem] = Field(..., min_length=1)
    note: Optional[str] = Field(None, max_length=500)
    valid_until: Optional[datetime] = None


class OrderTrackingEvent(BaseModel):
    status: str
    status_label: str
    occurred_at: datetime
    description: Optional[str] = None
    actor: Optional[str] = "system"


class OrderTrackingItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price: Optional[str] = None


class OrderTrackingResponse(BaseModel):
    """Minimal, non-sensitive projection for public order tracking."""

    tracking_code: str
    mode: str
    status: str
    status_label: str
    created_at: datetime
    items: List[OrderTrackingItemResponse] = Field(default_factory=list)
    timeline: List[OrderTrackingEvent] = Field(default_factory=list)
