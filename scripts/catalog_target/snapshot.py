"""READ-ONLY current-catalog snapshot. Never mutates the database."""

from __future__ import annotations

import csv
import os
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from catalog_target.core import CurrentProduct, canonicalize_brand, normalize_sku, parse_bool, parse_decimal

SNAPSHOT_KIND_LIVE = "live_db"
SNAPSHOT_KIND_FILE = "repository_snapshot_non_live"
SNAPSHOT_KIND_UNAVAILABLE = "unavailable"

SNAPSHOT_REQUIRED_FIELDS = (
    "id",
    "sku",
    "brand_id",
    "brand",
    "category_id",
    "slug",
    "name",
    "base_price",
    "is_active",
    "is_available",
    "deleted_at",
    "primary_image_url",
    "image_count",
)

# Prefer is_primary, then display_order, then id. Never first-by-id alone.
PRIMARY_IMAGE_ORDER_SQL = "pi.is_primary DESC NULLS LAST, pi.display_order ASC NULLS LAST, pi.id ASC"


def select_primary_image_url(images: list[dict[str, Any]]) -> str | None:
    """Pick primary image URL using the same precedence as the snapshot SQL."""
    if not images:
        return None

    def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
        is_primary = row.get("is_primary")
        primary_rank = 0 if is_primary is True else 1
        order_raw = row.get("display_order")
        try:
            order = int(order_raw) if order_raw is not None else 10**9
        except (TypeError, ValueError):
            order = 10**9
        id_raw = row.get("id")
        try:
            image_id = int(id_raw) if id_raw is not None else 10**9
        except (TypeError, ValueError):
            image_id = 10**9
        return primary_rank, order, image_id

    best = sorted(images, key=sort_key)[0]
    url = best.get("image_url")
    return str(url) if url else None


PRODUCTS_SNAPSHOT_SELECT_SQL = f"""
SELECT p.id, p.sku, p.brand_id, b.name AS brand, p.category_id, p.slug, p.name,
       p.base_price, p.is_active, p.is_available, p.deleted_at,
       (
         SELECT COUNT(*) FROM product_images pi WHERE pi.product_id = p.id
       ) AS image_count,
       (
         SELECT pi.image_url FROM product_images pi
         WHERE pi.product_id = p.id
         ORDER BY {PRIMARY_IMAGE_ORDER_SQL}
         LIMIT 1
       ) AS primary_image_url
FROM products p
LEFT JOIN brands b ON b.id = p.brand_id
"""


@dataclass
class SnapshotIntegrity:
    valid: bool = False
    expected_row_count: int | None = None
    observed_row_count: int = 0
    unique_ids: bool = False
    missing_columns: list[str] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    duplicate_skus: list[str] = field(default_factory=list)
    empty_skus: int = 0
    missing_brands: int = 0
    base_price_parse_failures: int = 0
    boolean_parse_failures: int = 0
    image_count_parse_failures: int = 0
    truncation_suspected: bool = False
    problems: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "CURRENT_SITE_SNAPSHOT_VALID": self.valid,
            "expected_row_count": self.expected_row_count,
            "observed_row_count": self.observed_row_count,
            "unique_ids": self.unique_ids,
            "missing_columns": self.missing_columns,
            "duplicate_ids": self.duplicate_ids[:20],
            "duplicate_skus": self.duplicate_skus[:20],
            "empty_skus": self.empty_skus,
            "missing_brands": self.missing_brands,
            "base_price_parse_failures": self.base_price_parse_failures,
            "boolean_parse_failures": self.boolean_parse_failures,
            "image_count_parse_failures": self.image_count_parse_failures,
            "truncation_suspected": self.truncation_suspected,
            "problems": self.problems,
            "stats": self.stats,
        }


def describe_snapshot_phase() -> dict[str, object]:
    """Describe the guarded READ-ONLY snapshot method. Does not connect or mutate."""
    return {
        "status": "prepared_not_run",
        "method": "scripts/catalog_target/snapshot.py:load_current_catalog",
        "read_only": True,
        "production_mutation": "ZERO",
        "production_hosts_refused": True,
        "refuses": [
            "karzartools.com",
            "data/imports/*_products.csv",
            "image-only historical extracts",
        ],
        "required_fields": list(SNAPSHOT_REQUIRED_FIELDS),
        "primary_image_order": "is_primary DESC, display_order ASC, id ASC",
        "cli": (
            "python3 scripts/reconcile_target_catalog.py "
            "--snapshot /path/to/current_catalog.csv"
            " | --read-db (local non-production only)"
        ),
        "CURRENT_SITE_RECONCILIATION_READY": False,
        "APPLY_READY": False,
        "note": "Do not reconcile against an incomplete or image-only historical extract.",
    }


def _is_production_host(host: str) -> bool:
    return "karzartools.com" in (host or "").lower()


def _parse_image_count(raw: Any) -> int | None:
    text = "" if raw is None else str(raw).strip()
    if text == "":
        return None
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def load_snapshot_csv(path: Path, *, label: str = SNAPSHOT_KIND_FILE) -> tuple[list[CurrentProduct], str]:
    products: list[CurrentProduct] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sku = str(row.get("sku") or "").strip()
            brand_raw = str(row.get("brand") or row.get("brand_name") or "").strip()
            products.append(
                CurrentProduct(
                    id=str(row.get("id") or row.get("product_id") or "") or None,
                    sku=sku,
                    normalized_sku=normalize_sku(sku) if sku else "",
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
                    image_count=_parse_image_count(row.get("image_count")),
                    source=label,
                )
            )
    return products, SNAPSHOT_KIND_FILE


def validate_snapshot_csv(
    path: Path,
    *,
    expected_row_count: int | None = None,
) -> SnapshotIntegrity:
    """Refuse incomplete/truncated snapshots before current-site reconciliation."""
    integrity = SnapshotIntegrity(expected_row_count=expected_row_count)
    if not path.is_file():
        integrity.problems.append(f"snapshot_missing:{path}")
        return integrity
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = [c for c in SNAPSHOT_REQUIRED_FIELDS if c not in fieldnames]
        integrity.missing_columns = missing
        if missing:
            integrity.problems.append(f"missing_columns:{','.join(missing)}")
        ids: list[str] = []
        sku_keys: list[str] = []
        active = inactive = deleted = with_sku = without_sku = with_brand = without_brand = 0
        with_images = without_images = 0
        for row in reader:
            integrity.observed_row_count += 1
            pid = str(row.get("id") or "").strip()
            if pid:
                ids.append(pid)
            sku = str(row.get("sku") or "").strip()
            if sku:
                with_sku += 1
                sku_keys.append(normalize_sku(sku))
            else:
                without_sku += 1
                integrity.empty_skus += 1
            brand = str(row.get("brand") or "").strip()
            brand_id = str(row.get("brand_id") or "").strip()
            if brand or brand_id:
                with_brand += 1
            else:
                without_brand += 1
                integrity.missing_brands += 1
            deleted_at = str(row.get("deleted_at") or "").strip()
            if deleted_at:
                deleted += 1
            else:
                active_val = parse_bool(row.get("is_active"))
                if active_val is True:
                    active += 1
                elif active_val is False:
                    inactive += 1
                else:
                    integrity.boolean_parse_failures += 1
            avail = row.get("is_available")
            if str(avail or "").strip() != "" and parse_bool(avail) is None:
                integrity.boolean_parse_failures += 1
            price_raw = str(row.get("base_price") or "").strip()
            if price_raw and parse_decimal(price_raw) is None:
                integrity.base_price_parse_failures += 1
            image_count = _parse_image_count(row.get("image_count"))
            if str(row.get("image_count") or "").strip() != "" and image_count is None:
                integrity.image_count_parse_failures += 1
            elif image_count is not None and image_count > 0:
                with_images += 1
            else:
                without_images += 1
    id_counts = Counter(ids)
    integrity.duplicate_ids = sorted(k for k, n in id_counts.items() if n > 1)
    integrity.unique_ids = not integrity.duplicate_ids and len(ids) == integrity.observed_row_count
    sku_counts = Counter(s for s in sku_keys if s)
    integrity.duplicate_skus = sorted(k for k, n in sku_counts.items() if n > 1)
    if expected_row_count is not None and integrity.observed_row_count != expected_row_count:
        integrity.truncation_suspected = True
        integrity.problems.append(
            f"row_count_mismatch:expected={expected_row_count}:observed={integrity.observed_row_count}"
        )
    if integrity.duplicate_ids:
        integrity.problems.append(f"duplicate_ids:{len(integrity.duplicate_ids)}")
    if integrity.base_price_parse_failures:
        integrity.problems.append(f"base_price_parse_failures:{integrity.base_price_parse_failures}")
    if integrity.boolean_parse_failures:
        integrity.problems.append(f"boolean_parse_failures:{integrity.boolean_parse_failures}")
    if integrity.image_count_parse_failures:
        integrity.problems.append(f"image_count_parse_failures:{integrity.image_count_parse_failures}")
    integrity.stats = {
        "total": integrity.observed_row_count,
        "active": active,
        "inactive": inactive,
        "deleted": deleted,
        "with_sku": with_sku,
        "without_sku": without_sku,
        "with_brand": with_brand,
        "without_brand": without_brand,
        "with_images": with_images,
        "without_images": without_images,
        "duplicate_sku_groups": len(integrity.duplicate_skus),
    }
    integrity.valid = not integrity.problems and not missing
    return integrity


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

    sql = PRODUCTS_SNAPSHOT_SELECT_SQL
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
                        normalized_sku=normalize_sku(sku) if sku else "",
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
