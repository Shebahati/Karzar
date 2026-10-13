#!/usr/bin/env python3
"""INSIZE final commercial APPLY — dry-run default; NOT authorized in audit PR."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.sales_wave_apply import ApplyAbort, assert_production_apply_authorized  # noqa: E402
from catalog_target.supplier_stock import FreshnessPolicy, file_sha256  # noqa: E402

from audit_insize_final_commercial_source import (  # noqa: E402
    FX_TOMAN_PER_USD,
    INSIZE_FINAL_SHA,
    INSIZE_FINAL_XLSX,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--evidence-dir",
        type=Path,
        default=ROOT / "audit" / "insize-final-commercial-source-2026-10-13",
    )
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm-production-write", action="store_true")
    p.add_argument("--confirm-plan-sha256", default="")
    args = p.parse_args(argv)

    plan = args.evidence_dir / "INSIZE_FINAL_COMMERCIAL_DRY_RUN.csv"
    if not plan.is_file():
        raise SystemExit(f"missing plan: {plan}")

    if file_sha256(INSIZE_FINAL_XLSX) != INSIZE_FINAL_SHA:
        raise SystemExit("source_sha_mismatch")

    freshness = FreshnessPolicy().classify(7)  # Owner-confirmed ~1 week
    if freshness not in {"CURRENT_ENOUGH", "AGING_BUT_USABLE"}:
        raise SystemExit("BLOCKED_SOURCE_STALE")

    plan_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    rows = list(csv.DictReader(plan.open(encoding="utf-8")))
    eligible = [r for r in rows if r.get("eligibility") == "APPLY_ELIGIBLE"]
    report = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "source_sha256": INSIZE_FINAL_SHA,
        "plan_sha256": plan_sha,
        "fx_toman_per_usd": str(FX_TOMAN_PER_USD),
        "eligible_rows": len(eligible),
        "freshness_policy_note": "OWNER_CONFIRMED_RECENCY at audit time",
    }

    if args.apply:
        assert_production_apply_authorized(
            database_url=__import__("os").environ.get("DATABASE_URL", ""),
            confirm_production_write=args.confirm_production_write,
        )
        if args.confirm_plan_sha256 != plan_sha:
            raise SystemExit("plan_sha_mismatch")
        raise SystemExit(
            "APPLY_NOT_ENABLED — implement Owner-authorized transaction path in follow-up"
        )

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApplyAbort as exc:
        print(f"ApplyAbort: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
