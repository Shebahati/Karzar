"""Provider-neutral shipping payment mode (who pays the carrier for shipping).

Karzar domain values are independent of Postex string literals:

  sender_prepaid  → Postex SENDER   (customer pays shipping via SEP at checkout)
  receiver_due    → Postex RECEIVER (پس‌کرایه; carrier collects shipping from recipient)

COD and FREE_SHIPPING are rejected. Merchandise payment remains SEP in both modes.
"""

from __future__ import annotations

from enum import StrEnum


class ShippingPaymentMode(StrEnum):
    SENDER_PREPAID = "sender_prepaid"
    RECEIVER_DUE = "receiver_due"


# Postex official payment_type strings (API-CONTRACT).
POSTEX_SENDER = "SENDER"
POSTEX_RECEIVER = "RECEIVER"
POSTEX_COD = "COD"
POSTEX_FREE_SHIPPING = "FREE_SHIPPING"

_ALLOWED_POSTEX_PAYMENT_TYPES = frozenset({POSTEX_SENDER, POSTEX_RECEIVER})
_REJECTED_POSTEX_PAYMENT_TYPES = frozenset({POSTEX_COD, POSTEX_FREE_SHIPPING})

_MODE_TO_POSTEX = {
    ShippingPaymentMode.SENDER_PREPAID: POSTEX_SENDER,
    ShippingPaymentMode.RECEIVER_DUE: POSTEX_RECEIVER,
}

_POSTEX_TO_MODE = {
    POSTEX_SENDER: ShippingPaymentMode.SENDER_PREPAID,
    POSTEX_RECEIVER: ShippingPaymentMode.RECEIVER_DUE,
}


def normalize_postex_payment_type(raw: str) -> str:
    """Validate a Postex payment_type string. Rejects COD / FREE_SHIPPING / unknown."""
    normalized = (raw or "").strip().upper()
    if normalized in _REJECTED_POSTEX_PAYMENT_TYPES:
        raise ValueError(
            f"POSTEX payment_type {normalized} is not supported "
            "(COD and FREE_SHIPPING are rejected; use RECEIVER for پس‌کرایه)"
        )
    if normalized not in _ALLOWED_POSTEX_PAYMENT_TYPES:
        raise ValueError(
            "POSTEX payment_type must be SENDER or RECEIVER "
            f"(got {normalized!r})"
        )
    return normalized


def mode_from_postex_payment_type(raw: str) -> ShippingPaymentMode:
    return _POSTEX_TO_MODE[normalize_postex_payment_type(raw)]


def postex_payment_type_for_mode(mode: ShippingPaymentMode | str) -> str:
    resolved = ShippingPaymentMode(str(mode))
    return _MODE_TO_POSTEX[resolved]


def default_shipping_payment_mode() -> ShippingPaymentMode:
    """Authority: POSTEX_SHIPPING_PAYMENT_MODE if set, else POSTEX_DEFAULT_PAYMENT_TYPE.

    POSTEX_DEFAULT_PAYMENT_TYPE remains for backward compatibility and is normalized
    once into the provider-neutral mode. Prefer POSTEX_SHIPPING_PAYMENT_MODE for new
    deployments so a single setting owns checkout/booking semantics.
    """
    from app.core.config import settings

    explicit = (getattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", None) or "").strip()
    if explicit:
        return ShippingPaymentMode(explicit)
    return mode_from_postex_payment_type(settings.POSTEX_DEFAULT_PAYMENT_TYPE)


def resolve_checkout_shipping_payment_mode(
    requested: str | None = None,
) -> ShippingPaymentMode:
    """Checkout may request a mode; blank falls back to configured default."""
    if requested is None or not str(requested).strip():
        return default_shipping_payment_mode()
    return ShippingPaymentMode(str(requested).strip().lower())


def postex_booking_enabled() -> bool:
    """Write-path gate for parcel create / mark-ready / cancel / edit mutations."""
    from app.core.config import settings

    return bool(getattr(settings, "POSTEX_BOOKING_ENABLED", False))
