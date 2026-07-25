"""Deprecated Hesabfa→site stock pull (disabled).

Warehouse quantities live only in Hesabfa. The site stores availability
(boolean) and must not import numeric stock.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.hesabfa.client import HesabfaClient

logger = get_logger(__name__)


@dataclass(frozen=True)
class StockSyncResult:
    checked: int
    updated: int
    unchanged: int
    missing_in_hesabfa: int
    disabled: bool = True


async def pull_stock_from_hesabfa(
    db: AsyncSession,
    *,
    client: HesabfaClient | None = None,
    batch_size: int = 100,
) -> StockSyncResult:
    """No-op: Hesabfa→site quantity sync is intentionally disabled."""
    del db, client, batch_size
    logger.info("Hesabfa stock pull skipped (site does not store warehouse quantities)")
    return StockSyncResult(
        checked=0,
        updated=0,
        unchanged=0,
        missing_in_hesabfa=0,
        disabled=True,
    )
