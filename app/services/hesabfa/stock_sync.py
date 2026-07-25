"""Pull Hesabfa stock into site inventory for matched SKUs only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.hesabfa import HesabfaItemMapping
from app.db.models.product import Product
from app.services.hesabfa.client import HesabfaClient, get_hesabfa_client
from app.services.stock_ledger_service import record_adjustment_movement

logger = get_logger(__name__)


@dataclass(frozen=True)
class StockSyncResult:
    checked: int
    updated: int
    unchanged: int
    missing_in_hesabfa: int


async def pull_stock_from_hesabfa(
    db: AsyncSession,
    *,
    client: HesabfaClient | None = None,
    batch_size: int = 100,
) -> StockSyncResult:
    """Overwrite site stock_quantity from Hesabfa for mapped products only.

    Never pushes site-only stock to Hesabfa.
    """
    api = client or get_hesabfa_client()
    mappings = (
        await db.execute(
            select(HesabfaItemMapping).options()
        )
    ).scalars().all()
    if not mappings:
        return StockSyncResult(checked=0, updated=0, unchanged=0, missing_in_hesabfa=0)

    codes = [m.hesabfa_code for m in mappings]
    quantities: dict[str, Decimal] = {}
    for i in range(0, len(codes), batch_size):
        chunk = codes[i : i + batch_size]
        rows = await api.get_quantity(codes=chunk)
        for row in rows:
            code = str(row.get("Code") or row.get("code") or "").strip()
            if not code:
                continue
            qty = Decimal(str(row.get("Quantity") if "Quantity" in row else row.get("quantity", 0)))
            quantities[code] = qty

    product_ids = [m.product_id for m in mappings]
    products = (
        await db.execute(select(Product).where(Product.id.in_(product_ids)))
    ).scalars().all()
    products_by_id = {p.id: p for p in products}

    updated = unchanged = missing = 0
    now = datetime.now(UTC)
    for mapping in mappings:
        product = products_by_id.get(mapping.product_id)
        if product is None or product.deleted_at is not None:
            continue
        if mapping.hesabfa_code not in quantities:
            missing += 1
            continue
        new_qty = quantities[mapping.hesabfa_code]
        if new_qty < 0:
            new_qty = Decimal("0")
        old_qty = Decimal(str(product.stock_quantity or 0))
        mapping.last_stock = new_qty
        mapping.last_synced_at = now
        if old_qty == new_qty:
            unchanged += 1
            continue
        delta = new_qty - old_qty
        product.stock_quantity = new_qty
        await record_adjustment_movement(
            db,
            product_id=product.id,
            quantity_delta=delta,
            reference_id=f"hesabfa-stock:{mapping.hesabfa_code}",
        )
        updated += 1

    await db.flush()
    logger.info(
        "Hesabfa stock pull checked=%s updated=%s unchanged=%s missing=%s",
        len(mappings),
        updated,
        unchanged,
        missing,
    )
    return StockSyncResult(
        checked=len(mappings),
        updated=updated,
        unchanged=unchanged,
        missing_in_hesabfa=missing,
    )
