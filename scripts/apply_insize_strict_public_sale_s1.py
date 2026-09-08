#!/usr/bin/env python3
"""INSIZE strict public-sale Safety S1 guarded APPLY CLI.

Default mode is DRY RUN (zero writes). Production APPLY requires:
  --apply
  --confirm-production-write
  --confirm-plan-sha256 <reviewed CSV sha256>
  KARZAR_ALLOW_PRODUCTION_WRITE=1
  KARZAR_INGESTION_CATEGORY=B

This task must not execute production APPLY.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.public_sale_safety_apply import (  # noqa: E402
    REVIEWED_ALLOWLIST_COUNT,
    REVIEWED_PLAN_CSV_SHA256,
    ApplyAbort,
    apply_allowlist,
    assert_production_apply_authorized,
    connect_runtime_db,
    default_plan_csv_path,
    load_and_validate_plan,
    post_apply_verification_contract,
    sha256_file,
    writer_contract_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="INSIZE strict public-sale Safety S1 guarded APPLY (DRY RUN default)."
    )
    parser.add_argument(
        "--plan-csv",
        default=str(default_plan_csv_path()),
        help="Reviewed immutable plan CSV",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute production APPLY (forbidden unless fully authorized)",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Required confirmation token for --apply",
    )
    parser.add_argument(
        "--confirm-plan-sha256",
        default="",
        help="Must equal reviewed plan CSV SHA-256",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="PostgreSQL URL (APPLY / live dry-run re-read)",
    )
    parser.add_argument(
        "--backup-dir",
        default="",
        help="Directory for pre-write backup + rollback SQL (APPLY only)",
    )
    parser.add_argument(
        "--report-json",
        default="",
        help="Optional path to write run report JSON",
    )
    args = parser.parse_args(argv)

    plan_path = Path(args.plan_csv)
    plan_sha = sha256_file(plan_path) if plan_path.is_file() else ""
    dry_run = not args.apply

    try:
        plan_rows = load_and_validate_plan(plan_path)
        assert_production_apply_authorized(
            apply=args.apply,
            confirm_production_write=args.confirm_production_write,
            confirm_plan_sha256=args.confirm_plan_sha256,
            plan_csv_sha256=plan_sha or REVIEWED_PLAN_CSV_SHA256,
            db_host="",
            database_url=args.database_url,
        )

        if dry_run and not args.database_url:
            # Plan-only dry-run: validate contract without DB.
            from catalog_target.public_sale_safety_apply import build_dry_run_lines

            result = {
                "mode": "dry_run_plan_only",
                "production_apply_executed": False,
                "aborted": False,
                "allowlist_count": len(plan_rows),
                "plan_csv_sha256": plan_sha,
                "dry_run_lines": [
                    {
                        "product_id": line.product_id,
                        "sku": line.sku,
                        "will_update_availability": line.will_update_availability,
                        "will_update_price": line.will_update_price,
                        "will_update_active": line.will_update_active,
                        "blocker": line.blocker,
                    }
                    for line in build_dry_run_lines(plan_rows)
                ],
                "writer_contract": writer_contract_summary(),
                "post_apply_verification_contract": post_apply_verification_contract(),
                "PRODUCTION_MUTATION": "ZERO",
            }
        else:
            if not args.database_url:
                raise ApplyAbort("database_url_required_for_live_reread_or_apply")
            if args.apply and not str(args.backup_dir or "").strip():
                raise ApplyAbort("backup_dir_required_for_apply")
            conn = connect_runtime_db(args.database_url)
            try:
                run = apply_allowlist(
                    conn,
                    plan_rows,
                    dry_run=dry_run,
                    backup_dir=Path(args.backup_dir) if args.backup_dir else None,
                )
            finally:
                close = getattr(conn, "close", None)
                if callable(close):
                    close()
            result = run.as_dict()
            result["plan_csv_sha256"] = plan_sha
            result["writer_contract"] = writer_contract_summary()
            result["post_apply_verification_contract"] = post_apply_verification_contract()
            if dry_run:
                result["PRODUCTION_MUTATION"] = "ZERO"

    except ApplyAbort as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        result = {
            "mode": "aborted",
            "production_apply_executed": False,
            "aborted": True,
            "abort_reason": str(exc),
            "PRODUCTION_MUTATION": "ZERO",
        }
        if args.report_json:
            Path(args.report_json).write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
        return 2

    print("=== INSIZE strict public-sale Safety S1 ===")
    print(f"mode: {result.get('mode')}")
    print(f"allowlist_count: {result.get('allowlist_count', REVIEWED_ALLOWLIST_COUNT)}")
    print(f"plan_sha256: {plan_sha}")
    print(f"production_apply_executed: {result.get('production_apply_executed')}")
    print(f"aborted: {result.get('aborted')}")
    print("PRODUCTION_MUTATION = ZERO" if dry_run or not result.get("production_apply_executed") else "APPLY_COMMITTED")

    if args.report_json:
        Path(args.report_json).write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
