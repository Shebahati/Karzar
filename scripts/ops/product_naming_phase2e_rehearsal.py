#!/usr/bin/env python3
"""Phase 2E — transactional Product.name rename rehearsal (ROLLBACK only)."""

from __future__ import annotations

import argparse
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
    ADVISORY_LOCK_KEY,
    CHANGE_LOG_CONTRACT_REFERENCE,
    CHANGE_LOG_EQUIVALENT_FIELDS,
    PHASE2D_CANDIDATE_SHA256,
    PHASE2D_EXPECTED_READY_ROWS,
    REHEARSAL_REASON,
    build_expected_prestate_rows,
    build_rehearsal_sql,
    load_audit_ready_rows,
    load_freeze_manifest,
    parse_rehearsal_metrics,
    prestate_csv_bytes,
    reconcile_live_row,
    rehearsal_logic_file_sha256,
    rehearsal_success_metrics,
    reject_real_apply_flags,
    sha256_bytes,
    sha256_file,
    target_fingerprint_row,
    validate_candidate_file,
    validate_phase2d_freeze_manifest,
)

DEFAULT_CANDIDATE = ROOT / "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
DEFAULT_MANIFEST = ROOT / "audit/product-naming-phase2d/PHASE2D_CANDIDATE_FREEZE_MANIFEST.json"
DEFAULT_AUDIT = ROOT / "audit/product-naming-phase2d/PHASE2D_CANONICAL_NAME_AUDIT.csv"
AUDIT_OUT = ROOT / "audit/product-naming-phase2e-rehearsal"

MUTATION_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE)\b", re.I)
COMMIT_RE = re.compile(r"(^|[^A-Z_])COMMIT(\s|;|$)", re.I)


def _run_ssh_psql(sql: str, *, ssh_host: str, allow_write: bool = False) -> str:
    if not allow_write and MUTATION_RE.search(sql):
        raise RuntimeError("Refusing mutation SQL outside rehearsal")
    if COMMIT_RE.search(sql):
        raise RuntimeError("COMMIT forbidden in Phase 2E tooling")
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
        raise RuntimeError("COMMIT forbidden")
    if "ROLLBACK" not in script.upper():
        raise RuntimeError("Rehearsal script must include ROLLBACK")
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


def _fetch_live_targets(ids: list[int], ssh_host: str) -> dict[str, dict[str, str]]:
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


def _log_baseline(ids: list[int], ssh_host: str) -> int:
    id_csv = ",".join(str(i) for i in ids)
    sql = f"""
SELECT COUNT(*) FROM product_change_logs
WHERE product_id IN ({id_csv}) AND reason = '{REHEARSAL_REASON}';
"""
    return int(_run_ssh_psql(sql, ssh_host=ssh_host).splitlines()[-1] or "0")


def _collision_precheck(proposed_names: list[str], target_ids: list[int], ssh_host: str) -> dict[str, int]:
    id_csv = ",".join(str(i) for i in target_ids)
    # Exact duplicate proposed names within cohort
    exact_dup = len(proposed_names) - len(set(proposed_names))
    names_sql = ",".join("'" + n.replace("'", "''") + "'" for n in set(proposed_names))
    catalog_sql = f"""
SELECT COUNT(*) FROM (
  SELECT name FROM products
  WHERE deleted_at IS NULL AND name IN ({names_sql}) AND id NOT IN ({id_csv})
) s;
"""
    catalog_hits = int(_run_ssh_psql(catalog_sql, ssh_host=ssh_host).splitlines()[-1] or "0")
    return {"cohort_exact_dup": exact_dup, "catalog_name_hits": catalog_hits}


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _sha256sums(out_dir: Path) -> None:
    lines: list[str] = []
    for p in sorted(out_dir.glob("*")):
        if p.is_file():
            lines.append(f"{sha256_file(p)}  {p.name}")
    (out_dir / "EVIDENCE_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    reject_real_apply_flags(argv)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate-file", type=Path, default=DEFAULT_CANDIDATE)
    p.add_argument("--expected-candidate-sha256", default=PHASE2D_CANDIDATE_SHA256)
    p.add_argument("--freeze-manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--audit-csv", type=Path, default=DEFAULT_AUDIT)
    p.add_argument("--report-dir", type=Path, default=AUDIT_OUT)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument("--rehearse", action="store_true")
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--rehearsal-logic-git-sha", default=None)
    args = p.parse_args(argv)

    if not args.rehearse and not args.preflight_only:
        print("ERROR: specify --preflight-only or --rehearse", file=sys.stderr)
        return 2

    out_dir = args.report_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    logic_sha = args.rehearsal_logic_git_sha or _git_head()
    logic_hashes = rehearsal_logic_file_sha256(ROOT)

    manifest = load_freeze_manifest(args.freeze_manifest)
    validate_phase2d_freeze_manifest(manifest)
    candidates, cand_sha = validate_candidate_file(
        args.candidate_file, expected_sha256=args.expected_candidate_sha256
    )
    audit_ready = load_audit_ready_rows(args.audit_csv)
    prestate = build_expected_prestate_rows(candidates, audit_ready)
    prestate_sha = sha256_bytes(prestate_csv_bytes(prestate))
    _write_csv(
        out_dir / "PHASE2E_EXPECTED_PRESTATE.csv",
        list(prestate[0].keys()),
        prestate,
    )

    from scripts.phase2c_live_readonly_census import (  # noqa: PLC0415
        collect_baseline,
        collect_runtime_identity,
        _read_only_session_proof,
    )

    runtime = collect_runtime_identity(args.ssh_host)
    ro_proof = _read_only_session_proof(args.ssh_host)
    baseline = collect_baseline(args.ssh_host)

    ids = [int(r["product_id"]) for r in prestate]
    live = _fetch_live_targets(ids, args.ssh_host)
    drift_errors: list[str] = []
    for row in prestate:
        drift_errors.extend(reconcile_live_row(row, live[row["product_id"]]))
    collisions = _collision_precheck(
        [r["proposed_name"] for r in prestate], ids, args.ssh_host
    )

    target_rows = []
    name_fp_parts = []
    protected_fp_parts = []
    for row in prestate:
        lv = live[row["product_id"]]
        target_rows.append({**row, **lv, "name_fingerprint": lv.get("name", "")})
        name_fp_parts.append(f"{row['product_id']}:{lv.get('name','')}")
        protected_fp_parts.append(f"{row['product_id']}:{target_fingerprint_row(lv)}")
    target_prestate_sha = sha256_bytes("\n".join(protected_fp_parts).encode("utf-8"))
    _write_csv(
        out_dir / "PHASE2E_TARGET_PRESTATE.csv",
        list(target_rows[0].keys()),
        target_rows,
    )
    (out_dir / "PHASE2E_TARGET_PRESTATE_SHA256").write_text(
        target_prestate_sha + "\n", encoding="utf-8"
    )
    _write_csv(
        out_dir / "PHASE2E_PROTECTED_FIELD_AUDIT.csv",
        ["product_id", "protected_fingerprint"],
        [
            {
                "product_id": r["product_id"],
                "protected_fingerprint": target_fingerprint_row(live[r["product_id"]]),
            }
            for r in prestate
        ],
    )
    seo_issues = [
        r["product_id"]
        for r in prestate
        if (r.get("seo_title_impact") or "").strip().lower() in ("yes", "true", "1")
    ]
    if seo_issues:
        drift_errors.append(f"seo_title_impact_live_gate:{','.join(seo_issues)}")

    log_baseline = _log_baseline(ids, args.ssh_host)
    precheck = {
        "expected_rows": len(prestate),
        "prestate_sha256": prestate_sha,
        "target_prestate_sha256": target_prestate_sha,
        "live_drift_errors": drift_errors,
        "collision_precheck": collisions,
        "rehearsal_log_baseline": log_baseline,
        "runtime_identity": runtime,
        "read_only_proof": ro_proof,
        "catalog_baseline": baseline,
    }
    _write_json(out_dir / "PHASE2E_PRECHECK.json", precheck)

    status = "BLOCKED"
    if drift_errors or collisions["cohort_exact_dup"] or collisions["catalog_name_hits"]:
        _write_json(
            out_dir / "PHASE2E_REHEARSAL_REPORT.json",
            {"status": status, "precheck": precheck},
        )
        print(json.dumps({"status": status, "precheck": precheck}, indent=2))
        return 1

    if args.preflight_only:
        status = "PARTIAL"
        _write_json(out_dir / "PHASE2E_REHEARSAL_REPORT.json", {"status": status, "precheck": precheck})
        print(json.dumps({"status": status}, indent=2))
        return 0

    sql = build_rehearsal_sql(prestate)
    assert "COMMIT" not in sql.upper().replace("ROLLBACK", "")
    stdout = _run_ssh_psql_script(sql, ssh_host=args.ssh_host)
    metrics = parse_rehearsal_metrics(stdout)
    metric_errors = rehearsal_success_metrics(metrics, PHASE2D_EXPECTED_READY_ROWS)

    post_live = _fetch_live_targets(ids, args.ssh_host)
    post_drift: list[str] = []
    for row in prestate:
        if (post_live[row["product_id"]].get("name") or "").strip() != row["expected_old_name"]:
            post_drift.append(row["product_id"])
        if (post_live[row["product_id"]].get("name") or "").strip() == row["proposed_name"]:
            post_drift.append(f"proposed_stuck:{row['product_id']}")
    post_log = _log_baseline(ids, args.ssh_host)
    post_protected_sha = sha256_bytes(
        "\n".join(
            f"{r['product_id']}:{target_fingerprint_row(post_live[r['product_id']])}"
            for r in prestate
        ).encode("utf-8")
    )

    in_tx_rows = [
        {
            "product_id": r["product_id"],
            "expected_old_name": r["expected_old_name"],
            "proposed_name": r["proposed_name"],
            "metrics": metrics,
        }
        for r in prestate
    ]
    _write_csv(
        out_dir / "PHASE2E_IN_TRANSACTION_RESULT.csv",
        ["product_id", "expected_old_name", "proposed_name", "metrics"],
        in_tx_rows,
    )
    log_audit = [
        {
            "product_id": r["product_id"],
            "field_name": "name",
            "old_value": r["expected_old_name"],
            "new_value": r["proposed_name"],
            "reason": REHEARSAL_REASON,
        }
        for r in prestate
    ]
    _write_csv(
        out_dir / "PHASE2E_IN_TRANSACTION_LOG_AUDIT.csv",
        ["product_id", "field_name", "old_value", "new_value", "reason"],
        log_audit,
    )
    _write_csv(
        out_dir / "PHASE2E_POST_ROLLBACK_VERIFY.csv",
        ["product_id", "name_after", "expected_old_name", "match"],
        [
            {
                "product_id": r["product_id"],
                "name_after": post_live[r["product_id"]].get("name", ""),
                "expected_old_name": r["expected_old_name"],
                "match": (
                    "yes"
                    if post_live[r["product_id"]].get("name", "") == r["expected_old_name"]
                    else "no"
                ),
            }
            for r in prestate
        ],
    )
    _write_json(
        out_dir / "PHASE2E_NON_TARGET_AUDIT.json",
        {"non_target_mutations": metrics.get("non_target_name_changes", -1)},
    )

    rollback_ok = not post_drift and post_log == log_baseline and post_protected_sha == target_prestate_sha
    if not metric_errors and rollback_ok:
        status = "READY_FOR_OWNER_APPLY_AUTHORIZATION"
    elif metric_errors:
        status = "BLOCKED"
    else:
        status = "PARTIAL"

    report = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "main_sha": subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "rehearsal_logic_git_sha": logic_sha,
        "rehearsal_logic_file_sha256": logic_hashes,
        "phase2d_candidate_sha256": cand_sha,
        "phase2d_candidate_rows": len(candidates),
        "prestate_sha256": prestate_sha,
        "target_prestate_sha256": target_prestate_sha,
        "post_rollback_prestate_sha256": post_protected_sha,
        "transient_product_name_updates": PHASE2D_EXPECTED_READY_ROWS,
        "transient_product_change_log_inserts": metrics.get("rehearsal_logs", 0),
        "persistent_product_name_delta": 0 if rollback_ok else "nonzero",
        "persistent_rehearsal_log_delta": post_log - log_baseline,
        "metrics": metrics,
        "metric_errors": metric_errors,
        "rollback_executed": True,
        "advisory_lock": ADVISORY_LOCK_KEY,
        "change_log_contract": CHANGE_LOG_CONTRACT_REFERENCE,
        "change_log_fields": list(CHANGE_LOG_EQUIVALENT_FIELDS),
    }
    _write_json(out_dir / "PHASE2E_REHEARSAL_REPORT.json", report)
    _write_json(
        out_dir / "PHASE2E_REHEARSAL_MANIFEST.json",
        {**report, "candidate_file": str(args.candidate_file)},
    )
    (out_dir / "PHASE2E_REHEARSAL_REPORT.md").write_text(
        (
            "# Phase 2E transactional rename rehearsal\n\n"
            "**REHEARSAL ONLY** — mandatory `ROLLBACK`; no Phase 2F authorization.\n\n"
            f"- Status: `{status}`\n"
            f"- Transient `Product.name` updates: **{PHASE2D_EXPECTED_READY_ROWS}**\n"
            f"- Transient `product_change_logs` inserts: **{metrics.get('rehearsal_logs', 0)}**\n"
            f"- Persistent `Product.name` delta after rollback: **{report['persistent_product_name_delta']}**\n"
            f"- Persistent rehearsal log delta: **{report['persistent_rehearsal_log_delta']}**\n"
            f"- Phase 2D candidate SHA256: `{cand_sha}`\n"
            f"- Rehearsal logic git SHA: `{logic_sha}`\n"
        ),
        encoding="utf-8",
    )
    _sha256sums(out_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if status == "READY_FOR_OWNER_APPLY_AUTHORIZATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
