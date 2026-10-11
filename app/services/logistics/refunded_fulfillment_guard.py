"""Block forward fulfillment while payment is refunded but order is not cancelled."""

from __future__ import annotations

from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.services.logistics.exceptions import ShipmentStateError

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
