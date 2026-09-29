"""Push site products into Hesabfa as item shells (quantity fields omitted).

Site remains source of truth for catalog publication and prices. Hesabfa
receives the accounting item so warehouse quantities stay there.

The website publication lifecycle and Hesabfa accounting item lifecycle are
intentionally independent: item shells are kept active regardless of site
``is_active`` / ``is_available``.
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
from app.services.hesabfa.client import (
    HesabfaClient,
    get_hesabfa_client,
    hesabfa_integration_active,
)
from app.services.hesabfa.exceptions import HesabfaError
from app.services.hesabfa.item_lifecycle import hesabfa_item_should_be_active
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
    """Build item/save body for a catalog item shell.

    Does not send opening stock or warehouse quantity. Hesabfa may default a
    brand-new item's quantity to 0; this payload omits those fields so the
    integration does not overwrite warehouse counts.

    This helper builds a **create** body only. ``buyPrice`` and ``sellPrice``
    are shell zeros for a brand-new item. Passing an existing Hesabfa ``code``
    is refused: an activation-only save must not overwrite an item whose
    price-preserving update semantics are unproven.

    ``active`` comes only from :func:`hesabfa_item_should_be_active`. The
    website publication lifecycle and Hesabfa accounting item lifecycle are
    intentionally independent: site ``is_active``, ``is_available``, price,
    and stock do not change this flag. Desired active state is not permission
    to save an existing item.
    """
    if hesabfa_code:
        raise HesabfaError(
            "refusing item/save payload for existing Hesabfa code "
            f"{hesabfa_code}: price-preserving update is unproven"
        )
    item: dict[str, Any] = {
        "name": product.name[:200],
        "itemType": ITEM_TYPE_PRODUCT,
        "productCode": product.sku,
        "unit": _unit_label(product),
        "active": hesabfa_item_should_be_active(product),
        "sellPrice": 0.0,
        "buyPrice": 0,
        "tag": f"karzar:{product.id}",
        "description": (product.description or "")[:500],
    }
    return item


def _exact_product_code_matches(
    items: list[dict[str, Any]], normalized: str
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for item in items:
        code = _normalize_sku(str(item.get("ProductCode") or item.get("productCode") or ""))
        if code == normalized:
            matches.append(item)
    return matches


def _require_unique_product_code_match(
    matches: list[dict[str, Any]], sku: str
) -> dict[str, Any] | None:
    """Fail closed when more than one Hesabfa item shares ProductCode."""
    if len(matches) > 1:
        raise HesabfaError(
            f"ambiguous Hesabfa ProductCode sku={sku} matches={len(matches)}"
        )
    if len(matches) == 1:
        return matches[0]
    return None


@dataclass(frozen=True)
class HesabfaItemPages:
    """Complete item/getItems read. ``items`` length equals ``reported_total``."""

    items: tuple[dict[str, Any], ...]
    reported_total: int
    pages_fetched: int


async def paginate_get_items(
    client: Any, *, page_size: int = 100
) -> HesabfaItemPages:
    """Read every Hesabfa item via item/getItems.

    Stops only when fetched rows equal reported TotalCount. A short page or a
    missing TotalCount is an error, not proof that later ProductCodes are absent.
    """
    if page_size < 1:
        raise HesabfaError("item/getItems page_size must be >= 1")
    items: list[dict[str, Any]] = []
    skip = 0
    pages = 0
    reported: int | None = None
    seen_pages: set[tuple[tuple[str, str], ...]] = set()
    seen_codes: set[str] = set()
    while True:
        page = await client.get_items(take=page_size, skip=skip)
        if not isinstance(page, dict):
            raise HesabfaError("item/getItems returned a non-object page")
        if page.get("TotalCount") is None:
            raise HesabfaError("item/getItems omitted TotalCount")
        total = int(page["TotalCount"])
        if reported is None:
            reported = total
        elif total != reported:
            raise HesabfaError(
                f"item/getItems TotalCount changed from {reported} to {total}"
            )
        batch = [dict(item) for item in (page.get("List") or [])]
        pages += 1
        if not batch:
            break
        fingerprint = tuple(
            (
                str(item.get("Code") or item.get("code") or "").strip(),
                str(item.get("ProductCode") or item.get("productCode") or "").strip(),
            )
            for item in batch
        )
        if fingerprint in seen_pages:
            raise HesabfaError(
                f"item/getItems pagination repeated a page skip={skip} pages={pages}"
            )
        seen_pages.add(fingerprint)
        for item in batch:
            code = str(item.get("Code") or item.get("code") or "").strip()
            if not code:
                continue
            if code in seen_codes:
                raise HesabfaError(f"item/getItems duplicate remote Code {code}")
            seen_codes.add(code)
        items.extend(batch)
        skip += len(batch)
        if skip >= total or len(batch) < page_size:
            break
        if pages > 100000:
            raise HesabfaError("item/getItems pagination did not terminate")
    if reported is None:
        reported = 0
    if len(items) != reported:
        raise HesabfaError(
            "item/getItems pagination incomplete "
            f"fetched={len(items)} TotalCount={reported} pages={pages}"
        )
    return HesabfaItemPages(tuple(items), reported, pages)


async def _find_hesabfa_item_by_product_code(
    client: HesabfaClient, sku: str, *, page_size: int = 100
) -> dict[str, Any] | None:
    """Find ProductCode=SKU by reading the full item list.

    The previous filter-plus-first-100 fallback could report a real item as
    missing when it was past the first page, and could miss a duplicate on a
    later page. Official list filters are not a proven exact ProductCode
    query (the published example uses operator ``*``). Absence is proven only
    after a complete read.
    """
    normalized = _normalize_sku(sku)
    if not normalized:
        return None
    pages = await paginate_get_items(client, page_size=page_size)
    return _require_unique_product_code_match(
        _exact_product_code_matches(list(pages.items), normalized), sku
    )


@dataclass(frozen=True)
class EnsureItemResult:
    """Outcome of ensuring one catalog product has a Hesabfa shell.

    ``existing_item_preserved`` means the remote item was left untouched.
    ``created`` is only for a lookup that proved no ProductCode exists.
    """

    action: str  # created | existing_item_preserved | skipped
    mapping: HesabfaItemMapping | None
    save_performed: bool


@dataclass(frozen=True)
class ItemReconcileResult:
    """Outcome of lookup-first Hesabfa shell reconciliation for one product."""

    action: str  # linked_existing | created | already_mapped | reconciliation_required | skipped
    mapping: HesabfaItemMapping | None
    hesabfa_code: str | None
    save_performed: bool


async def _upsert_local_mapping(
    db: AsyncSession,
    product: Product,
    *,
    code: str,
    product_code: str,
    existing: HesabfaItemMapping | None,
) -> HesabfaItemMapping:
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
    return existing


async def ensure_product_in_hesabfa(
    db: AsyncSession,
    product: Product,
    *,
    client: HesabfaClient | None = None,
) -> EnsureItemResult:
    """Create a new Hesabfa shell, or leave an existing item untouched.

    A local mapping or a remote ProductCode match is an existing item.
    That path does not call ``item/save``, so shell ``buyPrice``/``sellPrice``
    of 0 cannot overwrite accounting prices. Desired ``active=true`` is not
    write authorization.

    ``item/save`` runs only after lookup proves no ProductCode exists, and
    the payload then omits ``code``.
    """
    if not hesabfa_integration_active():
        return EnsureItemResult("skipped", None, False)
    if product.deleted_at is not None:
        # Soft-deleted site rows are not pushed. Skipping means do not touch
        # Hesabfa; it must not deactivate the accounting item.
        return EnsureItemResult("skipped", None, False)

    api = client or get_hesabfa_client()
    existing = (
        await db.execute(
            select(HesabfaItemMapping).where(HesabfaItemMapping.product_id == product.id)
        )
    ).scalar_one_or_none()
    if existing is not None and (existing.hesabfa_code or "").strip():
        logger.info(
            "Hesabfa existing item preserved product_id=%s sku=%s hesabfa_code=%s",
            product.id,
            product.sku,
            existing.hesabfa_code,
        )
        return EnsureItemResult("existing_item_preserved", existing, False)

    remote = await _find_hesabfa_item_by_product_code(api, product.sku)
    if remote is not None:
        code = str(remote.get("Code") or remote.get("code") or "").strip()
        product_code = str(
            remote.get("ProductCode") or remote.get("productCode") or product.sku
        ).strip()
        if not code:
            raise HesabfaError(f"remote item missing Code for sku={product.sku}")
        mapping = await _upsert_local_mapping(
            db,
            product,
            code=code,
            product_code=product_code,
            existing=existing,
        )
        logger.info(
            "Hesabfa existing item linked without save product_id=%s sku=%s hesabfa_code=%s",
            product.id,
            product.sku,
            code,
        )
        return EnsureItemResult("existing_item_preserved", mapping, False)

    payload = build_hesabfa_item_payload(product, hesabfa_code=None)
    if payload.get("code") or payload.get("Code"):
        raise HesabfaError(f"new Hesabfa shell must not send an existing code sku={product.sku}")
    if payload.get("active") is not True:
        raise HesabfaError(f"new Hesabfa item shell must stay active sku={product.sku}")
    saved = await api.save_item(payload)
    code = str(saved.get("Code") or saved.get("code") or "").strip()
    product_code = str(
        saved.get("ProductCode") or saved.get("productCode") or product.sku
    ).strip()
    if not code:
        raise HesabfaError(f"Hesabfa item/save returned no Code for sku={product.sku}")

    mapping = await _upsert_local_mapping(
        db,
        product,
        code=code,
        product_code=product_code,
        existing=existing,
    )
    logger.info(
        "Hesabfa item created product_id=%s sku=%s hesabfa_code=%s",
        product.id,
        product.sku,
        code,
    )
    return EnsureItemResult("created", mapping, True)


async def reconcile_product_item_shell(
    db: AsyncSession,
    product: Product,
    *,
    client: HesabfaClient | None = None,
    allow_save: bool = True,
) -> ItemReconcileResult:
    """Lookup-first reconciliation: link existing remote item without save when possible.

    If a verified remote item already exists for ProductCode=SKU, write/refresh the
    local mapping only. If absent and ``allow_save`` is true, call ``item/save``
    once, re-read by ProductCode, then write the local mapping. Never sets stock.

    Commerce gates (active, available, priced, or non-zero site stock) refuse the
    operation. Those gates limit which draft rows this reconciler may touch; they
    do not set Hesabfa ``active``. A shell that is saved is active.
    """
    if not hesabfa_integration_active():
        return ItemReconcileResult("skipped", None, None, False)
    if product.deleted_at is not None:
        return ItemReconcileResult("skipped", None, None, False)

    # Fail closed on commerce drift for draft reconciliation.
    if product.is_active or product.is_available:
        raise HesabfaError(
            f"refusing reconcile for active/available product id={product.id} sku={product.sku}"
        )
    if product.base_price is not None:
        raise HesabfaError(
            f"refusing reconcile for priced product id={product.id} sku={product.sku}"
        )
    stock = product.stock_quantity
    if stock is not None and float(stock) != 0.0:
        raise HesabfaError(
            f"refusing reconcile for non-zero stock product id={product.id} sku={product.sku}"
        )

    api = client or get_hesabfa_client()
    existing = (
        await db.execute(
            select(HesabfaItemMapping).where(HesabfaItemMapping.product_id == product.id)
        )
    ).scalar_one_or_none()

    remote = await _find_hesabfa_item_by_product_code(api, product.sku)
    if existing is not None and remote is None:
        # A local code with no remote match is not permission to create a
        # second shell or to save zero prices onto the mapped code.
        return ItemReconcileResult(
            "reconciliation_required", existing, existing.hesabfa_code, False
        )
    if remote is not None:
        code = str(remote.get("Code") or remote.get("code") or "").strip()
        product_code = str(
            remote.get("ProductCode") or remote.get("productCode") or product.sku
        ).strip()
        if not code:
            raise HesabfaError(f"remote item missing Code for sku={product.sku}")
        if existing is not None and existing.hesabfa_code == code:
            existing = await _upsert_local_mapping(
                db,
                product,
                code=code,
                product_code=product_code,
                existing=existing,
            )
            return ItemReconcileResult("already_mapped", existing, code, False)
        mapping = await _upsert_local_mapping(
            db,
            product,
            code=code,
            product_code=product_code,
            existing=existing,
        )
        logger.info(
            "Hesabfa item linked without save product_id=%s sku=%s hesabfa_code=%s",
            product.id,
            product.sku,
            code,
        )
        return ItemReconcileResult("linked_existing", mapping, code, False)

    if not allow_save:
        return ItemReconcileResult("skipped", existing, None, False)

    payload = build_hesabfa_item_payload(product, hesabfa_code=None)
    if payload.get("code") or payload.get("Code"):
        raise HesabfaError(
            f"create-missing shell must not send an existing code sku={product.sku}"
        )
    # Operation gates above decide whether this draft shell may be saved.
    # They do not decide Hesabfa activation. The website publication lifecycle
    # and Hesabfa accounting item lifecycle are intentionally independent, so
    # a new shell is active even when the site row is inactive, unavailable,
    # or unpriced. Zero shell prices apply only to this create-missing path
    # after lookup proved no remote ProductCode; they are not an activation
    # update of an existing priced item.
    if payload.get("active") is not True:
        raise HesabfaError(
            f"Hesabfa item shell must stay active sku={product.sku}"
        )
    payload["sellPrice"] = 0.0
    payload["buyPrice"] = 0
    saved = await api.save_item(payload)
    code = str(saved.get("Code") or saved.get("code") or "").strip()
    if not code:
        # Re-read before failing closed — Success path should return Code, but
        # verify remotely once when missing.
        reread = await _find_hesabfa_item_by_product_code(api, product.sku)
        if not reread:
            raise HesabfaError(
                f"Hesabfa item/save returned no Code and re-read miss for sku={product.sku}"
            )
        code = str(reread.get("Code") or reread.get("code") or "").strip()
        product_code = str(
            reread.get("ProductCode") or reread.get("productCode") or product.sku
        ).strip()
    else:
        reread = await _find_hesabfa_item_by_product_code(api, product.sku)
        if not reread:
            raise HesabfaError(
                f"Hesabfa item/save succeeded but re-read miss for sku={product.sku}"
            )
        verified = str(reread.get("Code") or reread.get("code") or "").strip()
        if verified and verified != code:
            raise HesabfaError(
                f"Hesabfa re-read Code mismatch for sku={product.sku}: save={code} read={verified}"
            )
        product_code = str(
            reread.get("ProductCode") or reread.get("productCode") or product.sku
        ).strip()
    if not code:
        raise HesabfaError(f"Hesabfa item/save returned no Code for sku={product.sku}")

    mapping = await _upsert_local_mapping(
        db,
        product,
        code=code,
        product_code=product_code,
        existing=existing,
    )
    logger.info(
        "Hesabfa item created via reconcile product_id=%s sku=%s hesabfa_code=%s",
        product.id,
        product.sku,
        code,
    )
    return ItemReconcileResult("created", mapping, code, True)


async def push_all_site_products_to_hesabfa(
    db: AsyncSession,
    *,
    client: HesabfaClient | None = None,
    limit: int | None = None,
) -> ItemPushResult:
    """Create missing Hesabfa shells. Already mapped items are not saved.

    Population is ``Product.deleted_at IS NULL``. Site ``is_active`` and
    ``is_available`` do not filter this set and do not deactivate Hesabfa.
    An existing mapping or ProductCode is preserved: this function does not
    send shell ``buyPrice``/``sellPrice`` of 0 onto that item.

    This request-scoped backfill is not the activation campaign. Inactive
    remote items stay a reconciliation finding. Activation APPLY stays blocked.
    """
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
            result = await ensure_product_in_hesabfa(db, product, client=api)
            if result.action == "skipped" or result.mapping is None:
                skipped += 1
                continue
            by_product[product.id] = result.mapping
            if result.action == "created":
                created += 1
                await db.commit()
            elif result.save_performed:
                updated += 1
                await db.commit()
            elif not had_mapping:
                # Local link of a remote item that already existed. No item/save.
                await db.commit()
                skipped += 1
            else:
                skipped += 1
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
