"""CRUD for storefront orders and status history."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.commerce import Order, OrderItem, OrderMode, OrderStatus, OrderStatusEvent
from app.utils.tracking_code import generate_unique_tracking_code


async def create_order(
    db: AsyncSession,
    *,
    tracking_prefix: str,
    mode: OrderMode,
    status: str,
    payment_status: str,
    estimated_total: Decimal | None,
    customer_full_name: str,
    customer_phone: str,
    customer_is_guest: bool,
    company_name: str | None,
    note: str | None,
    shipping: dict[str, Any] | None,
    user_id: int | None,
    items: list[dict[str, Any]],
) -> Order:
    tracking_code = await generate_unique_tracking_code(db, tracking_prefix)
    order = Order(
        tracking_code=tracking_code,
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


async def record_status_event(
    db: AsyncSession,
    *,
    order_id: int,
    status: str,
    description: str | None = None,
    actor: str = "system",
) -> OrderStatusEvent:
    event = OrderStatusEvent(
        order_id=order_id,
        status=status,
        description=description,
        actor=actor,
    )
    db.add(event)
    await db.flush()
    return event


async def list_status_events(db: AsyncSession, order_id: int) -> list[OrderStatusEvent]:
    stmt = (
        select(OrderStatusEvent)
        .where(OrderStatusEvent.order_id == order_id)
        .order_by(OrderStatusEvent.created_at.asc(), OrderStatusEvent.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_order_by_id(db: AsyncSession, order_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.deleted_at.is_(None))
        .options(selectinload(Order.items), selectinload(Order.status_events))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_id_for_update(db: AsyncSession, order_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.deleted_at.is_(None))
        .options(selectinload(Order.items), selectinload(Order.status_events))
        .with_for_update()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_payment_authority(db: AsyncSession, authority: str) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.payment_authority == authority, Order.deleted_at.is_(None))
        .options(selectinload(Order.items), selectinload(Order.status_events))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_payment_authority_for_update(db: AsyncSession, authority: str) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.payment_authority == authority, Order.deleted_at.is_(None))
        .options(selectinload(Order.items), selectinload(Order.status_events))
        .with_for_update()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_tracking_code(db: AsyncSession, tracking_code: str) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.tracking_code == tracking_code, Order.deleted_at.is_(None))
        .options(selectinload(Order.items), selectinload(Order.status_events))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_orders(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    mode: OrderMode | None = None,
    payment_status: str | None = None,
    phone: str | None = None,
    customer_phone: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
    sort: str = "newest",
) -> tuple[list[Order], int]:
    """Return a page of orders plus the total match count."""
    filters = [Order.deleted_at.is_(None)]
    if status is not None:
        filters.append(Order.status == status)
    if mode is not None:
        filters.append(Order.mode == mode)
    if payment_status is not None:
        filters.append(Order.payment_status == payment_status)

    resolved_phone = customer_phone or phone
    if resolved_phone:
        filters.append(Order.customer_phone == resolved_phone)

    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Order.tracking_code.ilike(pattern),
                Order.customer_full_name.ilike(pattern),
                Order.customer_phone.ilike(pattern),
            )
        )
    if user_id is not None:
        filters.append(Order.user_id == user_id)

    count_stmt = select(func.count()).select_from(Order)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    order_by = [Order.created_at.desc(), Order.id.desc()]
    if sort == "oldest":
        order_by = [Order.created_at.asc(), Order.id.asc()]
    elif sort == "total_asc":
        order_by = [Order.estimated_total.asc().nulls_last(), Order.id.desc()]
    elif sort == "total_desc":
        order_by = [Order.estimated_total.desc().nulls_last(), Order.id.desc()]

    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_events))
        .order_by(*order_by)
        .offset(skip)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def soft_delete_order(db: AsyncSession, order_id: int) -> bool:
    order = (
        await db.execute(select(Order).where(Order.id == order_id, Order.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if order is None:
        return False
    order.deleted_at = datetime.now(UTC)
    await db.flush()
    return True


async def has_user_purchased_product(
    db: AsyncSession,
    *,
    user_id: int,
    product_id: int,
) -> bool:
    paid_like_states = (
        OrderStatus.PAID.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.DELIVERED.value,
    )
    stmt = (
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user_id,
            Order.mode == OrderMode.PURCHASE,
            Order.status.in_(paid_like_states),
            Order.deleted_at.is_(None),
            OrderItem.product_id == product_id,
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None
