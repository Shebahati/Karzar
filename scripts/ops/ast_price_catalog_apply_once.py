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
from catalog_target.ast_price_catalog_backup_attestation import (  # noqa: E402
    BACKUP_ATTESTATION_FILENAME,
    assert_production_backup_attestation_gate,
)
from catalog_target.ast_price_catalog_constants import SOURCE_ARCHIVE_SHA256  # noqa: E402
from catalog_target.ast_price_catalog_execution import (  # noqa: E402
    ApplyCohort,
    execute_ast_apply_async,
)
from catalog_target.ast_price_catalog_database_identity import (  # noqa: E402
    fetch_database_identity_fingerprint,
)
from catalog_target.ast_price_catalog_manifest_acceptance import (  # noqa: E402
    assert_owner_manifest_acceptance_gate,
    manifest_file_sha256,
    resolve_bundle_path,
)
from catalog_target.ast_price_catalog_update_canary import (  # noqa: E402
    load_canary_registry,
    product_id_allowlist_sha256,
    resolve_stage_update_path,
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
    parser.add_argument("--apply-cohort", default="update", choices=["update", "create", "both"])
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
    parser.add_argument("--confirm-owner-acceptance-id", default="")
    parser.add_argument("--confirm-backup-artifact-sha256", default="")
    parser.add_argument("--backup-attestation-file", type=Path, default=None)
    parser.add_argument("--update-stage", default="full", choices=["stage1", "stage2", "stage3", "full"])
    parser.add_argument("--confirm-git-commit-sha", default="")
    parser.add_argument("--confirm-stage-manifest-sha256", default="")
    parser.add_argument("--confirm-master-update-manifest-sha256", default="")
    parser.add_argument("--confirm-product-id-allowlist-sha256", default="")
    parser.add_argument("--owner-acceptance-record-file", type=Path, default=None)
    parser.add_argument("--confirm-canary-full-cohort-bypass", action="store_true")
    args = parser.parse_args()

    cohort = _parse_cohort(args.apply_cohort)
    update_stage = (args.update_stage or "full").strip().lower()
    create_path = args.audit_dir / "CREATE_PRODUCTS.csv"
    master_update_path = args.audit_dir / "UPDATE_PRODUCTS.csv"
    master_update_sha = manifest_file_sha256(master_update_path)
    stage_allowlist_sha = ""
    if cohort == "update" and update_stage != "full":
        registry = load_canary_registry(args.audit_dir)
        stage_meta = registry.get("stages", {}).get(update_stage) or {}
        update_path = resolve_stage_update_path(args.audit_dir, update_stage)  # type: ignore[arg-type]
        stage_sha = manifest_file_sha256(update_path)
        if stage_sha != str(stage_meta.get("manifest_sha256") or ""):
            print(json.dumps({"status": "blocked", "reason": "stage_manifest_sha256_registry_mismatch"}, ensure_ascii=False))
            return 2
        stage_allowlist_sha = str(stage_meta.get("product_id_allowlist_sha256") or "")
    else:
        update_path = master_update_path
        stage_sha = master_update_sha
        if cohort == "update":
            stage_allowlist_sha = product_id_allowlist_sha256(
                [int(r["product_id"]) for r in load_update_plan(update_path)] if update_path.is_file() else []
            )

    bundle_path = resolve_bundle_path(args.audit_dir, cohort, update_stage=update_stage)
    journal_dir = args.journal_dir or (args.audit_dir / "journals")
    ids = manifest_identity(update_path, create_path)
    ids["master_update_manifest_sha256"] = master_update_sha
    ids["stage_manifest_sha256"] = stage_sha
    ids["update_stage"] = update_stage
    updates = load_update_plan(update_path) if cohort in {"update", "both"} else []
    creates = (
        load_create_plan(
            create_path,
            expected_manifest_sha256=ids["create_manifest_sha256"],
            require_owner_approval=True,
        )
        if cohort in {"create", "both"}
        else []
    )

    dry_run = not args.apply and not args.rollback
    if dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "apply_cohort": cohort,
                    "update_stage": update_stage,
                    "updates": len(updates),
                    "creates_eligible": len(creates),
                    "manifest": ids,
                    "owner_bundle_path": str(bundle_path),
                    "stage_product_id_allowlist_sha256": stage_allowlist_sha,
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
        if args.apply and cohort == "update":
            if update_stage == "full" and not args.confirm_canary_full_cohort_bypass:
                raise ApplyAbort("update_stage_full_blocked_use_stage1_stage2_stage3_canary_sequence")
            if update_stage in {"stage2", "stage3"} and args.database_url:
                from catalog_target.ast_price_catalog_execution import async_sqlalchemy_database_url
                from catalog_target.ast_price_catalog_execution_store import assert_prior_canary_stages_verified
                from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

                async def _check_prior() -> None:
                    engine = create_async_engine(async_sqlalchemy_database_url(args.database_url))
                    async with AsyncSession(engine) as session:
                        await assert_prior_canary_stages_verified(
                            session,
                            master_update_manifest_sha256=master_update_sha,
                            update_stage=update_stage,
                        )
                    await engine.dispose()

                asyncio.run(_check_prior())
        assert_apply_gates(
            apply=args.apply,
            rollback=args.rollback,
            owner_authorization=args.owner_authorization,
            confirm_production_write=args.confirm_production_write,
            confirm_source_sha256=args.confirm_source_sha256,
            confirm_update_manifest_sha256=args.confirm_update_manifest_sha256 or stage_sha,
            confirm_create_manifest_sha256=args.confirm_create_manifest_sha256,
            update_manifest_sha256=stage_sha,
            create_manifest_sha256=ids["create_manifest_sha256"],
            confirm_update_count=args.confirm_update_count,
            confirm_create_count=args.confirm_create_count,
            update_count=update_count,
            create_count=create_count,
        )
        if args.apply:
            assert_owner_manifest_acceptance_gate(
                cohort=cohort,
                bundle_path=bundle_path,
                confirm_manifest_bundle_sha256=args.confirm_manifest_bundle_sha256,
                confirm_owner_acceptance_id=args.confirm_owner_acceptance_id,
                live_update_manifest_sha256=stage_sha,
                live_create_manifest_sha256=ids["create_manifest_sha256"],
                live_update_count=update_count,
                live_create_count=create_count,
                owner_acceptance_record_path=args.owner_acceptance_record_file,
                confirm_update_stage=update_stage,
                confirm_stage_manifest_sha256=args.confirm_stage_manifest_sha256 or stage_sha,
                confirm_master_update_manifest_sha256=(
                    args.confirm_master_update_manifest_sha256 or master_update_sha
                ),
                confirm_product_id_allowlist_sha256=(
                    args.confirm_product_id_allowlist_sha256 or stage_allowlist_sha
                ),
            )
            attestation_path = args.backup_attestation_file or (
                args.audit_dir / "sanitized" / BACKUP_ATTESTATION_FILENAME
            )
            verified_db_identity = asyncio.run(fetch_database_identity_fingerprint(args.database_url))
            assert_production_backup_attestation_gate(
                attestation_path=attestation_path,
                confirm_backup_artifact_sha256=args.confirm_backup_artifact_sha256,
                verified_database_identity=verified_db_identity,
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
                    "update_manifest_sha256": stage_sha,
                    "master_update_manifest_sha256": master_update_sha,
                    "stage_manifest_sha256": stage_sha,
                    "update_stage": update_stage,
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
