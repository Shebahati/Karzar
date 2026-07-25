"""Match site products to Hesabfa items by SKU ↔ ProductCode."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.hesabfa import HesabfaItemMapping
from app.db.models.product import Product
from app.services.hesabfa.client import HesabfaClient, get_hesabfa_client

logger = get_logger(__name__)


@dataclass(frozen=True)
class ItemMappingSyncResult:
    matched: int
    created: int
    updated: int
    scanned_hesabfa: int
    unmatched_site_skus: int


def _normalize_sku(value: str | None) -> str:
    return (value or "").strip().upper()


async def sync_item_mappings_by_sku(
    db: AsyncSession,
    *,
    client: HesabfaClient | None = None,
    page_size: int = 100,
) -> ItemMappingSyncResult:
    """Pull Hesabfa items and upsert mappings where ProductCode matches product.sku.

    Does NOT create items in Hesabfa. Site-only SKUs stay unmatched.
    """
    api = client or get_hesabfa_client()

    products = (
        await db.execute(select(Product).where(Product.deleted_at.is_(None)))
    ).scalars().all()
    by_sku: dict[str, Product] = {}
    for product in products:
        key = _normalize_sku(product.sku)
        if key:
            by_sku[key] = product

    existing_rows = (await db.execute(select(HesabfaItemMapping))).scalars().all()
    by_product_id = {row.product_id: row for row in existing_rows}
    by_code = {row.hesabfa_code: row for row in existing_rows}

    created = updated = matched = scanned = 0
    skip = 0
    while True:
        page = await api.get_items(take=page_size, skip=skip)
        items: list[dict[str, Any]] = list(page.get("List") or [])
        if not items:
            break
        scanned += len(items)
        for item in items:
            product_code = _normalize_sku(
                str(item.get("ProductCode") or item.get("productCode") or "")
            )
            code = str(item.get("Code") or item.get("code") or "").strip()
            if not product_code or not code:
                continue
            product = by_sku.get(product_code)
            if product is None:
                continue
            matched += 1
            now = datetime.now(UTC)
            row = by_product_id.get(product.id) or by_code.get(code)
            if row is None:
                row = HesabfaItemMapping(
                    product_id=product.id,
                    sku=product.sku,
                    hesabfa_code=code,
                    hesabfa_product_code=str(
                        item.get("ProductCode") or item.get("productCode") or product.sku
                    ),
                    last_synced_at=now,
                )
                db.add(row)
                by_product_id[product.id] = row
                by_code[code] = row
                created += 1
            else:
                row.product_id = product.id
                row.sku = product.sku
                row.hesabfa_code = code
                row.hesabfa_product_code = str(
                    item.get("ProductCode") or item.get("productCode") or product.sku
                )
                row.last_synced_at = now
                updated += 1

        total = int(page.get("TotalCount") or 0)
        skip += len(items)
        if skip >= total or len(items) < page_size:
            break

    await db.flush()
    unmatched = max(0, len(by_sku) - matched)
    logger.info(
        "Hesabfa item mapping sync matched=%s created=%s updated=%s scanned=%s unmatched=%s",
        matched,
        created,
        updated,
        scanned,
        unmatched,
    )
    return ItemMappingSyncResult(
        matched=matched,
        created=created,
        updated=updated,
        scanned_hesabfa=scanned,
        unmatched_site_skus=unmatched,
    )
