"""Order API schemas for admin management, customer history, and tracking."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import PaginationMeta


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: str | None = None


class OrderInvoiceResponse(BaseModel):
    invoice_number: str
    issued_at: datetime
    valid_until: datetime | None = None
    total: str
    note: str | None = None


class OrderSummary(BaseModel):
    id: int
    tracking_code: str
    mode: str
    status: str
    status_label: str
    payment_status: str
    payment_status_label: str
    estimated_total: str | None = None
    customer_full_name: str
    customer_phone: str
    company_name: str | None = None
    created_at: datetime
    updated_at: datetime


class OrderDetailResponse(OrderSummary):
    customer_is_guest: bool
    note: str | None = None
    admin_note: str | None = None
    shipping: dict[str, Any] | None = None
    user_id: int | None = None
    postal_tracking_code: str | None = None
    delivery_eta: datetime | None = None
    invoice: OrderInvoiceResponse | None = None
    items: list[OrderItemResponse] = Field(default_factory=list)
    allowed_next_statuses: list[str] = Field(default_factory=list)
    timeline: list["OrderTrackingEvent"] = Field(default_factory=list)


class OrderListResponse(BaseModel):
    data: list[OrderSummary]
    meta: PaginationMeta


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target canonical order status code")
    note: str | None = Field(
        None,
        max_length=500,
        description="Admin annotation stored in admin_note (does not overwrite customer note)",
    )
    postal_tracking_code: str | None = Field(None, max_length=64)
    delivery_eta: datetime | None = None


class IssueQuoteLineItem(BaseModel):
    product_id: int
    unit_price: str
    quantity: int = Field(..., ge=1)


class IssueQuoteRequest(BaseModel):
    items: list[IssueQuoteLineItem] = Field(..., min_length=1)
    note: str | None = Field(None, max_length=500)
    valid_until: datetime | None = None


class OrderTrackingEvent(BaseModel):
    status: str
    status_label: str
    occurred_at: datetime
    description: str | None = None
    actor: str | None = "system"


class OrderTrackingItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price: str | None = None


class OrderTrackingResponse(BaseModel):
    """Minimal, non-sensitive projection for public order tracking."""

    tracking_code: str
    mode: str
    status: str
    status_label: str
    created_at: datetime
    items: list[OrderTrackingItemResponse] = Field(default_factory=list)
    timeline: list[OrderTrackingEvent] = Field(default_factory=list)
