#!/usr/bin/env python3
"""Official INSIZE Wave 1 content+identity rebuild CLI.

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

from catalog_target.official_insize_rebuild import (  # noqa: E402
    ApplyAbort,
    apply_plan,
    assert_production_apply_authorized,
    connect_runtime_db,
    load_allowlist_ids,
    load_and_validate_plan,
    normalize_database_url,
    sha256_file,
    writer_contract_summary,
)
from catalog_target.sales_wave_apply import (  # noqa: E402
    ALLOW_ENV,
    CATEGORY_ENV,
)


def _default_plan_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data/catalog-target/insize_official_rebuild_plan.csv"


def _default_allowlist_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / ".local-scratch/global-commerce-safety-containment/approved_sale_allowlist_158.csv"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-csv", type=Path, default=_default_plan_path())
    parser.add_argument("--allowlist-csv", type=Path, default=_default_allowlist_path())
    parser.add_argument("--database-url", default="", help="Only for APPLY/live dry-run against DB")
    parser.add_argument("--backup-dir", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="Request production mutation")
    parser.add_argument("--confirm-production-write", action="store_true")
    parser.add_argument("--confirm-plan-sha256", default="")
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        allowlist_ids = load_allowlist_ids(args.allowlist_csv)
        plan_rows = load_and_validate_plan(args.plan_csv, allowlist_ids=allowlist_ids)
        plan_sha = sha256_file(args.plan_csv)
        dry_run = not args.apply

        assert_production_apply_authorized(
            apply=args.apply,
            confirm_production_write=args.confirm_production_write,
            confirm_plan_sha256=args.confirm_plan_sha256,
            plan_csv_sha256=plan_sha,
            db_host="",
            database_url=args.database_url or "",
        )

        if not args.database_url:
            # Plan validation / contract dry check without DB.
            result = {
                "mode": "dry_run_plan_only",
                "production_apply_executed": False,
                "aborted": False,
                "plan_rows": len(plan_rows),
                "plan_sha256": plan_sha,
                "writer_contract": writer_contract_summary(),
                "gates": {
                    "apply": args.apply,
                    "confirm_production_write": args.confirm_production_write,
                    "confirm_plan_sha256_provided": bool(args.confirm_plan_sha256),
                    ALLOW_ENV: __import__("os").getenv(ALLOW_ENV, ""),
                    CATEGORY_ENV: __import__("os").getenv(CATEGORY_ENV, ""),
                },
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.report_json:
                args.report_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return 0

        conn = connect_runtime_db(normalize_database_url(args.database_url))
        run = apply_plan(
            conn,
            plan_rows,
            dry_run=dry_run,
            backup_dir=args.backup_dir,
        )
        payload = run.as_dict()
        payload["plan_sha256"] = plan_sha
        payload["writer_contract"] = writer_contract_summary()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if args.report_json:
            args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1 if run.aborted else 0
    except ApplyAbort as exc:
        print(json.dumps({"aborted": True, "abort_reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
