"""Order lifecycle business logic: status transitions and Persian labels."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import commerce as crud_commerce
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.schemas.order import IssueQuoteRequest, OrderInvoiceResponse
from app.services.notification_service import notify_order_status_change
from app.services.stock_ledger_service import record_return_movement
from app.utils.decimal_utils import to_decimal as _to_decimal
from app.utils.storefront_catalog import decimal_to_api_string

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

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    OrderStatus.PENDING_PAYMENT.value: (
        OrderStatus.PAID.value,
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
        OrderStatus.CANCELLED.value,
    ),
    OrderStatus.INQUIRY_CLOSED.value: (),
}

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


def build_invoice_response(invoice: dict | None) -> OrderInvoiceResponse | None:
    if not invoice:
        return None
    issued_at = invoice.get("issued_at")
    if isinstance(issued_at, str):
        issued_at = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    valid_until = invoice.get("valid_until")
    if isinstance(valid_until, str):
        valid_until = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
    return OrderInvoiceResponse(
        invoice_number=str(invoice.get("invoice_number", "")),
        issued_at=issued_at,
        valid_until=valid_until,
        total=str(invoice.get("total", "")),
        note=invoice.get("note"),
    )


async def record_initial_status_event(
    db: AsyncSession,
    order: Order,
    *,
    description: str | None = None,
) -> None:
    await crud_commerce.record_status_event(
        db,
        order_id=order.id,
        status=order.status,
        description=description,
        actor="system",
    )


async def transition_order_status(
    db: AsyncSession,
    order: Order,
    target_status: str,
    *,
    note: str | None = None,
    postal_tracking_code: str | None = None,
    delivery_eta: datetime | None = None,
    actor: str = "admin",
    event_description: str | None = None,
) -> Order:
    try:
        target = OrderStatus(target_status).value
    except ValueError as exc:
        raise ValueError(f"Unknown order status '{target_status}'") from exc

    current = order.status
    if current == target:
        raise ValueError(f"Order is already in status '{target}'")

    if not can_transition(current, target):
        raise ValueError(f"Cannot transition order from '{current}' to '{target}'")

    if target == OrderStatus.SHIPPED.value:
        tracking = (postal_tracking_code or order.postal_tracking_code or "").strip()
        if len(tracking) < 10:
            raise ValueError("برای ثبت ارسال، کد رهگیری پست الزامی است.")
        order.postal_tracking_code = tracking

    if (
        order.mode == OrderMode.PURCHASE
        and target == OrderStatus.PROCESSING.value
        and order.payment_status != PaymentStatus.PAID.value
    ):
        raise ValueError("Paid payment status is required before processing")

    if delivery_eta is not None:
        order.delivery_eta = delivery_eta

    if (
        target == OrderStatus.CANCELLED.value
        and order.mode == OrderMode.PURCHASE
        and current in _STOCK_RESERVED_STATES
    ):
        await _restore_stock(db, order)

    order.status = target

    if target == OrderStatus.PAID.value:
        order.payment_status = PaymentStatus.PAID.value

    if note is not None:
        # Admin annotations go to admin_note; never overwrite the customer checkout note.
        order.admin_note = note

    await crud_commerce.record_status_event(
        db,
        order_id=order.id,
        status=target,
        description=event_description,
        actor=actor,
    )
    await notify_order_status_change(
        phone=order.customer_phone,
        tracking_code=order.tracking_code,
        status=target,
    )
    await db.flush()
    return order


async def issue_order_quote(
    db: AsyncSession,
    order: Order,
    payload: IssueQuoteRequest,
) -> Order:
    if order.mode != OrderMode.INQUIRY:
        raise ValueError("فقط استعلام‌ها قابل پیش‌فاکتور هستند.")
    if order.status != OrderStatus.INQUIRY_REVIEW.value:
        raise ValueError("این استعلام در مرحله صدور پیش‌فاکتور نیست.")

    total = Decimal("0")
    items_by_product = {item.product_id: item for item in order.items}
    for line in payload.items:
        item = items_by_product.get(line.product_id)
        if item is None:
            raise ValueError(f"Product {line.product_id} is not part of this order")
        unit = _to_decimal(line.unit_price)
        if unit <= Decimal("0"):
            raise ValueError("قیمت همه اقلام باید معتبر باشد.")
        if line.quantity != item.quantity:
            raise ValueError(f"Quantity mismatch for product {line.product_id}")
        item.unit_price = unit
        total += unit * item.quantity

    issued_at = datetime.now(UTC)
    invoice_number = f"INV-{order.id}"
    order.estimated_total = total
    order.invoice_number = invoice_number
    order.invoice_valid_until = payload.valid_until
    order.invoice = {
        "invoice_number": invoice_number,
        "issued_at": issued_at.isoformat(),
        "valid_until": payload.valid_until.isoformat() if payload.valid_until else None,
        "total": decimal_to_api_string(total),
        "note": payload.note,
    }

    await transition_order_status(
        db,
        order,
        OrderStatus.INQUIRY_QUOTED.value,
        actor="admin",
        event_description="پیش‌فاکتور با قیمت‌گذاری ادمین صادر شد",
    )
    return order


async def _restore_stock(db: AsyncSession, order: Order) -> None:
    from app.crud import product as crud_product

    product_ids = [item.product_id for item in order.items]
    if not product_ids:
        return
    products = await crud_product.get_products_for_update(db, product_ids)
    for item in order.items:
        product = products.get(item.product_id)
        if product is not None:
            product.stock_quantity = product.stock_quantity + item.quantity
            await record_return_movement(
                db,
                product_id=item.product_id,
                quantity=item.quantity,
                order_id=order.id,
                user_id=order.user_id,
            )
