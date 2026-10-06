#!/usr/bin/env python3
"""Phase 2F — owner-authorized real Product.name APPLY (one-shot).

Persistent mutation requires ALL of:
  --apply
  --confirm-cohort-sha <Phase 2D candidate SHA256>
  --confirm-prestate-sha <Phase 2E prestate SHA256>
  --confirm-logic-sha <git SHA of frozen apply logic commit>

Plain invocation and --preflight-only never COMMIT.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming_phase2e import (  # noqa: E402
    CHANGE_LOG_CONTRACT_REFERENCE,
    CHANGE_LOG_EQUIVALENT_FIELDS,
    PHASE2D_CANDIDATE_SHA256,
    collision_precheck_python,
    normalize_name_for_collision,
    reconcile_live_row,
    sha256_file,
    target_fingerprint_row,
    validate_candidate_file,
    validate_phase2d_freeze_manifest,
    load_freeze_manifest,
)
from app.domain.product_naming_phase2f import (  # noqa: E402
    PHASE2E_MANIFEST,
    PHASE2E_PRESTATE_SHA256,
    PHASE2E_EXPECTED_PRESTATE,
    REAL_APPLY_ADVISORY_LOCK_KEY,
    REAL_APPLY_EXPECTED_ROWS,
    apply_change_log_reason,
    apply_success_metrics,
    audit_apply_logs,
    build_real_apply_sql,
    build_recovery_target_rows,
    load_expected_prestate_csv,
    parse_apply_stdout,
    real_apply_logic_file_sha256,
    reject_forbidden_apply_flags,
    second_apply_blocked_reason,
    validate_phase2e_manifest,
    assert_confirmation_sha,
)

from scripts.ops.phase2c_manufacturer_identity_apply_once import (  # noqa: E402
    EvidenceImmutabilityError,
    assert_evidence_writable,
    canonical_json_bytes,
    collect_live_health,
    collect_runtime_identity,
    write_csv,
    write_json,
    _run_ssh_psql,
    _run_ssh_psql_script,
)

AUDIT_OUT = ROOT / "audit" / "product-naming-phase2f-real-apply"
DEFAULT_CANDIDATE = ROOT / "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
DEFAULT_MANIFEST = ROOT / "audit/product-naming-phase2d/PHASE2D_CANDIDATE_FREEZE_MANIFEST.json"
DEFAULT_PRESTATE = ROOT / PHASE2E_EXPECTED_PRESTATE
DEFAULT_BACKUP_DIR = Path.home() / "karzar-backups" / "phase2f"

EXPECTED_VPS_HOSTNAME = "srv5944957438"
EXPECTED_ALEMBIC = "u4v5w6x7y8z9"
EXPECTED_APP_ENV = "staging"
EXPECTED_DB = "karzar_staging"
APPLY_COLLECTOR_HOSTNAME = "hp-g2-450"

IMMUTABLE_EVIDENCE_BASENAMES = frozenset(
    {
        "LIVE_RUNTIME_IDENTITY.json",
        "PRE_APPLY_HEALTH.json",
        "PHASE2F_PREFLIGHT_RECONCILIATION.csv",
        "PHASE2F_TARGET_PRE_APPLY.csv",
        "PHASE2F_COLLISION_PRECHECK.json",
        "BACKUP_MANIFEST.json",
        "RECOVERY_TARGETS.csv",
        "RECOVERY_MANIFEST.json",
        "RECOVERY_PLAN.md",
        "REAL_APPLY_TRANSACTION_RESULT.json",
        "PHASE2F_IN_TRANSACTION_LOG_AUDIT.csv",
        "PHASE2F_TARGET_POST_APPLY.csv",
        "POST_APPLY_CHANGE_LOG_AUDIT.json",
        "POST_APPLY_COLLISION_AUDIT.json",
        "POST_APPLY_READ_SMOKE.json",
        "SECOND_APPLY_SAFETY.json",
        "REAL_APPLY_MANIFEST.json",
        "PHASE2F_REAL_APPLY_SUMMARY.md",
        "EVIDENCE_SHA256SUMS.txt",
    }
)

MUTATION_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER)\b", re.I)


def evidence_dir_has_successful_apply(out_dir: Path) -> bool:
    manifest = out_dir / "REAL_APPLY_MANIFEST.json"
    if not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return payload.get("status") == "APPLIED_VERIFIED"


def resolve_writable_out_dir(requested: Path) -> Path:
    requested = requested.resolve()
    if requested != AUDIT_OUT.resolve():
        return requested
    if not evidence_dir_has_successful_apply(requested):
        return requested
    probe_dir = requested / "probes" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    probe_dir.mkdir(parents=True, exist_ok=False)
    return probe_dir


def _git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "UNKNOWN"


def _git_status_clean() -> bool:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and not proc.stdout.strip()


def validate_live_runtime_identity(runtime: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if runtime.get("vps_hostname") != EXPECTED_VPS_HOSTNAME:
        errors.append(f"vps_hostname={runtime.get('vps_hostname')}")
    if runtime.get("postgres_container") != "lathe_postgres":
        errors.append(f"postgres_container={runtime.get('postgres_container')}")
    if runtime.get("postgres_db_name") != EXPECTED_DB:
        errors.append(f"postgres_db_name={runtime.get('postgres_db_name')}")
    if runtime.get("APP_ENV") != EXPECTED_APP_ENV:
        errors.append(f"APP_ENV={runtime.get('APP_ENV')}")
    if runtime.get("alembic_current") != EXPECTED_ALEMBIC:
        errors.append(f"alembic={runtime.get('alembic_current')}")
    if runtime.get("api_container") != "lathe_api":
        errors.append(f"api_container={runtime.get('api_container')}")
    return errors


def create_live_backup(*, ssh_host: str, backup_dir: Path) -> dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.chmod(0o700)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"karzar_staging_phase2f_{ts}.dump"
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker exec -i lathe_postgres pg_dump -U karzar_staging -Fc karzar_staging",
        ],
        stdout=path.open("wb"),
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"pg_dump failed: {err}")
    size = path.stat().st_size
    if size <= 0:
        raise RuntimeError("backup empty")
    digest = sha256_file(path)
    list_proc = subprocess.run(
        ["pg_restore", "--list", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if list_proc.returncode != 0:
        raise RuntimeError(f"pg_restore --list failed: {list_proc.stderr}")
    list_lines = [ln for ln in list_proc.stdout.splitlines() if ln.strip()]
    pg_ver = _run_ssh_psql("SHOW server_version;", ssh_host=ssh_host)
    return {
        "created": True,
        "path": str(path),
        "timestamp_utc": ts,
        "size_bytes": size,
        "sha256": digest,
        "database_name": EXPECTED_DB,
        "postgresql_version": pg_ver,
        "pg_restore_list_entries": len(list_lines),
        "pg_restore_list_verification": "PASS",
        "committed_to_git": False,
    }


def fetch_live_targets(ids: list[int], ssh_host: str) -> dict[str, dict[str, str]]:
    id_csv = ",".join(str(i) for i in sorted(ids))
    sql = f"""
SELECT row_to_json(t) FROM (
  SELECT id, sku, name, slug, manufacturer_code, brand_id, category_id, product_type_id,
         meta_title, meta_description, base_price, original_price, is_available, is_active,
         deleted_at::text AS deleted_at, stock_quantity, tax_percent
  FROM products WHERE id IN ({id_csv}) ORDER BY id
) t;
"""
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    out: dict[str, dict[str, str]] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        pid = str(obj["id"])
        out[pid] = {k: str(v) if v is not None else "" for k, v in obj.items()}
    if len(out) != len(ids):
        raise RuntimeError(f"live fetch incomplete {len(out)}/{len(ids)}")
    return out


def fetch_catalog_names(ssh_host: str) -> list[tuple[int, str]]:
    sql = """
SELECT row_to_json(t) FROM (
  SELECT id, name FROM products WHERE deleted_at IS NULL ORDER BY id
) t;
"""
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    rows: list[tuple[int, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        rows.append((int(obj["id"]), str(obj["name"])))
    return rows


def write_recovery_package(
    out_dir: Path,
    prestate: list[dict[str, str]],
    *,
    cohort_sha256: str,
) -> dict[str, Any]:
    targets = build_recovery_target_rows(prestate)
    targets_path = out_dir / "RECOVERY_TARGETS.csv"
    write_csv(
        targets_path,
        targets,
        [
            "product_id",
            "sku",
            "manufacturer_code",
            "brand_id",
            "product_type_id",
            "pre_apply_name",
            "applied_name",
        ],
    )
    plan = f"""# Phase 2F Product.name recovery plan

## Status
NOT EXECUTED. Separate owner authorization required.

## Scope
- Rows: {len(targets)}
- Cohort SHA256: `{cohort_sha256}`

## Recovery semantics (if later authorized)
1. For each row in `RECOVERY_TARGETS.csv`, restore `products.name` to `pre_apply_name`
   only if current name still equals `applied_name`.
2. Revalidate SKU, manufacturer_code, brand_id, product_type_id before any write.
3. Write compensating `product_change_logs` rows; never delete original Phase 2F logs.
4. Use SERIALIZABLE transaction with advisory lock.

## Forbidden without new authorization
- SKU / slug / taxonomy / price / availability mutation
- Automatic full-database restore (disaster recovery dump only)
"""
    plan_path = out_dir / "RECOVERY_PLAN.md"
    assert_evidence_writable(plan_path)
    plan_path.write_text(plan, encoding="utf-8")
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cohort_sha256": cohort_sha256,
        "rows": len(targets),
        "executable_without_confirmation": False,
        "targets_csv_sha256": sha256_file(targets_path),
        "plan_sha256": sha256_file(plan_path),
    }
    payload_sha = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    manifest["manifest_payload_sha256"] = payload_sha
    manifest_path = out_dir / "RECOVERY_MANIFEST.json"
    write_json(manifest_path, manifest)
    if sha256_file(manifest_path) == payload_sha:
        raise RuntimeError("recovery manifest payload hash unexpectedly equals final file hash")
    return manifest


def run_read_smoke(
    prestate: list[dict[str, str]],
    pre_apply: dict[str, dict[str, str]],
    *,
    ssh_host: str,
) -> dict[str, Any]:
    samples = prestate[:5] + prestate[23:28] + prestate[-5:]
    seen: set[str] = set()
    picks: list[dict[str, str]] = []
    for row in samples:
        if row["product_id"] in seen:
            continue
        seen.add(row["product_id"])
        picks.append(row)
    results: list[dict[str, Any]] = []
    for row in picks:
        pid = int(row["product_id"])
        sql = f"""
SELECT row_to_json(t) FROM (
  SELECT id, name, slug, manufacturer_code, base_price
  FROM products WHERE id = {pid}
) t;
"""
        raw = _run_ssh_psql(sql, ssh_host=ssh_host)
        obj = json.loads(raw.splitlines()[-1])
        pre = pre_apply[row["product_id"]]
        ok_name = (obj.get("name") or "").strip() == row["proposed_name"]
        ok_slug = (obj.get("slug") or "").strip() == (pre.get("slug") or "").strip()
        ok_mc = (obj.get("manufacturer_code") or "").strip() == (
            pre.get("manufacturer_code") or ""
        ).strip()
        ok_price = str(obj.get("base_price") or "") == (pre.get("base_price") or "")
        results.append(
            {
                "product_id": pid,
                "proposed_name": row["proposed_name"],
                "live_name": obj.get("name"),
                "name_ok": ok_name,
                "slug_ok": ok_slug,
                "manufacturer_code_ok": ok_mc,
                "base_price_ok": ok_price,
            }
        )
    return {
        "checked": len(results),
        "all_pass": all(
            r["name_ok"] and r["slug_ok"] and r["manufacturer_code_ok"] and r["base_price_ok"]
            for r in results
        ),
        "samples": results,
    }


def write_evidence_sha256sums(out_dir: Path) -> None:
    lines: list[str] = []
    for p in sorted(out_dir.glob("*")):
        if p.is_file() and p.name != "EVIDENCE_SHA256SUMS.txt":
            lines.append(f"{sha256_file(p)}  {p.name}")
    path = out_dir / "EVIDENCE_SHA256SUMS.txt"
    assert_evidence_writable(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def authoritative_post_apply_state(
    prestate: list[dict[str, str]],
    reason: str,
    *,
    ssh_host: str,
) -> dict[str, Any]:
    ids = [int(r["product_id"]) for r in prestate]
    live = fetch_live_targets(ids, ssh_host)
    proposed_ok = sum(
        1 for r in prestate if (live[r["product_id"]].get("name") or "").strip() == r["proposed_name"]
    )
    old_left = sum(
        1
        for r in prestate
        if (live[r["product_id"]].get("name") or "").strip() == r["expected_old_name"]
    )
    id_csv = ",".join(str(i) for i in ids)
    esc = reason.replace("'", "''")
    log_sql = f"""
SELECT COUNT(*) FROM product_change_logs
WHERE field_name = 'name' AND reason = '{esc}' AND product_id IN ({id_csv});
"""
    log_count = int(_run_ssh_psql(log_sql, ssh_host=ssh_host).splitlines()[-1])
    dup_sql = f"""
SELECT COUNT(*) FROM (
  SELECT product_id FROM product_change_logs
  WHERE field_name = 'name' AND reason = '{esc}' AND product_id IN ({id_csv})
  GROUP BY product_id HAVING COUNT(*) > 1
) s;
"""
    dup_logs = int(_run_ssh_psql(dup_sql, ssh_host=ssh_host).splitlines()[-1])
    return {
        "proposed_names": proposed_ok,
        "old_names_remaining": old_left,
        "phase2f_logs": log_count,
        "duplicate_logs": dup_logs,
        "live": live,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    reject_forbidden_apply_flags(argv)

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--confirm-cohort-sha", default=None)
    p.add_argument("--confirm-prestate-sha", default=None)
    p.add_argument("--confirm-logic-sha", default=None)
    p.add_argument("--candidate-file", type=Path, default=DEFAULT_CANDIDATE)
    p.add_argument("--prestate-file", type=Path, default=DEFAULT_PRESTATE)
    p.add_argument("--phase2e-manifest", type=Path, default=ROOT / PHASE2E_MANIFEST)
    p.add_argument("--freeze-manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument("--out-dir", type=Path, default=AUDIT_OUT)
    p.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    args = p.parse_args(argv)

    if not args.apply and not args.preflight_only:
        print("ERROR: specify --preflight-only or authorized --apply", file=sys.stderr)
        return 2
    if args.apply and args.preflight_only:
        print("ERROR: --apply and --preflight-only are mutually exclusive", file=sys.stderr)
        return 2

    validate_phase2d_freeze_manifest(load_freeze_manifest(args.freeze_manifest))
    _, cand_sha = validate_candidate_file(
        args.candidate_file, expected_sha256=PHASE2D_CANDIDATE_SHA256
    )
    prestate = load_expected_prestate_csv(args.prestate_file)
    validate_phase2e_manifest(args.phase2e_manifest)
    cohort_sha = cand_sha
    reason = apply_change_log_reason(cohort_sha)

    out_dir = resolve_writable_out_dir(args.out_dir)
    if out_dir != args.out_dir.resolve():
        print(f"NOTE: writing probe diagnostics to {out_dir}", file=sys.stderr)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.apply:
        try:
            assert_confirmation_sha(args.confirm_cohort_sha, PHASE2D_CANDIDATE_SHA256, flag_name="confirm-cohort-sha")
            assert_confirmation_sha(
                args.confirm_prestate_sha, PHASE2E_PRESTATE_SHA256, flag_name="confirm-prestate-sha"
            )
            assert_confirmation_sha(args.confirm_logic_sha, _git_head(), flag_name="confirm-logic-sha")
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        if not _git_status_clean():
            print("ERROR: git worktree must be clean for --apply", file=sys.stderr)
            return 2
        collector_host = subprocess.run(
            ["hostname"], capture_output=True, text=True, check=False
        ).stdout.strip()
        if collector_host != APPLY_COLLECTOR_HOSTNAME:
            print(
                f"ERROR: real APPLY requires collector hostname {APPLY_COLLECTOR_HOSTNAME}, "
                f"got {collector_host!r}",
                file=sys.stderr,
            )
            return 2

    runtime = collect_runtime_identity(args.ssh_host)
    health = collect_live_health(args.ssh_host)
    write_json(out_dir / "LIVE_RUNTIME_IDENTITY.json", runtime)
    write_json(out_dir / "PRE_APPLY_HEALTH.json", health)
    identity_errors = validate_live_runtime_identity(runtime)
    if identity_errors or not health.get("all_pass"):
        write_json(
            out_dir / "REAL_APPLY_MANIFEST.json",
            {
                "status": "BLOCKED",
                "identity_errors": identity_errors,
                "health": health,
            },
        )
        print("ERROR: live identity or health gate failed", file=sys.stderr)
        return 1

    ids = [int(r["product_id"]) for r in prestate]
    live = fetch_live_targets(ids, args.ssh_host)
    recon_rows: list[dict[str, Any]] = []
    drift_errors: list[str] = []
    already_applied = 0
    for row in prestate:
        pid = row["product_id"]
        lv = live[pid]
        errs = reconcile_live_row(row, lv)
        if errs:
            drift_errors.extend([f"{pid}:{e}" for e in errs])
        if (lv.get("name") or "").strip() == row["proposed_name"]:
            already_applied += 1
        recon_rows.append(
            {
                "product_id": pid,
                "expected_old_name": row["expected_old_name"],
                "live_name": lv.get("name", ""),
                "proposed_name": row["proposed_name"],
                "sku_ok": (lv.get("sku") or "").strip() == row["sku"],
                "errors": ";".join(errs) if errs else "",
            }
        )
    write_csv(
        out_dir / "PHASE2F_PREFLIGHT_RECONCILIATION.csv",
        recon_rows,
        list(recon_rows[0].keys()) if recon_rows else ["product_id"],
    )

    target_pre_rows = [{**row, **live[row["product_id"]]} for row in prestate]
    if target_pre_rows:
        write_csv(out_dir / "PHASE2F_TARGET_PRE_APPLY.csv", target_pre_rows, list(target_pre_rows[0].keys()))

    catalog_names = fetch_catalog_names(args.ssh_host)
    collisions = collision_precheck_python(prestate, catalog_names)
    write_json(out_dir / "PHASE2F_COLLISION_PRECHECK.json", collisions)

    seo_issues = [
        r["product_id"]
        for r in prestate
        if (r.get("seo_title_impact") or "").strip().lower() in ("yes", "true", "1")
    ]
    if seo_issues:
        drift_errors.append(f"seo_title_impact:{','.join(seo_issues)}")

    collision_blocked = any(
        collisions.get(k, 0)
        for k in (
            "cohort_exact_dup",
            "cohort_normalized_dup",
            "catalog_exact_hits",
            "catalog_normalized_hits",
        )
    )
    second_block = second_apply_blocked_reason(prestate, live)
    preflight_ok = (
        not drift_errors
        and not collision_blocked
        and already_applied == 0
        and second_block == ""
    )

    recovery = write_recovery_package(out_dir, prestate, cohort_sha256=cohort_sha)

    backup: dict[str, Any] = {"created": False, "pg_restore_list_verification": "NOT_RUN"}
    if args.apply and preflight_ok:
        backup = create_live_backup(ssh_host=args.ssh_host, backup_dir=args.backup_dir)
    write_json(out_dir / "BACKUP_MANIFEST.json", backup)

    if args.preflight_only:
        status = "PREFLIGHT_PASS" if preflight_ok else "BLOCKED"
        if second_block:
            status = second_block
        write_json(
            out_dir / "REAL_APPLY_MANIFEST.json",
            {
                "status": status,
                "preflight_ok": preflight_ok,
                "already_applied_count": already_applied,
                "collision_precheck": collisions,
                "recovery_payload_sha256": recovery.get("manifest_payload_sha256"),
            },
        )
        if second_block == "ALREADY_APPLIED_BLOCKED":
            write_json(
                out_dir / "SECOND_APPLY_SAFETY.json",
                {
                    "preflight_attempted": True,
                    "already_applied_detected": True,
                    "new_writes": 0,
                    "new_logs": 0,
                    "status": second_block,
                },
            )
        print(json.dumps({"status": status, "preflight_ok": preflight_ok}, indent=2))
        return 0 if preflight_ok or second_block == "ALREADY_APPLIED_BLOCKED" else 1

    if not preflight_ok:
        write_json(out_dir / "REAL_APPLY_MANIFEST.json", {"status": "BLOCKED", "drift_errors": drift_errors})
        return 1

    if not backup.get("created"):
        print("ERROR: backup missing", file=sys.stderr)
        return 1

    catalog_norm_rows = [(pid, normalize_name_for_collision(name)) for pid, name in catalog_names]
    apply_logic_sha = _git_head()
    sql = build_real_apply_sql(prestate, catalog_norm_rows=catalog_norm_rows, cohort_sha256=cohort_sha)
    commit_ts = datetime.now(UTC).isoformat()
    commit_status = "APPLY_FAILED_ROLLED_BACK"
    metrics: dict[str, int] = {}
    log_rows: list[dict[str, Any]] = []
    txid: int | None = None
    try:
        stdout = _run_ssh_psql_script(sql, ssh_host=args.ssh_host, allow_commit=True)
        metrics, log_rows = parse_apply_stdout(stdout)
        txid = metrics.get("txid")
        commit_status = "COMMIT_ATTEMPTED"
    except Exception as exc:  # noqa: BLE001
        write_json(
            out_dir / "REAL_APPLY_TRANSACTION_RESULT.json",
            {"status": "APPLY_FAILED_ROLLED_BACK", "error": str(exc)},
        )
        write_json(out_dir / "REAL_APPLY_MANIFEST.json", {"status": "APPLY_FAILED_ROLLED_BACK"})
        print(f"ERROR: apply transaction failed: {exc}", file=sys.stderr)
        return 1

    post = authoritative_post_apply_state(prestate, reason, ssh_host=args.ssh_host)
    metric_errors = apply_success_metrics(metrics, REAL_APPLY_EXPECTED_ROWS)
    log_audit_summary, log_audit_csv = audit_apply_logs(prestate, log_rows, cohort_sha256=cohort_sha)
    write_csv(
        out_dir / "PHASE2F_IN_TRANSACTION_LOG_AUDIT.csv",
        log_audit_csv,
        list(log_audit_csv[0].keys()) if log_audit_csv else ["product_id"],
    )

    if (
        post["proposed_names"] != REAL_APPLY_EXPECTED_ROWS
        or post["old_names_remaining"] != 0
        or post["phase2f_logs"] != REAL_APPLY_EXPECTED_ROWS
        or metric_errors
        or log_audit_summary.get("actual_log_row_mismatches", 1) != 0
    ):
        final_status = "BLOCKED_CRITICAL" if post["proposed_names"] not in (0, REAL_APPLY_EXPECTED_ROWS) else "COMMIT_STATUS_UNKNOWN"
        if post["proposed_names"] == REAL_APPLY_EXPECTED_ROWS and metric_errors:
            final_status = "BLOCKED_CRITICAL"
        write_json(
            out_dir / "REAL_APPLY_TRANSACTION_RESULT.json",
            {
                "metrics": metrics,
                "txid": txid,
                "post_commit_probe": post,
                "metric_errors": metric_errors,
                "log_audit": log_audit_summary,
            },
        )
        write_json(out_dir / "REAL_APPLY_MANIFEST.json", {"status": final_status})
        return 1

    post_live = post["live"]
    post_rows = [{**row, **post_live[row["product_id"]]} for row in prestate]
    write_csv(
        out_dir / "PHASE2F_TARGET_POST_APPLY.csv",
        post_rows,
        list(post_rows[0].keys()) if post_rows else ["product_id"],
    )
    write_json(
        out_dir / "POST_APPLY_CHANGE_LOG_AUDIT.json",
        {"reason": reason, **log_audit_summary},
    )
    write_json(out_dir / "POST_APPLY_COLLISION_AUDIT.json", collisions)
    read_smoke = run_read_smoke(prestate, live, ssh_host=args.ssh_host)
    write_json(out_dir / "POST_APPLY_READ_SMOKE.json", read_smoke)

    write_json(
        out_dir / "REAL_APPLY_TRANSACTION_RESULT.json",
        {
            "committed": True,
            "commit_timestamp_utc": commit_ts,
            "txid": txid,
            "isolation": "SERIALIZABLE",
            "advisory_lock": REAL_APPLY_ADVISORY_LOCK_KEY,
            "metrics": metrics,
            "change_log_contract": {
                "contract_reference": CHANGE_LOG_CONTRACT_REFERENCE,
                "equivalent_fields": list(CHANGE_LOG_EQUIVALENT_FIELDS),
                "reason": reason,
            },
            "apply_logic_sha": apply_logic_sha,
        },
    )

    manifest = {
        "status": "APPLIED_VERIFIED",
        "owner_authorized": True,
        "owner_scope": "47 products.name + 47 product_change_logs",
        "latest_main_sha": apply_logic_sha,
        "apply_logic_sha": apply_logic_sha,
        "phase2d_candidate_sha256": cohort_sha,
        "phase2e_prestate_sha256": PHASE2E_PRESTATE_SHA256,
        "runtime_identity": runtime,
        "health": health,
        "backup": backup,
        "transaction": {"txid": txid, "metrics": metrics},
        "hesabfa_action": "NONE",
        "deploy": "NO",
    }
    write_json(out_dir / "REAL_APPLY_MANIFEST.json", manifest)

    second_preflight = second_apply_blocked_reason(prestate, post_live)
    write_json(
        out_dir / "SECOND_APPLY_SAFETY.json",
        {
            "preflight_attempted": True,
            "already_applied_detected": second_preflight == "ALREADY_APPLIED_BLOCKED",
            "new_writes": 0,
            "new_logs": 0,
            "status": second_preflight or "OK",
        },
    )
    summary = f"""# Phase 2F real apply summary

- Status: APPLIED_VERIFIED
- Rows: {REAL_APPLY_EXPECTED_ROWS}
- Cohort SHA256: `{cohort_sha}`
- Logic SHA: `{apply_logic_sha}`
- Backup: `{backup.get('path')}`
"""
    summary_path = out_dir / "PHASE2F_REAL_APPLY_SUMMARY.md"
    assert_evidence_writable(summary_path)
    summary_path.write_text(summary, encoding="utf-8")
    write_evidence_sha256sums(out_dir)
    print(json.dumps({"status": "APPLIED_VERIFIED", "txid": txid}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
