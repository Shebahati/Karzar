"""Public and admin shipping API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ShippingQuoteLine(BaseModel):
    product_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class ShippingQuoteRequest(BaseModel):
    items: list[ShippingQuoteLine] = Field(..., min_length=1)
    location_code: int = Field(..., ge=1)
    postal_code: str | None = None
    city_name: str | None = None
    province_name: str | None = None


class ShippingQuoteOptionResponse(BaseModel):
    quote_token: str
    carrier_code: str
    service_code: str
    title: str
    amount_toman: str
    eta: str | None = None
    expires_at: datetime


class ShippingQuoteResponse(BaseModel):
    quote_group_id: str
    expires_at: datetime
    options: list[ShippingQuoteOptionResponse]


class ShippingCityResponse(BaseModel):
    code: int
    name: str
    province_code: int | None = None
    province_name: str | None = None


class ShippingCityListResponse(BaseModel):
    data: list[ShippingCityResponse]


class ShippingStatusResponse(BaseModel):
    enabled: bool
    quote_ttl_seconds: int


class ShipmentEventPublic(BaseModel):
    status: str
    status_label: str
    provider_status: str | None = None
    occurred_at: datetime | None = None
    description: str | None = None


class ShipmentPublicResponse(BaseModel):
    id: str
    status: str
    status_label: str
    carrier_code: str | None = None
    service_code: str | None = None
    service_name: str | None = None
    tracking_code: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    events: list[ShipmentEventPublic] = Field(default_factory=list)


class ShipmentAdminResponse(ShipmentPublicResponse):
    internal_id: int
    provider: str
    provider_parcel_no: str | None = None
    quote_id: int | None = None
    package: dict[str, Any] | None = None
    customer_shipping_cost: str | None = None
    provider_quoted_cost: str | None = None
    provider_actual_cost: str | None = None
    ready_to_accept: bool = False
    booking_attempts: int = 0
    last_tracking_sync_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    cancellation_requested_at: datetime | None = None


class ShipmentCancelRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class ShipmentEditRequest(BaseModel):
    address_line: str | None = Field(None, min_length=10, max_length=500)
    postal_code: str | None = Field(None, min_length=10, max_length=10)
    first_name: str | None = Field(None, max_length=80)
    last_name: str | None = Field(None, max_length=80)
    mobile_no: str | None = Field(None, max_length=20)


class PostexHealthResponse(BaseModel):
    enabled: bool
    configured: bool
    whoami_ok: bool | None = None
    last_success: dict[str, str] = Field(default_factory=dict)
