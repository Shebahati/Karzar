#!/usr/bin/env python3
"""INSIZE +10% owner-authorized base_price APPLY (Category B, one-shot).

Dry-run by default. Persistent mutation requires:
  KARZAR_ALLOW_PRODUCTION_WRITE=1
  KARZAR_INGESTION_CATEGORY=B
  --apply
  --confirm-manifest-sha <SHA256 of manifest CSV>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.insize_price_110 import (  # noqa: E402
    CHANGE_REASON,
    EXPECTED_BRAND_ID,
    EXPECTED_BRAND_NAME,
    MULTIPLIER,
    build_manifest_row,
    build_real_apply_sql,
    build_rollback_sql,
    discount_impact_row,
    parse_money,
    proposed_base_price,
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

AUDIT_OUT = ROOT / "audit" / "insize-price-110"
DEFAULT_BACKUP_DIR = Path.home() / "karzar-backups" / "insize-price-110"
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
    "original_price",
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
    return {
        "reason": CHANGE_REASON,
        "log_row_count": count,
        "distinct_product_id_count": distinct,
        "already_present": count > 0,
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
        original = parse_money(live_row.get("original_price") or "")
        impact = discount_impact_row(
            old_base=live_old,
            new_base=expected_new,
            original_price=original,
        )
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
    csv_path = out_dir / f"INSIZE_PRICE_110_MANIFEST_{stamp}.csv"
    json_path = out_dir / f"INSIZE_PRICE_110_MANIFEST_{stamp}.json"
    flat_rows = [{k: row.get(k) for k in MANIFEST_FIELDS} for row in manifest]
    write_csv(csv_path, flat_rows, MANIFEST_FIELDS)
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "formula": f"proposed_base_price = quantize(old_base_price * {MULTIPLIER}, 0.01, ROUND_HALF_UP)",
        "authority": "current_live_priced_cohort",
        "brand_id": EXPECTED_BRAND_ID,
        "brand_name": EXPECTED_BRAND_NAME,
        "change_reason": CHANGE_REASON,
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
    exact = 0
    formula_ok = 0
    for row in manifest:
        pid = int(row["product_id"])
        old = row["old_base_price"]
        new = row["proposed_base_price"]
        raw = _run_ssh_psql(
            f"SELECT base_price::text FROM products WHERE id={pid} AND brand_id=3;",
            ssh_host=ssh_host,
        ).strip()
        if raw == new:
            exact += 1
        cur = parse_money(raw)
        old_d = parse_money(old)
        if cur is not None and old_d is not None and cur == proposed_base_price(old_d):
            formula_ok += 1
    log_sql = f"""
SELECT COUNT(*)::text, COUNT(DISTINCT product_id)::text
FROM product_change_logs WHERE md5(reason::text) = '{reason_md5}';
"""
    log_line = _run_ssh_psql(log_sql, ssh_host=ssh_host).splitlines()[-1]
    log_parts = log_line.split("\t") if "\t" in log_line else log_line.split("|")
    log_count = int(log_parts[0])
    log_distinct = int(log_parts[1]) if len(log_parts) > 1 else 0
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
        "change_log_rows_with_reason": log_count,
        "distinct_changed_product_ids": log_distinct,
        "duplicate_mutations": max(0, log_count - log_distinct),
        "sum_base_price_post": price_sum,
    }


def api_spot_check(manifest: list[dict[str, Any]], sample: int = 5) -> dict[str, Any]:
    picks = manifest[:sample] + manifest[-sample:]
    seen: set[int] = set()
    results: list[dict[str, Any]] = []
    for row in picks:
        pid = int(row["product_id"])
        if pid in seen:
            continue
        seen.add(pid)
        slug = row["slug"]
        url = f"https://api.karzartools.com/api/v1/products/{slug}"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                body = json.loads(resp.read().decode())
            data = body.get("data") or body
            api_price = str(data.get("base_price"))
            results.append(
                {
                    "product_id": pid,
                    "slug": slug,
                    "expected_base_price": row["proposed_base_price"],
                    "api_base_price": api_price,
                    "match": api_price == row["proposed_base_price"],
                    "http_ok": True,
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "product_id": pid,
                    "slug": slug,
                    "expected_base_price": row["proposed_base_price"],
                    "http_ok": False,
                    "error": str(exc),
                }
            )
    return {"samples": results, "all_match": all(r.get("match") for r in results if r.get("http_ok"))}


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

    if args.verify_frozen_manifest:
        path = args.verify_frozen_manifest.resolve()
        if not path.is_file():
            print(f"FATAL: missing manifest {path}", file=sys.stderr)
            return 2
        with path.open(encoding="utf-8", newline="") as fh:
            manifest = list(csv.DictReader(fh))
        drift = verify_frozen_manifest_against_live(manifest, args.ssh_host)
        drift["manifest_csv"] = str(path)
        drift["manifest_csv_sha256"] = sha256_file(path)
        drift["generated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        out_path = AUDIT_OUT / "MANIFEST_DRIFT_REPORT.json"
        write_json(out_path, drift)
        print(json.dumps(drift, indent=2))
        return 0 if drift["ok"] else 3

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ssh_host = args.ssh_host

    identity = collect_runtime_identity(ssh_host)
    health = collect_live_health(ssh_host)
    brand = fetch_brand(ssh_host)
    counts = insize_counts(ssh_host)
    idem = idempotency_probe(ssh_host)

    brand_ok = int(brand["id"]) == EXPECTED_BRAND_ID and brand.get("name") == EXPECTED_BRAND_NAME
    errors: list[str] = []
    if not brand_ok:
        errors.append("brand identity mismatch")
    if idem["already_present"]:
        errors.append("idempotency: change logs already present for this event reason")
    if counts["priced_insize"] == 0:
        errors.append("empty priced cohort")

    discount_rows: list[Any] = []
    drift_report: dict[str, Any] | None = None

    if args.manifest_csv:
        manifest_csv = args.manifest_csv.resolve()
        if not manifest_csv.is_file():
            errors.append(f"missing manifest csv: {manifest_csv}")
            manifest = []
            manifest_info = {"rows": 0, "csv_sha256": "", "csv_path": str(manifest_csv)}
        else:
            with manifest_csv.open(encoding="utf-8", newline="") as fh:
                manifest = list(csv.DictReader(fh))
            manifest_info = {
                "csv_path": str(manifest_csv),
                "csv_sha256": sha256_file(manifest_csv),
                "rows": len(manifest),
            }
            if len(manifest) != counts["priced_insize"]:
                errors.append(
                    f"manifest rows {len(manifest)} != live priced census {counts['priced_insize']}"
                )
            drift_report = verify_frozen_manifest_against_live(manifest, ssh_host)
            write_json(out_dir / f"MANIFEST_DRIFT_{stamp}.json", drift_report)
            if not drift_report["ok"]:
                errors.append(
                    f"frozen manifest drift: {drift_report['drift_count']} row(s) — see MANIFEST_DRIFT_{stamp}.json"
                )
            discount_rows = list(drift_report.get("discount_impacts_sample", []))
    else:
        raw_rows = fetch_insize_cohort(ssh_host)
        if len(raw_rows) != counts["priced_insize"]:
            errors.append(
                f"cohort count mismatch: fetched={len(raw_rows)} census={counts['priced_insize']}"
            )
        manifest = build_manifest(raw_rows)
        manifest_info = write_manifest_artifacts(out_dir, manifest, stamp)
    if not args.manifest_csv:
        discount_rows = [r for r in manifest if r.get("discount_impact")]
    write_json(out_dir / f"DISCOUNT_IMPACT_{stamp}.json", discount_rows)

    recovery_csv = out_dir / f"INSIZE_PRICE_110_RECOVERY_PREWRITE_{stamp}.csv"
    recovery_rows = [
        {"product_id": r["product_id"], "sku": r["sku"], "base_price": r["old_base_price"]}
        for r in manifest
    ]
    write_csv(recovery_csv, recovery_rows, ["product_id", "sku", "base_price"])
    rollback_path = out_dir / f"INSIZE_PRICE_110_ROLLBACK_{stamp}.sql"
    assert_evidence_writable(rollback_path)
    rollback_path.write_text(build_rollback_sql(manifest), encoding="utf-8")

    report: dict[str, Any] = {
        "STATUS": "PREFLIGHT",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stamp": stamp,
        "formula": f"new_base_price = quantize(old * {MULTIPLIER}, 0.01, ROUND_HALF_UP)",
        "change_reason": CHANGE_REASON,
        "RUNTIME": {"identity": identity, "health": health},
        "BRAND": {"ok": brand_ok, "brand": brand, "errors": errors},
        "IDEMPOTENCY": idem,
        "INSIZE_COUNTS": counts,
        "MANIFEST": manifest_info,
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

    if errors and args.apply:
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
        report["REHEARSAL"] = {"status": "ROLLED_BACK", "output_tail": out[-2000:]}
        report["STATUS"] = "REHEARSAL_OK"
        write_json(out_dir / "APPLY_REPORT.json", report)
        print(json.dumps(report, indent=2))
        return 0

    if not args.apply:
        report["STATUS"] = "PREFLIGHT_OK"
        write_json(out_dir / "APPLY_REPORT.json", report)
        print(json.dumps(report, indent=2))
        return 0

    _require_category_b()
    confirm = args.confirm_manifest_sha.strip().lower()
    if confirm != manifest_info["csv_sha256"]:
        print(
            f"FATAL: --confirm-manifest-sha mismatch "
            f"(expected {manifest_info['csv_sha256']})",
            file=sys.stderr,
        )
        return 2

    backup = create_live_backup(ssh_host=ssh_host, backup_dir=args.backup_dir)
    write_json(out_dir / "BACKUP_MANIFEST.json", backup)

    apply_out = _run_ssh_psql_script(apply_sql, ssh_host=ssh_host, allow_commit=True)
    verify = post_apply_verify(ssh_host, manifest)
    api_verify = api_spot_check(manifest)

    pre_sum = Decimal(manifest_stats(manifest)["current_sum"])
    post_sum = Decimal(verify.get("sum_base_price_post") or "0")

    report["BACKUP"] = backup
    report["INSIZE_APPLY"] = {
        "manifest_rows": len(manifest),
        "manifest_sha256_csv": manifest_info["csv_sha256"],
        "updated_rows": verify["price_exact_match"],
        "transaction_output_tail": apply_out[-3000:],
    }
    report["INSIZE_POST"] = verify
    report["SITE_VERIFY"] = api_verify
    report["PRICE_TOTALS"] = {
        "before_sum": str(pre_sum),
        "after_sum": str(post_sum),
    }

    all_ok = (
        verify["price_exact_match"] == len(manifest)
        and verify["change_log_rows_with_reason"] == len(manifest)
        and verify["duplicate_mutations"] == 0
        and (
            idem["log_row_count"] == 0
            or verify["change_log_rows_with_reason"] == len(manifest)
        )
    )
    report["STATUS"] = "APPLIED" if all_ok else "PARTIALLY_VERIFIED"
    report["FINAL_LINE"] = "INSIZE_PRICE_110_APPLY_OK" if all_ok else "INSIZE_PRICE_110_VERIFY_INCOMPLETE"
    write_json(out_dir / "APPLY_REPORT.json", report)
    write_json(out_dir / "VERIFY_REPORT.json", {"verify": verify, "api": api_verify})
    print(json.dumps(report, indent=2))
    return 0 if all_ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
