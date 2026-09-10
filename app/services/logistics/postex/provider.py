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
    ShippingServiceOption,
    TrackingEvent,
)
from app.services.logistics.postex.client import PostexClient
from app.services.logistics.postex.couriers import (
    MINIMAL_VALUE_ADDED_SERVICE,
    PostexCourierService,
    parse_quote_services_config,
    parse_shipping_methods,
    select_quote_services,
)
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
        methods = parse_shipping_methods(payload)
        return [
            {
                "courier_code": m.courier_code,
                "service_type": m.service_type,
                "service_name": m.service_name,
                "courier_service_id": m.courier_service_id,
                "is_active": m.is_active,
            }
            for m in methods
        ]

    def _configured_quote_services(self) -> list[PostexCourierService]:
        return parse_quote_services_config(settings.POSTEX_QUOTE_SERVICES)

    async def _resolve_quote_services(self) -> list[PostexCourierService]:
        configured = self._configured_quote_services()
        try:
            payload = await self.client.get_json(
                "/shipping-methods", operation="shipping_methods"
            )
            catalog = parse_shipping_methods(payload)
        except Exception:
            # Quote must still send live-required courier; fall back to configured pairs.
            catalog = None
        selected = select_quote_services(configured, catalog)
        if not selected:
            # Catalog fetch succeeded but none of the configured pairs were active —
            # do not invent carriers; use configured live-verified defaults only when
            # catalog was unavailable.
            if catalog is None:
                return configured
            raise ShippingUnavailableError(
                "هیچ سرویس ارسال فعالی مطابق پیکربندی پستکس یافت نشد."
            )
        return selected

    def _quote_request_body(
        self,
        *,
        origin: OriginAddress,
        destination: Destination,
        package: PackageSpec,
        declared_value_irr: object,
        payment_type: str,
        collection_type: str,
        courier: PostexCourierService,
        custom_parcel_id: str = "checkout",
    ) -> dict[str, Any]:
        """Build live-compatible POST /shipping/quotes body (courier + value_added_service)."""
        return {
            "collection_type": collection_type,
            "from_city_code": origin.city_code,
            "courier": courier.as_quote_courier(),
            "value_added_service": dict(MINIMAL_VALUE_ADDED_SERVICE),
            "parcels": [
                {
                    "custom_parcel_id": custom_parcel_id,
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

        services = await self._resolve_quote_services()
        merged: list[ShippingServiceOption] = []
        raw_responses: list[dict[str, Any]] = []
        pickup_amount_toman = None
        last_error: Exception | None = None

        for svc in services:
            body = self._quote_request_body(
                origin=origin,
                destination=destination,
                package=package,
                declared_value_irr=declared_value_irr,
                payment_type=payment_type,
                collection_type=collection_type,
                courier=svc,
            )
            try:
                payload = await self.client.post_json(
                    "/shipping/quotes",
                    body,
                    operation="quotes",
                    mutating=False,
                )
                result = parse_quotes(payload)
            except Exception as exc:
                last_error = exc
                continue
            merged.extend(result.options)
            if isinstance(result.raw_provider_response, dict):
                raw_responses.append(result.raw_provider_response)
            if result.pickup_amount_toman is not None:
                pickup_amount_toman = result.pickup_amount_toman

        if not merged:
            if last_error is not None:
                raise last_error
            raise ShippingUnavailableError("هیچ سرویس ارسالی برای این مقصد برگردانده نشد.")

        raw: dict[str, Any]
        if len(raw_responses) == 1:
            raw = raw_responses[0]
        else:
            raw = {"quotes": raw_responses}

        return QuoteResult(
            options=merged,
            package=package,
            declared_value_irr=Decimal(str(declared_value_irr)),
            raw_provider_response=raw,
            pickup_amount_toman=pickup_amount_toman,
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
