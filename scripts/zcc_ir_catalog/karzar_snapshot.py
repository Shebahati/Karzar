"""READ-ONLY Karzar catalog snapshot loaders.

Public GET against api.karzartools.com is observation only (no POST/PUT/PATCH/DELETE).
Production DB hosts are never opened here; local DB reuse goes through catalog_target.snapshot.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from catalog_target.core import CurrentProduct, canonicalize_brand, normalize_sku, parse_decimal
from catalog_target.snapshot import load_current_catalog
from zcc_ir_catalog import USER_AGENT
from zcc_ir_catalog.normalize import canonicalize_brand as zcc_canonicalize_brand

PUBLIC_API_ORIGIN = "https://api.karzartools.com"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _brand_key(name: str | None) -> str | None:
    return zcc_canonicalize_brand(name) or canonicalize_brand(name)


def products_from_public_json(rows: list[dict[str, Any]], *, source: str) -> list[CurrentProduct]:
    products: list[CurrentProduct] = []
    for row in rows:
        sku = str(row.get("sku") or "").strip()
        brand = row.get("brand") or {}
        brand_name = ""
        brand_id = None
        if isinstance(brand, dict):
            brand_name = str(brand.get("name") or "")
            if brand.get("id") is not None:
                brand_id = str(brand.get("id"))
        category = row.get("category") or {}
        category_id = None
        if isinstance(category, dict) and category.get("id") is not None:
            category_id = str(category["id"])
        thumb = str(row.get("thumbnail") or "") or None
        avail = row.get("availability")
        if isinstance(avail, bool):
            is_available = avail
        else:
            is_available = None
        products.append(
            CurrentProduct(
                id=str(row["id"]) if row.get("id") is not None else None,
                sku=sku,
                normalized_sku=normalize_sku(sku) if sku else "",
                slug=str(row.get("slug") or "") or None,
                name=str(row.get("name") or "") or None,
                brand_id=brand_id,
                brand=brand_name or None,
                brand_key=_brand_key(brand_name),
                category_id=category_id,
                base_price=parse_decimal(row.get("base_price")),
                is_active=True,
                is_available=is_available,
                deleted_at=None,
                primary_image_url=thumb,
                image_count=1 if thumb else 0,
                source=source,
            )
        )
    return products


def load_public_products_json(path: Path) -> list[CurrentProduct]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("data") or []
    return products_from_public_json(rows, source=f"file:{path}")


def _get_json(url: str, opener=None) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"unsupported_url:{url}")
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, method="GET")
    open_fn = opener or urlopen
    with open_fn(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_public_brands(*, opener=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_counts = _get_json(f"{PUBLIC_API_ORIGIN}/api/v1/brands/", opener=opener)
    storefront = _get_json(
        f"{PUBLIC_API_ORIGIN}/api/v1/brands/?storefront_product_counts=true",
        opener=opener,
    )
    return list(all_counts.get("data") or []), list(storefront.get("data") or [])


def fetch_public_categories(*, opener=None) -> list[dict[str, Any]]:
    body = _get_json(f"{PUBLIC_API_ORIGIN}/api/v1/categories/", opener=opener)
    return list(body.get("data") or body if isinstance(body, list) else [])


def fetch_public_brand_products(brand_id: str, *, opener=None, limit: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    skip = 0
    while True:
        url = (
            f"{PUBLIC_API_ORIGIN}/api/v1/products/?brand_id={brand_id}&limit={limit}&skip={skip}"
        )
        body = _get_json(url, opener=opener)
        chunk = list(body.get("data") or [])
        rows.extend(chunk)
        meta = body.get("meta") or {}
        if not meta.get("has_next") or len(chunk) < limit:
            break
        skip += limit
        if skip > 20_000:
            break
    return rows


def load_karzar_snapshot(
    *,
    snapshot_csv: str | None = None,
    products_json: str | None = None,
    read_db: bool = False,
    fetch_public: bool = False,
    opener=None,
) -> tuple[list[CurrentProduct], dict[str, Any]]:
    meta: dict[str, Any] = {
        "read_only": True,
        "production_db_mutation": False,
        "scope": None,
        "provenance": None,
        "brands": {},
        "categories_count": None,
    }
    if products_json:
        path = Path(products_json)
        products = load_public_products_json(path)
        meta["scope"] = "file_public_json"
        meta["provenance"] = f"file:{path}"
        return products, meta
    if snapshot_csv:
        products, kind, note = load_current_catalog(snapshot_path=snapshot_csv, read_db=False)
        # Re-key brands through zcc aliases so ZCC.CT matches source.
        remapped = []
        for product in products:
            remapped.append(
                CurrentProduct(
                    **{
                        **product.__dict__,
                        "brand_key": _brand_key(product.brand) or product.brand_key,
                    }
                )
            )
        meta["scope"] = kind
        meta["provenance"] = note
        return remapped, meta
    if read_db:
        products, kind, note = load_current_catalog(read_db=True)
        remapped = []
        for product in products:
            remapped.append(
                CurrentProduct(
                    **{
                        **product.__dict__,
                        "brand_key": _brand_key(product.brand) or product.brand_key,
                    }
                )
            )
        meta["scope"] = kind
        meta["provenance"] = note
        return remapped, meta
    if fetch_public:
        all_brands, storefront_brands = fetch_public_brands(opener=opener)
        meta["brands"] = {
            "all_counts": {b.get("name"): {"id": b.get("id"), "product_count": b.get("product_count")} for b in all_brands},
            "storefront_counts": {
                b.get("name"): {"id": b.get("id"), "product_count": b.get("product_count")}
                for b in storefront_brands
            },
        }
        wanted_ids = []
        for brand in all_brands:
            key = _brand_key(str(brand.get("name") or ""))
            if key in {"ZCC.CT", "SAN OU", "STC"}:
                wanted_ids.append(str(brand.get("id")))
        rows: list[dict[str, Any]] = []
        for brand_id in wanted_ids:
            rows.extend(fetch_public_brand_products(brand_id, opener=opener))
        try:
            cats = fetch_public_categories(opener=opener)
            meta["categories_count"] = len(cats)
            meta["categories"] = cats
        except Exception as exc:  # noqa: BLE001
            meta["categories_error"] = str(exc)
        products = products_from_public_json(rows, source="public_api_storefront")
        meta["scope"] = "public_api_storefront"
        meta["provenance"] = (
            "GET https://api.karzartools.com/api/v1/products/?brand_id=… "
            "(anonymous storefront catalog; inactive/non-public SKUs not included)"
        )
        return products, meta
    return [], {**meta, "scope": "unavailable", "provenance": "no_snapshot_configured"}
