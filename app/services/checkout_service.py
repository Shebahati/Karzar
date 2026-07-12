"""Checkout and contact submission business logic."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import commerce as crud_commerce
from app.crud import content as crud_content
from app.crud import product as crud_product
from app.db.models.commerce import OrderMode, OrderStatus, PaymentStatus
from app.db.models.user import User
from app.schemas.storefront import CheckoutRequest, CheckoutResponse, ContactRequest, ContactResponse
from app.services.cart_service import clear_cart_for_checkout, resolve_checkout_defaults
from app.services.order_expiry_service import cancel_expired_pending_payment_orders
from app.services.payment_flow_service import initialize_order_payment
from app.services.order_service import record_initial_status_event, status_label
from app.utils.decimal_utils import to_decimal as _to_decimal
from app.utils.storefront_catalog import decimal_to_api_string


class PurchaseAuthRequiredError(ValueError):
    """Raised when purchase checkout is attempted without authentication."""


def _merge_quantities(payload: CheckoutRequest) -> dict[int, int]:
    """Aggregate quantities per product so duplicate lines are validated together."""
    merged: dict[int, int] = {}
    for line in payload.items:
        merged[line.product_id] = merged.get(line.product_id, 0) + line.quantity
    return merged


async def submit_checkout(
    db: AsyncSession,
    payload: CheckoutRequest,
    current_user: Optional[User] = None,
    *,
    guest_cart_token: Optional[str] = None,
) -> CheckoutResponse:
    if not payload.items:
        raise ValueError("At least one item is required")

    mode_str, company_name = resolve_checkout_defaults(
        current_user, payload.mode, payload.company_name
    )
    mode = OrderMode(mode_str)
    is_purchase = mode == OrderMode.PURCHASE
    if is_purchase and current_user is None:
        raise PurchaseAuthRequiredError()
    if is_purchase and payload.shipping is None:
        raise ValueError("shipping is required for purchase mode")

    if is_purchase:
        await cancel_expired_pending_payment_orders(db)

    quantities = _merge_quantities(payload)

    # Lock the referenced product rows so concurrent purchases cannot oversell.
    products = await crud_product.get_products_for_update(db, list(quantities.keys()))

    line_items = []
    estimated_total = Decimal("0.0")
    has_priced_item = False

    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if not product or not product.is_active:
            raise ValueError(f"Product {product_id} is not available")

        # Stock is only enforced for real purchases; inquiries may quote any item.
        if is_purchase and product.stock_quantity < quantity:
            raise ValueError(
                f"Product {product_id} has insufficient stock "
                f"(available: {product.stock_quantity}, requested: {quantity})"
            )

        unit_price = product.base_price
        if unit_price is not None:
            has_priced_item = True
            line_total = _to_decimal(unit_price) * quantity
            tax_rate = _to_decimal(product.tax_percent or 0) / Decimal("100")
            estimated_total += line_total + (line_total * tax_rate)

        if is_purchase:
            product.stock_quantity = product.stock_quantity - quantity

        line_items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
            }
        )

    customer_is_guest = payload.customer.is_guest
    if current_user is not None:
        customer_is_guest = False

    status_value = (
        OrderStatus.PENDING_PAYMENT.value if is_purchase else OrderStatus.INQUIRY_REVIEW.value
    )

    order = await crud_commerce.create_order(
        db,
        tracking_prefix="KZ-",
        mode=mode,
        status=status_value,
        payment_status=PaymentStatus.UNPAID.value,
        estimated_total=estimated_total if has_priced_item and is_purchase else None,
        customer_full_name=payload.customer.full_name,
        customer_phone=payload.customer.phone,
        customer_is_guest=customer_is_guest,
        company_name=company_name,
        note=payload.note,
        shipping=payload.shipping.model_dump() if payload.shipping else None,
        user_id=current_user.id if current_user else None,
        items=line_items,
    )
    await record_initial_status_event(db, order, description="سفارش ثبت شد")
    await clear_cart_for_checkout(
        db,
        mode=mode_str,
        user=current_user,
        guest_token=guest_cart_token,
    )
    await db.commit()
    await db.refresh(order)

    payment_url: str | None = None
    authority: str | None = None
    if is_purchase and current_user is not None:
        payment = await initialize_order_payment(db, order)
        await db.commit()
        await db.refresh(order)
        payment_url = payment.payment_url
        authority = payment.authority

    return CheckoutResponse(
        order_id=order.id,
        tracking_code=order.tracking_code,
        mode=mode_str,
        status=order.status,
        status_label=status_label(order.status),
        estimated_total=decimal_to_api_string(order.estimated_total),
        created_at=order.created_at,
        payment_url=payment_url,
        authority=authority,
    )


async def submit_contact(db: AsyncSession, payload: ContactRequest) -> ContactResponse:
    submission = await crud_content.create_contact_submission(
        db,
        ticket_prefix="TK-",
        full_name=payload.full_name,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
    )
    await db.commit()
    return ContactResponse(ok=True, ticket=submission.ticket_code)
