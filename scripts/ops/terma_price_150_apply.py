#!/usr/bin/env python3
"""TERMA +50% base_price Category B APPLY — Owner-authorized 2026-09-26.

PIPELINE DECLARATION
  Source: current live products.base_price (× Decimal 1.50)
  Destination: CR-011 live Postgres (historic name karzar_staging / lathe_postgres)
  Owner: Owner-authorized emergency catalog mutation 2026-09-26
  Validation: count==312, brand_id=5 + name match, stale-price guard, fingerprints
  Audit Trail: manifests + recovery + product_change_logs (actor NULL) + FINAL_REPORT
  Rollback: exact old_base_price restore SQL (not divide-by-1.5)

Safety:
  - Fail closed on drift from expected live count 312
  - Single-transaction APPLY with FOR UPDATE + conditional UPDATE
  - Mutates base_price ONLY
  - No Hesabfa / deploy / other brands

Usage (inside lathe_api on karzar-vps):
  python /tmp/terma_price_150_apply.py --out-dir /tmp/karzar-terma-price-150-out
  python /tmp/terma_price_150_apply.py --out-dir ... --apply \\
      --confirm-owner-authorized-terma-price-150
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
EXPECTED_BRAND_ID = 5
EXPECTED_BRAND_NAME = "TERMA | ترما"
EXPECTED_LIVE_COUNT = 312
PRICE_FACTOR = Decimal("1.50")
QUANTUM = Decimal("0.01")
NUMERIC_15_2_MAX = Decimal("9999999999999.99")  # 13 integer digits + 2 decimal
CHANGE_REASON = "TERMA +50% owner-authorized price update 2026-09-26"
ALLOW_ENV = "KARZAR_ALLOW_PRODUCTION_WRITE"
CATEGORY_ENV = "KARZAR_INGESTION_CATEGORY"


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


def proposed_price(old: Decimal) -> Decimal:
    return _q(old * PRICE_FACTOR)


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


async def fetch_terma_live(conn: asyncpg.Connection) -> list[asyncpg.Record]:
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
            b.name AS brand_name
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


def validate_cohort(rows: list[asyncpg.Record]) -> dict[str, Any]:
    errors: list[str] = []
    if len(rows) != EXPECTED_LIVE_COUNT:
        errors.append(
            f"DRIFT: live TERMA count={len(rows)} expected={EXPECTED_LIVE_COUNT} "
            f"delta={len(rows) - EXPECTED_LIVE_COUNT}"
        )
    ids = [int(r["id"]) for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate product ids in cohort")
    for r in rows:
        if int(r["brand_id"]) != EXPECTED_BRAND_ID:
            errors.append(f"id={r['id']} brand_id={r['brand_id']}")
        if r["brand_name"] != EXPECTED_BRAND_NAME:
            errors.append(f"id={r['id']} brand_name={r['brand_name']!r}")
        if r["deleted_at"] is not None:
            errors.append(f"id={r['id']} soft-deleted")
        if r["base_price"] is None:
            errors.append(f"id={r['id']} base_price NULL")
            continue
        try:
            price = Decimal(str(r["base_price"]))
        except (InvalidOperation, ValueError):
            errors.append(f"id={r['id']} base_price unparsable")
            continue
        if price <= 0:
            errors.append(f"id={r['id']} base_price<=0 ({price})")
        proposed = proposed_price(price)
        if proposed > NUMERIC_15_2_MAX:
            errors.append(f"id={r['id']} proposed {proposed} exceeds Numeric(15,2)")
        if proposed != _q(price * PRICE_FACTOR):
            errors.append(f"id={r['id']} quantize mismatch")
    return {"ok": not errors, "errors": errors, "count": len(rows)}


def build_manifest(rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for r in rows:
        old = Decimal(str(r["base_price"]))
        new = proposed_price(old)
        orig = _dec(r["original_price"])
        manifest.append(
            {
                "product_id": int(r["id"]),
                "sku": str(r["sku"]),
                "name": str(r["name"]),
                "brand_id": int(r["brand_id"]),
                "brand_name": str(r["brand_name"]),
                "category_id": None if r["category_id"] is None else int(r["category_id"]),
                "old_base_price": str(old),
                "proposed_base_price": str(new),
                "original_price": None if orig is None else str(orig),
                "is_active": bool(r["is_active"]),
                "is_available": bool(r["is_available"]),
                "deleted_at": None,
            }
        )
    return manifest


def manifest_stats(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    olds = [Decimal(m["old_base_price"]) for m in manifest]
    news = [Decimal(m["proposed_base_price"]) for m in manifest]
    orig_nonnull = sum(1 for m in manifest if m["original_price"] is not None)
    proposed_ge_orig = 0
    for m in manifest:
        if m["original_price"] is None:
            continue
        if Decimal(m["proposed_base_price"]) >= Decimal(m["original_price"]):
            proposed_ge_orig += 1
    return {
        "row_count": len(manifest),
        "current_min": str(min(olds)) if olds else None,
        "current_max": str(max(olds)) if olds else None,
        "current_sum": str(sum(olds)) if olds else None,
        "proposed_min": str(min(news)) if news else None,
        "proposed_max": str(max(news)) if news else None,
        "proposed_sum": str(sum(news)) if news else None,
        "original_price_nonnull": orig_nonnull,
        "proposed_ge_original_price": proposed_ge_orig,
    }


def write_manifest_artifacts(
    out_dir: Path, manifest: list[dict[str, Any]], stamp: str
) -> dict[str, Any]:
    csv_path = out_dir / f"TERMA_PRICE_150_MANIFEST_{stamp}.csv"
    json_path = out_dir / f"TERMA_PRICE_150_MANIFEST_{stamp}.json"
    fields = [
        "product_id",
        "sku",
        "brand_id",
        "old_base_price",
        "proposed_base_price",
        "original_price",
        "is_active",
        "is_available",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in manifest:
            writer.writerow(row)
    json_path.write_text(
        json.dumps(
            {
                "generated_at": _utc_iso(),
                "formula": "proposed_base_price = quantize(old_base_price * 1.50, 0.01)",
                "expected_count": EXPECTED_LIVE_COUNT,
                "brand_id": EXPECTED_BRAND_ID,
                "brand_name": EXPECTED_BRAND_NAME,
                "stats": manifest_stats(manifest),
                "rows": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "csv_sha256": _sha256_file(csv_path),
        "json_sha256": _sha256_file(json_path),
        "stats": manifest_stats(manifest),
    }


def write_recovery_artifacts(
    out_dir: Path, manifest: list[dict[str, Any]], stamp: str
) -> dict[str, Any]:
    recovery_csv = out_dir / f"TERMA_PRICE_150_RECOVERY_PREWRITE_{stamp}.csv"
    rollback_sql = out_dir / f"TERMA_PRICE_150_ROLLBACK_{stamp}.sql"
    fields = [
        "product_id",
        "sku",
        "brand_id",
        "old_base_price",
        "proposed_base_price",
        "original_price",
        "is_active",
        "is_available",
        "category_id",
        "name",
    ]
    with recovery_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in manifest:
            writer.writerow(row)

    lines = [
        "-- TERMA +50% rollback — restore EXACT pre-write base_price values",
        f"-- generated_at={_utc_iso()}",
        f"-- expected_row_count={len(manifest)}",
        "-- DO NOT use divide-by-1.5; values below are captured pre-write.",
        "BEGIN;",
    ]
    for row in manifest:
        sku = str(row["sku"]).replace("'", "''")
        lines.append(
            "UPDATE products SET base_price = {old}, updated_at = NOW() "
            "WHERE id = {pid} AND brand_id = {bid} AND deleted_at IS NULL "
            "AND sku = '{sku}' AND base_price = {new};".format(
                old=row["old_base_price"],
                pid=row["product_id"],
                bid=EXPECTED_BRAND_ID,
                sku=sku,
                new=row["proposed_base_price"],
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
    non_terma = await conn.fetch(
        """
        SELECT id, base_price
        FROM products
        WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM $1
        ORDER BY id
        """,
        EXPECTED_BRAND_ID,
    )
    non_terma_null = sum(1 for r in non_terma if r["base_price"] is None)
    non_terma_hash = _sha256_text(
        "\n".join(
            f"{int(r['id'])}|{'' if r['base_price'] is None else str(r['base_price'])}"
            for r in non_terma
        )
    )

    terma_nonprice = await conn.fetch(
        """
        SELECT p.id, p.sku, p.brand_id, p.category_id, p.is_active, p.is_available,
               p.deleted_at, p.original_price
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
    terma_nonprice_hash = _sha256_text(
        "\n".join(
            "|".join(
                [
                    str(int(r["id"])),
                    str(r["sku"]),
                    str(int(r["brand_id"])),
                    "" if r["category_id"] is None else str(int(r["category_id"])),
                    str(bool(r["is_active"])).lower(),
                    str(bool(r["is_available"])).lower(),
                    "" if r["deleted_at"] is None else str(r["deleted_at"]),
                    "" if r["original_price"] is None else str(r["original_price"]),
                ]
            )
            for r in terma_nonprice
        )
    )

    products_count = await conn.fetchval("SELECT COUNT(*) FROM products")
    images_count = await conn.fetchval("SELECT COUNT(*) FROM product_images")
    return {
        "non_terma_live_count": len(non_terma),
        "non_terma_base_price_null_count": non_terma_null,
        "non_terma_id_price_sha256": non_terma_hash,
        "terma_nonprice_sha256": terma_nonprice_hash,
        "products_count": int(products_count),
        "product_images_count": int(images_count),
    }


async def run_transactional_mutate(
    conn: asyncpg.Connection,
    manifest: list[dict[str, Any]],
    *,
    commit: bool,
) -> dict[str, Any]:
    """Lock allowlist, stale-guard, UPDATE base_price only, optional change logs."""
    by_id = {int(m["product_id"]): m for m in manifest}
    ids = sorted(by_id.keys())
    result: dict[str, Any] = {
        "commit": commit,
        "target_rows": len(ids),
        "updated_rows": 0,
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
                   p.name, p.slug
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
            if live_price is None or live_price != Decimal(m["old_base_price"]):
                raise Abort(
                    f"stale_base_price id={mid} live={live_price} "
                    f"manifest={m['old_base_price']}"
                )
            if str(row["sku"]) != m["sku"]:
                raise Abort(f"stale_sku id={mid}")

        updated = 0
        for mid in ids:
            m = by_id[mid]
            status = await conn.execute(
                """
                UPDATE products
                SET base_price = $1::numeric,
                    updated_at = NOW()
                WHERE id = $2
                  AND brand_id = $3
                  AND deleted_at IS NULL
                  AND base_price = $4::numeric
                """,
                Decimal(m["proposed_base_price"]),
                mid,
                EXPECTED_BRAND_ID,
                Decimal(m["old_base_price"]),
            )
            # asyncpg: "UPDATE N"
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
                m["old_base_price"],
                m["proposed_base_price"],
                CHANGE_REASON,
            )

        if updated != len(ids):
            raise Abort(f"updated_rows={updated} != {len(ids)}")

        # Commit gates (still inside txn)
        post = await conn.fetch(
            """
            SELECT p.id, p.sku, p.base_price, p.original_price, p.is_active,
                   p.is_available, p.deleted_at, p.brand_id, p.category_id,
                   p.name, p.slug
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
            actual = _dec(row["base_price"])
            expected = Decimal(m["proposed_base_price"])
            if actual != expected:
                raise Abort(
                    f"post_price_mismatch id={row['id']} actual={actual} expected={expected}"
                )
            old = Decimal(m["old_base_price"])
            if actual != proposed_price(old):
                raise Abort(f"post_formula_mismatch id={row['id']}")
            if _dec(row["original_price"]) != (
                None
                if m["original_price"] is None
                else Decimal(m["original_price"])
            ):
                raise Abort(f"original_price_mutated id={row['id']}")
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
        result["change_log_rows"] = updated
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
    rows = await fetch_terma_live(conn)
    by_id = {int(m["product_id"]): m for m in manifest}
    exact = 0
    deltas: list[Decimal] = []
    prices: list[Decimal] = []
    for r in rows:
        mid = int(r["id"])
        if mid not in by_id:
            continue
        m = by_id[mid]
        actual = Decimal(str(r["base_price"]))
        expected = Decimal(m["proposed_base_price"])
        old = Decimal(m["old_base_price"])
        if actual == expected:
            exact += 1
        if old > 0:
            deltas.append(((actual - old) / old * Decimal("100")).quantize(Decimal("0.01")))
        prices.append(actual)

    post_fp = await capture_fingerprints(conn)
    isolation = {
        "non_terma_price_mutations": 0
        if post_fp["non_terma_id_price_sha256"] == pre_fp["non_terma_id_price_sha256"]
        else 1,
        "terma_nonprice_mutations": 0
        if post_fp["terma_nonprice_sha256"] == pre_fp["terma_nonprice_sha256"]
        else 1,
        "products_count_delta": post_fp["products_count"] - pre_fp["products_count"],
        "product_images_count_delta": post_fp["product_images_count"]
        - pre_fp["product_images_count"],
        "pre_fingerprints": pre_fp,
        "post_fingerprints": post_fp,
    }

    change_logs = await conn.fetchval(
        """
        SELECT COUNT(*) FROM product_change_logs
        WHERE reason = $1 AND field_name = 'base_price'
        """,
        CHANGE_REASON,
    )

    samples = []
    for m in manifest[:5]:
        samples.append(
            {
                "sku": m["sku"],
                "product_id": m["product_id"],
                "old_base_price": m["old_base_price"],
                "new_base_price": m["proposed_base_price"],
            }
        )

    return {
        "count": len(rows),
        "price_exact_match": exact,
        "min": str(min(prices)) if prices else None,
        "max": str(max(prices)) if prices else None,
        "sum": str(sum(prices)) if prices else None,
        "delta_pct_min": str(min(deltas)) if deltas else None,
        "delta_pct_max": str(max(deltas)) if deltas else None,
        "null_price": sum(1 for r in rows if r["base_price"] is None),
        "isolation": isolation,
        "change_log_rows_with_reason": int(change_logs),
        "samples": samples,
        "ok": (
            len(rows) == EXPECTED_LIVE_COUNT
            and exact == EXPECTED_LIVE_COUNT
            and isolation["non_terma_price_mutations"] == 0
            and isolation["terma_nonprice_mutations"] == 0
            and isolation["products_count_delta"] == 0
            and isolation["product_images_count_delta"] == 0
            and (not deltas or (min(deltas) == Decimal("50.00") and max(deltas) == Decimal("50.00")))
        ),
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


async def amain(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TERMA +50% guarded price APPLY")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit production mutation after successful rehearsal",
    )
    parser.add_argument(
        "--confirm-owner-authorized-terma-price-150",
        action="store_true",
        help="Required with --apply (Owner authorization 2026-09-26)",
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
        "formula": "proposed_base_price = quantize(current_base_price * 1.50, 0.01)",
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
        (out_dir / "IDENTITY_PROBE.json").write_text(
            json.dumps({"ok": ok, "errors": errs, "identity": identity}, indent=2) + "\n",
            encoding="utf-8",
        )
        if not ok:
            raise Abort("identity_gate_failed: " + "; ".join(errs))

        # --- PREFLIGHT (read-only semantics; connection is RW-capable) ---
        rows = await fetch_terma_live(conn)
        cohort = validate_cohort(rows)
        report["TERMA_PRE"] = {
            "count": len(rows),
            "priced_count": sum(
                1 for r in rows if r["base_price"] is not None and Decimal(str(r["base_price"])) > 0
            ),
            "validation": cohort,
        }
        if not cohort["ok"]:
            raise Abort("preflight_failed: " + "; ".join(cohort["errors"]))

        manifest = build_manifest(rows)
        man_art = write_manifest_artifacts(out_dir, manifest, stamp)
        report["TERMA_PRE"].update(man_art["stats"])
        report["MANIFEST"] = {
            "rows": len(manifest),
            "csv_sha256": man_art["csv_sha256"],
            "json_sha256": man_art["json_sha256"],
            "csv_path": man_art["csv_path"],
            "json_path": man_art["json_path"],
        }

        pre_fp = await capture_fingerprints(conn)
        (out_dir / f"TERMA_PRICE_150_FINGERPRINTS_PRE_{stamp}.json").write_text(
            json.dumps(pre_fp, indent=2) + "\n", encoding="utf-8"
        )
        report["FINGERPRINTS_PRE"] = pre_fp

        recovery = write_recovery_artifacts(out_dir, manifest, stamp)
        report["RECOVERY"] = recovery

        # --- REHEARSAL: exact mutate path then ROLLBACK ---
        rehearsal = await run_transactional_mutate(conn, manifest, commit=False)
        report["REHEARSAL"] = rehearsal
        if rehearsal.get("transaction_status") != "ROLLED_BACK_REHEARSAL":
            raise Abort("rehearsal_did_not_rollback")
        if rehearsal.get("updated_rows") != EXPECTED_LIVE_COUNT:
            raise Abort("rehearsal_updated_rows_mismatch")

        # Prove live unchanged after rehearsal
        after_rehearsal = await fetch_terma_live(conn)
        for r, m in zip(after_rehearsal, manifest, strict=True):
            if Decimal(str(r["base_price"])) != Decimal(m["old_base_price"]):
                raise Abort(
                    f"rehearsal_leaked_mutation id={r['id']} "
                    f"price={r['base_price']} expected_old={m['old_base_price']}"
                )
        fp_after_rehearsal = await capture_fingerprints(conn)
        if fp_after_rehearsal != pre_fp:
            raise Abort("rehearsal_fingerprint_drift")
        report["REHEARSAL"]["live_unchanged_proven"] = True

        # --- APPLY ---
        if not args.apply:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["ABORT_REASON"] = "apply_not_requested (preflight+rehearsal only)"
            report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
            return 0

        if args.skip_apply_even_if_requested:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["ABORT_REASON"] = "skip_apply_even_if_requested"
            report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
            return 0

        if not args.confirm_owner_authorized_terma_price_150:
            raise Abort("missing --confirm-owner-authorized-terma-price-150")

        assert_category_b_for_apply()

        apply_result = await run_transactional_mutate(conn, manifest, commit=True)
        report["TERMA_APPLY"] = {
            "manifest_rows": len(manifest),
            "manifest_sha256_csv": man_art["csv_sha256"],
            "manifest_sha256_json": man_art["json_sha256"],
            "updated_rows": apply_result["updated_rows"],
            "change_log_rows": apply_result["change_log_rows"],
            "formula": "base_price = quantize(old * 1.50, 0.01)",
            "transaction_status": apply_result["transaction_status"],
        }
        if apply_result.get("transaction_status") != "COMMITTED":
            raise Abort("apply_not_committed")
        if apply_result["updated_rows"] != EXPECTED_LIVE_COUNT:
            raise Abort("apply_updated_rows_mismatch")

        post = await post_commit_verify(conn, manifest, pre_fp)
        report["TERMA_POST"] = post
        report["ISOLATION"] = post["isolation"]
        report["AUDIT"] = {
            "product_change_logs_rows_created": apply_result["change_log_rows"],
            "reason": CHANGE_REASON,
            "actor_user_id": None,
        }
        (out_dir / f"TERMA_PRICE_150_FINGERPRINTS_POST_{stamp}.json").write_text(
            json.dumps(post["isolation"]["post_fingerprints"], indent=2) + "\n",
            encoding="utf-8",
        )

        if not post["ok"]:
            report["STATUS"] = "APPLIED_BUT_POSTVERIFY_FAILED"
            report["ABORT_REASON"] = "post_commit_verification_failed"
            report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
            return 4

        report["STATUS"] = "APPLIED"
        report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_OK"
        return 0

    except Abort as exc:
        # Do not downgrade a committed APPLY to ABORTED_NO_MUTATION.
        if report.get("STATUS") not in {"APPLIED", "APPLIED_BUT_POSTVERIFY_FAILED"}:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
        report["ABORT_REASON"] = str(exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        if report.get("STATUS") not in {"APPLIED", "APPLIED_BUT_POSTVERIFY_FAILED"}:
            report["STATUS"] = "ABORTED_NO_MUTATION"
            report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
        report["ABORT_REASON"] = f"unhandled:{type(exc).__name__}:{exc}"
        return 3
    finally:
        await conn.close()
        if "FINAL_LINE" not in report:
            if report.get("STATUS") == "APPLIED":
                report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_OK"
            else:
                report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
        report_path = out_dir / "FINAL_REPORT.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        summary_path = out_dir / "FINAL_REPORT.md"
        status = report.get("STATUS")
        final_line = report.get("FINAL_LINE", "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION")
        summary_path.write_text(
            "\n".join(
                [
                    f"# TERMA +50% Price APPLY — {status}",
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
                    json.dumps(report.get("TERMA_PRE"), indent=2, default=str),
                    "",
                    "## APPLY",
                    json.dumps(report.get("TERMA_APPLY"), indent=2, default=str),
                    "",
                    "## POST",
                    json.dumps(report.get("TERMA_POST"), indent=2, default=str),
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
