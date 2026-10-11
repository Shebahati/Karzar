"""Payment provider capability flags for admin workflows."""

from __future__ import annotations

from app.core.config import settings
from app.schemas.payment import PaymentCapabilitiesResponse, PaymentRefundMode


def get_payment_capabilities() -> PaymentCapabilitiesResponse:
    provider = settings.PAYMENT_PROVIDER
    if provider == "sep":
        return PaymentCapabilitiesResponse(
            provider="sep",
            automated_refund_supported=False,
            external_refund_confirmation_supported=True,
            refund_mode=PaymentRefundMode.EXTERNAL_CONFIRMATION,
        )
    if provider == "mock":
        return PaymentCapabilitiesResponse(
            provider="mock",
            automated_refund_supported=True,
            external_refund_confirmation_supported=False,
            refund_mode=PaymentRefundMode.AUTOMATED,
        )
    if provider == "zarinpal":
        return PaymentCapabilitiesResponse(
            provider="zarinpal",
            automated_refund_supported=True,
            external_refund_confirmation_supported=False,
            refund_mode=PaymentRefundMode.AUTOMATED,
        )
    return PaymentCapabilitiesResponse(
        provider=provider,
        automated_refund_supported=False,
        external_refund_confirmation_supported=False,
        refund_mode=PaymentRefundMode.AUTOMATED,
    )
