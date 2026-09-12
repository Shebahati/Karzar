"""ShippingProvider protocol — Postex is the only v1 implementation."""

from __future__ import annotations

from typing import Any, Protocol

from app.services.logistics.models import (
    BoxType,
    Destination,
    LocationCity,
    OriginAddress,
    PackageSpec,
    ParcelBooking,
    ParcelLookup,
    QuoteResult,
    TrackingEvent,
)


class ShippingProvider(Protocol):
    provider_id: str

    async def whoami(self) -> dict[str, Any]: ...

    async def list_cities(self) -> list[LocationCity]: ...

    async def list_provinces(self) -> list[LocationCity]: ...

    async def list_boxes(self) -> list[BoxType]: ...

    async def list_shipping_methods(self) -> list[dict[str, Any]]: ...

    async def quote(
        self,
        *,
        origin: OriginAddress,
        destination: Destination,
        package: PackageSpec,
        declared_value_irr: object,
        payment_type: str,
        collection_type: str,
    ) -> QuoteResult: ...

    async def create_parcel(self, request: dict[str, Any]) -> ParcelBooking: ...

    async def lookup_by_custom_order_no(self, custom_order_no: str) -> ParcelLookup: ...

    async def get_parcel(self, parcel_no: str) -> dict[str, Any]: ...

    async def mark_ready(self, parcel_nos: list[int]) -> dict[str, Any]: ...

    async def cancel_parcel(self, parcel_no: str, reason: str | None) -> dict[str, Any]: ...

    async def update_parcel(self, parcel_no: str, body: dict[str, Any]) -> dict[str, Any]: ...

    async def fetch_label_pdf(self, parcel_no: str) -> bytes: ...

    async def tracking_events(self, parcel_no: str) -> list[TrackingEvent]: ...

    async def tracking_events_by_barcode(
        self, courier: str, tracking_code: str
    ) -> list[TrackingEvent]: ...

    async def wallet_balance(self) -> dict[str, Any]: ...
