#!/usr/bin/env python3
"""Category B APPLY for AST manifests (dry-run default). Does not run without explicit gates."""

from __future__ import annotations

import argparse
import asyncio
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
    load_apply_journal,
    load_create_plan,
    load_update_plan,
    manifest_identity,
    new_batch_id,
    rollback_from_journal,
)
from catalog_target.ast_price_catalog_constants import SOURCE_ARCHIVE_SHA256  # noqa: E402
from catalog_target.ast_price_catalog_execution import (  # noqa: E402
    ApplyCohort,
    execute_ast_apply_async,
)
from catalog_target.ast_price_catalog_manifest_acceptance import (  # noqa: E402
    OWNER_MANIFEST_BUNDLE_FILENAME,
    assert_backup_evidence_gate,
    assert_owner_manifest_bundle_gate,
)
from catalog_target.sales_wave_apply import ApplyAbort, connect_runtime_db  # noqa: E402


def _parse_cohort(raw: str) -> ApplyCohort:
    value = (raw or "").strip().lower()
    if value not in {"update", "create", "both"}:
        raise ApplyAbort(f"invalid_apply_cohort:{raw}")
    return value  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "audit/ast-price-and-catalog-20261024")
    parser.add_argument("--journal-dir", type=Path, default=None)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--apply-cohort", default="both", choices=["update", "create", "both"])
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
    parser.add_argument("--confirm-manifest-bundle-sha256", default="")
    parser.add_argument("--confirm-backup-evidence-sha256", default="")
    parser.add_argument("--backup-evidence-file", type=Path, default=None)
    args = parser.parse_args()

    cohort = _parse_cohort(args.apply_cohort)
    update_path = args.audit_dir / "UPDATE_PRODUCTS.csv"
    create_path = args.audit_dir / "CREATE_PRODUCTS.csv"
    bundle_path = args.audit_dir / "sanitized" / OWNER_MANIFEST_BUNDLE_FILENAME
    journal_dir = args.journal_dir or (args.audit_dir / "journals")
    ids = manifest_identity(update_path, create_path)
    updates = load_update_plan(update_path) if cohort in {"update", "both"} else []
    creates = load_create_plan(
        create_path,
        expected_manifest_sha256=ids["create_manifest_sha256"],
        require_owner_approval=True,
    ) if cohort in {"create", "both"} else []

    dry_run = not args.apply and not args.rollback
    if dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "apply_cohort": cohort,
                    "updates": len(updates),
                    "creates_eligible": len(creates),
                    "manifest": ids,
                    "manifest_bundle_path": str(bundle_path),
                    "note": "Pass --apply with full Category B gates to mutate production.",
                },
                ensure_ascii=False,
            )
        )
        return 0

    update_count = len(updates)
    create_count = len(creates)
    if args.confirm_update_count < 0 or args.confirm_create_count < 0:
        print(json.dumps({"status": "blocked", "reason": "missing_explicit_confirm_mutation_counts"}, ensure_ascii=False))
        return 2

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
            confirm_update_count=args.confirm_update_count,
            confirm_create_count=args.confirm_create_count,
            update_count=update_count,
            create_count=create_count,
        )
        if args.apply:
            assert_owner_manifest_bundle_gate(
                confirm_manifest_bundle_sha256=args.confirm_manifest_bundle_sha256,
                bundle_path=bundle_path,
            )
            backup_path = args.backup_evidence_file or (args.audit_dir / "sanitized" / "BACKUP_EVIDENCE.sha256")
            assert_backup_evidence_gate(
                confirm_backup_evidence_sha256=args.confirm_backup_evidence_sha256,
                backup_evidence_path=backup_path,
            )
    except ApplyAbort as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2

    if not args.database_url:
        print(json.dumps({"status": "blocked", "reason": "missing_database_url"}, ensure_ascii=False))
        return 2

    if args.rollback:
        conn = connect_runtime_db(args.database_url)
        try:
            journal_path = args.rollback_journal
            if journal_path is None:
                print(json.dumps({"status": "blocked", "reason": "missing_rollback_journal"}, ensure_ascii=False))
                return 2
            journal = load_apply_journal(journal_path)
            rolled = rollback_from_journal(conn, journal, dry_run=False)
            print(json.dumps({"status": "ROLLED_BACK", "rows": rolled}, ensure_ascii=False))
            return 0
        except ApplyAbort as exc:
            print(json.dumps({"status": "ROLLBACK_FAILED", "reason": str(exc)}, ensure_ascii=False))
            return 4
        finally:
            conn.close()

    batch_id = new_batch_id()
    try:
        result = asyncio.run(
            execute_ast_apply_async(
                args.database_url,
                updates,
                creates,
                cohort=cohort,
                dry_run=False,
                batch_id=batch_id,
                journal_dir=journal_dir,
                metadata={
                    "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
                    "update_manifest_sha256": ids["update_manifest_sha256"],
                    "create_manifest_sha256": ids["create_manifest_sha256"],
                    "apply_cohort": cohort,
                },
            )
        )
    except ApplyAbort as exc:
        print(json.dumps({"status": "APPLY_FAILED", "reason": str(exc)}, ensure_ascii=False))
        return 4

    if not result.production_apply_executed:
        print(
            json.dumps(
                {
                    "status": "APPLY_ABORTED_OR_VERIFY_FAILED",
                    "reason": result.aborted_reason,
                    "batch_id": result.batch_id,
                    "journal_path": result.journal_path,
                    "committed": result.committed,
                },
                ensure_ascii=False,
            )
        )
        return 3

    print(
        json.dumps(
            {
                "status": "APPLIED_AND_VERIFIED",
                "apply_cohort": cohort,
                "updates_written": result.updates_written,
                "creates_written": result.creates_written,
                "batch_id": result.batch_id,
                "journal_path": result.journal_path,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
