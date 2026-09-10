"""Map Postex tracking vocabulary onto Karzar ShipmentStatus.

Official OpenAPI does not enumerate status codes. Live `GET /common/statuses`
plus `StatusChangeReport.event_code` / `event_name` / `event_desc` are the
documented fields. Unknown values are recorded verbatim and mapped
conservatively — never to delivered.
"""

from __future__ import annotations

from app.services.logistics.models import ShipmentStatus

# Rank used to ignore replay that would regress a terminal state.
STATUS_RANK: dict[str, int] = {
    ShipmentStatus.PENDING_BOOKING.value: 0,
    ShipmentStatus.ERROR.value: 1,
    ShipmentStatus.CREATION_UNCERTAIN.value: 1,
    ShipmentStatus.BOOKING.value: 2,
    ShipmentStatus.BOOKED.value: 3,
    ShipmentStatus.READY_FOR_PICKUP.value: 4,
    ShipmentStatus.PICKED_UP.value: 5,
    ShipmentStatus.IN_TRANSIT.value: 6,
    ShipmentStatus.OUT_FOR_DELIVERY.value: 7,
    ShipmentStatus.DELIVERY_FAILED.value: 6,
    ShipmentStatus.RETURNING.value: 6,
    ShipmentStatus.DELIVERED.value: 20,
    ShipmentStatus.RETURNED.value: 20,
    ShipmentStatus.CANCELLED.value: 20,
}

_DELIVERED_TOKENS = ("delivered", "deliveredtosender", "تحویل شد", "تحویل داده")
_RETURNED_TOKENS = ("returned", "return_delivered", "مرجوع")
_CANCELLED_TOKENS = ("cancelled", "canceled", "لغو", "انصراف")
_OUT_FOR_DELIVERY_TOKENS = ("out_for_delivery", "outfordelivery", "توزیع", "موزع")
_PICKED_TOKENS = ("picked_up", "pickedup", "collected", "جمع‌آوری", "جمع اوری", "قبول مرسوله")
_READY_TOKENS = (
    "ready_for_pickup",
    "readytoaccept",
    "ready_to_accept",
    "آماده به ارسال",
    "آماده ارسال",
)
_FAILED_TOKENS = ("delivery_failed", "failed", "عدم تحویل")
_RETURNING_TOKENS = ("returning", "in_return", "بازگشت")
_BOOKED_TOKENS = ("booked", "registered", "created", "ثبت مرسوله", "ثبت شده")


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return text.strip().lower().replace("‌", "").replace(" ", "").replace("-", "").replace("_", "")


def _contains_any(blob: str, tokens: tuple[str, ...]) -> bool:
    compact_tokens = tuple(_normalize(token) for token in tokens)
    return any(token and token in blob for token in compact_tokens)


def map_provider_status(
    *,
    event_code: str | None = None,
    event_name: str | None = None,
    event_desc: str | None = None,
    current: ShipmentStatus | str | None = None,
) -> ShipmentStatus:
    """Map a provider event onto an internal status without inventing delivery."""
    blob = _normalize(" ".join(part for part in (event_code, event_name, event_desc) if part))
    if not blob:
        if current in {ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED, ShipmentStatus.CANCELLED}:
            return ShipmentStatus(current) if not isinstance(current, ShipmentStatus) else current
        return ShipmentStatus.IN_TRANSIT if current else ShipmentStatus.BOOKED

    if _contains_any(blob, _CANCELLED_TOKENS):
        return ShipmentStatus.CANCELLED
    if _contains_any(blob, _RETURNED_TOKENS) and not _contains_any(blob, _RETURNING_TOKENS):
        return ShipmentStatus.RETURNED
    if _contains_any(blob, _RETURNING_TOKENS):
        return ShipmentStatus.RETURNING
    if _contains_any(blob, _DELIVERED_TOKENS):
        return ShipmentStatus.DELIVERED
    if _contains_any(blob, _FAILED_TOKENS):
        return ShipmentStatus.DELIVERY_FAILED
    if _contains_any(blob, _OUT_FOR_DELIVERY_TOKENS):
        return ShipmentStatus.OUT_FOR_DELIVERY
    if _contains_any(blob, _PICKED_TOKENS):
        return ShipmentStatus.PICKED_UP
    if _contains_any(blob, _READY_TOKENS):
        return ShipmentStatus.READY_FOR_PICKUP
    if _contains_any(blob, _BOOKED_TOKENS):
        return ShipmentStatus.BOOKED
    # Unknown: keep movement without claiming delivery.
    if current in {
        ShipmentStatus.DELIVERED,
        ShipmentStatus.RETURNED,
        ShipmentStatus.CANCELLED,
    }:
        return ShipmentStatus(str(current))
    if current in {
        ShipmentStatus.PICKED_UP,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.OUT_FOR_DELIVERY,
    }:
        return ShipmentStatus.IN_TRANSIT
    return ShipmentStatus.IN_TRANSIT


def can_advance(current: str, incoming: str) -> bool:
    """Refuse replay that would leave a terminal delivered/returned/cancelled state."""
    if current == incoming:
        return False
    if current in {
        ShipmentStatus.DELIVERED.value,
        ShipmentStatus.RETURNED.value,
        ShipmentStatus.CANCELLED.value,
    }:
        return False
    return STATUS_RANK.get(incoming, 6) >= STATUS_RANK.get(current, 0)
