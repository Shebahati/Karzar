"""Customer-facing shipping labels (no internal provider codes)."""

from __future__ import annotations

from typing import Any

from app.services.logistics.display_labels import PAYMENT_MODE_LABELS_FA, provider_label_fa
from app.services.logistics.shipping_methods import ShippingMethodCode


def _shipping_snapshot(order_shipping: dict[str, Any] | None) -> dict[str, Any]:
    return dict(order_shipping or {})


def resolve_shipping_method_code(
    *,
    shipping: dict[str, Any] | None,
    shipping_provider: str | None,
    shipping_service_code: str | None,
) -> str | None:
    snap = _shipping_snapshot(shipping)
    code = (snap.get("shipping_method_code") or "").strip()
    if code:
        return code
    provider = (shipping_provider or "").strip()
    service = (shipping_service_code or "").strip()
    if provider == "tipax" and service == "standard":
        return ShippingMethodCode.TIPAX_STANDARD.value
    if provider == "chapar" and service == "standard":
        return ShippingMethodCode.CHAPAR_STANDARD.value
    if provider == "local_delivery" and service == "tehran_express":
        return ShippingMethodCode.TEHRAN_EXPRESS.value
    return None


def customer_shipping_labels(
    *,
    shipping: dict[str, Any] | None,
    shipping_provider: str | None,
    shipping_service_code: str | None,
    shipping_payment_mode: str | None,
) -> tuple[str | None, str | None]:
    """Return (method_label_fa, cost_label_fa) for storefront display."""
    code = resolve_shipping_method_code(
        shipping=shipping,
        shipping_provider=shipping_provider,
        shipping_service_code=shipping_service_code,
    )
    if code == ShippingMethodCode.TEHRAN_EXPRESS.value:
        return ("ارسال فوری تهران", "پرداخت هنگام تحویل به پیک")
    if code == ShippingMethodCode.TIPAX_STANDARD.value:
        return ("تیپاکس", PAYMENT_MODE_LABELS_FA.get("receiver_due", "پس‌کرایه"))
    if code == ShippingMethodCode.CHAPAR_STANDARD.value:
        return ("چاپار", PAYMENT_MODE_LABELS_FA.get("receiver_due", "پس‌کرایه"))
    if (shipping_payment_mode or "").strip() == "receiver_due":
        label = provider_label_fa(shipping_provider, shipping_service_code)
        if shipping_provider == "postex":
            return (label, PAYMENT_MODE_LABELS_FA.get("receiver_due", "پس‌کرایه"))
        if shipping_provider in {"tipax", "chapar", "local_delivery"}:
            return (label, PAYMENT_MODE_LABELS_FA.get("receiver_due", "پس‌کرایه"))
    return (None, None)
