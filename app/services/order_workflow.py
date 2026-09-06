"""Canonical open/terminal order status sets for admin queues."""

from __future__ import annotations

from app.db.models.commerce import OrderMode, OrderStatus, PaymentStatus

# Purchase orders still actionable (not fulfilled or cancelled).
OPEN_PURCHASE_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        OrderStatus.PAID.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.SHIPPED.value,
    }
)

# Inquiry quotes still actionable.
OPEN_INQUIRY_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        OrderStatus.INQUIRY_REVIEW.value,
        OrderStatus.INQUIRY_QUOTED.value,
    }
)

TERMINAL_PURCHASE_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        OrderStatus.DELIVERED.value,
        OrderStatus.CANCELLED.value,
    }
)

TERMINAL_INQUIRY_ORDER_STATUSES: frozenset[str] = frozenset(
    {
        OrderStatus.INQUIRY_CLOSED.value,
    }
)

TERMINAL_PAYMENT_STATUSES: frozenset[str] = frozenset(
    {
        PaymentStatus.REFUNDED.value,
        PaymentStatus.FAILED.value,
    }
)


def is_open_purchase_order(status: str, *, payment_status: str | None = None) -> bool:
    if status in TERMINAL_PURCHASE_ORDER_STATUSES:
        return False
    if payment_status in TERMINAL_PAYMENT_STATUSES:
        return False
    return status in OPEN_PURCHASE_ORDER_STATUSES


def is_open_inquiry_order(status: str) -> bool:
    return status in OPEN_INQUIRY_ORDER_STATUSES


def open_statuses_for_mode(mode: OrderMode | str | None) -> frozenset[str] | None:
    if mode in (OrderMode.PURCHASE, OrderMode.PURCHASE.value, "purchase"):
        return OPEN_PURCHASE_ORDER_STATUSES
    if mode in (OrderMode.INQUIRY, OrderMode.INQUIRY.value, "inquiry"):
        return OPEN_INQUIRY_ORDER_STATUSES
    return None
