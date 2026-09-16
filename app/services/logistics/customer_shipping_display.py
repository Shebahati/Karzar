"""Customer-facing shipping labels (no internal provider codes)."""

from __future__ import annotations

from typing import Any

from app.services.logistics.display_labels import PAYMENT_MODE_LABELS_FA, provider_label_fa
from app.services.logistics.shipping_methods import ShippingMethodCode

_METHOD_TITLE_FA: dict[str, str] = {
    ShippingMethodCode.TIPAX_STANDARD.value: "تیپاکس",
    ShippingMethodCode.CHAPAR_STANDARD.value: "چاپار",
    ShippingMethodCode.POST_PISHTAZ.value: "پست پیشتاز",
    ShippingMethodCode.TEHRAN_MOTORCYCLE_48H.value: "پیک موتوری حداکثر تا ۴۸ ساعت",
    ShippingMethodCode.TEHRAN_EXPRESS_3H.value: "ارسال فوری ۳ ساعته",
}


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
    if provider == "iran_post" and service == "pishtaz":
        return ShippingMethodCode.POST_PISHTAZ.value
    if provider == "local_delivery" and service == "motorcycle_48h":
        return ShippingMethodCode.TEHRAN_MOTORCYCLE_48H.value
    if provider == "local_delivery" and service in {"express_3h", "tehran_express"}:
        return ShippingMethodCode.TEHRAN_EXPRESS_3H.value
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
    receiver_due_label = PAYMENT_MODE_LABELS_FA.get("receiver_due", "پس‌کرایه")
    if code and code in _METHOD_TITLE_FA:
        return (_METHOD_TITLE_FA[code], receiver_due_label)
    if (shipping_payment_mode or "").strip() == "receiver_due":
        label = provider_label_fa(shipping_provider, shipping_service_code)
        if shipping_provider in {"tipax", "chapar", "iran_post", "local_delivery", "postex"}:
            return (label, receiver_due_label)
    return (None, None)
