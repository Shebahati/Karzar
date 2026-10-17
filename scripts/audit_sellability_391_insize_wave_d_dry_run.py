#!/usr/bin/env python3
"""Issue #391 — INSIZE Wave D guarded dry-run (NO APPLY, NO production mutation)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.core import canonicalize_brand, normalize_sku  # noqa: E402
from catalog_target.supplier_stock import FreshnessPolicy, file_sha256, parse_quantity  # noqa: E402

from audit_sellability_391_insize_wave_a import (  # noqa: E402
    INSIZE_CANONICAL_SHA,
    INSIZE_CANONICAL_XLSX,
    INSIZE_SOURCE_DATE,
    INSIZE_SOURCE_DATE_EVIDENCE,
    _alembic_head,
    _copy_csv,
    _image_exists_sql,
    _read_only_session_proof,
    _run_ssh_psql,
    _scalar,
    _ssh,
    collect_fresh_census,
    export_catalog_products,
    insize_validation_report,
    load_insize_workbook_index,
    match_method_label,
    map_stock_to_catalog,
    write_json,
)

EXPECTED_PR488_HEAD = "10c2e53615aef70824be251a52d28340b06961ad"

# Owner-reviewed immutable allowlist (product IDs + catalog SKUs + expected source codes).
IMMUTABLE_ALLOWLIST: list[dict[str, str]] = [
    {"product_id": "1788", "catalog_sku": "1111-100", "source_code": "1111-100A"},
    {"product_id": "1795", "catalog_sku": "1120-150", "source_code": "1120-150A"},
    {"product_id": "2100", "catalog_sku": "8601-100", "source_code": "8601-100"},
    {"product_id": "3483", "catalog_sku": "2308-10", "source_code": "2308-10A"},
    {"product_id": "3550", "catalog_sku": "3109-25", "source_code": "3109-25A"},
    {"product_id": "3556", "catalog_sku": "3203-25", "source_code": "3203-25A"},
    {"product_id": "3618", "catalog_sku": "2310-30", "source_code": "2310-30A"},
    {"product_id": "3620", "catalog_sku": "2313-1", "source_code": "2313-1A"},
    {"product_id": "3763", "catalog_sku": "2383-08", "source_code": "2383-08A"},
    {"product_id": "4140", "catalog_sku": "5042", "source_code": "5042"},
]


def _git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _pr488_ci_state() -> dict[str, str]:
    proc = subprocess.run(
        ["gh", "pr", "checks", "488"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    text = proc.stdout or ""
    if proc.returncode not in {0, 8} and not text.strip():
        return {"gate": "UNKNOWN", "detail": proc.stderr.strip() or "no checks output"}
    pending: list[str] = []
    failing: list[str] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name, state = parts[0].strip(), parts[1].strip().lower()
        if state == "pending":
            pending.append(name)
        elif state in {"fail", "failure", "cancelled"}:
            failing.append(name)
    if failing:
        return {"gate": "FAIL", "detail": ",".join(failing)}
    if pending:
        return {"gate": "PENDING", "detail": ",".join(pending)}
    return {"gate": "PASS", "detail": "all reported checks pass"}


def state_hash_row(row: dict[str, str]) -> str:
    payload = "|".join(
        [
            row["product_id"],
            row.get("sku") or "",
            row.get("brand_id") or "",
            row.get("is_active") or "",
            row.get("is_available") or "",
            row.get("base_price") or "",
            row.get("deleted_at") or "NULL",
            row.get("image_present") or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def production_allowlist_rows(ssh_host: str, snapshot_utc: str) -> list[dict[str, str]]:
    ids = ",".join(entry["product_id"] for entry in IMMUTABLE_ALLOWLIST)
    imaged = _image_exists_sql("p")
    sql = f"""
    COPY (
      SELECT
        '{snapshot_utc}' AS snapshot_utc,
        p.id::text AS product_id,
        COALESCE(p.sku, '') AS sku,
        COALESCE(p.manufacturer_code, '') AS manufacturer_code,
        COALESCE(p.brand_id::text, '') AS brand_id,
        COALESCE(b.name, '') AS brand,
        COALESCE(p.deleted_at::text, '') AS deleted_at,
        p.is_active::text AS is_active,
        p.is_available::text AS is_available,
        COALESCE(p.base_price::text, '') AS base_price,
        ({imaged})::text AS image_present
      FROM products p
      LEFT JOIN brands b ON b.id = p.brand_id
      WHERE p.id IN ({ids})
      ORDER BY p.id
    ) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
    """
    rows = _copy_csv(sql, ssh_host)
    return [r for r in rows if (r.get("product_id") or "").isdigit()]


def sellability_blockers(row: dict[str, str]) -> list[str]:
    blockers: list[str] = []
    deleted = (row.get("deleted_at") or "").strip()
    if deleted and deleted.lower() not in {"", "null", "none"}:
        blockers.append("deleted_at_set")
    brand = canonicalize_brand(row.get("brand") or "")
    if brand != "INSIZE":
        blockers.append(f"brand_not_INSIZE:{row.get('brand')}")
    active = (row.get("is_active") or "").lower() in {"t", "true", "1"}
    if not active:
        blockers.append("is_active_false")
    avail = (row.get("is_available") or "").lower() in {"t", "true", "1"}
    if avail:
        blockers.append("already_available")
    try:
        price = float(row.get("base_price") or "0")
    except ValueError:
        price = 0.0
    if price <= 0:
        blockers.append("base_price_not_positive")
    imaged = (row.get("image_present") or "").lower() in {"t", "true", "1"}
    if not imaged:
        blockers.append("image_missing")
    if not blockers:
        return ["only_availability"]
    return blockers


def sha256sums(out_dir: Path) -> None:
    lines = []
    for p in sorted(out_dir.iterdir()):
        if p.name == "SHA256SUMS.txt" or p.is_dir():
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{h}  ./{p.name}")
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "audit" / "sellability-391-wave-d-insize-2026-10-13",
    )
    p.add_argument("--skip-ci-gate", action="store_true", help="Local only; do not use for Owner sign-off")
    args = p.parse_args(argv)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = _git_head()
    ci = _pr488_ci_state()

    age_days = (date.today() - date.fromisoformat(INSIZE_SOURCE_DATE)).days
    freshness = FreshnessPolicy().classify(age_days)

    status = "READY_FOR_OWNER_WAVE_D_APPLY_AUTHORIZATION"
    blockers: list[str] = []
    if freshness == "STALE":
        status = "BLOCKED_SOURCE_STALE"
        blockers.append("source_stale")
    if freshness not in {"CURRENT_ENOUGH", "AGING_BUT_USABLE"}:
        if status != "BLOCKED_SOURCE_STALE":
            status = "BLOCKED_SOURCE_STALE"
        blockers.append(f"freshness_{freshness}")
    if head != EXPECTED_PR488_HEAD:
        blockers.append(f"head_mismatch:{head}")
    if not args.skip_ci_gate:
        if ci["gate"] == "PENDING":
            status = "BLOCKED_PR488_CI"
            blockers.append(f"ci_pending:{ci['detail']}")
        elif ci["gate"] == "FAIL":
            status = "BLOCKED_PR488_CI"
            blockers.append(f"ci_fail:{ci['detail']}")

    actual_sha = file_sha256(INSIZE_CANONICAL_XLSX)
    if actual_sha != INSIZE_CANONICAL_SHA:
        status = "BLOCKED_ALLOWLIST_DRIFT"
        blockers.append("source_sha_mismatch")

    ro = _read_only_session_proof(args.ssh_host)
    host = _ssh("hostname", args.ssh_host)
    alembic = _alembic_head(args.ssh_host)
    identity = {
        "snapshot_utc": snapshot_utc,
        "git_head": head,
        "expected_pr488_head": EXPECTED_PR488_HEAD,
        "pr488_ci": ci,
        "transaction_read_only": ro.get("transaction_read_only", "unknown"),
        "host": host,
        "alembic": alembic,
        "mutation": {
            "PRODUCTION_MUTATION": "NO",
            "DATABASE_MUTATION": "NO",
            "AVAILABILITY_APPLY": "NO",
            "PRICE_APPLY": "NO",
            "HESABFA_MUTATION": "NO",
            "DEPLOYMENT": "NO",
        },
        "read_only_proof": ro,
    }
    write_json(out_dir / "PRODUCTION_IDENTITY.json", identity)

    census = collect_fresh_census(args.ssh_host, snapshot_utc)
    prod_rows = production_allowlist_rows(args.ssh_host, snapshot_utc)
    by_id = {r["product_id"]: r for r in prod_rows}

    allowlist_csv = []
    prod_recheck_fail = False
    for entry in IMMUTABLE_ALLOWLIST:
        pid = entry["product_id"]
        row = by_id.get(pid)
        if row is None:
            prod_recheck_fail = True
            allowlist_csv.append({**entry, "production_found": "NO", "blockers": "missing_product"})
            continue
        block = sellability_blockers(row)
        ok = block == ["only_availability"] and row.get("sku") == entry["catalog_sku"]
        if not ok:
            prod_recheck_fail = True
        allowlist_csv.append(
            {
                **entry,
                "production_found": "YES",
                "live_sku": row.get("sku"),
                "manufacturer_code": row.get("manufacturer_code"),
                "brand": row.get("brand"),
                "blockers": ";".join(block),
                "production_gate": "PASS" if ok else "FAIL",
            }
        )

    if prod_recheck_fail or len(prod_rows) != len(IMMUTABLE_ALLOWLIST):
        status = "BLOCKED_ALLOWLIST_DRIFT"
        blockers.append("production_recheck_failed")

    validation = insize_validation_report()
    workbook_index = load_insize_workbook_index(INSIZE_CANONICAL_XLSX)
    stock_by_code = {
        normalize_sku(sr.identity_key): sr
        for sr in validation.rows
        if sr.identity_key
    }
    catalog = export_catalog_products(
        args.ssh_host, [int(e["product_id"]) for e in IMMUTABLE_ALLOWLIST]
    )
    mapped = map_stock_to_catalog(validation, catalog, brand="INSIZE")
    map_by_pid = {m.product_id: m for m in mapped if m.product_id}

    source_recheck = []
    source_fail = False
    for entry in IMMUTABLE_ALLOWLIST:
        pid = entry["product_id"]
        m = map_by_pid.get(pid)
        src_code = entry["source_code"]
        wb = workbook_index.get(normalize_sku(src_code), {})
        sr = stock_by_code.get(normalize_sku(src_code))
        status_raw = sr.availability_status_raw if sr else ""
        norm = m.normalized_status if m else "NOT_MAPPED"
        qty_raw = wb.get("source_total_quantity", "")
        qty, qty_invalid = parse_quantity(qty_raw)
        qty_ok = qty is not None and not qty_invalid and qty > 5
        method = match_method_label(m) if m else "NOT_MAPPED"
        identity_ok = (
            m is not None
            and m.match_class == "EXACT_MATCH"
            and normalize_sku(m.manufacturer_sku or "") == normalize_sku(src_code)
            and method in {"EXACT_SKU", "manufacturer_code", "INSIZE_TRAILING_A_IDENTITY"}
        )
        source_ok = (
            identity_ok
            and norm == "AVAILABLE"
            and qty_ok
            and freshness in {"CURRENT_ENOUGH", "AGING_BUT_USABLE"}
        )
        if not source_ok:
            source_fail = True
        price_val = wb.get("source_price_value", "")
        source_recheck.append(
            {
                "product_id": pid,
                "catalog_sku": entry["catalog_sku"],
                "identity_match_method": method,
                "source_code": src_code,
                "source_status_raw": status_raw,
                "source_status_normalized": norm,
                "source_total_quantity": qty_raw,
                "source_total_quantity_gt_5": "YES" if qty_ok else "NO",
                "source_date": INSIZE_SOURCE_DATE,
                "freshness": freshness,
                "freshness_age_days": age_days,
                "source_price_value": price_val,
                "source_gate": "PASS" if source_ok else "FAIL",
            }
        )

    if source_fail:
        status = "BLOCKED_ALLOWLIST_DRIFT" if status != "BLOCKED_SOURCE_STALE" else status
        blockers.append("source_recheck_failed")

    expected_rows = []
    dry_run_rows = []
    rollback_rows = []
    for entry in IMMUTABLE_ALLOWLIST:
        pid = entry["product_id"]
        prod = by_id.get(pid, {})
        src = next(r for r in source_recheck if r["product_id"] == pid)
        h = state_hash_row(prod) if prod else ""
        expected_rows.append(
            {
                "product_id": pid,
                "sku": entry["catalog_sku"],
                "expected_current_hash": h,
                "expected_is_available": "false",
                "proposed_is_available": "true",
                "source_code": entry["source_code"],
                "source_sha256": INSIZE_CANONICAL_SHA,
                "source_status": src["source_status_normalized"],
                "source_quantity": src["source_total_quantity"],
                "source_date": INSIZE_SOURCE_DATE,
                "freshness": freshness,
            }
        )
        dry_run_rows.append(
            {
                "product_id": pid,
                "sku": entry["catalog_sku"],
                "field": "is_available",
                "before": prod.get("is_available", ""),
                "after": "true",
                "base_price_change": "NO",
                "is_active_change": "NO",
                "image_change": "NO",
                "identity_change": "NO",
            }
        )
        rollback_rows.append(
            {
                "product_id": pid,
                "sku": entry["catalog_sku"],
                "pre_is_available": prod.get("is_available", ""),
                "pre_state_hash": h,
                "rollback_action": "is_available true→false (only if APPLY succeeded)",
            }
        )

    production_recheck = []
    for entry in IMMUTABLE_ALLOWLIST:
        pid = entry["product_id"]
        row = by_id.get(pid, {})
        block = sellability_blockers(row) if row else ["missing_product"]
        production_recheck.append(
            {
                "product_id": pid,
                "sku": row.get("sku", ""),
                "manufacturer_code": row.get("manufacturer_code", ""),
                "brand": row.get("brand", ""),
                "deleted_at": row.get("deleted_at", ""),
                "is_active": row.get("is_active", ""),
                "is_available": row.get("is_available", ""),
                "base_price": row.get("base_price", ""),
                "image_present": row.get("image_present", ""),
                "current_sellability_blockers": ";".join(block),
            }
        )
    write_csv(
        out_dir / "PRODUCTION_RECHECK.csv",
        list(production_recheck[0].keys()) if production_recheck else ["product_id"],
        production_recheck,
    )

    write_csv(
        out_dir / "ALLOWLIST.csv",
        [
            "product_id",
            "catalog_sku",
            "source_code",
            "production_found",
            "live_sku",
            "manufacturer_code",
            "brand",
            "blockers",
            "production_gate",
        ],
        allowlist_csv,
    )
    write_csv(
        out_dir / "SOURCE_RECHECK.csv",
        list(source_recheck[0].keys()) if source_recheck else ["product_id"],
        source_recheck,
    )
    write_csv(
        out_dir / "INSIZE_WAVE_D_EXPECTED_STATE.csv",
        list(expected_rows[0].keys()) if expected_rows else ["product_id"],
        expected_rows,
    )
    write_csv(
        out_dir / "INSIZE_WAVE_D_DRY_RUN.csv",
        list(dry_run_rows[0].keys()) if dry_run_rows else ["product_id"],
        dry_run_rows,
    )
    write_csv(
        out_dir / "ROLLBACK_MANIFEST.csv",
        list(rollback_rows[0].keys()) if rollback_rows else ["product_id"],
        rollback_rows,
    )

    sellable_before = census["sellable"]
    delta = 10 if status == "READY_FOR_OWNER_WAVE_D_APPLY_AUTHORIZATION" else 0
    report_lines = [
        "# INSIZE Wave D dry-run report (#391)",
        "",
        f"**Snapshot UTC:** {snapshot_utc}",
        f"**Status:** `{status}`",
        "",
        "## CI gate (PR #488)",
        "",
        f"- Expected HEAD: `{EXPECTED_PR488_HEAD}`",
        f"- Actual HEAD: `{head}`",
        f"- CI: `{ci['gate']}` — {ci['detail']}",
        "",
        "## Source freshness",
        "",
        f"- SHA256: `{INSIZE_CANONICAL_SHA}` (verified: `{actual_sha == INSIZE_CANONICAL_SHA}`)",
        f"- source_date: **{INSIZE_SOURCE_DATE}** — {INSIZE_SOURCE_DATE_EVIDENCE}",
        f"- Age at execution: **{age_days}** days → **{freshness}**",
        "",
        "## Production recheck",
        "",
        f"- `transaction_read_only={identity['transaction_read_only']}`",
        f"- Allowlist size: **{len(IMMUTABLE_ALLOWLIST)}** (immutable)",
        f"- Production rows returned: **{len(prod_rows)}**",
        f"- Production gate: **{'PASS' if not prod_recheck_fail else 'FAIL'}**",
        "",
        "## Source recheck",
        "",
        f"- Source gate: **{'PASS' if not source_fail else 'FAIL'}**",
        "- Identity: governed EXACT / INSIZE_TRAILING_A_IDENTITY only",
        "- Availability: `وضعیت` → AVAILABLE and `موجودی کل` > 5",
        "",
        "## Price safety",
        "",
        "- **No price APPLY.** Mutation scope: `is_available` false→true only.",
        "- `8601-100`: source `قیمت دلاری` may be `#N/A`; non-blocking when site `base_price > 0`.",
        "",
        "## Dry-run delta",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Planned rows | {len(dry_run_rows)} |",
        "| Inserts | 0 |",
        "| Deletes | 0 |",
        "| Price changes | 0 |",
        "| Activation changes | 0 |",
        "| Image changes | 0 |",
        "| Identity changes | 0 |",
        f"| Availability false→true | {len(dry_run_rows) if status == 'READY_FOR_OWNER_WAVE_D_APPLY_AUTHORIZATION' else 0} |",
        "",
        "## Sellable projection",
        "",
        f"- Before (fresh census): **{sellable_before}**",
        f"- Delta (if all gates pass): **+10**",
        f"- After: **{sellable_before + 10}**",
        "",
        "## Safety",
        "",
        "```text",
        "PRODUCTION_MUTATION=NO",
        "DATABASE_MUTATION=NO",
        "AVAILABILITY_APPLY=NO",
        "PRICE_APPLY=NO",
        "DEPLOYMENT=NO",
        "```",
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        report_lines.extend(f"- {b}" for b in blockers)
    else:
        report_lines.append("- (none)")
    (out_dir / "INSIZE_WAVE_D_DRY_RUN_REPORT.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    apply_plan = f"""# INSIZE Wave D APPLY plan (guarded — NOT EXECUTED)

**Authorization phase:** dry-run only. Owner must separately issue `AUTHORIZE_WAVE_D_APPLY`.

## Entry point

```bash
python3 scripts/apply_insize_wave_d_391_availability.py \\
  --evidence-dir {out_dir.relative_to(ROOT)} \\
  # --apply  # NOT RUN in this phase
```

## Preconditions (fail-closed)

1. Immutable allowlist: exactly **10** product IDs in `ALLOWLIST.csv`
2. Source SHA256: `{INSIZE_CANONICAL_SHA}`
3. Freshness ∈ {{CURRENT_ENOUGH, AGING_BUT_USABLE}} at execution
4. Each row `expected_current_hash` in `INSIZE_WAVE_D_EXPECTED_STATE.csv` matches live DB
5. `UPDATE` scope: `is_available` only; rowcount must equal 10
6. Category B: `KARZAR_ALLOW_PRODUCTION_WRITE=1` and `KARZAR_INGESTION_CATEGORY=B` when `--apply`

## Rollback

Use `ROLLBACK_MANIFEST.csv` — set `is_available=false` only for rows successfully updated.

## Audit journal

Post-apply read-only reconciliation required; journal path TBD at APPLY authorization.
"""
    (out_dir / "APPLY_PLAN.md").write_text(apply_plan, encoding="utf-8")

    readme = f"""# INSIZE Wave D guarded dry-run (#391)

**Status:** `{status}`  
**PR #488 HEAD:** `{head}`  
**No APPLY.**

## Artifacts

- [`INSIZE_WAVE_D_DRY_RUN_REPORT.md`](INSIZE_WAVE_D_DRY_RUN_REPORT.md)
- [`PRODUCTION_RECHECK.csv`](PRODUCTION_RECHECK.csv)
- [`ALLOWLIST.csv`](ALLOWLIST.csv)
- [`SOURCE_RECHECK.csv`](SOURCE_RECHECK.csv)
- [`INSIZE_WAVE_D_EXPECTED_STATE.csv`](INSIZE_WAVE_D_EXPECTED_STATE.csv)
- [`INSIZE_WAVE_D_DRY_RUN.csv`](INSIZE_WAVE_D_DRY_RUN.csv)
- [`ROLLBACK_MANIFEST.csv`](ROLLBACK_MANIFEST.csv)
- [`APPLY_PLAN.md`](APPLY_PLAN.md)

Linked Wave A evidence: [`../sellability-391-wave-a-insize-2026-10-13/`](../sellability-391-wave-a-insize-2026-10-13/)
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    sha256sums(out_dir)

    print(
        json.dumps(
            {
                "status": status,
                "freshness": freshness,
                "age_days": age_days,
                "ci": ci,
                "head": head,
                "sellable_before": sellable_before,
                "blockers": blockers,
                "out_dir": str(out_dir),
            },
            indent=2,
        )
    )
    return 0 if status == "READY_FOR_OWNER_WAVE_D_APPLY_AUTHORIZATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
