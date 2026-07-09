"""CRUD for storefront orders."""

import uuid
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.commerce import Order, OrderItem, OrderMode


async def create_order(
    db: AsyncSession,
    *,
    tracking_prefix: str,
    mode: OrderMode,
    status: str,
    estimated_total: Optional[Decimal],
    customer_full_name: str,
    customer_phone: str,
    customer_is_guest: bool,
    company_name: Optional[str],
    note: Optional[str],
    shipping: Optional[dict[str, Any]],
    user_id: Optional[int],
    items: List[dict[str, Any]],
) -> Order:
    # Insert with a unique random placeholder so concurrent orders never collide
    # on the unique tracking_code index, then derive the human-friendly code from
    # the generated id within the same transaction.
    order = Order(
        tracking_code=f"pending-{uuid.uuid4().hex}",
        mode=mode,
        status=status,
        estimated_total=estimated_total,
        customer_full_name=customer_full_name,
        customer_phone=customer_phone,
        customer_is_guest=customer_is_guest,
        company_name=company_name,
        note=note,
        shipping=shipping,
        user_id=user_id,
    )
    db.add(order)
    await db.flush()

    order.tracking_code = f"{tracking_prefix}{order.id}"

    for item in items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item.get("unit_price"),
            )
        )

    await db.flush()
    await db.refresh(order, attribute_names=["items"])
    return order


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[Order]:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
