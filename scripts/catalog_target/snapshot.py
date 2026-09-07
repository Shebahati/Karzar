"""READ-ONLY current-catalog snapshot. Never mutates the database."""

from __future__ import annotations

import csv
import os
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from catalog_target.core import CurrentProduct, canonicalize_brand, normalize_sku, parse_bool, parse_decimal

SNAPSHOT_KIND_LIVE = "live_db"
SNAPSHOT_KIND_FILE = "repository_snapshot_non_live"
SNAPSHOT_KIND_UNAVAILABLE = "unavailable"


def _is_production_host(host: str) -> bool:
    return "karzartools.com" in (host or "").lower()


def load_snapshot_csv(path: Path, *, label: str = SNAPSHOT_KIND_FILE) -> tuple[list[CurrentProduct], str]:
    products: list[CurrentProduct] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sku = str(row.get("sku") or "").strip()
            if not sku:
                continue
            brand_raw = str(row.get("brand") or row.get("brand_name") or "").strip()
            products.append(
                CurrentProduct(
                    id=str(row.get("id") or row.get("product_id") or "") or None,
                    sku=sku,
                    normalized_sku=normalize_sku(sku),
                    slug=str(row.get("slug") or row.get("product_slug") or "") or None,
                    name=str(row.get("name") or row.get("product_name") or "") or None,
                    brand_id=str(row.get("brand_id") or "") or None,
                    brand=brand_raw or None,
                    brand_key=canonicalize_brand(brand_raw),
                    category_id=str(row.get("category_id") or "") or None,
                    base_price=parse_decimal(row.get("base_price")),
                    is_active=parse_bool(row.get("is_active") or row.get("product_is_active")),
                    is_available=parse_bool(row.get("is_available") or row.get("product_is_available")),
                    deleted_at=str(row.get("deleted_at") or "") or None,
                    primary_image_url=str(row.get("primary_image_url") or row.get("image_url") or "")
                    or None,
                    image_count=int(row["image_count"]) if str(row.get("image_count") or "").isdigit() else None,
                    source=label,
                )
            )
    return products, SNAPSHOT_KIND_FILE


def load_current_catalog(
    *,
    snapshot_path: str | Path | None = None,
    read_db: bool = False,
    env: dict[str, str] | None = None,
) -> tuple[list[CurrentProduct], str, str]:
    """Return (products, evidence_kind, note). Never writes."""
    environ = env if env is not None else os.environ
    if snapshot_path:
        path = Path(snapshot_path)
        if not path.is_file():
            return [], SNAPSHOT_KIND_UNAVAILABLE, f"snapshot_missing:{path}"
        products, kind = load_snapshot_csv(path)
        return products, kind, f"file:{path}"

    env_snapshot = environ.get("KARZAR_CURRENT_CATALOG_SNAPSHOT", "").strip()
    if env_snapshot:
        path = Path(env_snapshot)
        if path.is_file():
            products, kind = load_snapshot_csv(path)
            return products, kind, f"env_file:{path}"
        return [], SNAPSHOT_KIND_UNAVAILABLE, f"snapshot_missing:{path}"

    if not read_db:
        return (
            [],
            SNAPSHOT_KIND_UNAVAILABLE,
            "no_live_db_and_no_full_catalog_snapshot; "
            "refusing data/imports/*_products.csv (PDF parse, not site state) "
            "and image-only active-product extracts",
        )

    host = environ.get("POSTGRES_SERVER", "127.0.0.1")
    if _is_production_host(host):
        return [], SNAPSHOT_KIND_UNAVAILABLE, "refused_production_db_host"
    db_url = environ.get("DATABASE_URL", "")
    if db_url and _is_production_host(urlparse(db_url).hostname or ""):
        return [], SNAPSHOT_KIND_UNAVAILABLE, "refused_production_database_url"

    try:
        import psycopg2  # type: ignore
        from psycopg2.extras import RealDictCursor  # type: ignore
    except ImportError:
        return [], SNAPSHOT_KIND_UNAVAILABLE, "psycopg2_unavailable"

    try:
        conn = psycopg2.connect(
            host=host,
            port=int(environ.get("POSTGRES_PORT", "5432")),
            user=environ.get("POSTGRES_USER", "postgres"),
            password=environ.get("POSTGRES_PASSWORD", ""),
            dbname=environ.get("POSTGRES_DB", "karzar_db"),
        )
    except Exception as exc:  # noqa: BLE001
        return [], SNAPSHOT_KIND_UNAVAILABLE, f"db_connect_failed:{exc}"

    sql = """
        SELECT p.id, p.sku, p.slug, p.name, p.brand_id, b.name AS brand,
               p.category_id, p.base_price, p.is_active, p.is_available, p.deleted_at,
               (
                 SELECT COUNT(*) FROM product_images pi WHERE pi.product_id = p.id
               ) AS image_count,
               (
                 SELECT pi.image_url FROM product_images pi
                 WHERE pi.product_id = p.id
                 ORDER BY pi.id
                 LIMIT 1
               ) AS primary_image_url
        FROM products p
        LEFT JOIN brands b ON b.id = p.brand_id
    """
    products: list[CurrentProduct] = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            for row in cur.fetchall():
                brand_raw = str(row.get("brand") or "")
                sku = str(row.get("sku") or "")
                price = row.get("base_price")
                products.append(
                    CurrentProduct(
                        id=str(row.get("id")) if row.get("id") is not None else None,
                        sku=sku,
                        normalized_sku=normalize_sku(sku),
                        slug=row.get("slug"),
                        name=row.get("name"),
                        brand_id=str(row.get("brand_id")) if row.get("brand_id") is not None else None,
                        brand=brand_raw or None,
                        brand_key=canonicalize_brand(brand_raw),
                        category_id=str(row.get("category_id"))
                        if row.get("category_id") is not None
                        else None,
                        base_price=Decimal(str(price)) if price is not None else None,
                        is_active=bool(row.get("is_active")) if row.get("is_active") is not None else None,
                        is_available=bool(row.get("is_available"))
                        if row.get("is_available") is not None
                        else None,
                        deleted_at=str(row["deleted_at"]) if row.get("deleted_at") else None,
                        primary_image_url=row.get("primary_image_url"),
                        image_count=int(row["image_count"]) if row.get("image_count") is not None else None,
                        source=SNAPSHOT_KIND_LIVE,
                    )
                )
    finally:
        conn.close()
    return products, SNAPSHOT_KIND_LIVE, f"local_db:{host}"
