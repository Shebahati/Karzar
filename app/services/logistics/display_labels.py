"""Canonical human-readable shipping labels (FA)."""

from __future__ import annotations

PROVIDER_LABELS_FA: dict[str, str] = {
    "tipax": "تیپاکس",
    "chapar": "چاپار",
    "iran_post": "پست پیشتاز",
    "local_delivery": "ارسال محلی",
    "postex": "پستکس",
}

SERVICE_LABELS_FA: dict[str, str] = {
    "standard": "استاندارد",
    "pishtaz": "پست پیشتاز",
    "motorcycle_48h": "پیک موتوری حداکثر تا ۴۸ ساعت",
    "express_3h": "ارسال فوری ۳ ساعته",
    # Legacy pre-activation local service code
    "tehran_express": "ارسال فوری ۳ ساعته",
}

PAYMENT_MODE_LABELS_FA: dict[str, str] = {
    "receiver_due": "پس‌کرایه",
    "sender_prepaid": "پیش‌پرداخت",
}


def provider_label_fa(provider: str | None, service_code: str | None = None) -> str:
    service = (service_code or "").strip()
    if provider == "local_delivery" and service:
        return SERVICE_LABELS_FA.get(service, PROVIDER_LABELS_FA["local_delivery"])
    if provider == "iran_post":
        return PROVIDER_LABELS_FA["iran_post"]
    if provider:
        return PROVIDER_LABELS_FA.get(provider, provider)
    return "—"


def shipping_cost_label_fa(payment_mode: str | None, customer_cost: str | None = None) -> str:
    if payment_mode == "receiver_due":
        if customer_cost is not None and str(customer_cost).strip():
            # Historical prepaid rows only — receiver_due must stay NULL at checkout.
            return PAYMENT_MODE_LABELS_FA["receiver_due"]
        return PAYMENT_MODE_LABELS_FA["receiver_due"]
    if customer_cost is None:
        return PAYMENT_MODE_LABELS_FA.get(payment_mode or "", payment_mode or "—")
    return f"{customer_cost} تومان"
