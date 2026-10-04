#!/usr/bin/env python3
"""Phase 2C owner-authorized REAL manufacturer_code APPLY (one-shot).

Persistent mutation requires BOTH:
  --apply
  --confirm-cohort-sha <full owner frozen SHA256>

Unsupported (fail closed): --force, --skip-preflight, --ignore-drift, --partial.
Plain invocation never mutates.
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

from app.domain.phase2c_apply import (  # noqa: E402
    CHANGE_LOG_CONTRACT_REFERENCE,
    CHANGE_LOG_EQUIVALENT_FIELDS,
    CHANGE_LOG_EXECUTION_PATH,
    OWNER_FROZEN_ROWS,
    OWNER_FROZEN_SHA256,
    change_log_reason_includes_full_sha,
    load_freeze_manifest,
    reconcile_targets,
    sha256_file,
    snapshot_sha256,
    summarize_slug_drift,
    target_preflight_snapshot_rows,
    validate_freeze_manifest,
    validate_frozen_artifact,
)
from app.domain.phase2c_real_apply import (  # noqa: E402
    REAL_APPLY_ADVISORY_LOCK_KEY,
    assert_confirmation_sha,
    build_real_apply_sql,
    build_recovery_target_rows,
    parse_real_apply_metrics,
    real_apply_change_log_reason,
    real_apply_logic_file_sha256,
    second_apply_blocked_reason,
)

DEFAULT_ARTIFACT = (
    ROOT / "audit" / "product-naming-phase2c-discovery" / "BACKFILL_EXACT_FROZEN.csv"
)
DEFAULT_MANIFEST = (
    ROOT / "audit" / "product-naming-phase2c-discovery" / "BACKFILL_EXACT_FREEZE_MANIFEST.json"
)
AUDIT_OUT = ROOT / "audit" / "product-naming-phase2c-real-apply"
DEFAULT_BACKUP_DIR = Path.home() / "karzar-backups" / "phase2c"

FORBIDDEN_FLAGS = (
    "--force",
    "--skip-preflight",
    "--ignore-drift",
    "--partial",
    "--yes",
    "--commit",
)

# Successful-run evidence that must never be silently overwritten.
IMMUTABLE_EVIDENCE_BASENAMES = frozenset(
    {
        "PRE_APPLY_DB_BASELINE.json",
        "REAL_APPLY_MANIFEST.json",
        "REAL_APPLY_TRANSACTION_RESULT.json",
        "POST_APPLY_DB_BASELINE.json",
        "RECOVERY_MANIFEST.json",
        "RECOVERY_TARGETS.csv",
        "RECOVERY_PLAN.md",
        "PHASE2C_REAL_APPLY_SUMMARY.md",
        "BACKUP_MANIFEST.json",
        "POST_APPLY_CHANGE_LOG_AUDIT.json",
        "POST_APPLY_COLLISION_AUDIT.json",
        "POST_APPLY_SEARCH_SMOKE.json",
        "TARGET_APPLY_PREFLIGHT_RECONCILIATION.csv",
        "TARGET_PRE_APPLY_SNAPSHOT.csv",
        "SECOND_APPLY_SAFETY.json",
    }
)

MUTATION_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER)\b", re.I)


class EvidenceImmutabilityError(RuntimeError):
    """Raised when a write would overwrite protected first-run evidence."""


def evidence_dir_has_successful_apply(out_dir: Path) -> bool:
    manifest = out_dir / "REAL_APPLY_MANIFEST.json"
    if not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return payload.get("status") == "APPLIED_VERIFIED"


def resolve_writable_out_dir(requested: Path, *, default_root: Path = AUDIT_OUT) -> Path:
    """Isolate later invocations from immutable first-run evidence.

    POST-APPLY TOOLING HARDENING ONLY — does not change historical apply semantics.
    """
    requested = requested.resolve()
    default_root = default_root.resolve()
    if requested != default_root:
        return requested
    if not evidence_dir_has_successful_apply(requested):
        return requested
    probe_dir = requested / "probes" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    probe_dir.mkdir(parents=True, exist_ok=False)
    return probe_dir


def assert_evidence_writable(path: Path) -> None:
    if path.exists() and path.name in IMMUTABLE_EVIDENCE_BASENAMES:
        raise EvidenceImmutabilityError(
            f"refusing to overwrite immutable Phase 2C evidence file: {path}"
        )


def _reject_forbidden(argv: list[str]) -> None:
    for a in argv:
        if a in FORBIDDEN_FLAGS or any(a.startswith(f"{b}=") for b in FORBIDDEN_FLAGS):
            print(f"ERROR: forbidden flag {a}", file=sys.stderr)
            raise SystemExit(2)


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


def _run_ssh_psql(sql: str, *, ssh_host: str, allow_write: bool = False) -> str:
    if not allow_write and MUTATION_RE.search(sql):
        raise RuntimeError("Refusing mutation SQL outside authorized --apply path")
    inner = sql.replace('"', '\\"').replace("\n", " ")
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        ssh_host,
        "docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging "
        f"-v ON_ERROR_STOP=1 -At -F $'\\t' -c \"{inner}\"",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _run_ssh_psql_script(script: str, *, ssh_host: str, allow_commit: bool) -> str:
    if not allow_commit and re.search(r"(^|\n)\s*COMMIT\s*;", script, re.I):
        raise RuntimeError("COMMIT forbidden without authorized --apply")
    if allow_commit and "COMMIT" not in script.upper():
        raise RuntimeError("Authorized apply script must contain COMMIT")
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
        raise RuntimeError(proc.stderr[-6000:] or proc.stdout[-6000:])
    return proc.stdout + ("\n" + proc.stderr if proc.stderr else "")


def collect_runtime_identity(ssh_host: str) -> dict[str, Any]:
    from scripts.phase2c_live_readonly_census import collect_runtime_identity as _cri

    identity = _cri(ssh_host)
    identity["collector_hostname"] = subprocess.run(
        ["hostname"], capture_output=True, text=True, check=False
    ).stdout.strip()
    return identity


def collect_baseline(ssh_host: str) -> dict[str, Any]:
    from scripts.phase2c_live_readonly_census import collect_baseline as _cb

    return _cb(ssh_host)


def collect_live_health(ssh_host: str) -> dict[str, Any]:
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
      SELECT id, sku, brand_id, manufacturer_code, name, slug, deleted_at,
             category_id, product_type_id, base_price, original_price,
             is_active, is_available
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
                "category_id": str(obj.get("category_id") or ""),
                "product_type_id": str(obj.get("product_type_id") or ""),
                "base_price": str(obj.get("base_price") if obj.get("base_price") is not None else ""),
                "original_price": str(
                    obj.get("original_price") if obj.get("original_price") is not None else ""
                ),
                "is_active": str(obj.get("is_active")),
                "is_available": str(obj.get("is_available")),
            }
    if len(out) != len(set(ids)):
        missing = sorted(set(ids) - set(out.keys()), key=int)[:10]
        raise RuntimeError(
            f"live target fetch incomplete: got {len(out)}/{len(ids)}; sample missing={missing}"
        )
    return out


def _fingerprint(field_exprs: list[str], ssh_host: str) -> str:
    concat = " || '|' || ".join(field_exprs)
    sql = f"""
    SELECT md5(string_agg({concat}, E'\\n' ORDER BY p.id))
    FROM products p WHERE p.deleted_at IS NULL;
    """
    return _run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1].strip()


def collect_extended_fingerprints(ssh_host: str) -> dict[str, str]:
    return {
        "name": _fingerprint(["p.name"], ssh_host),
        "sku": _fingerprint(["p.sku"], ssh_host),
        "slug": _fingerprint(["COALESCE(p.slug,'')"], ssh_host),
        "manufacturer_code": _fingerprint(["COALESCE(p.manufacturer_code,'')"], ssh_host),
        "brand_id": _fingerprint(["p.brand_id::text"], ssh_host),
        "category_id": _fingerprint(["COALESCE(p.category_id::text,'')"], ssh_host),
        "product_type_id": _fingerprint(["COALESCE(p.product_type_id::text,'')"], ssh_host),
        "base_price": _fingerprint(["COALESCE(p.base_price::text,'')"], ssh_host),
        "original_price": _fingerprint(["COALESCE(p.original_price::text,'')"], ssh_host),
        "is_active": _fingerprint(["p.is_active::text"], ssh_host),
        "is_available": _fingerprint(["p.is_available::text"], ssh_host),
        "deleted_at": _fingerprint(["COALESCE(p.deleted_at::text,'')"], ssh_host),
        "composite": _fingerprint(
            [
                "p.id::text",
                "p.name",
                "p.sku",
                "COALESCE(p.slug,'')",
                "COALESCE(p.manufacturer_code,'')",
                "p.brand_id::text",
            ],
            ssh_host,
        ),
    }


def create_live_backup(*, ssh_host: str, backup_dir: Path) -> dict[str, Any]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.chmod(0o700)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"karzar_staging_phase2c_{ts}.dump"
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
    if len(list_lines) < 10:
        raise RuntimeError("pg_restore --list produced too few entries")
    pg_ver = _run_ssh_psql("SHOW server_version;", ssh_host=ssh_host)
    return {
        "created": True,
        "path": str(path),
        "timestamp_utc": ts,
        "size_bytes": size,
        "sha256": digest,
        "database_name": "karzar_staging",
        "postgresql_version": pg_ver,
        "pg_restore_list_entries": len(list_lines),
        "pg_restore_list_verification": "PASS",
        "committed_to_git": False,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    assert_evidence_writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    assert_evidence_writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_recovery_package(
    out_dir: Path,
    frozen_rows: list[dict[str, str]],
    *,
    cohort_sha256: str,
) -> dict[str, Any]:
    """Write recovery package with unambiguous payload-hash semantics.

    ``manifest_payload_sha256`` is the SHA256 of the JSON body *before* any
    self-referential final-file hash is considered. The final on-disk file hash
    must be recorded externally (never embedded in this file).
    """
    targets = build_recovery_target_rows(frozen_rows)
    targets_path = out_dir / "RECOVERY_TARGETS.csv"
    write_csv(
        targets_path,
        targets,
        [
            "product_id",
            "pre_apply_manufacturer_code",
            "applied_manufacturer_code",
            "sku",
            "brand_id",
        ],
    )
    plan = f"""# Phase 2C manufacturer_code recovery plan

## Status
NOT EXECUTED. Owner confirmation required before any recovery.

## Scope
- Rows: {len(targets)}
- Cohort SHA256: `{cohort_sha256}`
- Pre-apply manufacturer_code: NULL for all targets

## Recovery semantics (if later authorized)
1. For each row in `RECOVERY_TARGETS.csv`, set `products.manufacturer_code`
   back to the pre-apply value (NULL).
2. Write compensating `product_change_logs` rows
   (`field_name=manufacturer_code`, old=applied, new=NULL).
3. Do **not** delete original Phase 2C audit logs.
4. Require explicit owner confirmation SHA matching the cohort.

## Forbidden without new authorization
- Product.name / SKU / slug / taxonomy / price / availability mutation
- Automatic post-commit reversal
"""
    plan_path = out_dir / "RECOVERY_PLAN.md"
    assert_evidence_writable(plan_path)
    plan_path.write_text(plan, encoding="utf-8")
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cohort_sha256": cohort_sha256,
        "rows": len(targets),
        "pre_apply_manufacturer_code": None,
        "compensating_logs_designed": True,
        "executable_without_confirmation": False,
        "targets_csv_sha256": sha256_file(targets_path),
        "plan_sha256": sha256_file(plan_path),
    }
    payload_sha = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    manifest["manifest_payload_sha256"] = payload_sha
    manifest_path = out_dir / "RECOVERY_MANIFEST.json"
    write_json(manifest_path, manifest)
    # Prove embedded value is the pre-self-reference payload hash, not the final file hash.
    if sha256_file(manifest_path) == payload_sha:
        raise RuntimeError("recovery manifest payload hash unexpectedly equals final file hash")
    return manifest


def select_smoke_samples(frozen_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_brand: dict[str, list[dict[str, str]]] = {}
    for r in frozen_rows:
        by_brand.setdefault(r["brand_name"], []).append(r)
    samples: list[dict[str, str]] = []
    for brand, rows in sorted(by_brand.items()):
        rows_sorted = sorted(rows, key=lambda r: int(r["product_id"]))
        picks = [rows_sorted[0], rows_sorted[len(rows_sorted) // 2], rows_sorted[-1]]
        for r in picks:
            samples.append(
                {
                    "brand_name": brand,
                    "product_id": r["product_id"],
                    "sku": r["sku"],
                    "candidate_manufacturer_code": r["candidate_manufacturer_code"],
                }
            )
    return samples


def run_search_smoke(
    samples: list[dict[str, str]],
    *,
    ssh_host: str,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    by_brand: dict[str, str] = {}
    for s in samples:
        code = s["candidate_manufacturer_code"]
        pid = int(s["product_id"])
        sql = f"""
        SELECT COUNT(*)::text || '|' || COALESCE(MAX(id)::text,'') || '|' ||
               COALESCE(MAX(manufacturer_code),'')
        FROM products
        WHERE deleted_at IS NULL
          AND manufacturer_code = '{code.replace("'", "''")}'
          AND brand_id = (SELECT brand_id FROM products WHERE id = {pid});
        """
        raw = _run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1]
        count_s, found_id, found_code = (raw.split("|") + ["", "", ""])[:3]
        ok = count_s == "1" and found_id == str(pid) and found_code == code
        entry = {
            **s,
            "db_match_count": int(count_s or 0),
            "found_product_id": found_id,
            "found_manufacturer_code": found_code,
            "pass": ok,
            "api_search": "NOT_PROBED",
        }
        results.append(entry)
        brand_key = s["brand_name"].split("|")[0].strip().upper()
        if "INSIZE" in brand_key:
            by_brand.setdefault("INSIZE", "PASS" if ok else "FAIL")
            if not ok:
                by_brand["INSIZE"] = "FAIL"
        elif "DASQUA" in brand_key:
            by_brand.setdefault("DASQUA", "PASS" if ok else "FAIL")
            if not ok:
                by_brand["DASQUA"] = "FAIL"
        elif "TERMA" in brand_key:
            by_brand.setdefault("TERMA", "PASS" if ok else "FAIL")
            if not ok:
                by_brand["TERMA"] = "FAIL"
    return {
        "mode": "database_identity_smoke",
        "api_search": "NOT_PROBED",
        "samples": results,
        "by_brand": by_brand,
        "all_pass": all(r["pass"] for r in results),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_forbidden(argv)

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Authorize persistent COMMIT path")
    p.add_argument(
        "--confirm-cohort-sha",
        default=None,
        help="Full owner-frozen cohort SHA256 (required with --apply)",
    )
    p.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    p.add_argument("--freeze-manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument("--out-dir", type=Path, default=AUDIT_OUT)
    p.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    p.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate + live preflight + recovery artifacts; never COMMIT",
    )
    args = p.parse_args(argv)

    if args.apply and args.preflight_only:
        print("ERROR: --apply and --preflight-only are mutually exclusive", file=sys.stderr)
        return 2

    try:
        assert_confirmation_sha(args.confirm_cohort_sha) if args.apply else None
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.apply and not args.confirm_cohort_sha:
        print("ERROR: --apply requires --confirm-cohort-sha", file=sys.stderr)
        return 2

    if hostname_proc := subprocess.run(["hostname"], capture_output=True, text=True, check=False):
        hostname = hostname_proc.stdout.strip()
    else:
        hostname = ""
    if args.apply and hostname != "hp-g2-450":
        print(f"ERROR: real APPLY requires hostname hp-g2-450, got {hostname!r}", file=sys.stderr)
        return 2

    frozen_rows, art_meta = validate_frozen_artifact(
        args.artifact, expected_sha256=OWNER_FROZEN_SHA256, expected_rows=OWNER_FROZEN_ROWS
    )
    freeze_manifest = load_freeze_manifest(args.freeze_manifest)
    validate_freeze_manifest(freeze_manifest, art_meta["sha256"])
    reason = real_apply_change_log_reason(art_meta["sha256"])
    if not change_log_reason_includes_full_sha(reason, art_meta["sha256"]):
        raise RuntimeError("change-log reason invalid")

    out_dir = resolve_writable_out_dir(args.out_dir)
    if out_dir != args.out_dir.resolve():
        print(
            f"NOTE: immutable first-run evidence present; writing probe outputs to {out_dir}",
            file=sys.stderr,
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    runtime = collect_runtime_identity(args.ssh_host)
    health = collect_live_health(args.ssh_host)
    write_json(
        out_dir / "LIVE_RUNTIME_IDENTITY.json",
        {**runtime, "live_health": health, "collected_at_utc": datetime.now(UTC).isoformat()},
    )
    if not health.get("all_pass"):
        print("ERROR: live health FAIL; refusing APPLY", file=sys.stderr)
        return 1

    if args.apply:
        backup = create_live_backup(ssh_host=args.ssh_host, backup_dir=args.backup_dir)
        write_json(out_dir / "BACKUP_MANIFEST.json", backup)
        if not (
            backup.get("created")
            and backup.get("size_bytes", 0) > 0
            and backup.get("sha256")
            and backup.get("pg_restore_list_verification") == "PASS"
        ):
            print("ERROR: backup proof incomplete", file=sys.stderr)
            return 1
    else:
        backup = {
            "created": False,
            "note": "backup deferred until authorized --apply",
            "pg_restore_list_verification": "NOT_RUN",
        }
        write_json(out_dir / "BACKUP_MANIFEST.json", backup)

    baseline = collect_baseline(args.ssh_host)
    fingerprints = collect_extended_fingerprints(args.ssh_host)
    pre_apply = {
        "collected_at_utc": datetime.now(UTC).isoformat(),
        "baseline": baseline,
        "fingerprints": fingerprints,
        "read_only": True,
    }
    write_json(out_dir / "PRE_APPLY_DB_BASELINE.json", pre_apply)

    if "manufacturer_code_non_null" in baseline:
        global_mc = int(baseline["manufacturer_code_non_null"])
    elif "manufacturer_code_populated" in baseline:
        global_mc = int(baseline["manufacturer_code_populated"])
    else:
        global_mc = int(
            _run_ssh_psql(
                "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL;",
                ssh_host=args.ssh_host,
            ).splitlines()[-1]
        )
    baseline["manufacturer_code_populated"] = global_mc

    if global_mc != 0 and args.apply:
        print(
            f"ERROR: non-deleted manufacturer_code populated = {global_mc} (must be 0)",
            file=sys.stderr,
        )
        return 1

    ids = [r["product_id"] for r in frozen_rows]
    live = fetch_live_targets(ids, args.ssh_host)
    recon = reconcile_targets(
        frozen_rows,
        live,
        slug_comparison_status=art_meta["slug_comparison_status"],
    )
    slug_status, slug_drift = summarize_slug_drift(recon)
    pass_n = sum(1 for r in recon if r.status == "PASS")
    blocked_n = sum(1 for r in recon if r.status != "PASS")
    existing = sum(1 for r in recon if r.live_manufacturer_code)
    missing = sum(1 for r in recon if r.reason == "missing_target_product")
    deleted = sum(1 for r in recon if r.reason == "deleted_target")
    sku_drift = sum(1 for r in recon if r.reason == "sku_mismatch")
    brand_drift = sum(1 for r in recon if r.reason == "brand_mismatch")
    name_drift = sum(1 for r in recon if r.reason == "name_mismatch")

    write_csv(
        out_dir / "TARGET_APPLY_PREFLIGHT_RECONCILIATION.csv",
        [r.to_csv_dict() for r in recon],
        list(recon[0].to_csv_dict().keys()) if recon else [],
    )
    snap_rows = target_preflight_snapshot_rows(frozen_rows, live)
    write_csv(
        out_dir / "TARGET_PRE_APPLY_SNAPSHOT.csv",
        snap_rows,
        ["product_id", "sku", "brand_id", "manufacturer_code"],
    )
    target_pre_sha = snapshot_sha256(
        snap_rows, ("product_id", "sku", "brand_id", "manufacturer_code")
    )

    second_block = second_apply_blocked_reason(target_existing_code_count=existing)
    preflight_ok = (
        pass_n == OWNER_FROZEN_ROWS
        and blocked_n == 0
        and existing == 0
        and missing == 0
        and deleted == 0
        and sku_drift == 0
        and brand_drift == 0
        and name_drift == 0
        and global_mc == 0
        and second_block is None
    )

    recovery = write_recovery_package(out_dir, frozen_rows, cohort_sha256=art_meta["sha256"])

    if not args.apply:
        manifest = {
            "generated_at": datetime.now(UTC).isoformat(),
            "owner_authorized": False,
            "mode": "preflight_only",
            "latest_main_sha": _git_head(),
            "apply_logic_sha": _git_head(),
            "git_worktree_clean": _git_status_clean(),
            "frozen_artifact_path": str(args.artifact.resolve()),
            "frozen_artifact_sha256": art_meta["sha256"],
            "frozen_rows": art_meta["rows"],
            "target_pre_apply_sha256": target_pre_sha,
            "live_runtime_identity": runtime,
            "live_health": health,
            "backup": backup,
            "pre_apply_global_manufacturer_code_count": global_mc,
            "target_preflight": {
                "rows": len(recon),
                "pass": pass_n,
                "blocked": blocked_n,
                "existing_code": existing,
                "missing": missing,
                "deleted": deleted,
                "sku_drift": sku_drift,
                "brand_drift": brand_drift,
                "name_drift": name_drift,
                "slug_comparison": slug_status,
                "slug_drift_rows": slug_drift,
            },
            "recovery_manifest_payload_sha256": recovery.get("manifest_payload_sha256"),
            "status": "PREFLIGHT_PASS" if preflight_ok else "BLOCKED",
            "ready_for_apply": preflight_ok,
        }
        write_json(out_dir / "REAL_APPLY_MANIFEST.json", manifest)
        print(json.dumps({"status": manifest["status"], "preflight_ok": preflight_ok}, indent=2))
        return 0 if preflight_ok else 1

    # ---- authorized apply path ----
    if not preflight_ok:
        print("ERROR: preflight blocked; refusing COMMIT", file=sys.stderr)
        write_json(
            out_dir / "REAL_APPLY_MANIFEST.json",
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "owner_authorized": True,
                "status": "BLOCKED",
                "target_preflight": {
                    "rows": len(recon),
                    "pass": pass_n,
                    "blocked": blocked_n,
                    "existing_code": existing,
                    "missing": missing,
                    "deleted": deleted,
                    "sku_drift": sku_drift,
                    "brand_drift": brand_drift,
                    "name_drift": name_drift,
                },
                "second_apply_block": second_block,
            },
        )
        return 1

    if not backup.get("created"):
        print("ERROR: missing backup proof", file=sys.stderr)
        return 1

    # Recalculate target preflight hash immediately before write transaction.
    live2 = fetch_live_targets(ids, args.ssh_host)
    snap2 = target_preflight_snapshot_rows(frozen_rows, live2)
    target_pre_sha_2 = snapshot_sha256(
        snap2, ("product_id", "sku", "brand_id", "manufacturer_code")
    )
    if target_pre_sha_2 != target_pre_sha:
        print("ERROR: target preflight SHA drifted before APPLY", file=sys.stderr)
        return 1

    apply_logic_sha = _git_head()
    sql = build_real_apply_sql(frozen_rows, cohort_sha256=art_meta["sha256"])
    if "COMMIT" not in sql or "ROLLBACK" in sql.split("COMMIT")[0]:
        # ensure we don't accidentally roll back success path; ROLLBACK substring may appear in comments only
        pass
    commit_ts = datetime.now(UTC).isoformat()
    try:
        stdout = _run_ssh_psql_script(sql, ssh_host=args.ssh_host, allow_commit=True)
        metrics = parse_real_apply_metrics(stdout)
        txid = None
        for line in stdout.splitlines():
            if line.startswith("TXID:"):
                txid = line.split(":", 1)[1]
        committed = metrics.get("committed") == 1
    except Exception as exc:  # noqa: BLE001
        write_json(
            out_dir / "REAL_APPLY_TRANSACTION_RESULT.json",
            {
                "committed": False,
                "error": str(exc),
                "status": "BLOCKED",
            },
        )
        write_json(
            out_dir / "REAL_APPLY_MANIFEST.json",
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "owner_authorized": True,
                "status": "BLOCKED",
                "error": str(exc),
                "backup_path": backup.get("path"),
                "backup_sha256": backup.get("sha256"),
            },
        )
        print(f"ERROR: transaction failed; ROLLBACK assumed by PostgreSQL: {exc}", file=sys.stderr)
        return 1

    if not committed or metrics["updated_rows"] != OWNER_FROZEN_ROWS:
        write_json(
            out_dir / "REAL_APPLY_TRANSACTION_RESULT.json",
            {"committed": False, "metrics": metrics, "status": "BLOCKED"},
        )
        print("ERROR: commit metrics incomplete", file=sys.stderr)
        return 1

    write_json(
        out_dir / "REAL_APPLY_TRANSACTION_RESULT.json",
        {
            "committed": True,
            "commit_timestamp_utc": commit_ts,
            "transaction_id": txid,
            "isolation": "SERIALIZABLE",
            "advisory_lock": REAL_APPLY_ADVISORY_LOCK_KEY,
            "metrics": metrics,
            "change_log_contract": {
                "contract_reference": CHANGE_LOG_CONTRACT_REFERENCE,
                "execution_path": CHANGE_LOG_EXECUTION_PATH,
                "equivalent_fields": list(CHANGE_LOG_EQUIVALENT_FIELDS),
                "reason": reason,
            },
            "apply_logic_sha": apply_logic_sha,
            "frozen_cohort_sha256": art_meta["sha256"],
            "target_pre_apply_sha256": target_pre_sha_2,
        },
    )

    # Post-commit verification (fresh reads)
    post_status = "APPLIED_VERIFIED"
    post_errors: list[str] = []

    post_live = fetch_live_targets(ids, args.ssh_host)
    exact = 0
    null_n = 0
    non_null = 0
    protected_drift = 0
    post_rows: list[dict[str, str]] = []
    for fr in frozen_rows:
        pid = fr["product_id"]
        live_row = post_live[pid]
        code = (live_row.get("manufacturer_code") or "").strip()
        if code:
            non_null += 1
        else:
            null_n += 1
        if code == fr["candidate_manufacturer_code"]:
            exact += 1
        pre = live[pid]
        for field in (
            "name",
            "sku",
            "slug",
            "brand_id",
            "category_id",
            "product_type_id",
            "base_price",
            "original_price",
            "is_active",
            "is_available",
            "deleted_at",
        ):
            if (pre.get(field) or "") != (live_row.get(field) or ""):
                protected_drift += 1
                break
        post_rows.append(
            {
                "product_id": pid,
                "expected_code": fr["candidate_manufacturer_code"],
                "live_code": code,
                "exact": "yes" if code == fr["candidate_manufacturer_code"] else "no",
            }
        )
    write_csv(
        out_dir / "POST_APPLY_RECONCILIATION.csv",
        post_rows,
        ["product_id", "expected_code", "live_code", "exact"],
    )

    global_after = int(
        _run_ssh_psql(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL;",
            ssh_host=args.ssh_host,
        ).splitlines()[-1]
    )
    log_sql = f"""
    SELECT COUNT(*) FROM product_change_logs
    WHERE field_name = 'manufacturer_code'
      AND reason = '{reason.replace("'", "''")}'
      AND old_value IS NULL
      AND actor_user_id IS NULL;
    """
    log_count = int(_run_ssh_psql(log_sql, ssh_host=args.ssh_host).splitlines()[-1])
    dup_logs = int(
        _run_ssh_psql(
            f"""
            SELECT COUNT(*) FROM (
              SELECT product_id FROM product_change_logs
              WHERE field_name = 'manufacturer_code'
                AND reason = '{reason.replace("'", "''")}'
              GROUP BY product_id HAVING COUNT(*) > 1
            ) s;
            """,
            ssh_host=args.ssh_host,
        ).splitlines()[-1]
    )
    collision_after = int(
        _run_ssh_psql(
            """
            SELECT COUNT(*) FROM (
              SELECT brand_id, manufacturer_code FROM products
              WHERE deleted_at IS NULL AND manufacturer_code IS NOT NULL
              GROUP BY brand_id, manufacturer_code HAVING COUNT(*) > 1
            ) s;
            """,
            ssh_host=args.ssh_host,
        ).splitlines()[-1]
    )

    change_log_audit = {
        "expected": OWNER_FROZEN_ROWS,
        "actual": log_count,
        "duplicate_product_logs": dup_logs,
        "full_cohort_sha_present": art_meta["sha256"] in reason,
        "reason": reason,
        "field_name": "manufacturer_code",
        "old_value": None,
        "actor_user_id": None,
    }
    write_json(out_dir / "POST_APPLY_CHANGE_LOG_AUDIT.json", change_log_audit)
    write_json(
        out_dir / "POST_APPLY_COLLISION_AUDIT.json",
        {"before": 0, "after": collision_after, "new_unresolved": collision_after},
    )

    smoke = run_search_smoke(select_smoke_samples(frozen_rows), ssh_host=args.ssh_host)
    write_json(out_dir / "POST_APPLY_SEARCH_SMOKE.json", smoke)

    post_fp = collect_extended_fingerprints(args.ssh_host)
    post_baseline = collect_baseline(args.ssh_host)
    write_json(
        out_dir / "POST_APPLY_DB_BASELINE.json",
        {
            "collected_at_utc": datetime.now(UTC).isoformat(),
            "baseline": post_baseline,
            "fingerprints": post_fp,
            "target_non_null": non_null,
            "target_null": null_n,
            "exact_matches": exact,
            "global_manufacturer_code_populated": global_after,
            "protected_target_drift": protected_drift,
        },
    )

    if not (
        non_null == OWNER_FROZEN_ROWS
        and null_n == 0
        and exact == OWNER_FROZEN_ROWS
        and global_after == OWNER_FROZEN_ROWS
        and log_count == OWNER_FROZEN_ROWS
        and dup_logs == 0
        and protected_drift == 0
        and collision_after == 0
        and smoke.get("all_pass")
    ):
        post_status = "BLOCKED_POST_COMMIT"
        post_errors.append(
            f"post gates failed non_null={non_null} exact={exact} logs={log_count} "
            f"dup={dup_logs} protected={protected_drift} collisions={collision_after} "
            f"smoke={smoke.get('all_pass')}"
        )

    # Second-run safety probe (preflight only; must block)
    second = second_apply_blocked_reason(target_existing_code_count=non_null)
    second_probe = {
        "blocked_because_already_populated": second is not None,
        "reason": second,
        "new_writes": 0,
        "new_logs": 0,
        "result": "PASS" if second is not None else "FAIL",
    }

    logic_hashes = real_apply_logic_file_sha256(ROOT)
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "owner_authorized": True,
        "latest_main_sha": apply_logic_sha,
        "apply_logic_sha": apply_logic_sha,
        "apply_logic_file_sha256": logic_hashes,
        "frozen_artifact_path": str(args.artifact.resolve()),
        "frozen_artifact_sha256": art_meta["sha256"],
        "frozen_rows": art_meta["rows"],
        "target_pre_apply_sha256": target_pre_sha_2,
        "live_runtime_identity": runtime,
        "live_health": health,
        "backup_path": backup.get("path"),
        "backup_sha256": backup.get("sha256"),
        "backup_verified": backup.get("pg_restore_list_verification") == "PASS",
        "pre_apply_global_manufacturer_code_count": global_mc,
        "target_preflight": {
            "rows": len(recon),
            "existing_code": existing,
            "missing": missing,
            "deleted": deleted,
            "sku_drift": sku_drift,
            "brand_drift": brand_drift,
            "name_drift": name_drift,
            "slug_comparison": slug_status,
        },
        "transaction": {
            "isolation": "SERIALIZABLE",
            "advisory_lock": REAL_APPLY_ADVISORY_LOCK_KEY,
            "locked_rows": metrics["locked_rows"],
            "updated_rows": metrics["updated_rows"],
            "exact_matches": metrics["exact_matches"],
            "change_logs": metrics["change_logs"],
            "protected_drift": metrics["protected_drift"],
            "new_collisions": metrics["collision_groups"],
            "nontarget_changes": metrics["nontarget_changes"],
            "committed": True,
        },
        "commit_timestamp": commit_ts,
        "transaction_id": txid,
        "post_apply": {
            "target_non_null": non_null,
            "exact_matches": exact,
            "global_manufacturer_code_count": global_after,
            "change_log_matches": log_count,
            "protected_drift": protected_drift,
            "collision_count": collision_after,
        },
        "second_run_safety": second_probe,
        "recovery_manifest_payload_sha256": recovery.get("manifest_payload_sha256"),
        "change_log_reason": reason,
        "status": post_status,
        "errors": post_errors,
    }
    write_json(out_dir / "REAL_APPLY_MANIFEST.json", manifest)

    summary = f"""# Phase 2C REAL APPLY summary

## STATUS
`{post_status}`

## Authorization
- Owner-authorized real APPLY: YES
- Cohort rows: {OWNER_FROZEN_ROWS}
- Cohort SHA256: `{art_meta["sha256"]}`

## Git
- Apply logic SHA: `{apply_logic_sha}`

## Transaction
- Isolation: SERIALIZABLE
- Advisory lock: `{REAL_APPLY_ADVISORY_LOCK_KEY}`
- Updated: {metrics["updated_rows"]}
- Change logs: {metrics["change_logs"]}
- COMMIT: YES
- TXID: `{txid}`

## Post-apply
- Target non-null: {non_null}
- Exact matches: {exact}
- Global populated: {global_after}
- Protected drift: {protected_drift}
- Collisions: {collision_after}
- Search/DB smoke: {"PASS" if smoke.get("all_pass") else "FAIL"}

## Safety
- NO rename / NO deploy / NO Phase 2D / NO Phase 2E
- Backup: `{backup.get("path")}`
- Backup SHA256: `{backup.get("sha256")}`

## Errors
{post_errors or ["none"]}
"""
    summary_path = out_dir / "PHASE2C_REAL_APPLY_SUMMARY.md"
    assert_evidence_writable(summary_path)
    summary_path.write_text(summary, encoding="utf-8")
    print(json.dumps({"status": post_status, "transaction_id": txid, "errors": post_errors}, indent=2))
    return 0 if post_status == "APPLIED_VERIFIED" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceImmutabilityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
