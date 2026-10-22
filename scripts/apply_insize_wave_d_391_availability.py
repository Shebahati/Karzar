#!/usr/bin/env python3
"""INSIZE Wave D (#391) guarded availability APPLY — DRY RUN default.

Mutates only ``is_available`` (false→true) for the immutable 10-product allowlist.
Production ``--apply`` requires Category B authorization and expected-state hash match.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.sales_wave_apply import ApplyAbort, assert_production_apply_authorized  # noqa: E402
from catalog_target.supplier_stock import FreshnessPolicy, file_sha256  # noqa: E402

from audit_sellability_391_insize_wave_a import (  # noqa: E402
    INSIZE_CANONICAL_SHA,
    INSIZE_CANONICAL_XLSX,
    INSIZE_SOURCE_DATE,
)
from audit_sellability_391_insize_wave_d_dry_run import (  # noqa: E402
    IMMUTABLE_ALLOWLIST,
    production_allowlist_rows,
    state_hash_row,
)

ALLOWLIST_COUNT = 10


def _load_expected_state(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=ROOT / "audit" / "sellability-391-wave-d-insize-2026-10-13",
    )
    parser.add_argument("--ssh-host", default="karzar-vps")
    parser.add_argument("--apply", action="store_true", help="Execute mutation (requires auth)")
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required with --apply for production",
    )
    parser.add_argument(
        "--confirm-expected-state-sha256",
        default="",
        help="SHA256 of INSIZE_WAVE_D_EXPECTED_STATE.csv reviewed by Owner",
    )
    args = parser.parse_args(argv)

    evidence = args.evidence_dir
    expected_path = evidence / "INSIZE_WAVE_D_EXPECTED_STATE.csv"
    if not expected_path.is_file():
        raise SystemExit(f"missing expected state: {expected_path}")

    age_days = (date.today() - date.fromisoformat(INSIZE_SOURCE_DATE)).days
    freshness = FreshnessPolicy().classify(age_days)
    if freshness not in {"CURRENT_ENOUGH", "AGING_BUT_USABLE"}:
        raise SystemExit(f"BLOCKED_SOURCE_STALE freshness={freshness} age_days={age_days}")

    if file_sha256(INSIZE_CANONICAL_XLSX) != INSIZE_CANONICAL_SHA:
        raise SystemExit("source_sha_mismatch")

    expected_rows = _load_expected_state(expected_path)
    if len(expected_rows) != ALLOWLIST_COUNT:
        raise SystemExit(f"allowlist_count_mismatch:{len(expected_rows)}")

    reviewed_sha = hashlib.sha256(expected_path.read_bytes()).hexdigest()
    if args.apply and args.confirm_expected_state_sha256 != reviewed_sha:
        raise SystemExit("expected_state_sha256_mismatch")

    ids = sorted(int(r["product_id"]) for r in expected_rows)
    allow_ids = sorted(int(e["product_id"]) for e in IMMUTABLE_ALLOWLIST)
    if ids != allow_ids:
        raise SystemExit("immutable_allowlist_id_mismatch")

    from datetime import UTC, datetime

    snapshot_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    live = production_allowlist_rows(args.ssh_host, snapshot_utc)
    live_by_id = {r["product_id"]: r for r in live}
    if len(live_by_id) != ALLOWLIST_COUNT:
        raise SystemExit(f"live_rowcount_mismatch:{len(live_by_id)}")

    stale: list[str] = []
    plan: list[dict[str, str]] = []
    for exp in expected_rows:
        pid = exp["product_id"]
        row = live_by_id.get(pid)
        if row is None:
            stale.append(f"missing:{pid}")
            continue
        cur_hash = state_hash_row(row)
        if cur_hash != exp["expected_current_hash"]:
            stale.append(f"hash:{pid}")
        avail = (row.get("is_available") or "").lower() in {"t", "true", "1"}
        if avail:
            stale.append(f"already_available:{pid}")
        plan.append(
            {
                "product_id": pid,
                "sku": row.get("sku"),
                "is_available_before": row.get("is_available"),
                "is_available_after": "true",
            }
        )

    if stale:
        raise SystemExit(f"stale_guard_failed:{','.join(stale)}")

    report = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "row_count": len(plan),
        "freshness": freshness,
        "source_sha256": INSIZE_CANONICAL_SHA,
        "expected_state_sha256": reviewed_sha,
        "mutations": plan,
    }

    if not args.apply:
        print(json.dumps(report, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL", "")
    assert_production_apply_authorized(
        database_url=database_url,
        confirm_production_write=args.confirm_production_write,
    )

    id_list = ",".join(str(i) for i in ids)
    update_sql = f"""
BEGIN;
UPDATE products
SET is_available = TRUE, updated_at = NOW()
WHERE id IN ({id_list})
  AND deleted_at IS NULL
  AND is_active IS TRUE
  AND is_available IS FALSE
  AND base_price IS NOT NULL AND base_price > 0;
"""
    # Fail closed: refuse to run mutation SQL from this script in dry-run phase PR.
    raise SystemExit(
        "APPLY_SQL_NOT_ENABLED_IN_THIS_PR — use Owner-authorized runbook after "
        "AUTHORIZE_WAVE_D_APPLY; wire DATABASE_URL + audited transaction path."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApplyAbort as exc:
        print(f"ApplyAbort: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
