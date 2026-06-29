"""Checkout and contact submission business logic."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import commerce as crud_commerce
from app.crud import content as crud_content
from app.crud import product as crud_product
from app.db.models.commerce import OrderMode
from app.db.models.user import User
from app.schemas.storefront import CheckoutRequest, CheckoutResponse, ContactRequest, ContactResponse
from app.utils.decimal_utils import to_decimal as _to_decimal
from app.utils.storefront_catalog import decimal_to_api_string


PURCHASE_STATUS = "در انتظار پرداخت"
INQUIRY_STATUS = "در حال بررسی استعلام"


async def submit_checkout(
    db: AsyncSession,
    payload: CheckoutRequest,
    current_user: Optional[User] = None,
) -> CheckoutResponse:
    if not payload.items:
        raise ValueError("At least one item is required")

    mode = OrderMode(payload.mode)
    if mode == OrderMode.PURCHASE and payload.shipping is None:
        raise ValueError("shipping is required for purchase mode")

    line_items = []
    estimated_total = Decimal("0.0")
    has_priced_item = False

    for line in payload.items:
        product = await crud_product.get_product_by_id(db, line.product_id)
        if not product or not product.is_active:
            raise ValueError(f"Product {line.product_id} is not available")
        if product.stock_quantity < line.quantity:
            raise ValueError(
                f"Product {line.product_id} has insufficient stock "
                f"(available: {product.stock_quantity}, requested: {line.quantity})"
            )

        unit_price = product.base_price
        if unit_price is not None:
            has_priced_item = True
            estimated_total += _to_decimal(unit_price) * line.quantity

        line_items.append(
            {
                "product_id": line.product_id,
                "quantity": line.quantity,
                "unit_price": unit_price,
            }
        )

    customer_is_guest = payload.customer.is_guest
    if current_user is not None:
        customer_is_guest = False

    order = await crud_commerce.create_order(
        db,
        tracking_code="",
        mode=mode,
        status=PURCHASE_STATUS if mode == OrderMode.PURCHASE else INQUIRY_STATUS,
        estimated_total=estimated_total if has_priced_item and mode == OrderMode.PURCHASE else None,
        customer_full_name=payload.customer.full_name,
        customer_phone=payload.customer.phone,
        customer_is_guest=customer_is_guest,
        company_name=payload.company_name,
        note=payload.note,
        shipping=payload.shipping.model_dump() if payload.shipping else None,
        user_id=current_user.id if current_user else None,
        items=line_items,
    )
    order.tracking_code = f"KZ-{order.id}"
    await db.commit()
    await db.refresh(order)

    return CheckoutResponse(
        order_id=order.id,
        tracking_code=order.tracking_code,
        mode=payload.mode,
        status=order.status,
        estimated_total=decimal_to_api_string(order.estimated_total),
        created_at=order.created_at,
    )


async def submit_contact(db: AsyncSession, payload: ContactRequest) -> ContactResponse:
    submission = await crud_content.create_contact_submission(
        db,
        ticket_code="",
        full_name=payload.full_name,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
    )
    submission.ticket_code = f"TK-{submission.id:05d}"
    await db.commit()
    return ContactResponse(ok=True, ticket=submission.ticket_code)
