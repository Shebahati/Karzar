"""Block forward fulfillment while payment is refunded but order is not cancelled."""

from __future__ import annotations

from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import ShipmentStateError
from app.services.logistics.models import ShipmentStatus

_REFUNDED_FULFILLMENT_MESSAGE = (
    "سفارش بازپرداخت‌شده فقط باید لغو شود و ادامه فرایند ارسال مجاز نیست."
)


def order_blocks_forward_fulfillment(order: Order) -> bool:
    return (
        order.mode == OrderMode.PURCHASE
        and order.payment_status == PaymentStatus.REFUNDED.value
        and order.status != OrderStatus.CANCELLED.value
    )


def assert_order_forward_fulfillment_allowed(order: Order) -> None:
    if order_blocks_forward_fulfillment(order):
        raise ShipmentStateError(
            _REFUNDED_FULFILLMENT_MESSAGE,
            error_code="SHIPMENT_STATE_INVALID",
        )


def shipment_has_unresolved_provider_create(shipment: Shipment) -> bool:
    """Durable Postex create may be in flight or outcome unknown (no parcel id yet)."""
    if (shipment.provider_parcel_no or "").strip():
        return False
    if shipment.status in {
        ShipmentStatus.BOOKING.value,
        ShipmentStatus.CREATION_UNCERTAIN.value,
    }:
        return True
    if (shipment.provider_data or {}).get("create_attempted"):
        return True
    return False


_EXTERNAL_REFUND_BUSY_MESSAGE = (
    "مرسوله در حال ثبت/تطبیق با سرویس حمل است؛ "
    "ابتدا وضعیت ارسال را تعیین تکلیف کنید و سپس استرداد را در کارزار ثبت کنید."
)


class ExternalRefundFulfillmentBusy(Exception):
    """External refund blocked while provider parcel create is unresolved."""


def assert_external_refund_fulfillment_quiescent(order: Order) -> None:
    for shipment in order.shipments or []:
        if shipment_has_unresolved_provider_create(shipment):
            raise ExternalRefundFulfillmentBusy(_EXTERNAL_REFUND_BUSY_MESSAGE)
