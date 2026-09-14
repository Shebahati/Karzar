"""Postex fulfillment mode: API automation vs external manual portal."""

from __future__ import annotations

from enum import StrEnum

from app.core.config import settings
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import ShipmentStateError


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
    if not raw:
        return PostexFulfillmentMode.API
    try:
        return PostexFulfillmentMode(raw)
    except ValueError as exc:
        raise ShipmentStateError(
            "نوع تکمیل مرسوله در snapshot نامعتبر است.",
            error_code="SHIPMENT_STATE_INVALID",
        ) from exc


def is_manual_portal_shipment(shipment: Shipment) -> bool:
    try:
        return shipment_fulfillment_mode(shipment) == PostexFulfillmentMode.MANUAL_PORTAL
    except ShipmentStateError:
        return False


def is_corrupt_fulfillment_snapshot(shipment: Shipment) -> bool:
    data = shipment.provider_data or {}
    raw = (data.get("fulfillment_mode") or "").strip().lower()
    if not raw:
        return False
    try:
        PostexFulfillmentMode(raw)
        return False
    except ValueError:
        return True


def assert_provider_path_allowed_for_fulfillment_snapshot(shipment: Shipment) -> None:
    """Fail closed: corrupt snapshots and manual_portal never use generic Postex HTTP."""
    if is_corrupt_fulfillment_snapshot(shipment):
        raise ShipmentStateError(
            "نوع تکمیل مرسوله در snapshot نامعتبر است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if is_manual_portal_shipment(shipment):
        raise ShipmentStateError(
            "این مرسوله از مسیر ثبت دستی پنل پستکس است؛ عملیات API پستکس مجاز نیست.",
            error_code="SHIPMENT_STATE_INVALID",
        )


def registration_source(shipment: Shipment) -> str | None:
    data = shipment.provider_data or {}
    raw = data.get("registration_source")
    return str(raw).strip() if raw else None
