"""Postex ShippingProvider implementation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.services.logistics.exceptions import ShippingUnavailableError
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
from app.services.logistics.postex.client import PostexClient
from app.services.logistics.postex.mapper import (
    parse_boxes,
    parse_cities,
    parse_parcel_booking,
    parse_parcel_lookup,
    parse_quotes,
    parse_tracking_events,
)
from app.services.logistics.redaction import redact_secrets


class PostexProvider:
    provider_id = "postex"

    def __init__(self, client: PostexClient | None = None) -> None:
        if client is not None:
            self.client = client
            return
        if not (settings.POSTEX_API_KEY or "").strip():
            raise ShippingUnavailableError("Postex API key is not configured")
        self.client = PostexClient(
            base_url=settings.POSTEX_BASE_URL,
            api_key=settings.POSTEX_API_KEY,
            timeout_seconds=settings.POSTEX_TIMEOUT_SECONDS,
        )

    async def whoami(self) -> dict[str, Any]:
        payload = await self.client.whoami()
        return redact_secrets(payload) if isinstance(payload, dict) else {"ok": True}

    async def list_cities(self) -> list[LocationCity]:
        payload = await self.client.get_json("/locality/cities/all", operation="cities_all")
        return parse_cities(payload)

    async def list_provinces(self) -> list[LocationCity]:
        payload = await self.client.get_json("/locality/provinces", operation="provinces")
        return parse_cities(payload)

    async def list_boxes(self) -> list[BoxType]:
        payload = await self.client.get_json("/common/boxes", operation="boxes")
        return parse_boxes(payload)

    async def list_shipping_methods(self) -> list[dict[str, Any]]:
        payload = await self.client.get_json("/shipping-methods", operation="shipping_methods")
        if isinstance(payload, list):
            return [redact_secrets(item) if isinstance(item, dict) else item for item in payload]
        if isinstance(payload, dict):
            return [redact_secrets(payload)]
        return []

    async def quote(
        self,
        *,
        origin: OriginAddress,
        destination: Destination,
        package: PackageSpec,
        declared_value_irr: object,
        payment_type: str,
        collection_type: str,
    ) -> QuoteResult:
        if package.box_type_id is None:
            raise ShippingUnavailableError("box_type_id is required by Postex ParcelPropertyDto")
        body = {
            "collection_type": collection_type,
            "from_city_code": origin.city_code,
            "parcels": [
                {
                    "custom_parcel_id": "checkout",
                    "to_city_code": destination.location_code,
                    "payment_type": payment_type,
                    "parcel_properties": {
                        "length": package.length_cm,
                        "width": package.width_cm,
                        "height": package.height_cm,
                        "total_weight": package.weight_grams,
                        "box_type_id": package.box_type_id,
                        "is_fragile": package.is_fragile,
                        "is_liquid": package.is_liquid,
                        "total_value": int(Decimal(str(declared_value_irr))),
                        "total_value_currency": "IRR",
                    },
                }
            ],
        }
        payload = await self.client.post_json(
            "/shipping/quotes",
            body,
            operation="quotes",
            mutating=False,
        )
        result = parse_quotes(payload)
        return QuoteResult(
            options=result_options(result),
            package=package,
            declared_value_irr=Decimal(str(declared_value_irr)),
            raw_provider_response=result.raw_provider_response,
            pickup_amount_toman=result.pickup_amount_toman,
        )

    async def create_parcel(self, request: dict[str, Any]) -> ParcelBooking:
        payload = await self.client.post_json(
            "/parcels/bulk",
            request,
            operation="parcels_bulk",
            mutating=True,
        )
        return parse_parcel_booking(payload)

    async def lookup_by_custom_order_no(self, custom_order_no: str) -> ParcelLookup:
        try:
            payload = await self.client.get_json(
                f"/parcels/custom-order-no/{custom_order_no}",
                operation="parcel_by_custom_order_no",
            )
        except Exception as exc:
            from app.services.logistics.exceptions import ProviderNotFoundError

            if isinstance(exc, ProviderNotFoundError):
                return ParcelLookup(found=False)
            raise
        return parse_parcel_lookup(payload)

    async def get_parcel(self, parcel_no: str) -> dict[str, Any]:
        payload = await self.client.get_json(f"/parcels/{parcel_no}", operation="get_parcel")
        return redact_secrets(payload) if isinstance(payload, dict) else {"value": payload}

    async def mark_ready(self, parcel_nos: list[int]) -> dict[str, Any]:
        payload = await self.client.post_json(
            "/parcels/mark-ready",
            parcel_nos,
            operation="mark_ready",
            mutating=True,
        )
        return redact_secrets(payload) if isinstance(payload, dict) else {"ok": True}

    async def cancel_parcel(self, parcel_no: str, reason: str | None) -> dict[str, Any]:
        payload = await self.client.post_json(
            f"/parcels/cancel-request/{parcel_no}",
            {"reason": reason},
            operation="cancel_parcel",
            mutating=True,
        )
        return redact_secrets(payload) if isinstance(payload, dict) else {"ok": True}

    async def update_parcel(self, parcel_no: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = await self.client.patch_json(
            f"/parcels/{parcel_no}",
            body,
            operation="update_parcel",
        )
        return redact_secrets(payload) if isinstance(payload, dict) else {"ok": True}

    async def fetch_label_pdf(self, parcel_no: str) -> bytes:
        return await self.client.get_bytes(
            f"/parcels/{parcel_no}/label",
            operation="parcel_label",
        )

    async def tracking_events(self, parcel_no: str) -> list[TrackingEvent]:
        payload = await self.client.get_json(
            f"/tracking/events/{parcel_no}",
            operation="tracking_events",
        )
        return parse_tracking_events(payload)

    async def tracking_events_by_barcode(
        self, courier: str, tracking_code: str
    ) -> list[TrackingEvent]:
        payload = await self.client.get_json(
            f"/tracking/events/{courier}/{tracking_code}",
            operation="tracking_by_barcode",
        )
        return parse_tracking_events(payload)

    async def wallet_balance(self) -> dict[str, Any]:
        payload = await self.client.get_json("/wallet/balance", operation="wallet_balance")
        return redact_secrets(payload) if isinstance(payload, dict) else {}


def result_options(result: QuoteResult) -> list:
    return result.options
