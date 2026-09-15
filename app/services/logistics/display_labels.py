"""Canonical human-readable shipping labels (FA)."""

from __future__ import annotations

PROVIDER_LABELS_FA: dict[str, str] = {
    "tipax": "تیپاکس",
    "chapar": "چاپار",
    "local_delivery": "ارسال فوری تهران",
    "postex": "پستکس",
}

SERVICE_LABELS_FA: dict[str, str] = {
    "standard": "استاندارد",
    "tehran_express": "ارسال فوری تهران",
}

PAYMENT_MODE_LABELS_FA: dict[str, str] = {
    "receiver_due": "پس‌کرایه",
    "sender_prepaid": "پیش‌پرداخت",
}


def provider_label_fa(provider: str | None, service_code: str | None = None) -> str:
    if provider == "local_delivery" and service_code == "tehran_express":
        return PROVIDER_LABELS_FA["local_delivery"]
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
