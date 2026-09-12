"""Map Postex tracking vocabulary onto Karzar ShipmentStatus.

Official OpenAPI does not enumerate status codes. Live `GET /common/statuses`
plus `StatusChangeReport.event_code` / `event_name` / `event_desc` are the
documented fields. Unknown values are recorded as PROVIDER_UNKNOWN and must
never advance the shipment or order.
"""

from __future__ import annotations

from app.services.logistics.models import TERMINAL_SHIPMENT_STATUSES, ShipmentStatus

# Rank used to ignore replay that would regress a terminal state.
STATUS_RANK: dict[str, int] = {
    ShipmentStatus.PENDING_BOOKING.value: 0,
    ShipmentStatus.ERROR.value: 1,
    ShipmentStatus.CREATION_UNCERTAIN.value: 1,
    ShipmentStatus.PROVIDER_UNKNOWN.value: 1,
    ShipmentStatus.BOOKING.value: 2,
    ShipmentStatus.BOOKED.value: 3,
    ShipmentStatus.CANCELLATION_PENDING.value: 3,
    ShipmentStatus.READY_FOR_PICKUP.value: 4,
    ShipmentStatus.PICKED_UP.value: 5,
    ShipmentStatus.IN_TRANSIT.value: 6,
    ShipmentStatus.OUT_FOR_DELIVERY.value: 7,
    ShipmentStatus.DELIVERY_FAILED.value: 8,
    ShipmentStatus.RETURNING.value: 8,
    ShipmentStatus.DELIVERED.value: 20,
    ShipmentStatus.RETURNED.value: 20,
    ShipmentStatus.CANCELLED.value: 20,
}

# Exact normalized tokens only for terminal / failed-delivery states.
_RECIPIENT_DELIVERED_EXACT = frozenset(
    {
        "delivered",
        "تحویلشد",
        "تحویلدادهشد",
        "تحویلبهگیرنده",
        "recipientdelivered",
    }
)
_RETURNED_EXACT = frozenset(
    {
        "returned",
        "returndelivered",
        "deliveredtosender",
        "returntosender",
        "مرجوع",
        "مرجوعشد",
        "تحویلبهفرستنده",
        "تحویلفرستنده",
        "تحویلشدبهفرستنده",
    }
)
_CANCELLED_EXACT = frozenset(
    {
        "cancelled",
        "canceled",
        "لغو",
        "لغوشد",
        "انصراف",
        "انصرافشد",
    }
)
_FAILED_EXACT = frozenset(
    {
        "deliveryfailed",
        "faileddelivery",
        "failed",
        "undelivered",
        "عدمتحویل",
        "عدمتحویلشد",
        "تحویلناموفق",
    }
)
_RETURNING_EXACT = frozenset(
    {
        "returning",
        "inreturn",
        "بازگشت",
        "درحالبازگشت",
    }
)
_OUT_FOR_DELIVERY_TOKENS = ("out_for_delivery", "outfordelivery", "توزیع", "موزع")
_PICKED_TOKENS = ("picked_up", "pickedup", "collected", "جمع‌آوری", "جمع اوری", "قبول مرسوله")
_READY_TOKENS = (
    "ready_for_pickup",
    "readytoaccept",
    "ready_to_accept",
    "آماده به ارسال",
    "آماده ارسال",
)
_IN_TRANSIT_TOKENS = ("in_transit", "intransit", "درمسیر", "در مسیر")
_BOOKED_TOKENS = ("booked", "registered", "created", "ثبت مرسوله", "ثبت شده")


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return text.strip().lower().replace("‌", "").replace(" ", "").replace("-", "").replace("_", "")


def _contains_any(blob: str, tokens: tuple[str, ...]) -> bool:
    compact_tokens = tuple(_normalize(token) for token in tokens)
    return any(token and token in blob for token in compact_tokens)


def _candidates(event_code: str | None, event_name: str | None, event_desc: str | None) -> list[str]:
    values = [_normalize(event_code), _normalize(event_name), _normalize(event_desc)]
    return [value for value in values if value]


def _exact_in(candidates: list[str], exact: frozenset[str]) -> bool:
    return any(value in exact for value in candidates)


def map_provider_status(
    *,
    event_code: str | None = None,
    event_name: str | None = None,
    event_desc: str | None = None,
    current: ShipmentStatus | str | None = None,
) -> ShipmentStatus:
    """Map a provider event onto an internal status without inventing delivery."""
    _ = current
    candidates = _candidates(event_code, event_name, event_desc)
    blob = "".join(candidates)
    if not blob:
        return ShipmentStatus.PROVIDER_UNKNOWN

    # Terminal / failed states: exact field match only. Substring "تحویل شد" must
    # not match failed-delivery or return-to-sender strings.
    if _exact_in(candidates, _CANCELLED_EXACT):
        return ShipmentStatus.CANCELLED
    if _exact_in(candidates, _RETURNED_EXACT):
        return ShipmentStatus.RETURNED
    if _exact_in(candidates, _RETURNING_EXACT):
        return ShipmentStatus.RETURNING
    if _exact_in(candidates, _FAILED_EXACT):
        return ShipmentStatus.DELIVERY_FAILED
    if _exact_in(candidates, _RECIPIENT_DELIVERED_EXACT):
        return ShipmentStatus.DELIVERED
    if _contains_any(blob, _OUT_FOR_DELIVERY_TOKENS):
        return ShipmentStatus.OUT_FOR_DELIVERY
    if _contains_any(blob, _PICKED_TOKENS):
        return ShipmentStatus.PICKED_UP
    if _contains_any(blob, _READY_TOKENS):
        return ShipmentStatus.READY_FOR_PICKUP
    if _contains_any(blob, _IN_TRANSIT_TOKENS):
        return ShipmentStatus.IN_TRANSIT
    if _contains_any(blob, _BOOKED_TOKENS):
        return ShipmentStatus.BOOKED
    return ShipmentStatus.PROVIDER_UNKNOWN


def can_advance(current: str, incoming: str) -> bool:
    """Refuse unknown mapping and replay that would leave a terminal state."""
    if incoming == ShipmentStatus.PROVIDER_UNKNOWN.value:
        return False
    if current == incoming:
        return False
    if current in {status.value for status in TERMINAL_SHIPMENT_STATUSES}:
        return False
    return STATUS_RANK.get(incoming, 0) >= STATUS_RANK.get(current, 0)
