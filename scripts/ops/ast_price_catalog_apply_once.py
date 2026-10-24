#!/usr/bin/env python3
"""Category B APPLY for AST manifests (dry-run default). Does not run without explicit gates."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_apply import (  # noqa: E402
    assert_apply_gates,
    execute_ast_catalog_apply,
    load_apply_journal,
    load_create_plan,
    load_update_plan,
    manifest_identity,
    new_batch_id,
    rollback_from_journal,
)
from catalog_target.ast_price_catalog_constants import SOURCE_ARCHIVE_SHA256  # noqa: E402
from catalog_target.sales_wave_apply import ApplyAbort, connect_runtime_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "audit/ast-price-and-catalog-20261024")
    parser.add_argument("--journal-dir", type=Path, default=None)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--rollback-journal", type=Path, default=None)
    parser.add_argument("--confirm-production-write", action="store_true")
    parser.add_argument("--owner-authorization", default="")
    parser.add_argument("--confirm-source-sha256", default="")
    parser.add_argument("--confirm-update-manifest-sha256", default="")
    parser.add_argument("--confirm-create-manifest-sha256", default="")
    parser.add_argument("--confirm-update-count", type=int, default=-1)
    parser.add_argument("--confirm-create-count", type=int, default=-1)
    parser.add_argument(
        "--include-unapproved-creates",
        action="store_true",
        help="Test-only: load CREATE rows without OWNER_APPROVED_FOR_APPLY",
    )
    args = parser.parse_args()

    update_path = args.audit_dir / "UPDATE_PRODUCTS.csv"
    create_path = args.audit_dir / "CREATE_PRODUCTS.csv"
    journal_dir = args.journal_dir or (args.audit_dir / "journals")
    ids = manifest_identity(update_path, create_path)
    updates = load_update_plan(update_path)
    creates = load_create_plan(
        create_path,
        expected_manifest_sha256=ids["create_manifest_sha256"],
        require_owner_approval=not args.include_unapproved_creates,
    )

    dry_run = not args.apply and not args.rollback
    if dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "updates": len(updates),
                    "creates_eligible": len(creates),
                    "manifest": ids,
                    "note": "Pass --apply with full Category B gates to mutate production.",
                },
                ensure_ascii=False,
            )
        )
        return 0

    update_count = len(updates)
    create_count = len(creates)
    confirm_updates = args.confirm_update_count if args.confirm_update_count >= 0 else update_count
    confirm_creates = args.confirm_create_count if args.confirm_create_count >= 0 else create_count

    try:
        assert_apply_gates(
            apply=args.apply,
            rollback=args.rollback,
            owner_authorization=args.owner_authorization,
            confirm_production_write=args.confirm_production_write,
            confirm_source_sha256=args.confirm_source_sha256,
            confirm_update_manifest_sha256=args.confirm_update_manifest_sha256,
            confirm_create_manifest_sha256=args.confirm_create_manifest_sha256,
            update_manifest_sha256=ids["update_manifest_sha256"],
            create_manifest_sha256=ids["create_manifest_sha256"],
            confirm_update_count=confirm_updates,
            confirm_create_count=confirm_creates,
            update_count=update_count,
            create_count=create_count,
        )
    except ApplyAbort as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2

    if not args.database_url:
        print(json.dumps({"status": "blocked", "reason": "missing_database_url"}, ensure_ascii=False))
        return 2

    conn = connect_runtime_db(args.database_url)
    try:
        if args.rollback:
            journal_path = args.rollback_journal
            if journal_path is None:
                print(json.dumps({"status": "blocked", "reason": "missing_rollback_journal"}, ensure_ascii=False))
                return 2
            journal = load_apply_journal(journal_path)
            rolled = rollback_from_journal(conn, journal, dry_run=False)
            print(json.dumps({"status": "ROLLED_BACK", "rows": rolled}, ensure_ascii=False))
            return 0

        live_by_id: dict[int, dict[str, str]] = {}
        if updates:
            cur = conn.cursor()
            pids = [r.product_id for r in updates]
            cur.execute(
                "SELECT id, sku, base_price::text FROM products WHERE id = ANY(%s) AND deleted_at IS NULL",
                (pids,),
            )
            for row in cur.fetchall():
                live_by_id[int(row[0])] = {"sku": row[1], "base_price": row[2]}

        batch_id = new_batch_id()
        result = execute_ast_catalog_apply(
            conn,
            updates,
            creates,
            dry_run=False,
            batch_id=batch_id,
            journal_dir=journal_dir,
            metadata={
                "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
                "update_manifest_sha256": ids["update_manifest_sha256"],
                "create_manifest_sha256": ids["create_manifest_sha256"],
            },
            live_by_id=live_by_id,
        )
        if not result.production_apply_executed:
            print(
                json.dumps(
                    {
                        "status": "APPLY_ABORTED",
                        "reason": result.aborted_reason,
                        "batch_id": result.batch_id,
                    },
                    ensure_ascii=False,
                )
            )
            return 3
        print(
            json.dumps(
                {
                    "status": "APPLIED",
                    "updates_written": result.updates_written,
                    "creates_written": result.creates_written,
                    "batch_id": result.batch_id,
                    "journal_path": result.journal_path,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except ApplyAbort as exc:
        print(json.dumps({"status": "APPLY_FAILED", "reason": str(exc)}, ensure_ascii=False))
        return 4
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
