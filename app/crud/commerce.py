"""CRUD for storefront orders."""

import uuid
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.commerce import Order, OrderItem, OrderMode


async def create_order(
    db: AsyncSession,
    *,
    tracking_prefix: str,
    mode: OrderMode,
    status: str,
    payment_status: str,
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
        payment_status=payment_status,
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


async def get_order_by_tracking_code(db: AsyncSession, tracking_code: str) -> Optional[Order]:
    stmt = (
        select(Order)
        .where(Order.tracking_code == tracking_code)
        .options(selectinload(Order.items))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_orders(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    mode: Optional[OrderMode] = None,
    payment_status: Optional[str] = None,
    phone: Optional[str] = None,
    user_id: Optional[int] = None,
) -> tuple[List[Order], int]:
    """Return a page of orders (newest first) plus the total match count."""
    filters = []
    if status is not None:
        filters.append(Order.status == status)
    if mode is not None:
        filters.append(Order.mode == mode)
    if payment_status is not None:
        filters.append(Order.payment_status == payment_status)
    if phone:
        filters.append(Order.customer_phone == phone)
    if user_id is not None:
        filters.append(Order.user_id == user_id)

    count_stmt = select(func.count()).select_from(Order)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(skip)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total
