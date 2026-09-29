#!/usr/bin/env python3
"""Read-only forensic identity audit for three Hesabfa ambiguity cases.

Reads Production PostgreSQL in a read-only transaction and Hesabfa
``item/getItems`` only. Does not insert, update, or delete anything.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.db.models.hesabfa import HesabfaItemMapping
from app.db.models.product import Brand, Category, Product
from app.domain.product_naming import normalize_persian_text
from app.services.hesabfa.activation_reconcile import (
    DryRunHesabfaClient,
    DryRunSession,
    enforce_database_read_only,
    parse_remote_active,
    release_database_read_only,
)
from app.services.hesabfa.client import get_hesabfa_client, hesabfa_integration_active
from app.services.hesabfa.item_push import paginate_get_items
from app.services.hesabfa.mapping import _normalize_sku
from sqlalchemy import func, or_, select

TARGETS = (
    {
        "site_product_id": 1627,
        "sku": "6112-1287",
        "previous_reason": "duplicate_remote_product_code",
    },
    {
        "site_product_id": 2297,
        "sku": "103-143",
        "previous_reason": "duplicate_remote_product_code",
    },
    {
        "site_product_id": 3685,
        "sku": "4824-16",
        "previous_reason": "mapping_code_mismatch",
        "prior_mapped_code": "000893",
    },
)
PRIOR_CODES = ("000893",)


def _name_relation(local_name: str, remote_name: str) -> str:
    left = normalize_persian_text(local_name).casefold()
    right = normalize_persian_text(remote_name).casefold()
    if not left or not right:
        return "missing"
    if left == right:
        return "exact_normalized"
    if left in right or right in left:
        return "contains"
    return "different"


def _price_flags(item: dict[str, Any]) -> dict[str, bool]:
    def present(value: object) -> bool:
        return value is not None and value != ""

    def nonzero(value: object) -> bool:
        if not present(value):
            return False
        try:
            return float(value) != 0.0
        except (TypeError, ValueError):
            return False

    buy = item["BuyPrice"] if "BuyPrice" in item else item.get("buyPrice")
    sell = item["SellPrice"] if "SellPrice" in item else item.get("sellPrice")
    return {
        "buy_price_present": present(buy),
        "buy_price_nonzero": nonzero(buy),
        "sell_price_present": present(sell),
        "sell_price_nonzero": nonzero(sell),
    }


def _node_family(item: dict[str, Any]) -> dict[str, str] | str | None:
    raw = item.get("NodeFamily") if "NodeFamily" in item else item.get("nodeFamily")
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return {
            "code": str(raw.get("Code") or raw.get("code") or ""),
            "name": str(raw.get("Name") or raw.get("name") or "")[:200],
        }
    return str(raw)[:200]


def _remote_view(item: dict[str, Any]) -> dict[str, Any]:
    code = str(item.get("Code") or item.get("code") or "").strip()
    product_code = str(item.get("ProductCode") or item.get("productCode") or "").strip()
    name = str(item.get("Name") or item.get("name") or "")
    unit = item.get("Unit") if "Unit" in item else item.get("unit")
    item_type = item.get("ItemType") if "ItemType" in item else item.get("itemType")
    view: dict[str, Any] = {
        "Code": code,
        "ProductCode": product_code,
        "Name": name[:300],
        "Active": parse_remote_active(item),
        "itemType": item_type,
        "unit": None if unit is None else str(unit)[:80],
        "nodeFamily": _node_family(item),
        **_price_flags(item),
    }
    for key in ("Date", "ModifiedDate", "LastUpdate", "UpdateDate"):
        if key in item and item[key] not in (None, ""):
            view[key] = str(item[key])[:40]
    return view


def _codes_equivalent(left: str, right: str) -> str:
    a = left.strip()
    b = right.strip()
    if a == b:
        return "exact"
    if a.isdigit() and b.isdigit() and int(a) == int(b):
        return "numeric_equal_format_differs"
    return "different"


async def _breadcrumb(session: Any, category_id: int | None) -> list[dict[str, Any]]:
    if category_id is None:
        return []
    rows = (await session.execute(select(Category.id, Category.parent_id, Category.name))).all()
    by_id = {int(row.id): row for row in rows}
    chain: list[dict[str, Any]] = []
    seen: set[int] = set()
    current: int | None = int(category_id)
    while current is not None and current not in seen:
        seen.add(current)
        row = by_id.get(current)
        if row is None:
            break
        chain.append({"id": int(row.id), "name": str(row.name)})
        current = int(row.parent_id) if row.parent_id is not None else None
    chain.reverse()
    return chain


async def _local_facts(guard: DryRunSession) -> dict[str, Any]:
    ids = [int(row["site_product_id"]) for row in TARGETS]
    skus = [_normalize_sku(str(row["sku"])) for row in TARGETS]
    products = (
        await guard.execute(
            select(
                Product.id,
                Product.sku,
                Product.name,
                Product.brand_id,
                Product.category_id,
                Product.is_active,
                Product.is_available,
                Product.deleted_at,
                Product.base_price,
            ).where(or_(Product.id.in_(ids), func.upper(Product.sku).in_(skus)))
        )
    ).all()
    brand_ids = {int(row.brand_id) for row in products if row.brand_id is not None}
    brands: dict[int, str] = {}
    if brand_ids:
        brand_rows = (
            await guard.execute(select(Brand.id, Brand.name).where(Brand.id.in_(brand_ids)))
        ).all()
        brands = {int(row.id): str(row.name) for row in brand_rows}
    product_views = []
    for row in products:
        product_views.append(
            {
                "product_id": int(row.id),
                "sku": str(row.sku),
                "name": str(row.name),
                "brand_id": None if row.brand_id is None else int(row.brand_id),
                "brand_name": None if row.brand_id is None else brands.get(int(row.brand_id)),
                "category_id": None if row.category_id is None else int(row.category_id),
                "category_breadcrumb": await _breadcrumb(
                    guard, None if row.category_id is None else int(row.category_id)
                ),
                "is_active": bool(row.is_active),
                "is_available": bool(row.is_available),
                "deleted_at": None if row.deleted_at is None else row.deleted_at.isoformat(),
                "price_present": row.base_price is not None,
            }
        )
    mappings = (
        await guard.execute(
            select(HesabfaItemMapping).where(
                or_(
                    HesabfaItemMapping.product_id.in_(ids),
                    func.upper(HesabfaItemMapping.sku).in_(skus),
                    func.upper(func.coalesce(HesabfaItemMapping.hesabfa_product_code, "")).in_(skus),
                    HesabfaItemMapping.hesabfa_code.in_(PRIOR_CODES),
                )
            )
        )
    ).scalars().all()
    mapping_views = [
        {
            "mapping_id": int(row.id),
            "product_id": int(row.product_id),
            "sku": str(row.sku),
            "hesabfa_code": str(row.hesabfa_code),
            "hesabfa_product_code": row.hesabfa_product_code,
            "last_synced_at": None
            if row.last_synced_at is None
            else row.last_synced_at.isoformat(),
        }
        for row in mappings
    ]
    return {"products": product_views, "mappings": mapping_views}


async def _ownership(guard: DryRunSession, codes: set[str], product_codes: set[str]) -> list[dict[str, Any]]:
    if not codes and not product_codes:
        return []
    clauses = []
    if codes:
        clauses.append(HesabfaItemMapping.hesabfa_code.in_(sorted(codes)))
    if product_codes:
        clauses.append(func.upper(HesabfaItemMapping.sku).in_(sorted(product_codes)))
        clauses.append(
            func.upper(func.coalesce(HesabfaItemMapping.hesabfa_product_code, "")).in_(
                sorted(product_codes)
            )
        )
    mapping_rows = (
        await guard.execute(select(HesabfaItemMapping).where(or_(*clauses)))
    ).scalars().all()
    product_rows = []
    if product_codes:
        product_rows = (
            await guard.execute(
                select(Product.id, Product.sku, Product.name, Product.deleted_at).where(
                    func.upper(Product.sku).in_(sorted(product_codes))
                )
            )
        ).all()
    owners = [
        {
            "kind": "mapping",
            "mapping_id": int(row.id),
            "product_id": int(row.product_id),
            "sku": str(row.sku),
            "hesabfa_code": str(row.hesabfa_code),
            "hesabfa_product_code": row.hesabfa_product_code,
        }
        for row in mapping_rows
    ]
    owners.extend(
        {
            "kind": "product",
            "product_id": int(row.id),
            "sku": str(row.sku),
            "name": str(row.name),
            "deleted_at": None if row.deleted_at is None else row.deleted_at.isoformat(),
        }
        for row in product_rows
    )
    return owners


async def run_audit() -> dict[str, Any]:
    if not hesabfa_integration_active():
        raise SystemExit("FATAL: Hesabfa read credentials are not active")
    from app.db.database import async_session_maker

    async with async_session_maker() as session:
        guard = DryRunSession(session)
        mode = await enforce_database_read_only(guard)
        local = await _local_facts(guard)
        client = DryRunHesabfaClient(get_hesabfa_client())
        pages = await paginate_get_items(client, page_size=100)
        wanted = {_normalize_sku(str(row["sku"])) for row in TARGETS}
        wanted_codes = {code.strip() for code in PRIOR_CODES}
        remote_hits: list[dict[str, Any]] = []
        seen_codes: set[str] = set()
        for item in pages.items:
            view = _remote_view(dict(item))
            code = view["Code"]
            if code:
                if code in seen_codes:
                    raise SystemExit(f"FATAL: duplicate remote Code {code}")
                seen_codes.add(code)
            product_code = _normalize_sku(view["ProductCode"])
            code_hit = any(_codes_equivalent(code, prior) != "different" for prior in wanted_codes)
            if product_code in wanted or code_hit:
                view["product_code_normalized"] = product_code
                view["matches_prior_code_000893"] = _codes_equivalent(code, "000893")
                remote_hits.append(view)
        codes = {row["Code"] for row in remote_hits if row["Code"]}
        codes.update(wanted_codes)
        product_codes = {_normalize_sku(row["ProductCode"]) for row in remote_hits if row["ProductCode"]}
        product_codes.update(wanted)
        ownership = await _ownership(guard, codes, product_codes)
        database_writes = guard.database_writes
        await release_database_read_only(guard, mode)
    if client.remote_writes != 0 or database_writes != 0:
        raise SystemExit(
            f"FATAL: writes remote={client.remote_writes} database={database_writes}"
        )
    if len(pages.items) != pages.reported_total:
        raise SystemExit("FATAL: pagination incomplete")
    if not str(mode).startswith("postgresql:transaction_read_only=on"):
        raise SystemExit(f"FATAL: read-only mode {mode}")
    return {
        "DATABASE_WRITES": database_writes,
        "REMOTE_WRITES": client.remote_writes,
        "DATABASE_READ_ONLY": mode,
        "HESABFA_REPORTED_TOTAL": pages.reported_total,
        "HESABFA_ITEMS_FETCHED": len(pages.items),
        "HESABFA_PAGES_FETCHED": pages.pages_fetched,
        "PAGINATION_COMPLETE": True,
        "DUPLICATE_REMOTE_CODE": 0,
        "local": local,
        "remote_candidates": remote_hits,
        "ownership": ownership,
        "mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = asyncio.run(run_audit())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "facts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "DATABASE_WRITES": payload["DATABASE_WRITES"],
                "REMOTE_WRITES": payload["REMOTE_WRITES"],
                "DATABASE_READ_ONLY": payload["DATABASE_READ_ONLY"],
                "HESABFA_REPORTED_TOTAL": payload["HESABFA_REPORTED_TOTAL"],
                "HESABFA_ITEMS_FETCHED": payload["HESABFA_ITEMS_FETCHED"],
                "HESABFA_PAGES_FETCHED": payload["HESABFA_PAGES_FETCHED"],
                "PAGINATION_COMPLETE": payload["PAGINATION_COMPLETE"],
                "REMOTE_CANDIDATES": len(payload["remote_candidates"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
