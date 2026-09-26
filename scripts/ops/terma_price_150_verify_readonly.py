#!/usr/bin/env python3
"""READ-ONLY verification of TERMA +50% APPLY outcome.

NO WRITES. Sets default_transaction_read_only=on and uses BEGIN READ ONLY.

Checks product_change_logs reason:
  TERMA +50% owner-authorized price update 2026-09-26
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import asyncpg

EXPECTED_HOST = "srv5944957438"
EXPECTED_DB = "karzar_staging"
EXPECTED_CONTAINER = "lathe_postgres"
EXPECTED_BRAND_ID = 5
EXPECTED_BRAND_NAME = "TERMA | ترما"
EXPECTED_LIVE_COUNT = 312
CHANGE_REASON = "TERMA +50% owner-authorized price update 2026-09-26"
PRICE_FACTOR = Decimal("1.50")
QUANTUM = Decimal("0.01")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _q(v: Decimal) -> Decimal:
    return v.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(v))


async def connect_ro() -> asyncpg.Connection:
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
    await conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
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
    ro = await conn.fetchval("SHOW transaction_read_only")
    alembic = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
    return {
        "current_database": row["db"],
        "current_user": row["usr"],
        "inet_server_addr": row["addr"],
        "inet_server_port": row["port"],
        "version": row["ver"],
        "transaction_read_only": ro,
        "alembic_revision": alembic,
        "app_env": os.environ.get("APP_ENV"),
        "karzar_data_plane": os.environ.get("KARZAR_DATA_PLANE"),
        "host_proof": os.environ.get("KARZAR_HOST_PROOF"),
        "container_proof": os.environ.get("KARZAR_CONTAINER_PROOF"),
        "volume_proof": os.environ.get("KARZAR_VOLUME_PROOF"),
        "git_sha": os.environ.get("KARZAR_GIT_SHA") or os.environ.get("GITHUB_SHA"),
        "expected_host": EXPECTED_HOST,
        "expected_db": EXPECTED_DB,
    }


def identity_ok(identity: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if identity["current_database"] != EXPECTED_DB:
        errs.append(f"database={identity['current_database']} != {EXPECTED_DB}")
    if str(identity.get("transaction_read_only", "")).lower() not in {"on", "true"}:
        errs.append(f"transaction_read_only={identity.get('transaction_read_only')}")
    host_proof = (identity.get("host_proof") or "").strip()
    if host_proof != EXPECTED_HOST:
        errs.append(f"host_proof={host_proof!r} != {EXPECTED_HOST}")
    container_proof = (identity.get("container_proof") or "").strip()
    if EXPECTED_CONTAINER not in container_proof:
        errs.append(f"container_proof={container_proof!r}")
    volume_proof = (identity.get("volume_proof") or "").strip()
    if "postgres_data" not in volume_proof and "karzar_postgres_data" not in volume_proof:
        errs.append(f"volume_proof={volume_proof!r}")
    return (len(errs) == 0, errs)


async def amain() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": _utc_iso(),
        "mode": "READ_ONLY",
        "change_reason": CHANGE_REASON,
        "workflow_run_under_investigation": "36244999947",
    }

    conn = await connect_ro()
    try:
        async with conn.transaction(readonly=True):
            identity = await prove_identity(conn)
            ok, errs = identity_ok(identity)
            report["RUNTIME"] = {"identity": identity, "identity_ok": ok, "identity_errors": errs}
            (out_dir / "IDENTITY_PROBE.json").write_text(
                json.dumps({"ok": ok, "errors": errs, "identity": identity}, indent=2) + "\n",
                encoding="utf-8",
            )
            if not ok:
                report["STATUS"] = "INCIDENT_REQUIRES_RECONCILIATION"
                report["ABORT_REASON"] = "identity_gate_failed: " + "; ".join(errs)
                report["FINAL_LINE"] = "TERMA_PRICE_150_VERIFY_IDENTITY_FAILED"
                return 2

            logs = await conn.fetch(
                """
                SELECT
                    l.id,
                    l.product_id,
                    p.sku,
                    l.old_value,
                    l.new_value,
                    p.base_price,
                    p.slug,
                    p.is_active,
                    p.is_available,
                    p.deleted_at,
                    p.brand_id
                FROM product_change_logs l
                JOIN products p ON p.id = l.product_id
                WHERE l.field_name = 'base_price'
                  AND l.reason = $1
                ORDER BY l.product_id, l.id
                """,
                CHANGE_REASON,
            )

            formula_ok = 0
            price_match = 0
            formula_bad: list[dict[str, Any]] = []
            price_bad: list[dict[str, Any]] = []
            samples: list[dict[str, Any]] = []
            product_ids = [int(r["product_id"]) for r in logs]
            distinct_ids = sorted(set(product_ids))

            for r in logs:
                old = _dec(r["old_value"])
                new = _dec(r["new_value"])
                cur = _dec(r["base_price"])
                expected_new = None if old is None else _q(old * PRICE_FACTOR)
                f_ok = old is not None and new is not None and expected_new == new
                p_ok = cur is not None and new is not None and cur == new
                if f_ok:
                    formula_ok += 1
                else:
                    formula_bad.append(
                        {
                            "log_id": int(r["id"]),
                            "product_id": int(r["product_id"]),
                            "sku": r["sku"],
                            "old_value": None if old is None else str(old),
                            "new_value": None if new is None else str(new),
                            "expected_new": None if expected_new is None else str(expected_new),
                        }
                    )
                if p_ok:
                    price_match += 1
                else:
                    price_bad.append(
                        {
                            "log_id": int(r["id"]),
                            "product_id": int(r["product_id"]),
                            "sku": r["sku"],
                            "new_value": None if new is None else str(new),
                            "current_base_price": None if cur is None else str(cur),
                        }
                    )
                if len(samples) < 15 and old and new and cur and old > 0:
                    delta = _q((cur - old) / old * Decimal("100"))
                    samples.append(
                        {
                            "sku": r["sku"],
                            "product_id": int(r["product_id"]),
                            "slug": r["slug"],
                            "old_price": str(old),
                            "logged_new_price": str(new),
                            "current_db_price": str(cur),
                            "delta_pct": str(delta),
                            "is_active": bool(r["is_active"]),
                            "is_available": bool(r["is_available"]),
                        }
                    )

            # duplicate product ids in logs
            from collections import Counter

            id_counts = Counter(product_ids)
            dup_ids = sorted([pid for pid, n in id_counts.items() if n > 1])

            if len(logs) == 0:
                log_interp = "NO_COMMIT_OBSERVED"
            elif (
                len(logs) == EXPECTED_LIVE_COUNT
                and len(distinct_ids) == EXPECTED_LIVE_COUNT
                and formula_ok == EXPECTED_LIVE_COUNT
                and price_match == EXPECTED_LIVE_COUNT
                and not dup_ids
            ):
                log_interp = "DB_APPLY_CONFIRMED"
            elif len(logs) > EXPECTED_LIVE_COUNT or dup_ids:
                log_interp = "POSSIBLE_DOUBLE_APPLY_OR_REPEAT_APPLY"
            elif 1 <= len(logs) <= EXPECTED_LIVE_COUNT - 1:
                log_interp = "ANOMALOUS_PARTIAL_STATE"
            else:
                log_interp = "ANOMALOUS_INCONSISTENT_STATE"

            report["CHANGE_LOGS"] = {
                "total_log_rows": len(logs),
                "distinct_product_id_count": len(distinct_ids),
                "formula_matches": formula_ok,
                "current_price_matches_new_value": price_match,
                "duplicate_product_ids": dup_ids[:50],
                "duplicate_product_id_count": len(dup_ids),
                "formula_bad_count": len(formula_bad),
                "price_bad_count": len(price_bad),
                "formula_bad_sample": formula_bad[:20],
                "price_bad_sample": price_bad[:20],
                "interpretation": log_interp,
                "samples": samples,
            }

            cohort = await conn.fetch(
                """
                SELECT
                    p.id,
                    p.sku,
                    p.slug,
                    p.base_price,
                    p.original_price,
                    p.is_active,
                    p.is_available
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
            prices = [_dec(r["base_price"]) for r in cohort]
            priced = [p for p in prices if p is not None and p > 0]
            report["TERMA_COHORT"] = {
                "live_count": len(cohort),
                "priced_count": len(priced),
                "min_base_price": str(min(priced)) if priced else None,
                "max_base_price": str(max(priced)) if priced else None,
                "sum_base_price": str(sum(priced)) if priced else None,
                "expected_live_count": EXPECTED_LIVE_COUNT,
            }

            # API sample candidates: active+available from logs/cohort overlap
            api_candidates = []
            for r in logs:
                if bool(r["is_active"]) and r["deleted_at"] is None and r["slug"]:
                    api_candidates.append(
                        {
                            "product_id": int(r["product_id"]),
                            "sku": r["sku"],
                            "slug": r["slug"],
                            "base_price": str(_dec(r["base_price"])),
                        }
                    )
                if len(api_candidates) >= 12:
                    break
            if len(api_candidates) < 5:
                for r in cohort:
                    if bool(r["is_active"]) and r["slug"]:
                        api_candidates.append(
                            {
                                "product_id": int(r["id"]),
                                "sku": r["sku"],
                                "slug": r["slug"],
                                "base_price": str(_dec(r["base_price"])),
                            }
                        )
                    if len(api_candidates) >= 12:
                        break

            report["API_CANDIDATES"] = api_candidates
            report["STOREFRONT_CANDIDATES"] = api_candidates[:5]

            # Final decision from DB evidence alone (API filled by workflow/host)
            if log_interp == "DB_APPLY_CONFIRMED" and len(cohort) == EXPECTED_LIVE_COUNT:
                report["STATUS"] = "APPLIED"
                report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_OK"
                rc = 0
            elif log_interp == "NO_COMMIT_OBSERVED" and len(cohort) == EXPECTED_LIVE_COUNT:
                report["STATUS"] = "ABORTED_NO_MUTATION"
                report["FINAL_LINE"] = "TERMA_PRICE_150_APPLY_ABORTED_NO_MUTATION"
                rc = 0
            else:
                report["STATUS"] = "INCIDENT_REQUIRES_RECONCILIATION"
                report["FINAL_LINE"] = "TERMA_PRICE_150_VERIFY_INCIDENT"
                rc = 3

            # Always ROLLBACK the read-only txn explicitly via context exit
            return rc
    finally:
        await conn.close()
        (out_dir / "VERIFY_REPORT.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        md = [
            f"# TERMA +50% READ-ONLY VERIFY — {report.get('STATUS')}",
            "",
            f"Generated: {report.get('generated_at')}",
            f"Interpretation: {(report.get('CHANGE_LOGS') or {}).get('interpretation')}",
            "",
            "## CHANGE_LOGS",
            json.dumps(report.get("CHANGE_LOGS"), indent=2, ensure_ascii=False, default=str),
            "",
            "## TERMA_COHORT",
            json.dumps(report.get("TERMA_COHORT"), indent=2, ensure_ascii=False, default=str),
            "",
            "## SAMPLES",
            json.dumps(
                (report.get("CHANGE_LOGS") or {}).get("samples"),
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            "",
            str(report.get("FINAL_LINE")),
            "",
        ]
        (out_dir / "VERIFY_REPORT.md").write_text("\n".join(md), encoding="utf-8")
        print(json.dumps({"STATUS": report.get("STATUS"), "FINAL_LINE": report.get("FINAL_LINE")}, indent=2))
        print(report.get("FINAL_LINE"))


def main() -> None:
    raise SystemExit(asyncio.run(amain()))


if __name__ == "__main__":
    main()
