"""Order lifecycle business logic: status transitions and Persian labels.

The database stores canonical English status codes (see ``OrderStatus``); the
API layer exposes both the code and a localized Persian label so the storefront
and admin panel can display human-readable text without hardcoding it.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus

STATUS_LABELS_FA: dict[str, str] = {
    OrderStatus.PENDING_PAYMENT.value: "در انتظار پرداخت",
    OrderStatus.PAID.value: "پرداخت شده",
    OrderStatus.PROCESSING.value: "در حال آماده‌سازی",
    OrderStatus.SHIPPED.value: "ارسال شده",
    OrderStatus.DELIVERED.value: "تحویل داده شده",
    OrderStatus.CANCELLED.value: "لغو شده",
    OrderStatus.INQUIRY_REVIEW.value: "در حال بررسی استعلام",
    OrderStatus.INQUIRY_QUOTED.value: "استعلام قیمت‌گذاری شد",
    OrderStatus.INQUIRY_CLOSED.value: "استعلام بسته شد",
}

PAYMENT_STATUS_LABELS_FA: dict[str, str] = {
    PaymentStatus.UNPAID.value: "پرداخت‌نشده",
    PaymentStatus.PAID.value: "پرداخت‌شده",
    PaymentStatus.FAILED.value: "ناموفق",
    PaymentStatus.REFUNDED.value: "بازپرداخت‌شده",
}

# Allowed forward transitions per canonical status. Terminal states map to ().
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    OrderStatus.PENDING_PAYMENT.value: (
        OrderStatus.PAID.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.CANCELLED.value,
    ),
    OrderStatus.PAID.value: (
        OrderStatus.PROCESSING.value,
        OrderStatus.CANCELLED.value,
    ),
    OrderStatus.PROCESSING.value: (
        OrderStatus.SHIPPED.value,
        OrderStatus.CANCELLED.value,
    ),
    OrderStatus.SHIPPED.value: (
        OrderStatus.DELIVERED.value,
    ),
    OrderStatus.DELIVERED.value: (),
    OrderStatus.CANCELLED.value: (),
    OrderStatus.INQUIRY_REVIEW.value: (
        OrderStatus.INQUIRY_QUOTED.value,
        OrderStatus.INQUIRY_CLOSED.value,
        OrderStatus.CANCELLED.value,
    ),
    OrderStatus.INQUIRY_QUOTED.value: (
        OrderStatus.INQUIRY_CLOSED.value,
        OrderStatus.PENDING_PAYMENT.value,
        OrderStatus.CANCELLED.value,
    ),
    OrderStatus.INQUIRY_CLOSED.value: (),
}

# Statuses in which stock has been reserved (decremented) for a purchase order.
_STOCK_RESERVED_STATES = frozenset(
    {
        OrderStatus.PENDING_PAYMENT.value,
        OrderStatus.PAID.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.DELIVERED.value,
    }
)


def status_label(status: str) -> str:
    return STATUS_LABELS_FA.get(status, status)


def payment_status_label(payment_status: str) -> str:
    return PAYMENT_STATUS_LABELS_FA.get(payment_status, payment_status)


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, ())


def allowed_next_statuses(current: str) -> list[str]:
    return list(ALLOWED_TRANSITIONS.get(current, ()))


async def transition_order_status(
    db: AsyncSession,
    order: Order,
    target_status: str,
    *,
    note: Optional[str] = None,
) -> Order:
    """Apply a validated status transition, restocking on cancellation.

    Raises ``ValueError`` when the transition is not permitted by the state
    machine. The caller owns the surrounding transaction (commit/rollback).
    """
    try:
        target = OrderStatus(target_status).value
    except ValueError as exc:
        raise ValueError(f"Unknown order status '{target_status}'") from exc

    current = order.status
    if current == target:
        raise ValueError(f"Order is already in status '{target}'")

    if not can_transition(current, target):
        raise ValueError(
            f"Cannot transition order from '{current}' to '{target}'"
        )

    # Restore stock when a purchase order that had reserved inventory is cancelled.
    if (
        target == OrderStatus.CANCELLED.value
        and order.mode == OrderMode.PURCHASE
        and current in _STOCK_RESERVED_STATES
    ):
        await _restore_stock(db, order)

    order.status = target

    if target == OrderStatus.PAID.value:
        order.payment_status = PaymentStatus.PAID.value
    elif target == OrderStatus.CANCELLED.value and order.payment_status == PaymentStatus.PAID.value:
        order.payment_status = PaymentStatus.REFUNDED.value

    if note:
        order.note = note

    await db.flush()
    return order


async def _restore_stock(db: AsyncSession, order: Order) -> None:
    """Add reserved quantities back to product stock (used on cancellation)."""
    from app.crud import product as crud_product

    product_ids = [item.product_id for item in order.items]
    if not product_ids:
        return
    products = await crud_product.get_products_for_update(db, product_ids)
    for item in order.items:
        product = products.get(item.product_id)
        if product is not None:
            product.stock_quantity = product.stock_quantity + item.quantity
