"""Push site products into Hesabfa as item shells (stock/qty = 0).

Site remains source of truth for catalog/prices. Hesabfa receives the item
record so warehouse quantities can be managed only there.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.db.models.hesabfa import HesabfaItemMapping
from app.db.models.product import Product
from app.services.hesabfa.client import HesabfaClient, get_hesabfa_client, hesabfa_integration_active
from app.services.hesabfa.exceptions import HesabfaError
from app.services.hesabfa.mapping import _normalize_sku

logger = get_logger(__name__)

ITEM_TYPE_PRODUCT = 0

STOCK_UNIT_FA = {
    "piece": "عدد",
    "kg": "کیلوگرم",
    "meter": "متر",
    "pack": "بسته",
}


@dataclass(frozen=True)
class ItemPushResult:
    created: int
    updated: int
    skipped: int
    errors: int
    error_samples: tuple[str, ...] = ()


def _unit_label(product: Product) -> str:
    raw = product.stock_unit.value if hasattr(product.stock_unit, "value") else str(product.stock_unit)
    return STOCK_UNIT_FA.get(raw, "عدد")


def build_hesabfa_item_payload(
    product: Product,
    *,
    hesabfa_code: str | None = None,
) -> dict[str, Any]:
    """Build item/save body. Does not set opening stock (defaults to 0 in Hesabfa)."""
    item: dict[str, Any] = {
        "name": product.name[:200],
        "itemType": ITEM_TYPE_PRODUCT,
        "productCode": product.sku,
        "unit": _unit_label(product),
        "active": bool(product.is_active),
        "sellPrice": 0.0,
        "buyPrice": 0,
        "tag": f"karzar:{product.id}",
        "description": (product.description or "")[:500],
    }
    if hesabfa_code:
        item["code"] = hesabfa_code
    return item


async def _find_hesabfa_item_by_product_code(
    client: HesabfaClient, sku: str
) -> dict[str, Any] | None:
    normalized = _normalize_sku(sku)
    if not normalized:
        return None
    page = await client.get_items(
        take=20,
        skip=0,
        filters=[
            {
                "Property": "ProductCode",
                "Operator": 1,
                "Value": sku,
            }
        ],
    )
    for item in page.get("List") or []:
        code = _normalize_sku(str(item.get("ProductCode") or item.get("productCode") or ""))
        if code == normalized:
            return item
    if not (page.get("List") or []):
        page = await client.get_items(take=100, skip=0)
        for item in page.get("List") or []:
            code = _normalize_sku(str(item.get("ProductCode") or item.get("productCode") or ""))
            if code == normalized:
                return item
    return None


async def ensure_product_in_hesabfa(
    db: AsyncSession,
    product: Product,
    *,
    client: HesabfaClient | None = None,
) -> HesabfaItemMapping | None:
    """Create or link Hesabfa item for one product. Idempotent by SKU/ProductCode."""
    if not hesabfa_integration_active():
        return None
    if product.deleted_at is not None:
        return None

    api = client or get_hesabfa_client()
    existing = (
        await db.execute(
            select(HesabfaItemMapping).where(HesabfaItemMapping.product_id == product.id)
        )
    ).scalar_one_or_none()

    hesabfa_code = existing.hesabfa_code if existing else None
    if hesabfa_code is None:
        remote = await _find_hesabfa_item_by_product_code(api, product.sku)
        if remote:
            hesabfa_code = str(remote.get("Code") or remote.get("code") or "").strip() or None

    payload = build_hesabfa_item_payload(product, hesabfa_code=hesabfa_code)
    saved = await api.save_item(payload)
    code = str(saved.get("Code") or saved.get("code") or hesabfa_code or "").strip()
    product_code = str(
        saved.get("ProductCode") or saved.get("productCode") or product.sku
    ).strip()
    if not code:
        raise HesabfaError(f"Hesabfa item/save returned no Code for sku={product.sku}")

    now = datetime.now(UTC)
    if existing is None:
        existing = HesabfaItemMapping(
            product_id=product.id,
            sku=product.sku,
            hesabfa_code=code,
            hesabfa_product_code=product_code,
            last_stock=None,
            last_synced_at=now,
        )
        db.add(existing)
    else:
        existing.sku = product.sku
        existing.hesabfa_code = code
        existing.hesabfa_product_code = product_code
        existing.last_synced_at = now

    await db.flush()
    logger.info(
        "Hesabfa item ensured product_id=%s sku=%s hesabfa_code=%s",
        product.id,
        product.sku,
        code,
    )
    return existing


async def push_all_site_products_to_hesabfa(
    db: AsyncSession,
    *,
    client: HesabfaClient | None = None,
    limit: int | None = None,
) -> ItemPushResult:
    """Backfill: upsert every active site product into Hesabfa (stock left at 0)."""
    api = client or get_hesabfa_client()
    stmt = (
        select(Product)
        .where(Product.deleted_at.is_(None))
        .options(selectinload(Product.category), selectinload(Product.brand))
        .order_by(Product.id.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    products = (await db.execute(stmt)).scalars().all()

    created = updated = skipped = errors = 0
    samples: list[str] = []

    existing_rows = (await db.execute(select(HesabfaItemMapping))).scalars().all()
    by_product = {row.product_id: row for row in existing_rows}

    for product in products:
        had_mapping = product.id in by_product
        try:
            mapping = await ensure_product_in_hesabfa(db, product, client=api)
            if mapping is None:
                skipped += 1
                continue
            by_product[product.id] = mapping
            if had_mapping:
                updated += 1
            else:
                created += 1
            await db.commit()
        except Exception as exc:
            await db.rollback()
            errors += 1
            msg = f"sku={product.sku} id={product.id}: {exc}"
            if len(samples) < 10:
                samples.append(msg)
            logger.exception("Hesabfa backfill failed for %s", product.sku)

    return ItemPushResult(
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
        error_samples=tuple(samples),
    )
