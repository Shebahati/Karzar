"""Central registry for active storefront shipping methods."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import settings
from app.services.logistics.geo import is_tehran_city
from app.services.logistics.shipping_payment import ShippingPaymentMode


class ShippingMethodCode(StrEnum):
    TIPAX_STANDARD = "tipax_standard"
    CHAPAR_STANDARD = "chapar_standard"
    TEHRAN_EXPRESS = "tehran_express"


PROVIDER_TIPAX = "tipax"
PROVIDER_CHAPAR = "chapar"
PROVIDER_LOCAL_DELIVERY = "local_delivery"
PROVIDER_POSTEX = "postex"

MANUAL_FULFILLMENT_PROVIDERS = frozenset(
    {PROVIDER_TIPAX, PROVIDER_CHAPAR, PROVIDER_LOCAL_DELIVERY}
)

RECEIVER_DUE_PRICE_LABEL = "پس‌کرایه"


@dataclass(frozen=True)
class ShippingDestination:
    province: str
    city: str
    postal_code: str | None = None


@dataclass(frozen=True)
class ResolvedShippingMethod:
    code: ShippingMethodCode
    title: str
    provider: str
    carrier_code: str | None
    service_code: str
    payment_mode: ShippingPaymentMode
    price_label: str


@dataclass(frozen=True)
class ShippingMethodDefinition:
    code: ShippingMethodCode
    title: str
    provider: str
    carrier_code: str | None
    service_code: str
    payment_mode: ShippingPaymentMode
    enabled: bool
    sort_order: int
    tehran_only: bool = False

    def is_eligible(self, destination: ShippingDestination) -> bool:
        if self.tehran_only and not is_tehran_city(destination.province, destination.city):
            return False
        return True

    def resolve(self) -> ResolvedShippingMethod:
        return ResolvedShippingMethod(
            code=self.code,
            title=self.title,
            provider=self.provider,
            carrier_code=self.carrier_code,
            service_code=self.service_code,
            payment_mode=self.payment_mode,
            price_label=RECEIVER_DUE_PRICE_LABEL,
        )


def _registry() -> list[ShippingMethodDefinition]:
    return [
        ShippingMethodDefinition(
            code=ShippingMethodCode.TEHRAN_EXPRESS,
            title="ارسال فوری تهران",
            provider=PROVIDER_LOCAL_DELIVERY,
            carrier_code=None,
            service_code="tehran_express",
            payment_mode=ShippingPaymentMode.RECEIVER_DUE,
            enabled=bool(settings.SHIPPING_TEHRAN_EXPRESS_ENABLED),
            sort_order=0,
            tehran_only=True,
        ),
        ShippingMethodDefinition(
            code=ShippingMethodCode.TIPAX_STANDARD,
            title="تیپاکس",
            provider=PROVIDER_TIPAX,
            carrier_code=PROVIDER_TIPAX,
            service_code="standard",
            payment_mode=ShippingPaymentMode.RECEIVER_DUE,
            enabled=bool(settings.SHIPPING_TIPAX_ENABLED),
            sort_order=1,
        ),
        ShippingMethodDefinition(
            code=ShippingMethodCode.CHAPAR_STANDARD,
            title="چاپار",
            provider=PROVIDER_CHAPAR,
            carrier_code=PROVIDER_CHAPAR,
            service_code="standard",
            payment_mode=ShippingPaymentMode.RECEIVER_DUE,
            enabled=bool(settings.SHIPPING_CHAPAR_ENABLED),
            sort_order=2,
        ),
    ]


def storefront_shipping_enabled() -> bool:
    return any(m.enabled for m in _registry())


def postex_checkout_enabled() -> bool:
    from app.services.logistics.service import postex_enabled

    return bool(settings.SHIPPING_POSTEX_CHECKOUT_ENABLED) and postex_enabled()


def public_purchase_shipping_available() -> bool:
    """True when at least one explicit public checkout shipping path is enabled."""
    return storefront_shipping_enabled() or postex_checkout_enabled()


def list_available_methods(destination: ShippingDestination) -> list[ResolvedShippingMethod]:
    out: list[ResolvedShippingMethod] = []
    for definition in sorted(_registry(), key=lambda m: m.sort_order):
        if not definition.enabled:
            continue
        if not definition.is_eligible(destination):
            continue
        out.append(definition.resolve())
    return out


def get_method_definition(code: str) -> ShippingMethodDefinition | None:
    normalized = (code or "").strip()
    for definition in _registry():
        if definition.code.value == normalized:
            return definition
    return None


def resolve_shipping_method(
    code: str,
    destination: ShippingDestination,
) -> ResolvedShippingMethod:
    from app.services.logistics.exceptions import (
        ShippingMethodDestinationIneligibleError,
        ShippingMethodInvalidError,
        ShippingMethodUnavailableError,
    )

    definition = get_method_definition(code)
    if definition is None:
        raise ShippingMethodInvalidError("روش ارسال انتخاب‌شده معتبر نیست.")
    if not definition.enabled:
        raise ShippingMethodUnavailableError("روش ارسال انتخاب‌شده در حال حاضر فعال نیست.")
    if not definition.is_eligible(destination):
        raise ShippingMethodDestinationIneligibleError(
            "روش ارسال انتخاب‌شده برای مقصد شما در دسترس نیست."
        )
    return definition.resolve()
