#!/usr/bin/env python3
"""INSIZE +10% owner-authorized base_price APPLY (Category B, one-shot).

Dry-run by default. Persistent mutation requires:
  KARZAR_ALLOW_PRODUCTION_WRITE=1
  KARZAR_INGESTION_CATEGORY=B
  --manifest-csv <owner-frozen manifest CSV>
  --apply
  --confirm-manifest-sha <owner-frozen SHA256; must match domain FROZEN_MANIFEST_SHA256>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.insize_price_110_20261021 import (
    discount_display_state,  # noqa: E402
    CHANGE_REASON,
    COMMERCIAL_EVENT_ID,
    EXPECTED_ALEMBIC_REVISION,
    EXPECTED_PREFLIGHT_BASE_SUM,
    EXPECTED_PREVIOUS_EVENT_BASE_SUM,
    EXPECTED_PREVIOUS_EVENT_LOG_ROWS,
    PREVIOUS_EVENT_CHANGE_REASON,
    find_discount_semantics_blockers,
    merchandising_exception_comparison,
    PRICE_CURRENCY_LABEL,
    AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS,
    EXPECTED_BRAND_ID,
    EXPECTED_BRAND_NAME,
    EXPECTED_DATABASE,
    EXPECTED_DATABASE_USER,
    EXPECTED_DOCKER_VOLUME,
    EXPECTED_PG_SYSTEM_IDENTIFIER,
    EXPECTED_POST_APPLY_BASE_SUM,
    EXPECTED_POSTGRES_CONTAINER,
    EXPECTED_VPS_HOSTNAME,
    FROZEN_MANIFEST_SHA256,
    MIN_PUBLIC_API_PRICE_VERIFICATIONS,
    MULTIPLIER,
    ROLLBACK_CHANGE_REASON,
    ORIGINAL_PRICE_CLEAR_CHANGE_REASON,
    build_manifest_row,
    build_real_apply_sql,
    build_rollback_sql,
    classify_api_sample_result,
    cohort_id_set_diff,
    discount_impact_row,
    evaluate_api_verification,
    evaluate_db_post_apply_verification,
    evaluate_frozen_handoff_readiness,
    parse_money,
    normalize_manifest_from_csv_rows,
    rehearsal_contract_summary,
    validate_owner_frozen_commercial_contract,
    money_equal_nullable,
    EXPECTED_TOTAL_EVENT_LOG_ROWS,
    EXPECTED_ORIGINAL_EXCEPTION_COUNT,
    proposed_base_price,
    reconcile_collector_vs_proof,
    resolve_post_commit_status,
    select_public_api_verification_candidates,
    validate_frozen_manifest_authority,
    validate_production_identity_gates,
)
from scripts.ops.phase2c_manufacturer_identity_apply_once import (  # noqa: E402
    _git_head,
    _run_ssh_psql,
    _run_ssh_psql_script,
    assert_evidence_writable,
    collect_live_health,
    collect_runtime_identity,
    create_live_backup,
    write_csv,
    write_json,
)

AUDIT_OUT = ROOT / "audit" / "insize-price-110-20261021"
DEFAULT_BACKUP_DIR = Path.home() / "karzar-backups" / "insize-price-110-20261021"
DEFAULT_SSH = "karzar-vps"
MANIFEST_FIELDS = [
    "product_id",
    "sku",
    "name",
    "slug",
    "brand_id",
    "brand_name",
    "category_id",
    "product_type_id",
    "old_base_price",
    "proposed_base_price",
    "old_original_price",
    "proposed_original_price",
    "authorized_original_price_exception",
    "is_active",
    "is_available",
    "deleted_at",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _require_category_b() -> None:
    if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
        print("FATAL: set KARZAR_ALLOW_PRODUCTION_WRITE=1", file=sys.stderr)
        raise SystemExit(2)
    if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
        print("FATAL: set KARZAR_INGESTION_CATEGORY=B", file=sys.stderr)
        raise SystemExit(2)



def verify_previous_event_completion(ssh_host: str) -> dict[str, Any]:
    """Read-only proof the 2026-10-19 +10% event completed (not re-run)."""
    reason_md5 = hashlib.md5(PREVIOUS_EVENT_CHANGE_REASON.encode("utf-8")).hexdigest()
    log_line = _run_ssh_psql(
        f"""
SELECT COUNT(*)::text, COUNT(DISTINCT product_id)::text
FROM product_change_logs
WHERE md5(reason::text) = '{reason_md5}';
""",
        ssh_host=ssh_host,
    ).splitlines()[-1]
    parts = log_line.split("\t") if "\t" in log_line else log_line.split("|")
    log_count = int(parts[0]) if parts else 0
    distinct = int(parts[1]) if len(parts) > 1 else 0
    sum_line = _run_ssh_psql(
        """
SELECT COALESCE(SUM(base_price),0)::text
FROM products
WHERE brand_id=3 AND deleted_at IS NULL
  AND base_price IS NOT NULL AND base_price > 0;
""",
        ssh_host=ssh_host,
    ).splitlines()[-1].strip()
    live_sum = parse_money(sum_line)
    sum_ok = live_sum == EXPECTED_PREVIOUS_EVENT_BASE_SUM
    count_ok = (
        log_count == EXPECTED_PREVIOUS_EVENT_LOG_ROWS
        and distinct == EXPECTED_PREVIOUS_EVENT_LOG_ROWS
    )
    return {
        "ok": count_ok and sum_ok,
        "previous_change_reason": PREVIOUS_EVENT_CHANGE_REASON,
        "log_row_count": log_count,
        "distinct_product_ids": distinct,
        "expected_log_rows": EXPECTED_PREVIOUS_EVENT_LOG_ROWS,
        "live_priced_base_sum": str(live_sum) if live_sum is not None else sum_line,
        "expected_priced_base_sum": str(EXPECTED_PREVIOUS_EVENT_BASE_SUM),
        "sum_matches_post_oct19": sum_ok,
        "log_count_matches": count_ok,
    }

def fetch_brand(ssh_host: str) -> dict[str, Any]:
    raw = _run_ssh_psql(
        f"SELECT row_to_json(t)::text FROM (SELECT id, name FROM brands WHERE id={EXPECTED_BRAND_ID}) t;",
        ssh_host=ssh_host,
    )
    if not raw.strip():
        raise RuntimeError(f"brand_id={EXPECTED_BRAND_ID} missing")
    return json.loads(raw.splitlines()[-1])


def _reason_md5() -> str:
    return hashlib.md5(CHANGE_REASON.encode("utf-8")).hexdigest()


def _parse_kv_proof(output: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in output.splitlines():
        if "PROOF:" not in line:
            continue
        segment = line[line.index("PROOF:") :]
        parts = segment.split(":", 2)
        if len(parts) < 3:
            continue
        out[f"PROOF:{parts[1]}"] = parts[2].strip()
    return out


def collect_production_identity_proof(ssh_host: str) -> dict[str, Any]:
    """Independent SSH/docker/psql proof — not inferred from collector labels."""
    host_proof = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "hostname"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    vol_proof = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker inspect -f '{{range .Mounts}}{{.Name}} {{end}}' lathe_postgres",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    container_proof = (
        subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                ssh_host,
                "docker inspect -f '{{.Name}}' lathe_postgres",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .lstrip("/")
    )
    app_env_raw = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' lathe_api "
            "| grep -E '^(APP_ENV|KARZAR_DATA_PLANE)=' || true",
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    env_map: dict[str, str | None] = {"APP_ENV": None, "KARZAR_DATA_PLANE": None}
    for line in app_env_raw.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            if key in env_map:
                env_map[key] = value

    db_name = _run_ssh_psql("SELECT current_database();", ssh_host=ssh_host).splitlines()[-1].strip()
    db_user = _run_ssh_psql("SELECT current_user;", ssh_host=ssh_host).splitlines()[-1].strip()
    pg_sys = _run_ssh_psql(
        "SELECT system_identifier::text FROM pg_control_system();",
        ssh_host=ssh_host,
    ).splitlines()[-1].strip()
    alembic = _run_ssh_psql(
        "SELECT version_num FROM alembic_version LIMIT 1;",
        ssh_host=ssh_host,
    ).splitlines()[-1].strip()
    proof_raw = _run_ssh_psql_script(
        """
BEGIN;
SET TRANSACTION READ ONLY;
SELECT 'PROOF:transaction_read_only:' || current_setting('transaction_read_only');
ROLLBACK;
""",
        ssh_host=ssh_host,
        allow_commit=False,
    )
    kv = _parse_kv_proof(proof_raw)
    tro = kv.get("PROOF:transaction_read_only", "")
    proof = {
        "host_proof": host_proof,
        "container_proof": container_proof,
        "volume_proof": vol_proof,
        "database_proof": db_name,
        "database_user_proof": db_user,
        "pg_system_identifier": pg_sys,
        "alembic_revision": alembic,
        "transaction_read_only": tro,
        "APP_ENV": env_map["APP_ENV"],
        "karzar_data_plane": env_map["KARZAR_DATA_PLANE"],
        "gates": {
            "host_ok": host_proof == EXPECTED_VPS_HOSTNAME,
            "container_ok": EXPECTED_POSTGRES_CONTAINER in container_proof,
            "db_ok": db_name == EXPECTED_DATABASE,
            "user_ok": db_user == EXPECTED_DATABASE_USER,
            "volume_ok": EXPECTED_DOCKER_VOLUME in vol_proof,
            "pg_system_identifier_ok": pg_sys == EXPECTED_PG_SYSTEM_IDENTIFIER,
            "alembic_ok": alembic == EXPECTED_ALEMBIC_REVISION,
            "transaction_read_only_on": tro == "on",
        },
    }
    proof["identity_errors"] = validate_production_identity_gates(proof)
    return proof


def runtime_gate_errors(
    *,
    collector_identity: dict[str, Any],
    health: dict[str, Any],
    proof: dict[str, Any],
) -> list[str]:
    errors = list(proof.get("identity_errors") or [])
    errors.extend(reconcile_collector_vs_proof(collector_identity, proof))
    if not health.get("all_pass"):
        errors.append("health_all_pass_failed")
    return errors


def fetch_live_priced_cohort_ids(ssh_host: str) -> list[int]:
    raw = _run_ssh_psql(
        """
SELECT id::text FROM products
WHERE brand_id=3 AND deleted_at IS NULL
  AND base_price IS NOT NULL AND base_price > 0
ORDER BY id;
""",
        ssh_host=ssh_host,
    )
    ids: list[int] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.isdigit():
            ids.append(int(line))
    return ids


def verify_cohort_membership(
    manifest: list[dict[str, Any]],
    live_ids: list[int],
) -> dict[str, Any]:
    manifest_ids = {int(r["product_id"]) for r in manifest}
    live_set = set(live_ids)
    diff = cohort_id_set_diff(manifest_ids, live_set)
    return {
        "ok": not diff["extra_in_live"] and not diff["missing_from_live"],
        "manifest_ids": len(manifest_ids),
        "live_ids": len(live_set),
        **diff,
    }


def _original_clear_reason_md5() -> str:
    return hashlib.md5(ORIGINAL_PRICE_CLEAR_CHANGE_REASON.encode("utf-8")).hexdigest()


def idempotency_probe(ssh_host: str) -> dict[str, Any]:
    reason_md5 = _reason_md5()
    sql = f"""
SELECT COUNT(*)::text,
       COUNT(DISTINCT product_id)::text
FROM product_change_logs
WHERE md5(reason::text) = '{reason_md5}';
"""
    line = _run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1]
    parts = line.split("\t") if "\t" in line else line.split("|")
    count = int(parts[0]) if parts else 0
    distinct = int(parts[1]) if len(parts) > 1 else 0
    orig_md5 = _original_clear_reason_md5()
    orig_sql = f"""
SELECT COUNT(*)::text,
       COUNT(DISTINCT product_id)::text
FROM product_change_logs
WHERE md5(reason::text) = '{orig_md5}';
"""
    orig_line = _run_ssh_psql(orig_sql, ssh_host=ssh_host).splitlines()[-1]
    orig_parts = orig_line.split("\t") if "\t" in orig_line else orig_line.split("|")
    orig_count = int(orig_parts[0]) if orig_parts else 0
    orig_distinct = int(orig_parts[1]) if len(orig_parts) > 1 else 0
    return {
        "reason": CHANGE_REASON,
        "log_row_count": count,
        "distinct_product_id_count": distinct,
        "already_present": count > 0,
        "original_clear_reason": ORIGINAL_PRICE_CLEAR_CHANGE_REASON,
        "original_clear_log_row_count": orig_count,
        "original_clear_distinct_product_ids": orig_distinct,
        "original_clear_already_present": orig_count > 0,
    }


def fetch_insize_cohort(ssh_host: str) -> list[dict[str, Any]]:
    sql = """
SELECT row_to_json(t)::text FROM (
  SELECT p.id, p.sku, p.name, p.slug, p.brand_id, b.name AS brand_name,
         p.category_id, p.product_type_id,
         p.base_price::text AS old_base_price,
         p.original_price::text AS original_price,
         p.is_active, p.is_available, p.deleted_at
  FROM products p
  JOIN brands b ON b.id = p.brand_id
  WHERE p.brand_id = 3 AND p.deleted_at IS NULL
    AND p.base_price IS NOT NULL AND p.base_price > 0
  ORDER BY p.id
) t;
"""
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def insize_counts(ssh_host: str) -> dict[str, int]:
    sql = """
SELECT
  (SELECT COUNT(*) FROM products WHERE brand_id=3 AND deleted_at IS NULL),
  (SELECT COUNT(*) FROM products WHERE brand_id=3 AND deleted_at IS NULL
     AND base_price IS NOT NULL AND base_price > 0),
  (SELECT COUNT(*) FROM products WHERE brand_id=3 AND deleted_at IS NULL
     AND (base_price IS NULL OR base_price <= 0));
"""
    line = _run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1]
    parts = line.split("\t") if "\t" in line else line.split("|")
    return {
        "live_insize": int(parts[0]),
        "priced_insize": int(parts[1]),
        "unpriced_insize": int(parts[2]),
    }


def manifest_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    olds = [parse_money(r["old_base_price"]) for r in rows]
    news = [parse_money(r["proposed_base_price"]) for r in rows]
    assert all(o is not None and n is not None for o, n in zip(olds, news, strict=True))
    discount_changes = [r for r in rows if r.get("discount_impact")]
    return {
        "row_count": len(rows),
        "current_min": f"{min(olds):.2f}",
        "current_max": f"{max(olds):.2f}",
        "current_sum": f"{sum(olds):.2f}",
        "proposed_min": f"{min(news):.2f}",
        "proposed_max": f"{max(news):.2f}",
        "proposed_sum": f"{sum(news):.2f}",
        "discount_display_changes": len(discount_changes),
    }


def build_manifest(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    manifest = [build_manifest_row(r) for r in raw_rows]
    manifest.sort(key=lambda r: int(r["product_id"]))
    return manifest


def verify_frozen_manifest_against_live(
    manifest: list[dict[str, Any]],
    ssh_host: str,
    *,
    drift_sample_limit: int = 50,
) -> dict[str, Any]:
    """Fail-closed compare of frozen manifest vs live DB (read-only)."""
    from scripts.ops.phase2c_manufacturer_identity_apply_once import fetch_live_targets

    ids = [str(row["product_id"]) for row in manifest]
    live = fetch_live_targets(ids, ssh_host=ssh_host)
    drifts: list[dict[str, Any]] = []
    discount_impacts: list[dict[str, Any]] = []

    for row in manifest:
        pid = str(row["product_id"])
        sku = str(row.get("sku") or "").strip()
        live_row = live.get(pid)
        if live_row is None:
            drifts.append({"product_id": pid, "sku": sku, "reason": "missing_live_row"})
            continue
        if live_row.get("deleted_at"):
            drifts.append({"product_id": pid, "sku": sku, "reason": "soft_deleted"})
        brand_id = int(live_row.get("brand_id") or 0)
        if brand_id != EXPECTED_BRAND_ID:
            drifts.append(
                {
                    "product_id": pid,
                    "sku": sku,
                    "reason": "brand_id_mismatch",
                    "live_brand_id": brand_id,
                }
            )
        if (live_row.get("sku") or "").strip() != sku:
            drifts.append(
                {
                    "product_id": pid,
                    "sku": sku,
                    "reason": "sku_mismatch",
                    "live_sku": live_row.get("sku"),
                }
            )
        manifest_old = parse_money(str(row.get("old_base_price") or ""))
        live_old = parse_money(live_row.get("base_price") or "")
        if manifest_old is None or live_old is None:
            drifts.append({"product_id": pid, "sku": sku, "reason": "unparseable_base_price"})
            continue
        if manifest_old != live_old:
            drifts.append(
                {
                    "product_id": pid,
                    "sku": sku,
                    "reason": "base_price_drift",
                    "manifest_old_base_price": str(manifest_old),
                    "live_base_price": str(live_old),
                }
            )
        manifest_old_orig = parse_money(row.get("old_original_price"))
        live_original_all = parse_money(live_row.get("original_price") or "")
        if not money_equal_nullable(manifest_old_orig, live_original_all):
            drifts.append(
                {
                    "product_id": pid,
                    "sku": sku,
                    "reason": "old_original_price_drift",
                    "manifest_old_original_price": (
                        str(manifest_old_orig) if manifest_old_orig is not None else None
                    ),
                    "live_original_price": (
                        str(live_original_all) if live_original_all is not None else None
                    ),
                }
            )
        expected_new = proposed_base_price(live_old)
        manifest_new = parse_money(str(row.get("proposed_base_price") or ""))
        if manifest_new != expected_new:
            drifts.append(
                {
                    "product_id": pid,
                    "sku": sku,
                    "reason": "proposed_price_mismatch",
                    "manifest_proposed": str(manifest_new),
                    "expected_from_live": str(expected_new),
                }
            )
        live_original = parse_money(live_row.get("original_price") or "")
        manifest_prop_orig = row.get("proposed_original_price")
        proposed_orig = (
            None
            if manifest_prop_orig in (None, "", "null")
            else parse_money(str(manifest_prop_orig))
        )
        before = discount_display_state(base_price=live_old, original_price=live_original)
        after = discount_display_state(base_price=expected_new, original_price=proposed_orig)
        impact = None if before == after else {
            "before": before,
            "after": after,
            "original_price": str(live_original) if live_original is not None else None,
            "old_base_price": str(live_old),
            "new_base_price": str(expected_new),
        }
        if impact:
            discount_impacts.append({"product_id": int(pid), "sku": sku, **impact})

    return {
        "ok": len(drifts) == 0,
        "manifest_rows": len(manifest),
        "live_rows_fetched": len(live),
        "drift_count": len(drifts),
        "drifts_sample": drifts[:drift_sample_limit],
        "drifts_truncated": len(drifts) > drift_sample_limit,
        "discount_display_changes": len(discount_impacts),
        "discount_impacts_sample": discount_impacts[:30],
    }


def write_manifest_artifacts(
    out_dir: Path,
    manifest: list[dict[str, Any]],
    stamp: str,
) -> dict[str, Any]:
    csv_path = out_dir / f"INSIZE_PRICE_110_20261021_MANIFEST_{stamp}.csv"
    json_path = out_dir / f"INSIZE_PRICE_110_20261021_MANIFEST_{stamp}.json"
    flat_rows = []
    for row in manifest:
        flat = {k: row.get(k) for k in MANIFEST_FIELDS}
        if "authorized_original_price_exception" in flat:
            flat["authorized_original_price_exception"] = bool(
                flat["authorized_original_price_exception"]
            )
        flat_rows.append(flat)
    write_csv(csv_path, flat_rows, MANIFEST_FIELDS)
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "formula": f"proposed_base_price = quantize(old_base_price * {MULTIPLIER}, 0.01, ROUND_HALF_UP)",
        "authority": "current_live_priced_cohort",
        "brand_id": EXPECTED_BRAND_ID,
        "brand_name": EXPECTED_BRAND_NAME,
        "commercial_event_id": COMMERCIAL_EVENT_ID,
        "change_reason": CHANGE_REASON,
        "price_currency": PRICE_CURRENCY_LABEL,
        "authorized_original_price_exceptions": sorted(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS),
        "merchandising_exception_comparisons": [
            merchandising_exception_comparison(r)
            for r in manifest
            if r.get("authorized_original_price_exception")
        ],
        "stats": manifest_stats(manifest),
        "rows": manifest,
    }
    write_json(json_path, payload)
    return {
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "csv_sha256": sha256_file(csv_path),
        "json_sha256": sha256_file(json_path),
        "rows": len(manifest),
    }


def post_apply_verify(ssh_host: str, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    reason_md5 = _reason_md5()
    orig_md5 = _original_clear_reason_md5()
    exact = 0
    formula_ok = 0
    orig_null_exception = 0
    orig_unchanged_non_exception = 0
    unexpected_original_mutations = 0
    for row in manifest:
        pid = int(row["product_id"])
        old = row["old_base_price"]
        new = row["proposed_base_price"]
        expected_new = parse_money(new)
        old_orig = parse_money(row.get("old_original_price"))
        is_exception = bool(row.get("authorized_original_price_exception"))
        raw_base = _run_ssh_psql(
            f"SELECT base_price::text FROM products WHERE id={pid} AND brand_id=3;",
            ssh_host=ssh_host,
        ).strip()
        cur = parse_money(raw_base)
        old_d = parse_money(old)
        if cur is not None and expected_new is not None and cur == expected_new:
            exact += 1
        if cur is not None and old_d is not None and cur == proposed_base_price(old_d):
            formula_ok += 1
        raw_orig = _run_ssh_psql(
            f"SELECT original_price::text FROM products WHERE id={pid} AND brand_id=3;",
            ssh_host=ssh_host,
        ).strip()
        live_orig = parse_money(raw_orig) if raw_orig and raw_orig.lower() != "null" else None
        if is_exception:
            if live_orig is None:
                orig_null_exception += 1
            else:
                unexpected_original_mutations += 1
        elif money_equal_nullable(live_orig, old_orig):
            orig_unchanged_non_exception += 1
        else:
            unexpected_original_mutations += 1
    base_log_sql = f"""
SELECT COUNT(*)::text, COUNT(DISTINCT product_id)::text
FROM product_change_logs WHERE md5(reason::text) = '{reason_md5}';
"""
    base_log_line = _run_ssh_psql(base_log_sql, ssh_host=ssh_host).splitlines()[-1]
    base_parts = base_log_line.split("\t") if "\t" in base_log_line else base_log_line.split("|")
    base_log_count = int(base_parts[0])
    base_log_distinct = int(base_parts[1]) if len(base_parts) > 1 else 0
    orig_log_sql = f"""
SELECT COUNT(*)::text, COUNT(DISTINCT product_id)::text
FROM product_change_logs WHERE md5(reason::text) = '{orig_md5}';
"""
    orig_log_line = _run_ssh_psql(orig_log_sql, ssh_host=ssh_host).splitlines()[-1]
    orig_parts = orig_log_line.split("\t") if "\t" in orig_log_line else orig_log_line.split("|")
    orig_log_count = int(orig_parts[0])
    orig_log_distinct = int(orig_parts[1]) if len(orig_parts) > 1 else 0
    unexpected_orig_logs_sql = f"""
SELECT COUNT(*)::text FROM product_change_logs
WHERE field_name = 'original_price'
  AND md5(reason::text) NOT IN ('{orig_md5}');
"""
    unexpected_orig_logs = int(
        _run_ssh_psql(unexpected_orig_logs_sql, ssh_host=ssh_host).splitlines()[-1].strip() or 0
    )
    sum_sql = """
SELECT COALESCE(SUM(base_price),0)::text
FROM products WHERE brand_id=3 AND deleted_at IS NULL
  AND base_price IS NOT NULL AND base_price > 0;
"""
    price_sum = _run_ssh_psql(sum_sql, ssh_host=ssh_host).strip()
    return {
        "target_rows": len(manifest),
        "price_exact_match": exact,
        "formula_matches": formula_ok,
        "base_change_log_rows": base_log_count,
        "original_change_log_rows": orig_log_count,
        "total_event_log_rows": base_log_count + orig_log_count,
        "change_log_rows_with_reason": base_log_count,
        "distinct_changed_product_ids": base_log_distinct,
        "duplicate_mutations": max(0, base_log_count - base_log_distinct),
        "original_null_exception_count": orig_null_exception,
        "original_unchanged_non_exception_count": orig_unchanged_non_exception,
        "unexpected_original_mutations": unexpected_original_mutations,
        "unexpected_original_change_logs": unexpected_orig_logs,
        "original_clear_log_distinct_product_ids": orig_log_distinct,
        "sum_base_price_post": price_sum,
    }


def load_manifest_csv(path: Path) -> tuple[list[dict[str, Any]], str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    with resolved.open(encoding="utf-8", newline="") as fh:
        raw_rows = list(csv.DictReader(fh))
    manifest = normalize_manifest_from_csv_rows(raw_rows)
    return manifest, sha256_file(resolved)


def run_frozen_manifest_handoff_verification(
    manifest_path: Path,
    *,
    ssh_host: str,
) -> dict[str, Any]:
    """Full read-only handoff gate for the owner-frozen manifest."""
    manifest, csv_sha = load_manifest_csv(manifest_path)
    authority = validate_frozen_manifest_authority(manifest, csv_sha256=csv_sha)
    live_cohort_ids = fetch_live_priced_cohort_ids(ssh_host)
    cohort_membership = verify_cohort_membership(manifest, live_cohort_ids)
    drift_report = verify_frozen_manifest_against_live(manifest, ssh_host)
    idem = idempotency_probe(ssh_host)
    counts = insize_counts(ssh_host)
    readiness = evaluate_frozen_handoff_readiness(
        manifest_authority=authority,
        cohort_membership=cohort_membership,
        drift_report=drift_report,
        idempotency=idem,
        priced_census=counts["priced_insize"],
    )
    return {
        **readiness,
        "manifest_csv": str(manifest_path.resolve()),
        "manifest_csv_sha256": csv_sha,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "insize_counts": counts,
    }


def require_frozen_manifest_for_mutation(args: argparse.Namespace) -> int | None:
    """Return exit code if --apply/--rehearsal missing frozen manifest flags."""
    if not (args.apply or args.rehearsal):
        return None
    if not args.manifest_csv:
        print(
            "FATAL: --manifest-csv is required for --apply and --rehearsal "
            "(owner-frozen manifest only; live re-snapshot forbidden).",
            file=sys.stderr,
        )
        return 2
    confirm = args.confirm_manifest_sha.strip().lower()
    if confirm != FROZEN_MANIFEST_SHA256.lower():
        print(
            f"FATAL: --confirm-manifest-sha must equal owner-frozen SHA256 "
            f"{FROZEN_MANIFEST_SHA256}",
            file=sys.stderr,
        )
        return 2
    return None


def api_spot_check(
    manifest: list[dict[str, Any]],
    *,
    minimum_verified: int = MIN_PUBLIC_API_PRICE_VERIFICATIONS,
) -> dict[str, Any]:
    picks = select_public_api_verification_candidates(
        manifest,
        minimum=minimum_verified,
    )
    results: list[dict[str, Any]] = []
    for row in picks:
        slug = str(row["slug"])
        url = f"https://api.karzartools.com/api/v1/products/{slug}"
        http_ok = False
        http_status: int | None = None
        api_price: str | None = None
        error: str | None = None
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                http_status = int(resp.status)
                body = json.loads(resp.read().decode())
            data = body.get("data") or body
            api_price = str(data.get("base_price"))
            http_ok = True
        except urllib.error.HTTPError as exc:
            http_status = int(exc.code)
            error = str(exc)
            http_ok = False
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            http_ok = False
        results.append(
            classify_api_sample_result(
                row=row,
                http_ok=http_ok,
                http_status=http_status,
                api_base_price=api_price,
                error=error,
            )
        )
    summary = evaluate_api_verification(results, required_verified=minimum_verified)
    return {"samples": results, **summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="INSIZE +10% price APPLY (Category B)")
    parser.add_argument("--ssh-host", default=DEFAULT_SSH)
    parser.add_argument("--out-dir", type=Path, default=AUDIT_OUT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-manifest-sha", default="")
    parser.add_argument("--rehearsal", action="store_true", help="Run apply SQL then ROLLBACK")
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=None,
        help="Apply using frozen manifest CSV (skip live re-snapshot)",
    )
    parser.add_argument(
        "--verify-frozen-manifest",
        type=Path,
        default=None,
        help="Read-only drift check of frozen manifest CSV vs live DB; then exit",
    )
    args = parser.parse_args()

    mutation_gate = require_frozen_manifest_for_mutation(args)
    if mutation_gate is not None:
        return mutation_gate

    if args.verify_frozen_manifest:
        path = args.verify_frozen_manifest.resolve()
        if not path.is_file():
            print(f"FATAL: missing manifest {path}", file=sys.stderr)
            return 2
        report = run_frozen_manifest_handoff_verification(path, ssh_host=args.ssh_host)
        out_path = AUDIT_OUT / "MANIFEST_DRIFT_REPORT.json"
        write_json(out_path, report)
        print(json.dumps(report, indent=2))
        return 0 if report.get("ok") else 3

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ssh_host = args.ssh_host

    identity = collect_runtime_identity(ssh_host)
    health = collect_live_health(ssh_host)
    identity_proof = collect_production_identity_proof(ssh_host)
    brand = fetch_brand(ssh_host)
    counts = insize_counts(ssh_host)
    live_cohort_ids = fetch_live_priced_cohort_ids(ssh_host)
    idem = idempotency_probe(ssh_host)
    previous_event = verify_previous_event_completion(ssh_host)

    brand_ok = int(brand["id"]) == EXPECTED_BRAND_ID and brand.get("name") == EXPECTED_BRAND_NAME
    errors: list[str] = []
    errors.extend(runtime_gate_errors(collector_identity=identity, health=health, proof=identity_proof))
    if not brand_ok:
        errors.append("brand identity mismatch")
    if not previous_event.get("ok"):
        errors.append("previous_event_incomplete_or_unverified")
    if idem["already_present"]:
        errors.append("idempotency: change logs already present for this event reason")
    if idem.get("original_clear_already_present"):
        errors.append("idempotency: original_price clear logs already present")
    if counts["priced_insize"] == 0:
        errors.append("empty priced cohort")

    discount_rows: list[Any] = []
    drift_report: dict[str, Any] | None = None
    cohort_membership: dict[str, Any] | None = None
    manifest_authority: dict[str, Any] | None = None
    semantics_blockers: list[dict[str, Any]] = []

    if args.manifest_csv:
        manifest_csv = args.manifest_csv.resolve()
        try:
            manifest, manifest_sha = load_manifest_csv(manifest_csv)
        except FileNotFoundError:
            errors.append(f"missing manifest csv: {manifest_csv}")
            manifest = []
            manifest_sha = ""
            manifest_info = {"rows": 0, "csv_sha256": "", "csv_path": str(manifest_csv)}
        else:
            manifest_info = {
                "csv_path": str(manifest_csv),
                "csv_sha256": manifest_sha,
                "rows": len(manifest),
            }
            manifest_authority = validate_frozen_manifest_authority(
                manifest, csv_sha256=manifest_sha
            )
            commercial = validate_owner_frozen_commercial_contract(manifest)
            if not commercial["ok"]:
                errors.extend(commercial["errors"][:10])
                manifest_authority = {
                    **manifest_authority,
                    "ok": False,
                    "errors": (manifest_authority.get("errors") or [])
                    + ["commercial_contract_failed"],
                }
            if not manifest_authority["ok"]:
                errors.extend(manifest_authority["errors"])
            handoff = evaluate_frozen_handoff_readiness(
                manifest_authority=manifest_authority,
                cohort_membership=verify_cohort_membership(manifest, live_cohort_ids),
                drift_report=verify_frozen_manifest_against_live(manifest, ssh_host),
                idempotency=idem,
                priced_census=counts["priced_insize"],
            )
            cohort_membership = handoff["cohort_membership"]
            drift_report = handoff["drift"]
            write_json(out_dir / f"MANIFEST_DRIFT_{stamp}.json", handoff)
            if not handoff["ok"]:
                errors.extend(handoff["blockers"])
            semantics_blockers = find_discount_semantics_blockers(manifest)
            if semantics_blockers:
                errors.append(f"discount_semantics_blockers:{len(semantics_blockers)}")
            discount_rows = list(drift_report.get("discount_impacts_sample", []))
    elif args.apply or args.rehearsal:
        errors.append("frozen manifest required for mutation paths")
        manifest = []
        manifest_info = {"rows": 0, "csv_sha256": "", "csv_path": ""}
    else:
        raw_rows = fetch_insize_cohort(ssh_host)
        if len(raw_rows) != counts["priced_insize"]:
            errors.append(
                f"cohort count mismatch: fetched={len(raw_rows)} census={counts['priced_insize']}"
            )
        manifest = build_manifest(raw_rows)
        semantics_blockers = find_discount_semantics_blockers(manifest)
        if semantics_blockers:
            errors.append(f"discount_semantics_blockers:{len(semantics_blockers)}")
        cohort_membership = verify_cohort_membership(manifest, live_cohort_ids)
        if not cohort_membership["ok"]:
            errors.append(
                "live cohort membership mismatch during snapshot: "
                f"extra={cohort_membership['extra_in_live'][:5]} "
                f"missing={cohort_membership['missing_from_live'][:5]}"
            )
        manifest_info = write_manifest_artifacts(out_dir, manifest, stamp)
    if not args.manifest_csv:
        discount_rows = [r for r in manifest if r.get("discount_impact")]
    write_json(out_dir / f"DISCOUNT_IMPACT_{stamp}.json", discount_rows)

    recovery_csv = out_dir / f"INSIZE_PRICE_110_20261021_RECOVERY_PREWRITE_{stamp}.csv"
    recovery_rows = [
        {
            "product_id": r["product_id"],
            "sku": r["sku"],
            "base_price": r["old_base_price"],
            "original_price": r.get("old_original_price"),
        }
        for r in manifest
    ]
    write_csv(
        recovery_csv,
        recovery_rows,
        ["product_id", "sku", "base_price", "original_price"],
    )
    rollback_path = out_dir / f"INSIZE_PRICE_110_20261021_ROLLBACK_{stamp}.sql"
    assert_evidence_writable(rollback_path)
    rollback_path.write_text(build_rollback_sql(manifest), encoding="utf-8")

    report: dict[str, Any] = {
        "STATUS": "PREFLIGHT",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stamp": stamp,
        "price_currency": PRICE_CURRENCY_LABEL,
        "formula": f"new_base_price = quantize(old * {MULTIPLIER}, 0.01, ROUND_HALF_UP)",
        "commercial_event_id": COMMERCIAL_EVENT_ID,
        "change_reason": CHANGE_REASON,
        "PREVIOUS_EVENT_VERIFICATION": previous_event,
        "DISCOUNT_SEMANTICS_BLOCKERS": semantics_blockers,
        "RUNTIME": {
            "identity": identity,
            "identity_proof": identity_proof,
            "health": health,
            "cohort_membership": cohort_membership,
        },
        "BRAND": {"ok": brand_ok, "brand": brand, "errors": errors},
        "IDEMPOTENCY": idem,
        "INSIZE_COUNTS": counts,
        "MANIFEST": manifest_info,
        "FROZEN_MANIFEST_AUTHORITY": manifest_authority,
        "FROZEN_MANIFEST_SHA256_REQUIRED": FROZEN_MANIFEST_SHA256,
        "DISCOUNT_IMPACT_COUNT": (
            drift_report.get("discount_display_changes", len(discount_rows))
            if drift_report
            else len(discount_rows)
        ),
        "MANIFEST_DRIFT": drift_report,
        "RECOVERY": {
            "recovery_csv": str(recovery_csv),
            "recovery_csv_sha256": sha256_file(recovery_csv),
            "rollback_sql": str(rollback_path),
            "rollback_sql_sha256": sha256_file(rollback_path),
        },
        "git_sha": _git_head(),
    }

    if errors and (args.apply or args.rehearsal):
        report["STATUS"] = "BLOCKED"
        write_json(out_dir / "APPLY_REPORT.json", report)
        print(json.dumps(report, indent=2))
        return 4

    apply_sql = build_real_apply_sql(
        manifest,
        expected_rows=len(manifest),
        manifest_sha256=manifest_info["csv_sha256"],
    )

    if args.rehearsal:
        rehearsal_sql = apply_sql.replace("COMMIT;", "ROLLBACK;")
        out = _run_ssh_psql_script(rehearsal_sql, ssh_host=ssh_host, allow_commit=False)
        report["REHEARSAL"] = {
            "status": "ROLLED_BACK",
            "output_tail": out[-2000:],
            "contract": rehearsal_contract_summary(),
        }
        report["STATUS"] = "REHEARSAL_OK"
        write_json(out_dir / "APPLY_REPORT.json", report)
        print(json.dumps(report, indent=2))
        return 0

    if not args.apply:
        report["STATUS"] = "PREFLIGHT_BLOCKED" if errors else "PREFLIGHT_OK"
        report["PREFLIGHT_ERRORS"] = errors
        write_json(out_dir / "APPLY_REPORT.json", report)
        print(json.dumps(report, indent=2))
        return 3 if errors else 0

    _require_category_b()
    if manifest_info["csv_sha256"].lower() != FROZEN_MANIFEST_SHA256.lower():
        print(
            f"FATAL: manifest file SHA256 must equal owner-frozen "
            f"{FROZEN_MANIFEST_SHA256}",
            file=sys.stderr,
        )
        return 2

    backup = create_live_backup(ssh_host=ssh_host, backup_dir=args.backup_dir)
    write_json(out_dir / "BACKUP_MANIFEST.json", backup)

    apply_out = _run_ssh_psql_script(apply_sql, ssh_host=ssh_host, allow_commit=True)
    verify = post_apply_verify(ssh_host, manifest)
    api_verify = api_spot_check(manifest)

    pre_sum = Decimal(manifest_stats(manifest)["current_sum"])
    db_eval = evaluate_db_post_apply_verification(
        verify,
        expected_rows=len(manifest),
        expected_sum=EXPECTED_POST_APPLY_BASE_SUM,
    )
    api_ok = bool(api_verify.get("api_verification_ok"))
    db_ok = bool(db_eval.get("db_verification_ok"))
    status, final_line = resolve_post_commit_status(
        db_committed=True,
        db_verification_ok=db_ok,
        api_verification_ok=api_ok,
    )

    report["BACKUP"] = backup
    report["DB_COMMIT"] = {
        "status": "COMMITTED",
        "transaction_output_tail": apply_out[-3000:],
        "do_not_rerun_apply_after_commit": True,
    }
    report["INSIZE_APPLY"] = {
        "manifest_rows": len(manifest),
        "manifest_sha256_csv": manifest_info["csv_sha256"],
        "updated_rows": verify["price_exact_match"],
    }
    report["INSIZE_POST"] = verify
    report["DB_VERIFICATION"] = db_eval
    report["SITE_VERIFY"] = api_verify
    report["PRICE_TOTALS"] = {
        "before_sum": str(pre_sum),
        "after_sum": db_eval.get("sum_base_price_post"),
        "expected_after_sum": str(EXPECTED_POST_APPLY_BASE_SUM),
    }
    report["ROLLBACK_PREP"] = {
        "rollback_sql": str(rollback_path),
        "rollback_change_reason": ROLLBACK_CHANGE_REASON,
        "auto_execute_on_verify_failure": False,
        "note": "Rollback is prepared evidence only; separate human authorization required.",
    }
    report["STATUS"] = status
    report["FINAL_LINE"] = final_line
    write_json(out_dir / "APPLY_REPORT.json", report)
    write_json(
        out_dir / "VERIFY_REPORT.json",
        {
            "db_commit": report["DB_COMMIT"],
            "db_verification": db_eval,
            "api_verification": api_verify,
            "status": status,
        },
    )
    print(json.dumps(report, indent=2))
    return 0 if status == "COMMITTED_VERIFIED" else 5


if __name__ == "__main__":
    raise SystemExit(main())
