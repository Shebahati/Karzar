"""Postex fulfillment mode: API automation vs external manual portal."""

from __future__ import annotations

from enum import StrEnum

from app.core.config import settings
from app.db.models.logistics import Shipment


class PostexFulfillmentMode(StrEnum):
    API = "api"
    MANUAL_PORTAL = "manual_portal"


def configured_fulfillment_mode() -> PostexFulfillmentMode:
    raw = (settings.POSTEX_FULFILLMENT_MODE or PostexFulfillmentMode.API.value).strip().lower()
    return PostexFulfillmentMode(raw)


def shipment_fulfillment_mode(shipment: Shipment) -> PostexFulfillmentMode:
    """Effective mode for this shipment (snapshot at creation; never follow runtime config)."""
    data = shipment.provider_data or {}
    raw = (data.get("fulfillment_mode") or "").strip().lower()
    if raw:
        try:
            return PostexFulfillmentMode(raw)
        except ValueError:
            return PostexFulfillmentMode.API
    return PostexFulfillmentMode.API


def is_manual_portal_shipment(shipment: Shipment) -> bool:
    return shipment_fulfillment_mode(shipment) == PostexFulfillmentMode.MANUAL_PORTAL


def registration_source(shipment: Shipment) -> str | None:
    data = shipment.provider_data or {}
    raw = data.get("registration_source")
    return str(raw).strip() if raw else None
