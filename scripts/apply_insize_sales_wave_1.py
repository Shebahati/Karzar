#!/usr/bin/env python3
"""INSIZE Sales Wave 1 guarded APPLY CLI.

Default mode is DRY RUN (zero writes). Production APPLY requires:
  --apply
  --confirm-production-write
  --confirm-plan-sha256 <reviewed CSV sha256>
  KARZAR_ALLOW_PRODUCTION_WRITE=1
  KARZAR_INGESTION_CATEGORY=B

This PR must not execute production APPLY.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.sales_wave_apply import (  # noqa: E402
    REVIEWED_ALLOWLIST_COUNT,
    REVIEWED_AVAILABILITY_CHANGES,
    REVIEWED_PLAN_CSV_SHA256,
    REVIEWED_PLAN_JSON_SHA256,
    REVIEWED_PRICE_CHANGES,
    REVIEWED_SNAPSHOT_SHA256,
    REVIEWED_SNAPSHOT_TIMESTAMP,
    ApplyAbort,
    LiveProduct,
    apply_allowlist,
    assert_production_apply_authorized,
    default_plan_csv_path,
    load_and_validate_plan,
    post_apply_verification_contract,
    price_change_stats,
    sha256_file,
    stale_guard,
    writer_contract_summary,
)


def _parse_live_bool(raw: str, *, field_name: str) -> bool | None:
    text = (raw or "").strip().lower()
    if text in {"", "none", "null"}:
        return None
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    raise ApplyAbort(f"malformed_live_bool:{field_name}:{raw!r}")


def _load_live_csv(path: Path) -> list[LiveProduct]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"id", "sku", "base_price", "is_active", "is_available", "deleted_at"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ApplyAbort(f"live_csv_missing_columns:{','.join(sorted(missing))}")
        out: list[LiveProduct] = []
        for raw in reader:
            price_raw = (raw.get("base_price") or "").strip()
            if price_raw.lower() in {"", "none", "null"}:
                price_raw = ""
            deleted = (raw.get("deleted_at") or "").strip() or None
            if deleted and deleted.lower() in {"none", "null"}:
                deleted = None
            out.append(
                LiveProduct(
                    id=int(str(raw["id"]).strip()),
                    sku=str(raw["sku"]).strip(),
                    base_price=None if not price_raw else Decimal(price_raw),
                    is_active=_parse_live_bool(raw.get("is_active") or "", field_name="is_active"),
                    is_available=_parse_live_bool(
                        raw.get("is_available") or "", field_name="is_available"
                    ),
                    deleted_at=deleted,
                )
            )
        return out


def _connect_psycopg(database_url: str):
    try:
        import psycopg2  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ApplyAbort("psycopg2_not_installed") from exc
    return psycopg2.connect(database_url)


class _MemoryConn:
    """In-process connection used only for CSV-backed dry-run stale checks."""

    def __init__(self, live_rows: list[LiveProduct]):
        self._live = live_rows
        self.committed = False
        self.rolled_back = False

    def cursor(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return _MemoryCursor(self._live)

    def commit(self) -> None:
        self.committed = True
        raise ApplyAbort("memory_conn_commit_forbidden")

    def rollback(self) -> None:
        self.rolled_back = True


class _MemoryCursor:
    def __init__(self, live_rows: list[LiveProduct]):
        self._live = live_rows
        self.rowcount = 0
        self._rows: list[tuple] = []

    def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
        sql_l = " ".join(sql.lower().split())
        if sql_l.startswith("update "):
            raise ApplyAbort("memory_conn_update_forbidden")
        ids = list(params[0]) if params else []
        wanted = set(ids)
        self._rows = [
            (
                row.id,
                row.sku,
                row.base_price,
                row.is_active,
                row.is_available,
                row.deleted_at,
                row.brand_id,
                row.category_id,
                row.name,
                row.slug,
            )
            for row in self._live
            if row.id in wanted
        ]
        self.rowcount = len(self._rows)

    def fetchall(self):
        return list(self._rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="INSIZE Sales Wave 1 guarded APPLY (DRY RUN default)."
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=None,
        help="Reviewed plan CSV (defaults to data/catalog-target/insize_sales_wave_1_plan.csv)",
    )
    parser.add_argument(
        "--plan-json",
        type=Path,
        default=None,
        help="Optional companion JSON for checksum reporting",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="PostgreSQL URL for live stale-guard / apply (local test DB by default)",
    )
    parser.add_argument(
        "--live-csv",
        type=Path,
        default=None,
        help="READ-ONLY live product CSV for stale-guard dry-run (no DB writes)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(".local-scratch/insize-sales-wave-1-apply"),
        help="Outside-git backup/rollback directory (gitignored .local-scratch)",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Write machine-readable run report JSON",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Request mutation mode (still requires production auth tokens)",
    )
    parser.add_argument(
        "--confirm-production-write",
        action="store_true",
        help="Unmistakable confirmation that production mutation is intended",
    )
    parser.add_argument(
        "--confirm-plan-sha256",
        default="",
        help="Must equal the reviewed plan CSV SHA-256 to authorize APPLY",
    )
    parser.add_argument(
        "--skip-plan-checksum",
        action="store_true",
        help="Test-only: allow loading a temporary malformed/variant plan",
    )
    parser.add_argument(
        "--print-contract",
        action="store_true",
        help="Print writer contract JSON and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.print_contract:
        print(json.dumps(writer_contract_summary(), indent=2, ensure_ascii=False))
        return 0

    plan_path = args.plan or default_plan_csv_path()
    plan_json = args.plan_json
    if plan_json is None:
        candidate = plan_path.with_suffix(".json")
        if candidate.is_file():
            plan_json = candidate

    try:
        plan_rows = load_and_validate_plan(
            plan_path,
            require_checksum=not args.skip_plan_checksum,
        )
        plan_csv_sha = sha256_file(plan_path)
        plan_json_sha = sha256_file(plan_json) if plan_json and plan_json.is_file() else ""

        dry_run = not args.apply
        assert_production_apply_authorized(
            apply=args.apply,
            confirm_production_write=args.confirm_production_write,
            confirm_plan_sha256=args.confirm_plan_sha256,
            plan_csv_sha256=plan_csv_sha,
            db_host="",
            database_url=args.database_url or "",
        )

        if args.live_csv is not None:
            live = _load_live_csv(args.live_csv)
            if args.apply:
                raise ApplyAbort("apply_requires_database_url_not_live_csv")
            conn = _MemoryConn(live)
            result = apply_allowlist(
                conn,
                plan_rows,
                dry_run=True,
                backup_dir=args.backup_dir if not dry_run else None,
            )
            # Also attach explicit stale guard from CSV for reporting clarity.
            result.stale_guard = stale_guard(plan_rows, live).as_dict()
        elif args.database_url:
            conn = _connect_psycopg(args.database_url)
            try:
                result = apply_allowlist(
                    conn,
                    plan_rows,
                    dry_run=dry_run,
                    backup_dir=args.backup_dir if args.apply else args.backup_dir,
                )
            finally:
                conn.close()
        else:
            # Plan-only dry-run: no live re-read; stale guard marked pending.
            from dataclasses import asdict

            from catalog_target.sales_wave_apply import (  # noqa: PLC0415
                ApplyRunResult,
                build_dry_run_lines,
            )

            result = ApplyRunResult(
                mode="dry_run_plan_only",
                production_apply_executed=False,
                aborted=False,
                plan_path=str(plan_path),
                plan_csv_sha256=plan_csv_sha,
                plan_json_sha256=plan_json_sha,
                allowlist_count=len(plan_rows),
                expected_price_changes=REVIEWED_PRICE_CHANGES,
                expected_availability_changes=REVIEWED_AVAILABILITY_CHANGES,
                expected_active_changes=0,
                stale_guard={
                    "ok": None,
                    "pending_fresh_live_reread": True,
                    "note": "Provide --live-csv or --database-url for stale-guard",
                },
                dry_run_lines=[asdict(line) for line in build_dry_run_lines(plan_rows)],
                price_change_stats=price_change_stats(plan_rows),
                transaction_safeguards={
                    "single_transaction": True,
                    "partial_commit_allowed": False,
                    "default_mode": "DRY_RUN",
                },
                implementation_ready=True,
            )

        result.plan_path = str(plan_path)
        result.plan_csv_sha256 = plan_csv_sha
        result.plan_json_sha256 = plan_json_sha

        report = result.as_dict()
        report["reviewed_snapshot_timestamp"] = REVIEWED_SNAPSHOT_TIMESTAMP
        report["reviewed_snapshot_sha256"] = REVIEWED_SNAPSHOT_SHA256
        report["reviewed_plan_csv_sha256_constant"] = REVIEWED_PLAN_CSV_SHA256
        report["reviewed_plan_json_sha256_constant"] = REVIEWED_PLAN_JSON_SHA256
        report["post_apply_verification"] = post_apply_verification_contract()
        report["INSIZE_SALES_WAVE_1_APPLY_IMPLEMENTATION_READY"] = bool(
            result.implementation_ready and not result.production_apply_executed
        )
        report["PRODUCTION_APPLY_EXECUTED"] = bool(result.production_apply_executed)
        report["PRODUCTION_DB_MUTATION"] = (
            "NONZERO" if result.production_apply_executed else "ZERO"
        )

        print("=== INSIZE Sales Wave 1 APPLY ===")
        print(f"mode: {result.mode}")
        print(f"plan: {plan_path}")
        print(f"plan_csv_sha256: {plan_csv_sha}")
        print(f"allowlist_count: {result.allowlist_count}")
        print(f"expected_price_changes: {REVIEWED_PRICE_CHANGES}")
        print(f"expected_availability_changes: {REVIEWED_AVAILABILITY_CHANGES}")
        print(f"stale_guard_ok: {result.stale_guard.get('ok')}")
        print(f"stale_guard_drift_count: {result.stale_guard.get('drift_count')}")
        print(f"aborted: {result.aborted}")
        if result.abort_reason:
            print(f"abort_reason: {result.abort_reason}")
        print(f"production_apply_executed: {result.production_apply_executed}")
        print(f"updated_count: {result.updated_count}")
        if result.backup_path:
            print(f"backup_path: {result.backup_path}")
            print(f"backup_sha256: {result.backup_sha256}")
            print(f"rollback_sql_path: {result.rollback_sql_path}")
        print(
            "INSIZE_SALES_WAVE_1_APPLY_IMPLEMENTATION_READY =",
            str(report["INSIZE_SALES_WAVE_1_APPLY_IMPLEMENTATION_READY"]).upper(),
        )
        print(
            "PRODUCTION_APPLY_EXECUTED =",
            str(report["PRODUCTION_APPLY_EXECUTED"]).upper(),
        )
        print("PRODUCTION DB MUTATION:", report["PRODUCTION_DB_MUTATION"])

        # Compact per-row preview (first 5 + checkout candidate).
        preview_skus = set()
        shown = 0
        for line in result.dry_run_lines:
            sku = line["sku"]
            if shown < 5 or sku == "4602-32":
                print(
                    f"  {line['product_id']} {sku}: "
                    f"price {line['current_base_price']} -> {line['proposed_base_price']} "
                    f"({line['price_delta_pct']}%); "
                    f"avail {line['current_is_available']} -> {line['proposed_is_available']}"
                )
                preview_skus.add(sku)
                shown += 1
        print(f"dry_run_preview_rows: {len(preview_skus)} of {REVIEWED_ALLOWLIST_COUNT}")
        stats = result.price_change_stats
        if stats:
            print(
                "price_delta_pct:",
                f"min={stats.get('min_pct')} median={stats.get('median_pct')} "
                f"max={stats.get('max_pct')} outliers_ge_50={len(stats.get('outliers_abs_pct_ge_50') or [])}",
            )

        if args.report_json is not None:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            # Omit full dry_run_lines from default report if huge? Keep them — needed for audit.
            args.report_json.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"report_json: {args.report_json}")

        if result.aborted:
            return 4
        return 0
    except ApplyAbort as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
