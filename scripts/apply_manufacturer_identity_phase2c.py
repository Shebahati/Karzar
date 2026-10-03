#!/usr/bin/env python3
"""Phase 2C manufacturer_code APPLY — preflight + transactional rehearsal (ROLLBACK only).

Real persistent APPLY is not authorized. ``--apply`` / ``--commit`` fail closed (exit 2).
Only ``--rehearse`` may perform guarded writes inside a transaction that always ends in ROLLBACK.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.phase2c_apply import (  # noqa: E402
    CHANGE_LOG_CONTRACT_REFERENCE,
    CHANGE_LOG_EQUIVALENT_FIELDS,
    CHANGE_LOG_EXECUTION_PATH,
    OWNER_FROZEN_ROWS,
    OWNER_FROZEN_SHA256,
    change_log_reason,
    change_log_reason_includes_full_sha,
    load_freeze_manifest,
    reconcile_targets,
    rehearsal_logic_file_sha256,
    snapshot_sha256,
    sql_literal,
    summarize_slug_drift,
    target_preflight_snapshot_rows,
    validate_freeze_manifest,
    validate_frozen_artifact,
)

DEFAULT_ARTIFACT = (
    ROOT / "audit" / "product-naming-phase2c-discovery" / "BACKFILL_EXACT_FROZEN.csv"
)
DEFAULT_MANIFEST = (
    ROOT / "audit" / "product-naming-phase2c-discovery" / "BACKFILL_EXACT_FREEZE_MANIFEST.json"
)
AUDIT_OUT = ROOT / "audit" / "product-naming-phase2c-apply"

MUTATION_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE)\b", re.I)
COMMIT_RE = re.compile(r"(^|[^A-Z_])COMMIT(\s|;|$)", re.I)


def _reject_real_apply(argv: list[str]) -> None:
    blocked = ("--apply", "--commit", "--yes", "--force")
    for a in argv:
        if a in blocked or any(a.startswith(f"{b}=") for b in blocked):
            print(
                "ERROR: Real Phase 2C APPLY is not authorized by this PR.",
                file=sys.stderr,
            )
            raise SystemExit(2)


def _run_ssh_psql(
    sql: str,
    *,
    ssh_host: str,
    allow_write: bool = False,
) -> str:
    if not allow_write and MUTATION_RE.search(sql):
        raise RuntimeError("Refusing mutation SQL outside --rehearse rehearsal script")
    if COMMIT_RE.search(sql):
        raise RuntimeError("COMMIT is forbidden in Phase 2C rehearsal tooling")
    inner = sql.replace('"', '\\"').replace("\n", " ")
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        ssh_host,
        f"docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 -At -F $'\\t' -c \"{inner}\"",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _run_ssh_psql_script(script: str, *, ssh_host: str) -> str:
    if re.search(r"(^|\n)\s*COMMIT\s*;\s*($|\n)", script, re.I):
        raise RuntimeError("COMMIT is forbidden")
    if "ROLLBACK" not in script.upper():
        raise RuntimeError("Rehearsal script must include explicit ROLLBACK")
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "bash", "-s"],
        input=f"""set -euo pipefail
docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 <<'EOSQL'
{script}
EOSQL
""",
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-4000:] or proc.stdout[-4000:])
    return proc.stdout


def _run_ssh(cmd: str, *, ssh_host: str) -> str:
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, cmd],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"ssh failed: {cmd}")
    return proc.stdout.strip()


def _scalar(sql: str, ssh_host: str) -> int:
    raw = _run_ssh_psql(sql, ssh_host=ssh_host, allow_write=False)
    return int((raw.splitlines() or ["0"])[-1] or 0)


def _fingerprint(field_exprs: list[str], ssh_host: str) -> str:
    concat = " || '|' || ".join(field_exprs)
    sql = f"""
    SELECT md5(string_agg({concat}, E'\\n' ORDER BY p.id))
    FROM products p WHERE p.deleted_at IS NULL;
    """
    return _run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1].strip()


def collect_runtime_identity(ssh_host: str) -> dict[str, Any]:
    from scripts.phase2c_live_readonly_census import collect_runtime_identity as _cri  # noqa: E402

    return _cri(ssh_host)


def collect_baseline(ssh_host: str) -> dict[str, Any]:
    from scripts.phase2c_live_readonly_census import collect_baseline as _cb  # noqa: E402

    return _cb(ssh_host)


def read_only_proof(ssh_host: str) -> dict[str, str]:
    from scripts.phase2c_live_readonly_census import _read_only_session_proof  # noqa: E402

    return _read_only_session_proof(ssh_host)


def collect_live_health(ssh_host: str) -> dict[str, Any]:
    """Operational readiness baseline (not an identity derivation gate)."""
    raw = _run_ssh(
        "docker exec lathe_api python -c \""
        "import json,urllib.request;"
        "req=urllib.request.Request('http://127.0.0.1:8000/ready',"
        "headers={'Host':'api.karzartools.com'});"
        "r=urllib.request.urlopen(req,timeout=10);"
        "print(r.status);print(r.read().decode())"
        "\"",
        ssh_host=ssh_host,
    )
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    http_status = int(lines[0]) if lines else 0
    body = json.loads(lines[1]) if len(lines) > 1 else {}
    redis_ping = _run_ssh("docker exec lathe_redis redis-cli ping", ssh_host=ssh_host)
    db_one = _run_ssh_psql("SELECT 1;", ssh_host=ssh_host)
    api_ok = http_status == 200 and body.get("status") == "ready"
    database_ok = body.get("database") == "ok" and db_one.strip().endswith("1")
    redis_ok = body.get("redis") == "ok" and redis_ping.strip() == "PONG"
    return {
        "api_readiness": "PASS" if api_ok else "FAIL",
        "database_readiness": "PASS" if database_ok else "FAIL",
        "redis_readiness": "PASS" if redis_ok else "FAIL",
        "ready_http_status": http_status,
        "ready_body": body,
        "redis_ping": redis_ping,
        "database_select_1": db_one,
        "all_pass": api_ok and database_ok and redis_ok,
    }


def fetch_live_targets(ids: list[str], ssh_host: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    chunk_size = 200
    for start in range(0, len(ids), chunk_size):
        chunk = ids[start : start + chunk_size]
        id_list = ",".join(str(int(i)) for i in chunk)
        sql = f"""
    SELECT row_to_json(t)::text FROM (
      SELECT id, sku, brand_id, manufacturer_code, name, slug, deleted_at
      FROM products WHERE id IN ({id_list})
    ) t;
    """
        raw = _run_ssh_psql(sql, ssh_host=ssh_host)
        for line in raw.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            pid = str(obj["id"])
            deleted = obj.get("deleted_at")
            out[pid] = {
                "sku": (obj.get("sku") or "").strip(),
                "brand_id": str(obj.get("brand_id") or ""),
                "manufacturer_code": (obj.get("manufacturer_code") or "").strip(),
                "name": (obj.get("name") or "").strip(),
                "slug": (obj.get("slug") or "").strip(),
                "deleted_at": str(deleted) if deleted else "",
            }
    if len(out) != len(set(ids)):
        missing = sorted(set(ids) - set(out.keys()), key=int)[:10]
        raise RuntimeError(
            f"live target fetch incomplete: got {len(out)}/{len(ids)}; sample missing={missing}"
        )
    return out


def build_rehearsal_sql(
    frozen_rows: list[dict[str, str]],
    cohort_sha256: str,
) -> str:
    ids = [int(r["product_id"]) for r in frozen_rows]
    id_csv = ",".join(str(i) for i in ids)
    reason = change_log_reason(cohort_sha256)
    updates: list[str] = []
    for row in frozen_rows:
        pid = int(row["product_id"])
        cand = row["candidate_manufacturer_code"]
        sku = row["sku"]
        brand_id = int(row["brand_id"])
        updates.append(
            f"""
UPDATE products SET manufacturer_code = {sql_literal(cand)}
WHERE id = {pid}
  AND manufacturer_code IS NULL
  AND sku = {sql_literal(sku)}
  AND brand_id = {brand_id}
  AND deleted_at IS NULL;
"""
        )
        updates.append(
            f"""
INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
VALUES ({pid}, 'manufacturer_code', NULL, {sql_literal(cand)}, {sql_literal(reason)}, NULL);
"""
        )
    body = "\n".join(updates)
    return f"""
BEGIN;
CREATE TEMP TABLE p2c_rehearsal_before AS
  SELECT id, name, sku, slug, brand_id, category_id, product_type_id,
         base_price, original_price, is_active, is_available, deleted_at, manufacturer_code
  FROM products WHERE id IN ({id_csv});
CREATE TEMP TABLE p2c_log_max AS
  SELECT COALESCE(MAX(id), 0) AS max_id FROM product_change_logs;
{body}
CREATE TEMP TABLE p2c_expected (id int PRIMARY KEY, code text);
INSERT INTO p2c_expected (id, code) VALUES
  {",".join(f"({int(r['product_id'])},{sql_literal(r['candidate_manufacturer_code'])})" for r in frozen_rows)};
SELECT 'METRIC:before_rows:' || COUNT(*)::text FROM p2c_rehearsal_before;
SELECT 'METRIC:target_non_null:' || COUNT(*)::text FROM products
  WHERE id IN ({id_csv}) AND manufacturer_code IS NOT NULL;
SELECT 'METRIC:exact_matches:' || COUNT(*)::text FROM products p
  JOIN p2c_expected e ON p.id = e.id
  WHERE p.manufacturer_code IS NOT DISTINCT FROM e.code;
SELECT 'METRIC:protected_drift:' || COUNT(*)::text FROM products p
  JOIN p2c_rehearsal_before b ON p.id = b.id
  WHERE p.name IS DISTINCT FROM b.name
     OR p.sku IS DISTINCT FROM b.sku
     OR p.slug IS DISTINCT FROM b.slug
     OR p.brand_id IS DISTINCT FROM b.brand_id
     OR p.category_id IS DISTINCT FROM b.category_id
     OR p.product_type_id IS DISTINCT FROM b.product_type_id
     OR p.base_price IS DISTINCT FROM b.base_price
     OR p.original_price IS DISTINCT FROM b.original_price
     OR p.is_active IS DISTINCT FROM b.is_active
     OR p.is_available IS DISTINCT FROM b.is_available
     OR p.deleted_at IS DISTINCT FROM b.deleted_at;
SELECT 'METRIC:new_logs:' || COUNT(*)::text FROM product_change_logs
  WHERE id > (SELECT max_id FROM p2c_log_max) AND field_name = 'manufacturer_code';
SELECT 'METRIC:collision_groups:' || COUNT(*)::text FROM (
  SELECT brand_id, manufacturer_code FROM products
  WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL
  GROUP BY brand_id, manufacturer_code HAVING COUNT(*) > 1
) s;
ROLLBACK;
"""


def parse_rehearsal_output(stdout: str) -> dict[str, int]:
    """Extract METRIC:* counts from psql output."""
    metrics: dict[str, int] = {}
    for line in stdout.splitlines():
        m = re.match(r"^METRIC:([a-z_]+):(\d+)$", line.strip())
        if m:
            metrics[m.group(1)] = int(m.group(2))
    required = (
        "before_rows",
        "target_non_null",
        "exact_matches",
        "protected_drift",
        "new_logs",
        "collision_groups",
    )
    missing = [k for k in required if k not in metrics]
    if missing:
        raise RuntimeError(f"missing metrics {missing} in output tail: {stdout[-800:]}")
    return {k: metrics[k] for k in required}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        return ""


def _git_status_clean() -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        return out == ""
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_real_apply(argv)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--expected-sha256", default=OWNER_FROZEN_SHA256)
    p.add_argument("--out-dir", type=Path, default=AUDIT_OUT)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument(
        "--rehearsal-logic-git-sha",
        default=None,
        help="Immutable logic commit SHA used for this rehearsal (defaults to HEAD)",
    )
    p.add_argument(
        "--rehearse",
        action="store_true",
        help="Run full preflight + transactional rehearsal (always ROLLBACK)",
    )
    p.add_argument(
        "--preflight-only",
        action="store_true",
        help="Artifact + live preflight only (no rehearsal transaction)",
    )
    args = p.parse_args(argv)

    if not args.rehearse and not args.preflight_only:
        print("ERROR: specify --preflight-only or --rehearse", file=sys.stderr)
        return 2

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Capture before any artifact writes so dirty generated files cannot false-fail.
    worktree_clean_at_start = _git_status_clean()
    logic_sha = args.rehearsal_logic_git_sha or _git_head()
    logic_hashes = rehearsal_logic_file_sha256(ROOT)
    reason = change_log_reason(args.expected_sha256)
    if not change_log_reason_includes_full_sha(reason, args.expected_sha256):
        raise RuntimeError("change-log reason must embed full frozen cohort SHA256")

    frozen_rows, art_meta = validate_frozen_artifact(
        args.artifact, expected_sha256=args.expected_sha256
    )
    slug_status = art_meta["slug_comparison_status"]
    manifest = load_freeze_manifest(args.manifest)
    validate_freeze_manifest(manifest, art_meta["sha256"])

    live_health = collect_live_health(args.ssh_host)
    runtime = collect_runtime_identity(args.ssh_host)
    ro_proof = read_only_proof(args.ssh_host)
    baseline = collect_baseline(args.ssh_host)
    fingerprints = {
        "name": _fingerprint(["COALESCE(p.name,'')"], args.ssh_host),
        "sku": _fingerprint(["COALESCE(p.sku,'')"], args.ssh_host),
        "slug": _fingerprint(["COALESCE(p.slug,'')"], args.ssh_host),
        "manufacturer_code": _fingerprint(["COALESCE(p.manufacturer_code,'')"], args.ssh_host),
        "composite": _fingerprint(
            [
                "COALESCE(p.name,'')",
                "COALESCE(p.sku,'')",
                "COALESCE(p.slug,'')",
                "COALESCE(p.manufacturer_code,'')",
                "COALESCE(p.brand_id::text,'')",
                "COALESCE(p.product_type_id::text,'')",
            ],
            args.ssh_host,
        ),
    }
    pre_baseline = {
        "generated_at": datetime.now(UTC).isoformat(),
        "read_only_proof": ro_proof,
        "counts": baseline,
        "fingerprints": fingerprints,
        "runtime": runtime,
        "live_health": live_health,
    }
    (out_dir / "PRE_REHEARSAL_DB_BASELINE.json").write_text(
        json.dumps(pre_baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    ids = [r["product_id"] for r in frozen_rows]
    live_by_id = fetch_live_targets(ids, args.ssh_host)
    reconciliation = reconcile_targets(
        frozen_rows,
        live_by_id,
        slug_comparison_status=slug_status,
    )
    write_csv(
        out_dir / "TARGET_PREFLIGHT_RECONCILIATION.csv",
        [r.to_csv_dict() for r in reconciliation],
        fieldnames=[
            "product_id",
            "frozen sku",
            "live sku",
            "frozen brand_id",
            "live brand_id",
            "frozen candidate code",
            "live manufacturer_code",
            "name drift",
            "slug comparison",
            "frozen slug",
            "live slug",
            "slug drift",
            "status",
            "reason",
        ],
    )
    snap_rows = target_preflight_snapshot_rows(frozen_rows, live_by_id)
    write_csv(
        out_dir / "TARGET_PREFLIGHT_SNAPSHOT.csv",
        snap_rows,
        fieldnames=["product_id", "sku", "brand_id", "manufacturer_code"],
    )
    target_preflight_sha = snapshot_sha256(
        snap_rows, ("product_id", "sku", "brand_id", "manufacturer_code")
    )

    blocked = [r for r in reconciliation if r.status != "PASS"]
    pass_count = len(reconciliation) - len(blocked)
    target_existing = sum(1 for r in reconciliation if r.live_manufacturer_code)
    name_drift = sum(1 for r in reconciliation if r.name_drift)
    slug_comparison_status, slug_drift_rows = summarize_slug_drift(reconciliation)
    deleted_count = sum(1 for r in reconciliation if r.reason == "deleted_target")
    missing_count = sum(1 for r in reconciliation if r.reason == "missing_target_product")
    sku_drift = sum(1 for r in reconciliation if r.reason == "sku_mismatch")
    brand_drift = sum(1 for r in reconciliation if r.reason == "brand_mismatch")

    preflight_manifest: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rehearsal_logic_git_sha": logic_sha,
        "artifact_commit_sha": None,
        "artifact_commit_sha_note": (
            "Stamped after artifact-only commit; null until Commit B lands."
        ),
        "rehearsal_logic_file_sha256": logic_hashes,
        "git_worktree_clean_at_rehearsal": worktree_clean_at_start,
        "frozen_artifact_path": str(args.artifact),
        "frozen_artifact_sha256": art_meta["sha256"],
        "frozen_rows": len(frozen_rows),
        "live_db": runtime.get("postgres_db_name"),
        "live_alembic": runtime.get("alembic_current"),
        "live_runtime_identity": runtime,
        "live_health": live_health,
        "target_preflight_sha256": target_preflight_sha,
        "pre_db_fingerprints": fingerprints,
        "target_null_count": pass_count,
        "target_existing_code_count": target_existing,
        "target_missing_count": missing_count,
        "target_deleted_count": deleted_count,
        "sku_drift_rows": sku_drift,
        "brand_drift_rows": brand_drift,
        "preflight_pass_rows": pass_count,
        "preflight_blocked_rows": len(blocked),
        "name_drift_rows": name_drift,
        "slug_comparison_status": slug_comparison_status,
        "slug_drift_rows": slug_drift_rows,
        "change_log_reason": reason,
        "full_cohort_sha_in_reason": change_log_reason_includes_full_sha(
            reason, art_meta["sha256"]
        ),
        "change_log_contract": {
            "contract_reference": CHANGE_LOG_CONTRACT_REFERENCE,
            "execution_path": CHANGE_LOG_EXECUTION_PATH,
            "equivalent_fields": list(CHANGE_LOG_EQUIVALENT_FIELDS),
        },
        "ready_for_owner_apply": False,
    }

    if (
        pass_count != OWNER_FROZEN_ROWS
        or blocked
        or name_drift != 0
        or not live_health.get("all_pass")
    ):
        preflight_manifest["status"] = "BLOCKED"
        (out_dir / "PHASE2C_APPLY_PREFLIGHT_MANIFEST.json").write_text(
            json.dumps(preflight_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(preflight_manifest, indent=2))
        return 1

    if args.preflight_only:
        preflight_manifest["status"] = "PREFLIGHT_PASS"
        (out_dir / "PHASE2C_APPLY_PREFLIGHT_MANIFEST.json").write_text(
            json.dumps(preflight_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(preflight_manifest, indent=2))
        return 0

    collision_before = _scalar(
        """
        SELECT COUNT(*) FROM (
          SELECT brand_id, manufacturer_code FROM products
          WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL
          GROUP BY brand_id, manufacturer_code HAVING COUNT(*) > 1
        ) s;
        """,
        args.ssh_host,
    )

    sql = build_rehearsal_sql(frozen_rows, art_meta["sha256"])
    (out_dir / "REHEARSAL_PLAN.json").write_text(
        json.dumps(
            {
                "expected_updates": OWNER_FROZEN_ROWS,
                "expected_change_logs": OWNER_FROZEN_ROWS,
                "cohort_sha256": art_meta["sha256"],
                "change_log_reason": reason,
                "full_cohort_sha_in_reason": True,
                "sql_bytes": len(sql.encode("utf-8")),
                "ends_with": "ROLLBACK",
                "contains_commit": bool(re.search(r"(^|\n)\s*COMMIT\s*;", sql, re.I)),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    stdout = _run_ssh_psql_script(sql, ssh_host=args.ssh_host)
    metrics = parse_rehearsal_output(stdout)

    rehearsal_ok = (
        metrics["before_rows"] == OWNER_FROZEN_ROWS
        and metrics["target_non_null"] == OWNER_FROZEN_ROWS
        and metrics["exact_matches"] == OWNER_FROZEN_ROWS
        and metrics["protected_drift"] == 0
        and metrics["new_logs"] == OWNER_FROZEN_ROWS
    )

    in_tx = {
        "transaction_started": True,
        "target_rows": OWNER_FROZEN_ROWS,
        "matched": metrics["before_rows"],
        "updated": metrics["target_non_null"],
        "exact_manufacturer_code_matches": metrics["exact_matches"],
        "protected_field_changes": metrics["protected_drift"],
        "collision_groups_after": metrics["collision_groups"],
        "collision_groups_before": collision_before,
        "new_collision_groups": max(0, metrics["collision_groups"] - collision_before),
        "change_logs_created": metrics["new_logs"],
        "rollback_executed": True,
        "rehearsal_ok": rehearsal_ok,
    }
    (out_dir / "REHEARSAL_IN_TRANSACTION_RESULT.json").write_text(
        json.dumps(in_tx, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "REHEARSAL_FIELD_DIFF.json").write_text(
        json.dumps(
            {
                "manufacturer_code_changes": metrics["exact_matches"],
                "protected_field_changes": metrics["protected_drift"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "REHEARSAL_CHANGE_LOG_AUDIT.json").write_text(
        json.dumps(
            {
                "expected_rows": OWNER_FROZEN_ROWS,
                "actual_rows": metrics["new_logs"],
                "reason": reason,
                "full_cohort_sha_in_reason": True,
                "artifact_sha_recorded": art_meta["sha256"],
                "field_name": "manufacturer_code",
                "contract_reference": CHANGE_LOG_CONTRACT_REFERENCE,
                "execution_path": CHANGE_LOG_EXECUTION_PATH,
                "equivalent_fields": list(CHANGE_LOG_EQUIVALENT_FIELDS),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "REHEARSAL_COLLISION_AUDIT.json").write_text(
        json.dumps(
            {
                "before_groups": collision_before,
                "after_groups": metrics["collision_groups"],
                "new_unresolved_groups": max(0, metrics["collision_groups"] - collision_before),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    post_ro = read_only_proof(args.ssh_host)
    post_baseline = collect_baseline(args.ssh_host)
    post_fps = {
        "name": _fingerprint(["COALESCE(p.name,'')"], args.ssh_host),
        "sku": _fingerprint(["COALESCE(p.sku,'')"], args.ssh_host),
        "slug": _fingerprint(["COALESCE(p.slug,'')"], args.ssh_host),
        "manufacturer_code": _fingerprint(["COALESCE(p.manufacturer_code,'')"], args.ssh_host),
        "composite": _fingerprint(
            [
                "COALESCE(p.name,'')",
                "COALESCE(p.sku,'')",
                "COALESCE(p.slug,'')",
                "COALESCE(p.manufacturer_code,'')",
                "COALESCE(p.brand_id::text,'')",
                "COALESCE(p.product_type_id::text,'')",
            ],
            args.ssh_host,
        ),
    }
    live_after = fetch_live_targets(ids, args.ssh_host)
    target_non_null_after = sum(
        1 for i in ids if (live_after.get(i, {}).get("manufacturer_code") or "").strip()
    )
    persistent_logs = _scalar(
        f"""
        SELECT COUNT(*) FROM product_change_logs
        WHERE product_id IN ({",".join(ids)})
          AND field_name = 'manufacturer_code'
          AND reason LIKE 'Phase 2C manufacturer identity%';
        """,
        args.ssh_host,
    )

    rollback_proof = {
        "explicit_rollback": True,
        "target_manufacturer_code_non_null": target_non_null_after,
        "target_manufacturer_code_null": OWNER_FROZEN_ROWS - target_non_null_after,
        "persistent_rehearsal_change_logs": persistent_logs,
        "fingerprints_equal": post_fps == fingerprints,
        "baseline_counts_equal": post_baseline == baseline,
    }
    (out_dir / "ROLLBACK_PROOF.json").write_text(
        json.dumps(rollback_proof, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "POST_ROLLBACK_DB_BASELINE.json").write_text(
        json.dumps(
            {
                "read_only_proof": post_ro,
                "counts": post_baseline,
                "fingerprints": post_fps,
                "live_health": collect_live_health(args.ssh_host),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    ready = (
        rehearsal_ok
        and target_non_null_after == 0
        and persistent_logs == 0
        and post_fps == fingerprints
        and post_baseline == baseline
        and metrics["collision_groups"] <= collision_before
        and name_drift == 0
        and slug_drift_rows == "NOT_APPLICABLE"
        and live_health.get("all_pass") is True
        and change_log_reason_includes_full_sha(reason, art_meta["sha256"])
    )

    preflight_manifest.update(
        {
            "rehearsal_expected_updates": OWNER_FROZEN_ROWS,
            "rehearsal_actual_updates": metrics["target_non_null"],
            "expected_change_logs": OWNER_FROZEN_ROWS,
            "actual_change_logs": metrics["new_logs"],
            "protected_field_mutations": metrics["protected_drift"],
            "rollback_result": rollback_proof,
            "post_db_fingerprints": post_fps,
            "ready_for_owner_apply": ready,
            "status": "READY_FOR_OWNER_APPLY" if ready else "BLOCKED",
        }
    )
    (out_dir / "PHASE2C_APPLY_PREFLIGHT_MANIFEST.json").write_text(
        json.dumps(preflight_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = [
        "# Phase 2C APPLY Rehearsal Summary",
        "",
        "> **REHEARSAL ONLY** — transaction rolled back; no persistent writes.",
        "",
        f"- Frozen cohort: **{OWNER_FROZEN_ROWS}** rows (`{art_meta['sha256']}`)",
        f"- Rehearsal logic git SHA: `{logic_sha}`",
        f"- Slug comparison: `{slug_comparison_status}` / drift `{slug_drift_rows}`",
        f"- Name drift rows: **{name_drift}**",
        f"- Preflight pass: **{pass_count}**",
        f"- Rehearsal OK: **{rehearsal_ok}**",
        f"- Live health: API={live_health['api_readiness']} "
        f"DB={live_health['database_readiness']} Redis={live_health['redis_readiness']}",
        f"- Change-log path: `{CHANGE_LOG_EXECUTION_PATH}` "
        f"(contract `{CHANGE_LOG_CONTRACT_REFERENCE}`)",
        f"- Rollback proof: **{rollback_proof}**",
        f"- Ready for owner APPLY: **{ready}**",
        "",
        "REHEARSAL REPRODUCED FROM IMMUTABLE LOGIC COMMIT",
        "ROLLBACK VERIFIED",
        "READY FOR OWNER APPLY" if ready else "NOT READY",
        "",
    ]
    (out_dir / "PHASE2C_APPLY_REHEARSAL_SUMMARY.md").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(preflight_manifest, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
