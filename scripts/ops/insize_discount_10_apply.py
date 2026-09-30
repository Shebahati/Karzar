#!/usr/bin/env python3
"""INSIZE 10% storefront discount Category B APPLY — Owner-authorized 2026-09-30.

PIPELINE DECLARATION
  Source: CURRENT live products.base_price (post +12% INSIZE update)
  Destination: CR-011 live Postgres (historic name karzar_staging / lathe_postgres)
  Owner: Owner-authorized catalog mutation 2026-09-30
  Validation: brand_id=3 + name match, priced cohort only, stale-price guard,
              fingerprints, idempotency gate on change reason
  Audit Trail: manifests + recovery + product_change_logs (actor NULL) + reports
  Rollback: exact pre-write base_price + original_price restore SQL
            (never divide-by-0.90)

Semantics (existing storefront discount model — no new engine):
  campaign_original_price = pre-mutation base_price
  campaign_sale_price     = quantize(pre-mutation base_price × 0.90, 0.01, ROUND_HALF_UP)
  discount_percent        = derived from base_price/original_price ≈ 10

Safety:
  - CURRENT live priced cohort is the mutation authority (no historical count)
  - Fail closed on identity / cohort / Category B gates
  - Single-transaction APPLY with FOR UPDATE + conditional UPDATE
  - Mutates base_price AND original_price ONLY
  - Preserves prior original_price in rollback manifest
  - No Hesabfa catalog rewrite / deploy / other brands
  - Idempotent: second run with same reason refuses (no 0.90×0.90)

Usage (inside lathe_api on karzar-vps):
  python /tmp/insize_discount_10_apply.py --out-dir /tmp/karzar-insize-discount-10-out
  python /tmp/insize_discount_10_apply.py --out-dir ... --apply \\
      --confirm-owner-authorized-insize-discount-10
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path
from typing import Any

import asyncpg

EXPECTED_HOST = "srv5944957438"
EXPECTED_DB = "karzar_staging"
EXPECTED_CONTAINER = "lathe_postgres"
EXPECTED_BRAND_ID = 3
EXPECTED_BRAND_NAME = "INSIZE | اینسایز"
PRICE_FACTOR = Decimal("0.90")
QUANTUM = Decimal("0.01")
EXPECTED_DELTA_PCT = Decimal("-10.00")
EXPECTED_DISCOUNT_PERCENT = 10
NUMERIC_15_2_MAX = Decimal("9999999999999.99")
CHANGE_REASON = "INSIZE 10% storefront discount owner-authorized 2026-09-30"
ALLOW_ENV = "KARZAR_ALLOW_PRODUCTION_WRITE"
CATEGORY_ENV = "KARZAR_INGESTION_CATEGORY"
ARTIFACT_PREFIX = "INSIZE_DISCOUNT_10"


class Abort(Exception):
    """Fail-closed abort (no COMMIT of production APPLY)."""


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(v))


def _q(price: Decimal) -> Decimal:
    return price.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def proposed_sale_price(old: Decimal) -> Decimal:
    return _q(old * PRICE_FACTOR)


def compute_discount_percent(base: Decimal, original: Decimal) -> int | None:
    if original <= Decimal("0.0") or base >= original:
        return None
    return int(round((1 - base / original) * 100))


def is_priced(row: asyncpg.Record) -> bool:
    if row["base_price"] is None:
        return False
    try:
        return Decimal(str(row["base_price"])) > 0
    except (InvalidOperation, ValueError):
        return False


async def connect_rw() -> asyncpg.Connection:
    user = os.environ.get("POSTGRES_USER", "karzar_staging")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "karzar_staging")
    host = os.environ.get("POSTGRES_SERVER") or os.environ.get("POSTGRES_HOST") or "db"
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    dsn = os.environ.get("AUDIT_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if dsn:
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
        conn = await asyncpg.connect(dsn)
    else:
        conn = await asyncpg.connect(
            user=user, password=password, database=db, host=host, port=port
        )
    return conn


async def prove_identity(conn: asyncpg.Connection) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT current_database() AS db,
               current_user AS usr,
               inet_server_addr()::text AS addr,
               inet_server_port() AS port,
               version() AS ver
        """
    )
    ro = await conn.fetchval("SHOW default_transaction_read_only")
    alembic = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
    return {
        "current_database": row["db"],
        "current_user": row["usr"],
        "inet_server_addr": row["addr"],
        "inet_server_port": row["port"],
        "version": row["ver"],
        "default_transaction_read_only": ro,
        "alembic_revision": alembic,
        "app_env": os.environ.get("APP_ENV"),
        "karzar_data_plane": os.environ.get("KARZAR_DATA_PLANE"),
        "hostname_env": os.environ.get("HOSTNAME"),
        "host_proof": os.environ.get("KARZAR_HOST_PROOF"),
        "container_proof": os.environ.get("KARZAR_CONTAINER_PROOF"),
        "volume_proof": os.environ.get("KARZAR_VOLUME_PROOF"),
        "expected_host": EXPECTED_HOST,
        "expected_db": EXPECTED_DB,
        "git_sha": os.environ.get("KARZAR_GIT_SHA") or os.environ.get("GITHUB_SHA"),
        "utc_timestamp": _utc_iso(),
    }


def identity_ok(identity: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if identity["current_database"] != EXPECTED_DB:
        errs.append(f"database={identity['current_database']} != {EXPECTED_DB}")
    host_proof = (identity.get("host_proof") or "").strip()
    if host_proof != EXPECTED_HOST:
        errs.append(f"host_proof={host_proof!r} != {EXPECTED_HOST}")
    container_proof = (identity.get("container_proof") or "").strip()
    if EXPECTED_CONTAINER not in container_proof:
        errs.append(f"container_proof={container_proof!r} missing {EXPECTED_CONTAINER}")
    volume_proof = (identity.get("volume_proof") or "").strip()
    if "postgres_data" not in volume_proof and "karzar_postgres_data" not in volume_proof:
        errs.append(f"volume_proof={volume_proof!r} missing postgres_data")
    app_env = (identity.get("app_env") or "").lower()
    if app_env and app_env not in {"staging", "production"}:
        errs.append(f"unexpected APP_ENV={app_env}")
    plane = (identity.get("karzar_data_plane") or "").lower()
    if plane == "catalog_staging":
        errs.append("KARZAR_DATA_PLANE=catalog_staging (refusing live APPLY path)")
    return (len(errs) == 0, errs)


async def prove_brand(conn: asyncpg.Connection) -> dict[str, Any]:
    row = await conn.fetchrow(
        "SELECT id, name FROM brands WHERE id = $1",
        EXPECTED_BRAND_ID,
    )
    if row is None:
        return {"ok": False, "errors": [f"brand_id={EXPECTED_BRAND_ID} missing"]}
    name = str(row["name"])
    ok = name == EXPECTED_BRAND_NAME
    return {
        "ok": ok,
        "brand_id": int(row["id"]),
        "brand_name": name,
        "expected_brand_name": EXPECTED_BRAND_NAME,
        "errors": [] if ok else [f"brand_name={name!r} != {EXPECTED_BRAND_NAME!r}"],
    }


async def fetch_insize_live(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT
            p.id,
            p.sku,
            p.name,
            p.slug,
            p.base_price,
            p.original_price,
            p.is_active,
            p.is_available,
            p.deleted_at,
            p.brand_id,
            p.category_id,
            p.product_type_id,
            b.name AS brand_name,
            EXISTS (
                SELECT 1 FROM product_images pi
                WHERE pi.product_id = p.id
                  AND pi.image_url IS NOT NULL
                  AND length(trim(pi.image_url)) > 0
            ) AS has_image
        FROM products p
        JOIN brands b ON b.id = p.brand_id
        WHERE p.deleted_at IS NULL
          AND p.brand_id = $1
          AND b.name = $2
        ORDER BY p.id
        """,
        EXPECTED_BRAND_ID,
        EXPECTED_BRAND_NAME,
    )


def census(rows: list[asyncpg.Record]) -> dict[str, Any]:
    live = len(rows)
    priced_rows = [r for r in rows if is_priced(r)]
    unpriced = live - len(priced_rows)
    prices = [Decimal(str(r["base_price"])) for r in priced_rows]
    active = sum(1 for r in rows if bool(r["is_active"]))
    available = sum(1 for r in rows if bool(r["is_available"]))
    imaged = sum(1 for r in rows if bool(r["has_image"]))
    storefront_visible = sum(
        1 for r in rows if bool(r["is_active"]) and bool(r["has_image"])
    )
    sellable = sum(
        1
        for r in rows
        if bool(r["is_active"])
        and bool(r["is_available"])
        and is_priced(r)
        and bool(r["has_image"])
    )
    orig_null = sum(1 for r in rows if r["original_price"] is None)
    orig_nonnull = live - orig_null
    orig_gt_base = 0
    orig_le_base = 0
    for r in rows:
        if r["original_price"] is None or r["base_price"] is None:
            continue
        o = Decimal(str(r["original_price"]))
        b = Decimal(str(r["base_price"]))
        if o > b:
            orig_gt_base += 1
        else:
            orig_le_base += 1
    priced_orig_nonnull = sum(1 for r in priced_rows if r["original_price"] is not None)
    return {
        "live_insize": live,
        "priced_insize": len(priced_rows),
        "unpriced_insize": unpriced,
        "active": active,
        "available": available,
        "storefront_visible": storefront_visible,
        "sellable": sellable,
        "imaged": imaged,
        "active_priced": sum(1 for r in priced_rows if bool(r["is_active"])),
        "inactive_priced": sum(1 for r in priced_rows if not bool(r["is_active"])),
        "available_priced": sum(1 for r in priced_rows if bool(r["is_available"])),
        "unavailable_priced": sum(1 for r in priced_rows if not bool(r["is_available"])),
        "original_price_null": orig_null,
        "original_price_nonnull": orig_nonnull,
        "original_price_gt_base_price": orig_gt_base,
        "original_price_le_base_price": orig_le_base,
        "priced_with_existing_original_price": priced_orig_nonnull,
        "min_base_price": str(min(prices)) if prices else None,
        "max_base_price": str(max(prices)) if prices else None,
        "sum_base_price": str(sum(prices)) if prices else None,
    }


def validate_priced_cohort(rows: list[asyncpg.Record]) -> dict[str, Any]:
    errors: list[str] = []
    priced = [r for r in rows if is_priced(r)]
    if not priced:
        errors.append("priced cohort is empty — refusing APPLY with zero targets")
    ids = [int(r["id"]) for r in priced]
    if len(ids) != len(set(ids)):
        errors.append("duplicate product ids in priced cohort")
    for r in priced:
        if int(r["brand_id"]) != EXPECTED_BRAND_ID:
            errors.append(f"id={r['id']} brand_id={r['brand_id']}")
        if r["brand_name"] != EXPECTED_BRAND_NAME:
            errors.append(f"id={r['id']} brand_name={r['brand_name']!r}")
        if r["deleted_at"] is not None:
            errors.append(f"id={r['id']} soft-deleted")
        try:
            price = Decimal(str(r["base_price"]))
        except (InvalidOperation, ValueError):
            errors.append(f"id={r['id']} base_price unparsable")
            continue
        if price <= 0:
            errors.append(f"id={r['id']} base_price<=0 ({price})")
            continue
        try:
            sale = proposed_sale_price(price)
        except (InvalidOperation, ValueError) as exc:
            errors.append(f"id={r['id']} arithmetic error: {exc}")
            continue
        if sale >= price:
            errors.append(f"id={r['id']} sale {sale} is not less than old {price}")
        if sale <= 0:
            errors.append(f"id={r['id']} sale {sale} <= 0")
        if sale > NUMERIC_15_2_MAX:
            errors.append(f"id={r['id']} sale {sale} exceeds Numeric(15,2)")
        if sale != _q(price * PRICE_FACTOR):
            errors.append(f"id={r['id']} quantize mismatch")
        disc = compute_discount_percent(sale, price)
        if disc != EXPECTED_DISCOUNT_PERCENT:
            errors.append(
                f"id={r['id']} expected_discount_percent={EXPECTED_DISCOUNT_PERCENT} got={disc}"
            )
    return {
        "ok": not errors,
        "errors": errors,
        "priced_count": len(priced),
        "live_count": len(rows),
    }


def build_manifest(priced_rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for r in priced_rows:
        pre_base = Decimal(str(r["base_price"]))
        post_base = proposed_sale_price(pre_base)
        pre_orig = _dec(r["original_price"])
        post_orig = pre_base  # campaign snapshot = current customer price
        disc = compute_discount_percent(post_base, post_orig)
        manifest.append(
            {
                "product_id": int(r["id"]),
                "sku": str(r["sku"]),
                "name": str(r["name"]),
                "slug": str(r["slug"]) if r["slug"] is not None else None,
                "brand_id": int(r["brand_id"]),
                "brand_name": str(r["brand_name"]),
                "category_id": None if r["category_id"] is None else int(r["category_id"]),
                "product_type_id": (
                    None if r["product_type_id"] is None else int(r["product_type_id"])
                ),
                "pre_base_price": str(pre_base),
                "pre_original_price": None if pre_orig is None else str(pre_orig),
                "computed_post_base_price": str(post_base),
                "computed_post_original_price": str(post_orig),
                "expected_discount_percent": disc,
                "is_active": bool(r["is_active"]),
                "is_available": bool(r["is_available"]),
                "has_image": bool(r["has_image"]),
                "deleted_at": None,
            }
        )
    return manifest


def manifest_stats(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    olds = [Decimal(m["pre_base_price"]) for m in manifest]
    news = [Decimal(m["computed_post_base_price"]) for m in manifest]
    discount_amount = sum(olds) - sum(news) if olds else Decimal("0")
    return {
        "row_count": len(manifest),
        "current_min": str(min(olds)) if olds else None,
        "current_max": str(max(olds)) if olds else None,
        "current_sum": str(sum(olds)) if olds else None,
        "proposed_min": str(min(news)) if news else None,
        "proposed_max": str(max(news)) if news else None,
        "proposed_sum": str(sum(news)) if news else None,
        "absolute_discount_total": str(discount_amount),
        "pre_existing_original_price_nonnull": sum(
            1 for m in manifest if m["pre_original_price"] is not None
        ),
        "active_priced": sum(1 for m in manifest if m["is_active"]),
        "inactive_priced": sum(1 for m in manifest if not m["is_active"]),
        "available_priced": sum(1 for m in manifest if m["is_available"]),
        "unavailable_priced": sum(1 for m in manifest if not m["is_available"]),
    }


def write_manifest_artifacts(
    out_dir: Path, manifest: list[dict[str, Any]], stamp: str
) -> dict[str, Any]:
    csv_path = out_dir / f"{ARTIFACT_PREFIX}_MANIFEST_{stamp}.csv"
    json_path = out_dir / f"{ARTIFACT_PREFIX}_MANIFEST_{stamp}.json"
    sha_path = out_dir / "MANIFEST.sha256"
    fields = [
        "product_id",
        "sku",
        "name",
        "brand_id",
        "brand_name",
        "pre_base_price",
        "pre_original_price",
        "computed_post_base_price",
        "computed_post_original_price",
        "expected_discount_percent",
        "is_active",
        "is_available",
        "has_image",
        "category_id",
        "product_type_id",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in manifest:
            writer.writerow(row)
    payload = {
        "generated_at": _utc_iso(),
        "formula": (
            "computed_post_original_price = pre_base_price; "
            "computed_post_base_price = quantize(pre_base_price * 0.90, 0.01, ROUND_HALF_UP)"
        ),
        "authority": "current_live_priced_cohort",
        "brand_id": EXPECTED_BRAND_ID,
        "brand_name": EXPECTED_BRAND_NAME,
        "change_reason": CHANGE_REASON,
        "stats": manifest_stats(manifest),
        "rows": manifest,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    csv_sha = _sha256_file(csv_path)
    json_sha = _sha256_file(json_path)
    sha_path.write_text(
        f"{csv_sha}  {csv_path.name}\n{json_sha}  {json_path.name}\n",
        encoding="utf-8",
    )
    return {
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "sha_path": str(sha_path),
        "csv_sha256": csv_sha,
        "json_sha256": json_sha,
        "stats": manifest_stats(manifest),
    }


def write_recovery_artifacts(
    out_dir: Path, manifest: list[dict[str, Any]], stamp: str
) -> dict[str, Any]:
    recovery_csv = out_dir / f"{ARTIFACT_PREFIX}_RECOVERY_PREWRITE_{stamp}.csv"
    rollback_sql = out_dir / f"{ARTIFACT_PREFIX}_ROLLBACK_{stamp}.sql"
    fields = [
        "product_id",
        "sku",
        "brand_id",
        "pre_base_price",
        "pre_original_price",
        "computed_post_base_price",
        "computed_post_original_price",
        "is_active",
        "is_available",
        "category_id",
        "product_type_id",
        "name",
    ]
    with recovery_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in manifest:
            writer.writerow(row)

    lines = [
        "-- INSIZE 10% discount rollback — restore EXACT pre-write base_price AND original_price",
        f"-- generated_at={_utc_iso()}",
        f"-- expected_row_count={len(manifest)}",
        "-- DO NOT use divide-by-0.90; values below are captured pre-write.",
        "BEGIN;",
    ]
    for row in manifest:
        sku = str(row["sku"]).replace("'", "''")
        pre_orig = row["pre_original_price"]
        if pre_orig is None:
            orig_sql = "NULL"
        else:
            orig_sql = str(pre_orig)
        lines.append(
            "UPDATE products SET "
            "base_price = {pre_base}, "
            "original_price = {pre_orig}, "
            "updated_at = NOW() "
            "WHERE id = {pid} AND brand_id = {bid} AND deleted_at IS NULL "
            "AND sku = '{sku}' "
            "AND base_price = {post_base} "
            "AND original_price = {post_orig};".format(
                pre_base=row["pre_base_price"],
                pre_orig=orig_sql,
                pid=row["product_id"],
                bid=EXPECTED_BRAND_ID,
                sku=sku,
                post_base=row["computed_post_base_price"],
                post_orig=row["computed_post_original_price"],
            )
        )
    lines.append(f"-- expected_affected={len(manifest)}")
    lines.append("COMMIT;")
    rollback_sql.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "recovery_csv": str(recovery_csv),
        "recovery_csv_sha256": _sha256_file(recovery_csv),
        "rollback_sql": str(rollback_sql),
        "rollback_sql_sha256": _sha256_file(rollback_sql),
    }


async def capture_fingerprints(conn: asyncpg.Connection) -> dict[str, Any]:
    """Fingerprints for isolation gates.

    Non-INSIZE: id + base_price + original_price (must not change).
    INSIZE non-campaign fields: exclude base_price and original_price
    (those are the authorized mutation fields).
    """
    non_insize = await conn.fetch(
        """
        SELECT id, base_price, original_price
        FROM products
        WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM $1
        ORDER BY id
        """,
        EXPECTED_BRAND_ID,
    )
    non_insize_null = sum(1 for r in non_insize if r["base_price"] is None)
    non_insize_hash = _sha256_text(
        "\n".join(
            f"{int(r['id'])}|"
            f"{'' if r['base_price'] is None else str(r['base_price'])}|"
            f"{'' if r['original_price'] is None else str(r['original_price'])}"
            for r in non_insize
        )
    )

    insize_other = await conn.fetch(
        """
        SELECT p.id, p.sku, p.brand_id, p.category_id, p.product_type_id,
               p.is_active, p.is_available, p.deleted_at, p.name, p.slug,
               p.stock_quantity, p.tax_percent
        FROM products p
        JOIN brands b ON b.id = p.brand_id
        WHERE p.deleted_at IS NULL
          AND p.brand_id = $1
          AND b.name = $2
        ORDER BY p.id
        """,
        EXPECTED_BRAND_ID,
        EXPECTED_BRAND_NAME,
    )
    insize_other_hash = _sha256_text(
        "\n".join(
            "|".join(
                [
                    str(int(r["id"])),
                    str(r["sku"]),
                    str(int(r["brand_id"])),
                    "" if r["category_id"] is None else str(int(r["category_id"])),
                    ""
                    if r["product_type_id"] is None
                    else str(int(r["product_type_id"])),
                    str(bool(r["is_active"])).lower(),
                    str(bool(r["is_available"])).lower(),
                    "" if r["deleted_at"] is None else str(r["deleted_at"]),
                    str(r["name"]),
                    "" if r["slug"] is None else str(r["slug"]),
                    "" if r["stock_quantity"] is None else str(r["stock_quantity"]),
                    "" if r["tax_percent"] is None else str(r["tax_percent"]),
                ]
            )
            for r in insize_other
        )
    )

    products_count = await conn.fetchval("SELECT COUNT(*) FROM products")
    images_count = await conn.fetchval("SELECT COUNT(*) FROM product_images")
    return {
        "non_insize_live_count": len(non_insize),
        "non_insize_base_price_null_count": non_insize_null,
        "non_insize_id_price_sha256": non_insize_hash,
        "insize_other_fields_sha256": insize_other_hash,
        "products_count": int(products_count),
        "product_images_count": int(images_count),
    }


async def change_log_idempotency(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch(
        """
        SELECT id, product_id, field_name, old_value, new_value, reason, created_at
        FROM product_change_logs
        WHERE reason = $1
          AND field_name IN ('base_price', 'original_price')
        ORDER BY product_id, field_name, id
        """,
        CHANGE_REASON,
    )
    product_ids = [int(r["product_id"]) for r in rows]
    base_rows = [r for r in rows if r["field_name"] == "base_price"]
    orig_rows = [r for r in rows if r["field_name"] == "original_price"]
    base_pids = [int(r["product_id"]) for r in base_rows]
    orig_pids = [int(r["product_id"]) for r in orig_rows]
    distinct = sorted(set(product_ids))
    base_dupes = sorted({pid for pid in base_pids if base_pids.count(pid) > 1})
    orig_dupes = sorted({pid for pid in orig_pids if orig_pids.count(pid) > 1})
    return {
        "reason": CHANGE_REASON,
        "log_row_count": len(rows),
        "base_price_log_count": len(base_rows),
        "original_price_log_count": len(orig_rows),
        "distinct_product_id_count": len(distinct),
        "duplicate_base_price_product_ids": base_dupes[:50],
        "duplicate_original_price_product_ids": orig_dupes[:50],
        "duplicate_product_id_count": len(set(base_dupes) | set(orig_dupes)),
        "already_present": len(rows) > 0,
    }


async def run_transactional_mutate(
    conn: asyncpg.Connection,
    manifest: list[dict[str, Any]],
    *,
    commit: bool,
) -> dict[str, Any]:
    """Lock allowlist, stale-guard, UPDATE base_price+original_price, change logs."""
    by_id = {int(m["product_id"]): m for m in manifest}
    ids = sorted(by_id.keys())
    result: dict[str, Any] = {
        "commit": commit,
        "target_rows": len(ids),
        "updated_rows": 0,
        "base_price_change_log_rows": 0,
        "original_price_change_log_rows": 0,
        "change_log_rows": 0,
        "status": "STARTED",
    }

    tr = conn.transaction()
    await tr.start()
    try:
        locked = await conn.fetch(
            """
            SELECT p.id, p.sku, p.base_price, p.original_price, p.is_active,
                   p.is_available, p.deleted_at, p.brand_id, p.category_id,
                   p.product_type_id, p.name, p.slug
            FROM products p
            WHERE p.id = ANY($1::int[])
            ORDER BY p.id
            FOR UPDATE
            """,
            ids,
        )
        if len(locked) != len(ids):
            raise Abort(
                f"lock_count_mismatch: locked={len(locked)} expected={len(ids)}"
            )

        for row in locked:
            mid = int(row["id"])
            m = by_id[mid]
            if int(row["brand_id"]) != EXPECTED_BRAND_ID:
                raise Abort(f"stale_brand id={mid}")
            if row["deleted_at"] is not None:
                raise Abort(f"stale_deleted id={mid}")
            live_price = _dec(row["base_price"])
            if live_price is None or live_price != Decimal(m["pre_base_price"]):
                raise Abort(
                    f"stale_base_price id={mid} live={live_price} "
                    f"manifest={m['pre_base_price']}"
                )
            live_orig = _dec(row["original_price"])
            expected_pre_orig = (
                None
                if m["pre_original_price"] is None
                else Decimal(m["pre_original_price"])
            )
            if live_orig != expected_pre_orig:
                raise Abort(
                    f"stale_original_price id={mid} live={live_orig} "
                    f"manifest={m['pre_original_price']}"
                )
            if str(row["sku"]) != m["sku"]:
                raise Abort(f"stale_sku id={mid}")

        updated = 0
        base_logs = 0
        orig_logs = 0
        for mid in ids:
            m = by_id[mid]
            status = await conn.execute(
                """
                UPDATE products
                SET base_price = $1::numeric,
                    original_price = $2::numeric,
                    updated_at = NOW()
                WHERE id = $3
                  AND brand_id = $4
                  AND deleted_at IS NULL
                  AND base_price = $5::numeric
                  AND original_price IS NOT DISTINCT FROM $6::numeric
                """,
                Decimal(m["computed_post_base_price"]),
                Decimal(m["computed_post_original_price"]),
                mid,
                EXPECTED_BRAND_ID,
                Decimal(m["pre_base_price"]),
                None
                if m["pre_original_price"] is None
                else Decimal(m["pre_original_price"]),
            )
            n = int(str(status).split()[-1])
            if n != 1:
                raise Abort(f"update_affected id={mid} status={status}")
            updated += 1

            await conn.execute(
                """
                INSERT INTO product_change_logs
                    (product_id, field_name, old_value, new_value, reason, actor_user_id)
                VALUES ($1, 'base_price', $2, $3, $4, NULL)
                """,
                mid,
                m["pre_base_price"],
                m["computed_post_base_price"],
                CHANGE_REASON,
            )
            base_logs += 1

            await conn.execute(
                """
                INSERT INTO product_change_logs
                    (product_id, field_name, old_value, new_value, reason, actor_user_id)
                VALUES ($1, 'original_price', $2, $3, $4, NULL)
                """,
                mid,
                m["pre_original_price"],
                m["computed_post_original_price"],
                CHANGE_REASON,
            )
            orig_logs += 1

        if updated != len(ids):
            raise Abort(f"updated_rows={updated} != {len(ids)}")

        post = await conn.fetch(
            """
            SELECT p.id, p.sku, p.base_price, p.original_price, p.is_active,
                   p.is_available, p.deleted_at, p.brand_id, p.category_id,
                   p.product_type_id, p.name, p.slug
            FROM products p
            WHERE p.id = ANY($1::int[])
            ORDER BY p.id
            """,
            ids,
        )
        if len(post) != len(ids):
            raise Abort("post_read_count_mismatch")

        for row in post:
            m = by_id[int(row["id"])]
            actual_base = _dec(row["base_price"])
            actual_orig = _dec(row["original_price"])
            expected_base = Decimal(m["computed_post_base_price"])
            expected_orig = Decimal(m["computed_post_original_price"])
            if actual_base != expected_base:
                raise Abort(
                    f"post_base_mismatch id={row['id']} actual={actual_base} "
                    f"expected={expected_base}"
                )
            if actual_orig != expected_orig:
                raise Abort(
                    f"post_original_mismatch id={row['id']} actual={actual_orig} "
                    f"expected={expected_orig}"
                )
            old = Decimal(m["pre_base_price"])
            if actual_base != proposed_sale_price(old):
                raise Abort(f"post_formula_mismatch id={row['id']}")
            if actual_orig != old:
                raise Abort(f"post_original_not_pre_base id={row['id']}")
            disc = compute_discount_percent(actual_base, actual_orig)  # type: ignore[arg-type]
            if disc != EXPECTED_DISCOUNT_PERCENT:
                raise Abort(f"post_discount_percent id={row['id']} got={disc}")
            if bool(row["is_active"]) != bool(m["is_active"]):
                raise Abort(f"is_active_mutated id={row['id']}")
            if bool(row["is_available"]) != bool(m["is_available"]):
                raise Abort(f"is_available_mutated id={row['id']}")
            if int(row["brand_id"]) != EXPECTED_BRAND_ID:
                raise Abort(f"brand_mutated id={row['id']}")
            if row["deleted_at"] is not None:
                raise Abort(f"deleted_at_mutated id={row['id']}")
            if str(row["sku"]) != m["sku"]:
                raise Abort(f"sku_mutated id={row['id']}")

        null_prices = sum(1 for row in post if row["base_price"] is None)
        if null_prices:
            raise Abort(f"null_prices_after_update={null_prices}")

        result["updated_rows"] = updated
        result["base_price_change_log_rows"] = base_logs
        result["original_price_change_log_rows"] = orig_logs
        result["change_log_rows"] = base_logs + orig_logs
        result["status"] = "GATES_PASSED"

        if commit:
            await tr.commit()
            result["transaction_status"] = "COMMITTED"
        else:
            await tr.rollback()
            result["transaction_status"] = "ROLLED_BACK_REHEARSAL"
        return result
    except Exception:
        await tr.rollback()
        raise


async def post_commit_verify(
    conn: asyncpg.Connection,
    manifest: list[dict[str, Any]],
    pre_fp: dict[str, Any],
) -> dict[str, Any]:
    rows = await fetch_insize_live(conn)
    by_id = {int(m["product_id"]): m for m in manifest}
    exact_base = 0
    exact_orig = 0
    formula_ok = 0
    discount_ok = 0
    still_old = 0
    compounded = 0
    deltas: list[Decimal] = []
    prices: list[Decimal] = []
    for r in rows:
        mid = int(r["id"])
        if mid not in by_id:
            continue
        m = by_id[mid]
        actual_base = Decimal(str(r["base_price"]))
        actual_orig = (
            None if r["original_price"] is None else Decimal(str(r["original_price"]))
        )
        expected_base = Decimal(m["computed_post_base_price"])
        expected_orig = Decimal(m["computed_post_original_price"])
        pre_base = Decimal(m["pre_base_price"])
        if actual_base == expected_base:
            exact_base += 1
        if actual_orig == expected_orig:
            exact_orig += 1
        if actual_base == pre_base:
            still_old += 1
        # Detect accidental second ×0.90 relative to already-discounted expected
        if actual_base == proposed_sale_price(expected_base):
            compounded += 1
        if actual_base == proposed_sale_price(pre_base) and actual_orig == pre_base:
            formula_ok += 1
        disc = (
            compute_discount_percent(actual_base, actual_orig)
            if actual_orig is not None
            else None
        )
        if disc == EXPECTED_DISCOUNT_PERCENT:
            discount_ok += 1
        if pre_base > 0:
            deltas.append(
                ((actual_base - pre_base) / pre_base * Decimal("100")).quantize(
                    Decimal("0.01")
                )
            )
        prices.append(actual_base)

    post_fp = await capture_fingerprints(conn)
    isolation = {
        "non_insize_mutations": 0
        if post_fp["non_insize_id_price_sha256"] == pre_fp["non_insize_id_price_sha256"]
        else 1,
        "insize_other_field_mutations": 0
        if post_fp["insize_other_fields_sha256"] == pre_fp["insize_other_fields_sha256"]
        else 1,
        "products_count_delta": post_fp["products_count"] - pre_fp["products_count"],
        "product_images_count_delta": post_fp["product_images_count"]
        - pre_fp["product_images_count"],
        "pre_fingerprints": pre_fp,
        "post_fingerprints": post_fp,
    }

    change_logs = await conn.fetch(
        """
        SELECT product_id, field_name, old_value, new_value
        FROM product_change_logs
        WHERE reason = $1
          AND field_name IN ('base_price', 'original_price')
        ORDER BY product_id, field_name, id
        """,
        CHANGE_REASON,
    )
    base_logs = [r for r in change_logs if r["field_name"] == "base_price"]
    orig_logs = [r for r in change_logs if r["field_name"] == "original_price"]
    base_pids = [int(r["product_id"]) for r in base_logs]
    orig_pids = [int(r["product_id"]) for r in orig_logs]
    distinct_logs = sorted(set(base_pids) | set(orig_pids))
    dup_base = sorted({pid for pid in base_pids if base_pids.count(pid) > 1})
    dup_orig = sorted({pid for pid in orig_pids if orig_pids.count(pid) > 1})

    current_matches_log = 0
    base_log_by_pid = {int(r["product_id"]): r for r in base_logs}
    orig_log_by_pid = {int(r["product_id"]): r for r in orig_logs}
    for mid, m in by_id.items():
        blog = base_log_by_pid.get(mid)
        olog = orig_log_by_pid.get(mid)
        if blog is None or olog is None:
            continue
        live = next((r for r in rows if int(r["id"]) == mid), None)
        if live is None:
            continue
        if (
            Decimal(str(live["base_price"])) == Decimal(str(blog["new_value"]))
            and Decimal(str(live["original_price"])) == Decimal(str(olog["new_value"]))
        ):
            current_matches_log += 1

    pre_sum = sum(Decimal(m["pre_base_price"]) for m in manifest)
    post_sum = sum(prices) if prices else Decimal("0")
    discount_amount = pre_sum - post_sum

    target_n = len(manifest)
    ok = (
        exact_base == target_n
        and exact_orig == target_n
        and formula_ok == target_n
        and discount_ok == target_n
        and still_old == 0
        and compounded == 0
        and len(base_logs) == target_n
        and len(orig_logs) == target_n
        and len(distinct_logs) == target_n
        and len(dup_base) == 0
        and len(dup_orig) == 0
        and current_matches_log == target_n
        and isolation["non_insize_mutations"] == 0
        and isolation["insize_other_field_mutations"] == 0
        and isolation["products_count_delta"] == 0
        and isolation["product_images_count_delta"] == 0
        and (
            not deltas
            or (
                min(deltas) == EXPECTED_DELTA_PCT and max(deltas) == EXPECTED_DELTA_PCT
            )
        )
    )
    return {
        "target_rows": target_n,
        "base_price_exact_match": exact_base,
        "original_price_exact_match": exact_orig,
        "formula_matches": formula_ok,
        "discount_percent_10": discount_ok,
        "still_at_old_price": still_old,
        "compounded_0_90_count": compounded,
        "current_matches_logged_new": current_matches_log,
        "change_log_base_price_rows": len(base_logs),
        "change_log_original_price_rows": len(orig_logs),
        "change_log_rows_total": len(change_logs),
        "distinct_changed_product_ids": len(distinct_logs),
        "duplicate_mutations": len(dup_base) + len(dup_orig),
        "pre_min": str(min(Decimal(m["pre_base_price"]) for m in manifest)),
        "pre_max": str(max(Decimal(m["pre_base_price"]) for m in manifest)),
        "pre_sum": str(pre_sum),
        "min": str(min(prices)) if prices else None,
        "max": str(max(prices)) if prices else None,
        "sum": str(post_sum) if prices else None,
        "discount_amount": str(discount_amount),
        "delta_pct_min": str(min(deltas)) if deltas else None,
        "delta_pct_max": str(max(deltas)) if deltas else None,
        "null_price": sum(1 for r in rows if r["base_price"] is None),
        "isolation": isolation,
        "ok": ok,
    }


async def already_applied_verify(conn: asyncpg.Connection) -> dict[str, Any]:
    idemp = await change_log_idempotency(conn)
    logs = await conn.fetch(
        """
        SELECT cl.product_id, cl.field_name, cl.old_value, cl.new_value,
               p.base_price, p.original_price, p.sku,
               p.is_active, p.is_available, p.deleted_at, p.brand_id
        FROM product_change_logs cl
        JOIN products p ON p.id = cl.product_id
        WHERE cl.reason = $1
          AND cl.field_name IN ('base_price', 'original_price')
        ORDER BY cl.product_id, cl.field_name, cl.id
        """,
        CHANGE_REASON,
    )
    base_logs = [r for r in logs if r["field_name"] == "base_price"]
    formula_ok = 0
    current_ok = 0
    discount_ok = 0
    bad_brand = 0
    soft_deleted = 0
    for r in base_logs:
        try:
            old = Decimal(str(r["old_value"]))
            new = Decimal(str(r["new_value"]))
            cur = Decimal(str(r["base_price"])) if r["base_price"] is not None else None
            cur_orig = (
                Decimal(str(r["original_price"]))
                if r["original_price"] is not None
                else None
            )
        except (InvalidOperation, ValueError):
            continue
        if new == proposed_sale_price(old):
            formula_ok += 1
        if cur is not None and cur == new and cur_orig == old:
            current_ok += 1
            if compute_discount_percent(cur, cur_orig) == EXPECTED_DISCOUNT_PERCENT:
                discount_ok += 1
        if int(r["brand_id"]) != EXPECTED_BRAND_ID:
            bad_brand += 1
        if r["deleted_at"] is not None:
            soft_deleted += 1

    live = await fetch_insize_live(conn)
    priced = [r for r in live if is_priced(r)]
    interpretation = "ALREADY_APPLIED_COMPLETE"
    if idemp["duplicate_product_id_count"] > 0:
        interpretation = "ALREADY_APPLIED_PARTIAL_OR_DUPLICATE"
    elif idemp["log_row_count"] == 0:
        interpretation = "NOT_APPLIED"
    elif (
        formula_ok != idemp["base_price_log_count"]
        or current_ok != idemp["base_price_log_count"]
        or idemp["base_price_log_count"] != idemp["original_price_log_count"]
    ):
        interpretation = "ALREADY_APPLIED_PARTIAL_OR_MISMATCH"
    elif idemp["distinct_product_id_count"] != len(priced):
        interpretation = "ALREADY_APPLIED_VERIFY_COHORT_DRIFT"

    return {
        "idempotency": idemp,
        "formula_matches": formula_ok,
        "current_matches_logged_new": current_ok,
        "discount_percent_10": discount_ok,
        "bad_brand_rows": bad_brand,
        "soft_deleted_rows": soft_deleted,
        "live_insize": len(live),
        "priced_insize": len(priced),
        "interpretation": interpretation,
        "census": census(live),
    }


def assert_category_b_for_apply() -> None:
    allow = os.environ.get(ALLOW_ENV, "").strip()
    category = os.environ.get(CATEGORY_ENV, "").strip().upper()
    errs = []
    if allow != "1":
        errs.append(f"set {ALLOW_ENV}=1")
    if category != "B":
        errs.append(f"set {CATEGORY_ENV}=B")
    if errs:
        raise Abort("Category B incomplete: " + "; ".join(errs))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


async def amain(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="INSIZE 10% storefront discount guarded APPLY"
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit production mutation after successful rehearsal",
    )
    parser.add_argument(
        "--confirm-owner-authorized-insize-discount-10",
        action="store_true",
        help="Required with --apply (Owner authorization 2026-09-30)",
    )
    parser.add_argument(
        "--skip-apply-even-if-requested",
        action="store_true",
        help="Force abort of APPLY (safety latch)",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    report: dict[str, Any] = {
        "STATUS": "ABORTED_NO_MUTATION",
        "generated_at": _utc_iso(),
        "stamp": stamp,
        "formula": (
            "original_price = pre_base_price; "
            "base_price = quantize(pre_base_price * 0.90, 0.01, ROUND_HALF_UP)"
        ),
        "change_reason": CHANGE_REASON,
        "semantics_proof": {
            "base_price": "final customer-facing sale price (docs/COMMERCE.md)",
            "original_price": "strike-through / pre-discount list price",
            "discount_percent": "derived via compute_discount_percent(base, original)",
            "cart_checkout": "uses base_price; tax_percent never surcharges payable",
            "hesabfa": "site SoT for catalog price; invoice unitPrice=gross paid, tax=0",
            "emalls": "current_price=base_price; old_price=original_price (or base)",
            "code_changes_required": False,
        },
    }

    conn = await connect_rw()
    try:
        identity = await prove_identity(conn)
        ok, errs = identity_ok(identity)
        report["RUNTIME"] = {
            "identity": identity,
            "identity_ok": ok,
            "identity_errors": errs,
        }
        _write_json(
            out_dir / "IDENTITY_PROBE.json",
            {"ok": ok, "errors": errs, "identity": identity},
        )
        if not ok:
            raise Abort("identity_gate_failed: " + "; ".join(errs))

        brand = await prove_brand(conn)
        report["BRAND"] = brand
        if not brand["ok"]:
            raise Abort("brand_gate_failed: " + "; ".join(brand["errors"]))

        idemp = await change_log_idempotency(conn)
        report["IDEMPOTENCY"] = idemp
        if idemp["already_present"]:
            verify = await already_applied_verify(conn)
            report["ALREADY_APPLIED_VERIFY"] = verify
            report["STATUS"] = "ALREADY_APPLIED_VERIFIED"
            report["ABORT_REASON"] = (
                "idempotency_gate: change logs already exist for this reason; "
                "refusing second 0.90 compounding"
            )
            report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_ALREADY_APPLIED_VERIFIED"
            _write_json(out_dir / "VERIFY_REPORT.json", verify)
            return 0

        rows = await fetch_insize_live(conn)
        pre_census = census(rows)
        cohort = validate_priced_cohort(rows)
        report["INSIZE_PRE"] = {**pre_census, "validation": cohort}
        _write_json(
            out_dir / "PRE_REPORT.json",
            {
                "generated_at": _utc_iso(),
                "identity": identity,
                "brand": brand,
                "census": pre_census,
                "validation": cohort,
                "idempotency": idemp,
            },
        )
        if not cohort["ok"]:
            raise Abort("preflight_failed: " + "; ".join(cohort["errors"]))

        priced_rows = [r for r in rows if is_priced(r)]
        manifest = build_manifest(priced_rows)
        man_art = write_manifest_artifacts(out_dir, manifest, stamp)
        report["INSIZE_PRE"].update(man_art["stats"])
        report["MANIFEST"] = {
            "rows": len(manifest),
            "csv_sha256": man_art["csv_sha256"],
            "json_sha256": man_art["json_sha256"],
            "csv_path": man_art["csv_path"],
            "json_path": man_art["json_path"],
            "sha_path": man_art["sha_path"],
        }

        pre_fp = await capture_fingerprints(conn)
        _write_json(out_dir / f"{ARTIFACT_PREFIX}_FINGERPRINTS_PRE_{stamp}.json", pre_fp)
        report["FINGERPRINTS_PRE"] = pre_fp

        recovery = write_recovery_artifacts(out_dir, manifest, stamp)
        report["RECOVERY"] = recovery

        rehearsal = await run_transactional_mutate(conn, manifest, commit=False)
        report["REHEARSAL"] = rehearsal
        if rehearsal.get("transaction_status") != "ROLLED_BACK_REHEARSAL":
            raise Abort("rehearsal_did_not_rollback")
        if rehearsal.get("updated_rows") != len(manifest):
            raise Abort("rehearsal_updated_rows_mismatch")

        after_rehearsal = await fetch_insize_live(conn)
        after_priced = [r for r in after_rehearsal if is_priced(r)]
        if len(after_priced) != len(manifest):
            raise Abort("rehearsal_priced_count_drift")
        for r, m in zip(after_priced, manifest, strict=True):
            if int(r["id"]) != int(m["product_id"]):
                raise Abort(f"rehearsal_id_order_drift id={r['id']}")
            if Decimal(str(r["base_price"])) != Decimal(m["pre_base_price"]):
                raise Abort(
                    f"rehearsal_leaked_base id={r['id']} "
                    f"price={r['base_price']} expected={m['pre_base_price']}"
                )
            live_orig = _dec(r["original_price"])
            expected_pre_orig = (
                None
                if m["pre_original_price"] is None
                else Decimal(m["pre_original_price"])
            )
            if live_orig != expected_pre_orig:
                raise Abort(
                    f"rehearsal_leaked_original id={r['id']} "
                    f"original={live_orig} expected={expected_pre_orig}"
                )
        fp_after_rehearsal = await capture_fingerprints(conn)
        if fp_after_rehearsal != pre_fp:
            raise Abort("rehearsal_fingerprint_drift")
        report["REHEARSAL"]["live_unchanged_proven"] = True
        report["REHEARSAL"]["fingerprints_unchanged"] = True
        report["REHEARSAL"]["field_restoration"] = "base_price+original_price exact"
        report["REHEARSAL"]["scope_gates"] = "non_insize+other_fields unchanged"
        _write_json(out_dir / "REHEARSAL_REPORT.json", report["REHEARSAL"])

        if not args.apply:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["ABORT_REASON"] = "apply_not_requested (preflight+rehearsal only)"
            report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_ABORTED_NO_MUTATION"
            return 0

        if args.skip_apply_even_if_requested:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["ABORT_REASON"] = "skip_apply_even_if_requested"
            report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_ABORTED_NO_MUTATION"
            return 0

        if not args.confirm_owner_authorized_insize_discount_10:
            raise Abort("missing --confirm-owner-authorized-insize-discount-10")

        assert_category_b_for_apply()

        idemp2 = await change_log_idempotency(conn)
        report["IDEMPOTENCY_PRE_APPLY"] = idemp2
        if idemp2["already_present"]:
            raise Abort("idempotency_gate_pre_apply: change logs appeared before APPLY")

        apply_result = await run_transactional_mutate(conn, manifest, commit=True)
        report["INSIZE_APPLY"] = {
            "manifest_rows": len(manifest),
            "manifest_sha256_csv": man_art["csv_sha256"],
            "manifest_sha256_json": man_art["json_sha256"],
            "updated_rows": apply_result["updated_rows"],
            "updated_base_price": apply_result["updated_rows"],
            "updated_original_price": apply_result["updated_rows"],
            "base_price_change_log_rows": apply_result["base_price_change_log_rows"],
            "original_price_change_log_rows": apply_result[
                "original_price_change_log_rows"
            ],
            "change_log_rows": apply_result["change_log_rows"],
            "formula": (
                "original_price = pre_base; "
                "base_price = quantize(pre_base * 0.90, 0.01, ROUND_HALF_UP)"
            ),
            "transaction_status": apply_result["transaction_status"],
            "reason": CHANGE_REASON,
        }
        _write_json(out_dir / "APPLY_REPORT.json", report["INSIZE_APPLY"])
        if apply_result.get("transaction_status") != "COMMITTED":
            raise Abort("apply_not_committed")
        if apply_result["updated_rows"] != len(manifest):
            raise Abort("apply_updated_rows_mismatch")

        post = await post_commit_verify(conn, manifest, pre_fp)
        report["INSIZE_POST"] = post
        report["ISOLATION"] = post["isolation"]
        report["AUDIT"] = {
            "product_change_logs_rows_created": apply_result["change_log_rows"],
            "base_price_rows": apply_result["base_price_change_log_rows"],
            "original_price_rows": apply_result["original_price_change_log_rows"],
            "reason": CHANGE_REASON,
            "actor_user_id": None,
        }
        _write_json(
            out_dir / f"{ARTIFACT_PREFIX}_FINGERPRINTS_POST_{stamp}.json",
            post["isolation"]["post_fingerprints"],
        )
        _write_json(out_dir / "VERIFY_REPORT.json", post)

        if not post["ok"]:
            report["STATUS"] = "APPLIED_BUT_POSTVERIFY_FAILED"
            report["ABORT_REASON"] = "post_commit_verification_failed"
            report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_POSTVERIFY_FAILED"
            return 4

        report["STATUS"] = "APPLIED"
        report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_OK"
        return 0

    except Abort as exc:
        if report.get("STATUS") not in {
            "APPLIED",
            "APPLIED_BUT_POSTVERIFY_FAILED",
            "ALREADY_APPLIED_VERIFIED",
        }:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_ABORTED_NO_MUTATION"
        report["ABORT_REASON"] = str(exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        if report.get("STATUS") not in {
            "APPLIED",
            "APPLIED_BUT_POSTVERIFY_FAILED",
            "ALREADY_APPLIED_VERIFIED",
        }:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_ABORTED_NO_MUTATION"
        report["ABORT_REASON"] = f"unhandled:{type(exc).__name__}:{exc}"
        return 3
    finally:
        await conn.close()
        if "FINAL_LINE" not in report:
            if report.get("STATUS") == "APPLIED":
                report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_OK"
            elif report.get("STATUS") == "ALREADY_APPLIED_VERIFIED":
                report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_ALREADY_APPLIED_VERIFIED"
            else:
                report["FINAL_LINE"] = "INSIZE_DISCOUNT_10_APPLY_ABORTED_NO_MUTATION"
        # Keep a complete FINAL_REPORT for workflow consumption; also mirror as APPLY when applied.
        _write_json(out_dir / "FINAL_REPORT.json", report)
        if report.get("STATUS") == "APPLIED":
            _write_json(out_dir / "APPLY_REPORT.json", report)
        status = report.get("STATUS")
        final_line = report.get(
            "FINAL_LINE", "INSIZE_DISCOUNT_10_APPLY_ABORTED_NO_MUTATION"
        )
        (out_dir / "FINAL_REPORT.md").write_text(
            "\n".join(
                [
                    f"# INSIZE 10% Storefront Discount APPLY — {status}",
                    "",
                    f"Generated: {report.get('generated_at')}",
                    f"Abort reason: {report.get('ABORT_REASON', '')}",
                    "",
                    "## RUNTIME",
                    f"- DB: {(report.get('RUNTIME') or {}).get('identity', {}).get('current_database')}",
                    f"- Host proof: {(report.get('RUNTIME') or {}).get('identity', {}).get('host_proof')}",
                    f"- Git SHA: {(report.get('RUNTIME') or {}).get('identity', {}).get('git_sha')}",
                    "",
                    "## PRE",
                    json.dumps(report.get("INSIZE_PRE"), indent=2, default=str),
                    "",
                    "## REHEARSAL",
                    json.dumps(report.get("REHEARSAL"), indent=2, default=str),
                    "",
                    "## APPLY",
                    json.dumps(report.get("INSIZE_APPLY"), indent=2, default=str),
                    "",
                    "## POST",
                    json.dumps(report.get("INSIZE_POST"), indent=2, default=str),
                    "",
                    "## RECOVERY",
                    json.dumps(report.get("RECOVERY"), indent=2, default=str),
                    "",
                    final_line,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(json.dumps({"STATUS": status, "FINAL_LINE": final_line}, indent=2))
        print(final_line)


def main() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main()
