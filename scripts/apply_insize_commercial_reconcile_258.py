#!/usr/bin/env python3
"""INSIZE #258 final commercial reconcile APPLY — dry-run default; guarded production write.

Production APPLY requires every gate in assert_apply_authorization_gates plus
KARZAR_ALLOW_PRODUCTION_WRITE=1 and KARZAR_INGESTION_CATEGORY=B.

This PR must not execute production --apply.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_insize_commercial_reconcile_258 import (  # noqa: E402
    INSIZE_OWNER_SOURCE_SHA,
    INSIZE_OWNER_SOURCE_XLSX,
)
from catalog_target.insize_commercial_reconcile_258 import (  # noqa: E402
    OWNER_AUTH_APPLY,
    OWNER_AUTH_ROLLBACK,
    OWNER_SOURCE_SHA256,
    PLAN_CSV_NAME,
    ROLLBACK_CSV_NAME,
    apply_plan_rows,
    assert_apply_authorization_gates,
    assert_plan_matches_evidence,
    classify_owner_freshness,
    load_plan_rows,
    load_rollback_rows,
    load_source_manifest,
    production_preflight,
    rollback_plan_rows,
    sha256_file,
    validate_source_sha256,
    writer_contract_summary,
)
from catalog_target.sales_wave_apply import (  # noqa: E402
    ApplyAbort,
    assert_production_apply_authorized,
    connect_runtime_db,
)


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--evidence-dir",
        type=Path,
        default=ROOT / "audit" / "insize-commercial-reconcile-258-2026-10-13",
    )
    p.add_argument("--journal-dir", type=Path, default=None)
    p.add_argument("--source-xlsx", type=Path, default=INSIZE_OWNER_SOURCE_XLSX)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    p.add_argument("--production-preflight", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--rollback", action="store_true")
    p.add_argument("--confirm-production-write", action="store_true")
    p.add_argument("--confirm-source-sha256", default="")
    p.add_argument("--confirm-plan-sha256", default="")
    p.add_argument("--confirm-mutation-count", type=int, default=-1)
    p.add_argument("--confirm-rollback-manifest-sha256", default="")
    p.add_argument("--confirm-batch-id", default="")
    p.add_argument("--owner-authorization", default="")
    p.add_argument("--owner-freshness-attestation-at", default="")
    p.add_argument("--owner-freshness-source-age-days", type=int, default=-1)
    p.add_argument("--report-json", type=Path, default=None)
    args = p.parse_args(argv)

    evidence = args.evidence_dir
    plan_path = evidence / PLAN_CSV_NAME
    rollback_path = evidence / ROLLBACK_CSV_NAME
    plan_sha = sha256_file(plan_path)
    rollback_sha = sha256_file(rollback_path)
    plan_rows = load_plan_rows(plan_path)
    stats = assert_plan_matches_evidence(plan_rows, evidence)
    manifest = load_source_manifest(evidence)

    attestation_at = None
    if args.owner_freshness_attestation_at:
        attestation_at = datetime.fromisoformat(
            args.owner_freshness_attestation_at.replace("Z", "+00:00")
        )
    attested_age = None
    if args.owner_freshness_source_age_days >= 0:
        attested_age = args.owner_freshness_source_age_days
    age, freshness_class = classify_owner_freshness(
        manifest,
        attestation_at=attestation_at,
        attested_source_age_days=attested_age,
    )
    if freshness_class == "STALE":
        raise SystemExit("BLOCKED_SOURCE_STALE")

    if args.source_xlsx.is_file():
        validate_source_sha256(args.source_xlsx, expected=INSIZE_OWNER_SOURCE_SHA)

    journal_dir = args.journal_dir or (evidence / "apply-journals")

    if args.production_preflight:
        report = production_preflight(
            evidence_dir=evidence,
            plan_rows=plan_rows,
            source_xlsx=args.source_xlsx,
            ssh_host=args.ssh_host,
            database_url=args.database_url,
        )
        report["mode"] = "production_preflight"
        print(json.dumps(report, indent=2))
        if args.report_json:
            args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0 if report.get("STATUS") == "READY" else 2

    dry_run = not args.apply and not args.rollback
    if args.apply:
        assert_apply_authorization_gates(
            apply=True,
            rollback=False,
            confirm_production_write=args.confirm_production_write,
            confirm_source_sha256=args.confirm_source_sha256,
            confirm_plan_sha256=args.confirm_plan_sha256,
            confirm_mutation_count=args.confirm_mutation_count,
            owner_authorization=args.owner_authorization,
            plan_sha256=plan_sha,
            eligible_count=len(plan_rows),
        )
        assert_production_apply_authorized(
            apply=True,
            confirm_production_write=args.confirm_production_write,
            confirm_plan_sha256=args.confirm_plan_sha256,
            plan_csv_sha256=plan_sha,
            db_host="",
            database_url=args.database_url,
        )
        if not args.database_url:
            raise ApplyAbort("apply_requires_database_url")
        batch_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        metadata = {
            "started_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_sha256": OWNER_SOURCE_SHA256,
            "plan_sha256": plan_sha,
            "rollback_manifest_sha256": rollback_sha,
            "git_sha": _git_head(),
            "database_identity": {"database_url": args.database_url.split("@")[-1]},
            "authorization": OWNER_AUTH_APPLY,
        }
        conn = connect_runtime_db(args.database_url)
        try:
            result = apply_plan_rows(
                conn,
                plan_rows,
                dry_run=False,
                batch_id=batch_id,
                metadata=metadata,
                journal_dir=journal_dir,
            )
        finally:
            conn.close()
        print(json.dumps({"result": result.journal, "aborted": result.aborted_reason}, indent=2))
        return 0 if result.committed else 2

    if args.rollback:
        assert_apply_authorization_gates(
            apply=False,
            rollback=True,
            confirm_production_write=args.confirm_production_write,
            confirm_source_sha256="",
            confirm_plan_sha256="",
            confirm_mutation_count=0,
            owner_authorization=args.owner_authorization,
            plan_sha256=plan_sha,
            eligible_count=len(plan_rows),
            confirm_rollback_manifest_sha256=args.confirm_rollback_manifest_sha256,
            rollback_manifest_sha256=rollback_sha,
            confirm_batch_id=args.confirm_batch_id,
        )
        assert_production_apply_authorized(
            apply=True,
            confirm_production_write=args.confirm_production_write,
            confirm_plan_sha256=args.confirm_rollback_manifest_sha256,
            plan_csv_sha256=rollback_sha,
            db_host="",
            database_url=args.database_url,
        )
        if not args.database_url:
            raise ApplyAbort("rollback_requires_database_url")
        rollback_rows = load_rollback_rows(rollback_path)
        batch_id = args.confirm_batch_id
        metadata = {
            "started_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_sha256": OWNER_SOURCE_SHA256,
            "plan_sha256": plan_sha,
            "rollback_manifest_sha256": rollback_sha,
            "git_sha": _git_head(),
            "database_identity": {"database_url": args.database_url.split("@")[-1]},
            "authorization": OWNER_AUTH_ROLLBACK,
        }
        conn = connect_runtime_db(args.database_url)
        try:
            result = rollback_plan_rows(
                conn,
                rollback_rows,
                batch_id=batch_id,
                metadata=metadata,
                journal_dir=journal_dir,
            )
        finally:
            conn.close()
        print(json.dumps({"result": result.journal, "aborted": result.aborted_reason}, indent=2))
        return 0 if result.committed else 2

    if dry_run:
        report = {
            "mode": "DRY_RUN",
            "source_sha256": INSIZE_OWNER_SOURCE_SHA,
            "plan_sha256": plan_sha,
            "rollback_manifest_sha256": rollback_sha,
            "eligible_rows": len(plan_rows),
            "plan_stats": stats,
            "effective_source_age_days": age,
            "freshness_classification": freshness_class,
            "freshness_basis": manifest.get("freshness_basis"),
            "writer_contract": writer_contract_summary(),
            "PRODUCTION_MUTATION": "NO",
            "DATABASE_MUTATION": "NO",
        }
        print(json.dumps(report, indent=2))
        return 0

    raise SystemExit("no_mode_selected")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApplyAbort as exc:
        print(f"ApplyAbort: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
