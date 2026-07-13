"""Append-only inventory movement ledger helpers."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import StockMovement, StockMovementType


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
        reference_id=f"order:{order_id}",
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
        reference_id=f"order:{order_id}",
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
