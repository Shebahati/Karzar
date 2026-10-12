"""Append-only inventory movement ledger helpers."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.stock_movement import list_stock_movements_for_reference
from app.db.models.commerce import Order, OrderMode
from app.db.models.product import StockMovement, StockMovementType


def order_stock_reference(order_id: int) -> str:
    return f"order:{order_id}"


async def _load_order_items(db: AsyncSession, order: Order) -> Order:
    if order.items:
        return order
    refreshed = (
        (
            await db.execute(
                select(Order)
                .where(Order.id == order.id)
                .options(selectinload(Order.items))
            )
        )
        .scalars()
        .first()
    )
    if refreshed is None:
        raise ValueError(f"Order {order.id} not found")
    return refreshed


def _sale_quantity_recorded(movements: list[StockMovement], product_id: int) -> Decimal:
    total = Decimal("0")
    for movement in movements:
        if movement.product_id != product_id:
            continue
        if movement.movement_type != StockMovementType.SALE.value:
            continue
        total += abs(Decimal(str(movement.quantity_change)))
    return total


def _net_quantity_by_product(movements: list[StockMovement]) -> dict[int, Decimal]:
    nets: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for movement in movements:
        nets[movement.product_id] += Decimal(str(movement.quantity_change))
    return nets


async def _append(
    db: AsyncSession,
    *,
    product_id: int,
    quantity_change: Decimal,
    movement_type: StockMovementType,
    reference_id: str,
    user_id: int | None = None,
) -> StockMovement:
    row = StockMovement(
        product_id=product_id,
        quantity_change=quantity_change,
        movement_type=movement_type.value,
        reference_id=str(reference_id),
        user_id=user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def record_sale_movement(
    db: AsyncSession,
    *,
    product_id: int,
    quantity: Decimal | int | float | str,
    order_id: int,
    user_id: int | None = None,
) -> StockMovement:
    amount = Decimal(str(quantity))
    return await _append(
        db,
        product_id=product_id,
        quantity_change=-abs(amount),
        movement_type=StockMovementType.SALE,
        reference_id=order_stock_reference(order_id),
        user_id=user_id,
    )


async def record_return_movement(
    db: AsyncSession,
    *,
    product_id: int,
    quantity: Decimal | int | float | str,
    order_id: int,
    user_id: int | None = None,
) -> StockMovement:
    amount = Decimal(str(quantity))
    return await _append(
        db,
        product_id=product_id,
        quantity_change=abs(amount),
        movement_type=StockMovementType.RETURN,
        reference_id=order_stock_reference(order_id),
        user_id=user_id,
    )


async def record_adjustment_movement(
    db: AsyncSession,
    *,
    product_id: int,
    quantity_delta: Decimal | int | float | str,
    reference_id: str,
    user_id: int | None = None,
) -> StockMovement:
    return await _append(
        db,
        product_id=product_id,
        quantity_change=Decimal(str(quantity_delta)),
        movement_type=StockMovementType.ADJUSTMENT,
        reference_id=reference_id,
        user_id=user_id,
    )


async def ensure_order_sale_movements(
    db: AsyncSession,
    order: Order,
    *,
    user_id: int | None = None,
) -> None:
    """Record SALE movements for paid commercial sale (idempotent, legacy-safe).

    Safe to call repeatedly. Skips lines already covered by pre-deploy SALE rows.
    """
    if order.mode != OrderMode.PURCHASE:
        return
    order = await _load_order_items(db, order)
    if not order.items:
        return

    reference = order_stock_reference(order.id)
    movements = await list_stock_movements_for_reference(db, reference)
    actor_id = user_id if user_id is not None else order.user_id

    for item in order.items:
        recorded = _sale_quantity_recorded(movements, item.product_id)
        needed = Decimal(str(item.quantity)) - recorded
        if needed <= Decimal("0"):
            continue
        await record_sale_movement(
            db,
            product_id=item.product_id,
            quantity=needed,
            order_id=order.id,
            user_id=actor_id,
        )
        movements = await list_stock_movements_for_reference(db, reference)


async def ensure_compensating_returns_for_order(
    db: AsyncSession,
    order: Order,
    *,
    user_id: int | None = None,
) -> None:
    """Append RETURN movements only when a net SALE remains for a line (idempotent)."""
    if order.mode != OrderMode.PURCHASE:
        return
    order = await _load_order_items(db, order)
    if not order.items:
        return

    reference = order_stock_reference(order.id)
    movements = await list_stock_movements_for_reference(db, reference)
    nets = _net_quantity_by_product(movements)
    actor_id = user_id if user_id is not None else order.user_id

    for item in order.items:
        net = nets.get(item.product_id, Decimal("0"))
        if net >= Decimal("0"):
            continue
        await record_return_movement(
            db,
            product_id=item.product_id,
            quantity=-net,
            order_id=order.id,
            user_id=actor_id,
        )
        nets[item.product_id] = Decimal("0")
