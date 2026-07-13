"""Read helpers for the append-only stock movement ledger."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import StockMovement


async def list_stock_movements_for_reference(
    db: AsyncSession,
    reference_id: str,
) -> list[StockMovement]:
    stmt = (
        select(StockMovement)
        .where(StockMovement.reference_id == reference_id)
        .order_by(StockMovement.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
