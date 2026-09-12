"""Provider-neutral logistics DTOs. Business code must not use Postex HTTP shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ShippingClass(StrEnum):
    PARCEL = "parcel"
    FREIGHT_ONLY = "freight_only"


class ShipmentStatus(StrEnum):
    PENDING_BOOKING = "pending_booking"
    BOOKING = "booking"
    BOOKED = "booked"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    RETURNING = "returning"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    CANCELLATION_PENDING = "cancellation_pending"
    PROVIDER_UNKNOWN = "provider_unknown"
    CREATION_UNCERTAIN = "creation_uncertain"
    ERROR = "error"


TERMINAL_SHIPMENT_STATUSES = frozenset(
    {
        ShipmentStatus.DELIVERED,
        ShipmentStatus.RETURNED,
        ShipmentStatus.CANCELLED,
    }
)

# Physical handoff into the delivery network — not "label created" and not unknown text.
PHYSICAL_HANDOFF_STATUSES = frozenset(
    {
        ShipmentStatus.PICKED_UP,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.OUT_FOR_DELIVERY,
        ShipmentStatus.DELIVERED,
    }
)

READY_ELIGIBLE_STATUSES = frozenset(
    {
        ShipmentStatus.BOOKED,
        ShipmentStatus.READY_FOR_PICKUP,
    }
)

# States that already have (or must never obtain) a second Postex create.
BOOKING_CREATE_FORBIDDEN_STATUSES = frozenset(
    {
        ShipmentStatus.BOOKED,
        ShipmentStatus.READY_FOR_PICKUP,
        ShipmentStatus.PICKED_UP,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.OUT_FOR_DELIVERY,
        ShipmentStatus.DELIVERED,
        ShipmentStatus.DELIVERY_FAILED,
        ShipmentStatus.RETURNING,
        ShipmentStatus.RETURNED,
        ShipmentStatus.CANCELLED,
        ShipmentStatus.CANCELLATION_PENDING,
        ShipmentStatus.PROVIDER_UNKNOWN,
    }
)

SHIPMENT_STATUS_LABELS_FA: dict[str, str] = {
    ShipmentStatus.PENDING_BOOKING.value: "در انتظار رزرو ارسال",
    ShipmentStatus.BOOKING.value: "در حال ثبت مرسوله",
    ShipmentStatus.BOOKED.value: "مرسوله ثبت شد",
    ShipmentStatus.READY_FOR_PICKUP.value: "آماده جمع‌آوری",
    ShipmentStatus.PICKED_UP.value: "جمع‌آوری شد",
    ShipmentStatus.IN_TRANSIT.value: "در مسیر",
    ShipmentStatus.OUT_FOR_DELIVERY.value: "در حال توزیع",
    ShipmentStatus.DELIVERED.value: "تحویل شد",
    ShipmentStatus.DELIVERY_FAILED.value: "تحویل ناموفق",
    ShipmentStatus.RETURNING.value: "در حال بازگشت",
    ShipmentStatus.RETURNED.value: "مرجوع شد",
    ShipmentStatus.CANCELLED.value: "لغو شد",
    ShipmentStatus.CANCELLATION_PENDING.value: "درخواست انصراف ثبت شد",
    ShipmentStatus.PROVIDER_UNKNOWN.value: "وضعیت ارائه‌دهنده ناشناخته",
    ShipmentStatus.CREATION_UNCERTAIN.value: "ثبت مرسوله نامشخص — در حال تطبیق",
    ShipmentStatus.ERROR.value: "خطای لجستیک",
}


@dataclass(frozen=True)
class PackageSpec:
    length_cm: int
    width_cm: int
    height_cm: int
    weight_grams: int
    is_fragile: bool = False
    is_liquid: bool = False
    box_type_id: int | None = None
    box_name: str | None = None


@dataclass(frozen=True)
class QuoteLine:
    product_id: int
    sku: str
    quantity: int
    unit_price_toman: Decimal
    weight_grams: Decimal | None
    length_cm: Decimal | None
    width_cm: Decimal | None
    height_cm: Decimal | None
    is_fragile: bool | None
    is_liquid: bool | None
    shipping_class: str | None
    is_available: bool
    name: str


@dataclass(frozen=True)
class Destination:
    location_code: int
    city_name: str | None = None
    province_name: str | None = None
    postal_code: str | None = None
    address_line: str | None = None


@dataclass(frozen=True)
class OriginAddress:
    city_code: int
    city_name: str | None
    postal_code: str
    address: str
    first_name: str
    last_name: str
    mobile: str
    company_name: str | None = None
    lat: str | None = None
    lon: str | None = None


@dataclass(frozen=True)
class ShippingServiceOption:
    carrier_code: str
    service_code: str
    service_name: str
    provider_amount: Decimal
    provider_currency: str
    provider_amount_toman: Decimal
    customer_amount_toman: Decimal
    pickup_amount_toman: Decimal | None = None
    eta_text: str | None = None

    @property
    def provider_total_toman(self) -> Decimal:
        """Service + pickup; use for provider-cost snapshots (not customer policy)."""
        from app.services.logistics.money import provider_total_toman as _total

        return _total(
            provider_amount_toman=self.provider_amount_toman,
            pickup_amount_toman=self.pickup_amount_toman,
        )


@dataclass(frozen=True)
class QuoteResult:
    options: list[ShippingServiceOption]
    package: PackageSpec
    declared_value_irr: Decimal
    raw_provider_response: dict[str, Any]
    pickup_amount_toman: Decimal | None = None


@dataclass(frozen=True)
class LocationCity:
    code: int
    name: str
    province_code: int | None = None
    province_name: str | None = None


@dataclass(frozen=True)
class BoxType:
    id: int
    name: str | None
    length_cm: int | None
    width_cm: int | None
    height_cm: int | None


@dataclass(frozen=True)
class TrackingEvent:
    provider_status: str | None
    provider_code: str | None
    occurred_at: datetime | None
    description: str | None
    location: str | None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParcelBooking:
    provider_parcel_no: str | None
    tracking_code: str | None
    carrier_code: str | None
    service_code: str | None
    provider_status: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParcelLookup:
    found: bool
    booking: ParcelBooking | None = None
