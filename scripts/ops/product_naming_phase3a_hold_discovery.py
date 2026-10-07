#!/usr/bin/env python3
"""Phase 3A HOLD resolution discovery — READ-ONLY.

No Product.name / ProductType / KB / policy mutation. Generates audit artifacts only.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming_phase3a import (  # noqa: E402
    EXPECTED_REASON_COUNTS,
    MULTI_FUNCTION_OPTIONS,
    OEM_REGISTRY_REL,
    OWNER_TITLE_OPTIONS,
    PHASE2D_AUDIT_REL,
    PHASE2D_CANDIDATE_SHA256,
    PHASE2D_CANDIDATES_REL,
    PHASE2D_EXPECTED_APPLIED_ROWS,
    PHASE2D_EXPECTED_HOLD_ROWS,
    PHASE2D_HOLDS_REL,
    PHASE2D_HOLDS_SHA256,
    PHASE2D_OEM_REL,
    assert_matrix_invariants,
    assert_no_applied_intersection,
    build_root_cause_matrix,
    family_cluster_key,
    load_candidates,
    load_holds,
    normalize_brand_bucket,
    prioritize_score,
    reconcile_reason_counts,
    reject_mutation_flags,
    sha256_file,
)

MUTATION_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE)\b", re.I)
OUT_DIR = ROOT / "audit" / "product-naming-phase3a-hold-resolution"


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _run_ssh_psql(sql: str, *, ssh_host: str) -> str:
    if MUTATION_RE.search(sql):
        raise RuntimeError("Phase 3A refuses mutation-capable SQL")
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


def collect_runtime_identity(ssh_host: str) -> dict[str, Any]:
    from scripts.phase2c_live_readonly_census import collect_runtime_identity as _cri

    return _cri(ssh_host)


def fetch_live_targets(ids: list[int], ssh_host: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    chunk = 250
    for start in range(0, len(ids), chunk):
        part = ids[start : start + chunk]
        id_csv = ",".join(str(i) for i in part)
        sql = f"""
SELECT row_to_json(t) FROM (
  SELECT id, sku, name, manufacturer_code, brand_id, category_id, product_type_id,
         is_active, is_available, deleted_at::text AS deleted_at
  FROM products WHERE id IN ({id_csv}) ORDER BY id
) t;
"""
        raw = _run_ssh_psql(sql, ssh_host=ssh_host)
        for line in raw.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            out[str(obj["id"])] = {k: str(v) if v is not None else "" for k, v in obj.items()}
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_sha256sums(out_dir: Path) -> None:
    lines: list[str] = []
    for p in sorted(out_dir.iterdir()):
        if p.is_file() and p.name != "EVIDENCE_SHA256SUMS.txt":
            lines.append(f"{sha256_file(p)}  {p.name}")
    (out_dir / "EVIDENCE_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    reject_mutation_flags(argv)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument("--skip-live", action="store_true", help="Offline-only (no SSH)")
    args = p.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    holds = load_holds(ROOT / PHASE2D_HOLDS_REL)
    candidates = load_candidates(ROOT / PHASE2D_CANDIDATES_REL)
    assert_no_applied_intersection(holds, candidates)
    reason_counts, reason_errors = reconcile_reason_counts(holds)
    if reason_errors:
        write_json(
            out_dir / "PHASE3A_REPORT.json",
            {"status": "BLOCKED", "reason": "BASELINE_RECONCILIATION_MISMATCH", "errors": reason_errors},
        )
        print(json.dumps({"status": "BLOCKED", "errors": reason_errors}, indent=2))
        return 1

    audit_rows = list(csv.DictReader((ROOT / PHASE2D_AUDIT_REL).open(encoding="utf-8")))
    audit_by = {r["product_id"]: r for r in audit_rows}
    oem_rows = list(csv.DictReader((ROOT / PHASE2D_OEM_REL).open(encoding="utf-8")))
    oem_by = {r["product_id"]: r for r in oem_rows}
    registry_rows = list(csv.DictReader((ROOT / OEM_REGISTRY_REL).open(encoding="utf-8")))
    # Prefer EXACT identity rows when multiple registry entries exist.
    registry_by: dict[str, dict[str, str]] = {}
    for r in registry_rows:
        code = (r.get("manufacturer_code") or "").strip()
        if not code:
            continue
        prev = registry_by.get(code)
        if prev is None:
            registry_by[code] = r
            continue
        rank = {"EXACT_PRODUCT_IDENTITY": 2, "AMBIGUOUS": 1, "INSUFFICIENT": 0}
        if rank.get(r.get("evidence_status", ""), -1) > rank.get(prev.get("evidence_status", ""), -1):
            registry_by[code] = r

    # Brand reconciliation
    brand_rows = []
    for hold in holds:
        a = audit_by.get(hold["product_id"], {})
        bucket = normalize_brand_bucket(
            hold.get("brand", ""),
            current_name=hold.get("current_name", ""),
            brand_name=a.get("brand_name", ""),
        )
        brand_rows.append(
            {
                "product_id": hold["product_id"],
                "manufacturer_code": hold["manufacturer_code"],
                "hold_csv_brand": hold.get("brand", ""),
                "audit_brand_id": a.get("brand_id", ""),
                "audit_brand_name": a.get("brand_name", ""),
                "brand_bucket": bucket,
                "hold_reason": hold["_hold_reason"],
                "historical_missing_row": "yes" if not (hold.get("brand") or "").strip() else "no",
            }
        )
    missing_brand = [r for r in brand_rows if r["historical_missing_row"] == "yes"]
    brand_summary = Counter(r["brand_bucket"] for r in brand_rows)

    live_by: dict[str, dict[str, str]] = {}
    runtime: dict[str, Any] = {"skipped": True}
    mutation_sql_executed = 0
    if not args.skip_live:
        runtime = collect_runtime_identity(args.ssh_host)
        ids = [int(r["product_id"]) for r in holds]
        live_by = fetch_live_targets(ids, args.ssh_host)
        # prove SELECT 1 only
        one = _run_ssh_psql("SELECT 1;", ssh_host=args.ssh_host)
        if not one.endswith("1"):
            raise RuntimeError("SELECT 1 failed")

    matrix = build_root_cause_matrix(
        holds=holds,
        audit_by_id=audit_by,
        oem_by_id=oem_by,
        registry_by_code=registry_by,
        live_by_id=live_by if live_by else None,
    )
    inv_errors = assert_matrix_invariants(matrix)
    if inv_errors:
        write_json(out_dir / "PHASE3A_REPORT.json", {"status": "BLOCKED", "errors": inv_errors})
        print(json.dumps({"status": "BLOCKED", "errors": inv_errors}, indent=2))
        return 1

    # Universe + reason reconciliation
    universe = []
    for hold in holds:
        a = audit_by.get(hold["product_id"], {})
        universe.append(
            {
                "product_id": hold["product_id"],
                "sku": hold["sku"],
                "manufacturer_code": hold["manufacturer_code"],
                "brand": hold.get("brand", ""),
                "historical_hold_reason": hold["_hold_reason"],
                "dependency": hold["_dependency"],
                "remediation": hold["_remediation"],
                "current_name": hold.get("current_name", ""),
                "product_type_code": a.get("product_type_code", ""),
                "brand_id": a.get("brand_id", ""),
            }
        )
    write_csv(out_dir / "PHASE3A_HOLD_UNIVERSE.csv", universe)
    write_json(
        out_dir / "PHASE3A_HOLD_UNIVERSE_MANIFEST.json",
        {
            "rows": len(universe),
            "holds_sha256": PHASE2D_HOLDS_SHA256,
            "candidate_sha256": PHASE2D_CANDIDATE_SHA256,
            "applied_intersection": 0,
            "unique_product_ids": len({r["product_id"] for r in universe}),
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "logic_git_sha": _git_head(),
            "read_only": True,
        },
    )
    write_csv(
        out_dir / "PHASE3A_REASON_RECONCILIATION.csv",
        [
            {
                "hold_reason": reason,
                "expected": EXPECTED_REASON_COUNTS[reason],
                "actual": reason_counts[reason],
                "match": "yes",
            }
            for reason in EXPECTED_REASON_COUNTS
        ],
    )
    write_csv(out_dir / "PHASE3A_BRAND_RECONCILIATION.csv", brand_rows)

    # Live drift
    drift_rows = []
    if live_by:
        for hold in holds:
            pid = hold["product_id"]
            a = audit_by.get(pid, {})
            live = live_by.get(pid)
            from app.domain.product_naming_phase3a import live_drift_flags

            flags = live_drift_flags(
                {
                    "current_name": hold.get("current_name", ""),
                    "sku": hold.get("sku", ""),
                    "manufacturer_code": hold.get("manufacturer_code", ""),
                    "product_type_id": a.get("product_type_id", ""),
                    "brand_id": a.get("brand_id", ""),
                },
                live,
            )
            drift_rows.append(
                {
                    "product_id": pid,
                    "manufacturer_code": hold["manufacturer_code"],
                    "drift_flags": "|".join(flags),
                    "historical_name": hold.get("current_name", ""),
                    "live_name": (live or {}).get("name", ""),
                    "live_sku": (live or {}).get("sku", ""),
                    "live_manufacturer_code": (live or {}).get("manufacturer_code", ""),
                    "live_product_type_id": (live or {}).get("product_type_id", ""),
                    "live_brand_id": (live or {}).get("brand_id", ""),
                    "live_deleted_at": (live or {}).get("deleted_at", ""),
                    "live_is_active": (live or {}).get("is_active", ""),
                    "live_is_available": (live or {}).get("is_available", ""),
                }
            )
    else:
        drift_rows = [
            {
                "product_id": h["product_id"],
                "manufacturer_code": h["manufacturer_code"],
                "drift_flags": "LIVE_NOT_QUERIED",
            }
            for h in holds
        ]
    write_csv(out_dir / "PHASE3A_LIVE_IDENTITY_DRIFT.csv", drift_rows)

    matrix_dicts = [asdict(r) for r in matrix]
    write_csv(out_dir / "PHASE3A_ROOT_CAUSE_MATRIX.csv", matrix_dicts)
    write_csv(
        out_dir / "PHASE3A_BLOCKER_CHAIN.csv",
        [
            {
                "product_id": r.product_id,
                "manufacturer_code": r.manufacturer_code,
                "primary_blocker": r.primary_blocker,
                "secondary_blockers": r.secondary_blockers,
                "next_blocker_after_primary_fix": r.next_blocker_after_primary_fix,
                "projected_unlock_state": r.projected_unlock_state,
                "wave": r.wave,
            }
            for r in matrix
        ],
    )

    # Lane-specific CSVs
    write_csv(
        out_dir / "PHASE3A_PRODUCT_TYPE_MISSING_ANALYSIS.csv",
        [asdict(r) for r in matrix if r.resolution_lane == "A_MISSING_PRODUCT_TYPE"],
    )
    write_csv(
        out_dir / "PHASE3A_OEM_EVIDENCE_GAPS.csv",
        [asdict(r) for r in matrix if r.resolution_lane == "B_OEM_SEMANTIC_EVIDENCE"],
    )
    write_csv(
        out_dir / "PHASE3A_NAMING_POLICY_GAPS.csv",
        [asdict(r) for r in matrix if r.resolution_lane == "C_NAMING_POLICY"],
    )
    write_csv(
        out_dir / "PHASE3A_VARIANT_POLICY_GAPS.csv",
        [asdict(r) for r in matrix if r.resolution_lane == "D_VARIANT_POLICY"],
    )
    write_csv(
        out_dir / "PHASE3A_VARIANT_FACT_GAPS.csv",
        [asdict(r) for r in matrix if r.resolution_lane == "E_VARIANT_FACT"],
    )
    write_csv(
        out_dir / "PHASE3A_AUTHORITY_CONFLICTS.csv",
        [
            asdict(r)
            for r in matrix
            if r.resolution_lane in {"F_AUTHORITY_CONFLICT", "G_OWNER_TITLE", "H_MULTI_FUNCTION"}
        ],
    )

    # Family clusters
    clusters: dict[str, list] = defaultdict(list)
    for r in matrix:
        clusters[family_cluster_key(r)].append(r)
    cluster_rows = []
    for key, rows in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        cluster_rows.append(
            {
                "cluster_key": key,
                "rows": len(rows),
                "common_blocker": rows[0].primary_blocker,
                "common_lane": rows[0].resolution_lane,
                "common_wave": rows[0].wave,
                "automation_confidence": Counter(x.automation_confidence for x in rows).most_common(1)[0][0],
                "sample_product_ids": ",".join(x.product_id for x in rows[:8]),
            }
        )
    write_csv(out_dir / "PHASE3A_FAMILY_CLUSTERS.csv", cluster_rows)

    # Projected unlocks + waves
    projected_counts = Counter(r.projected_unlock_state for r in matrix)
    write_csv(
        out_dir / "PHASE3A_PROJECTED_UNLOCKS.csv",
        [{"projected_unlock_state": k, "rows": v} for k, v in sorted(projected_counts.items())],
    )

    wave_order = [
        "WAVE_3B_GOVERNANCE_QUICK_WINS",
        "WAVE_3C_VARIANT_FACTS",
        "WAVE_3D_INSIZE_OEM_EVIDENCE",
        "WAVE_3E_INSIZE_MISSING_PT",
        "WAVE_3F_DASQUA_PT",
        "WAVE_3G_TERMA_PT",
        "WAVE_3H_MANUAL_EXCEPTIONS",
    ]
    wave_rows = []
    cumulative = PHASE2D_EXPECTED_APPLIED_ROWS
    for wave in wave_order:
        rows = [r for r in matrix if r.wave == wave]
        # Expected unlock = DIRECT + TWO_STEP for conservative yield? Spec wants expected unlock.
        # Use DIRECT_UNLOCK count as "expected unlock" for governance waves; for others use
        # direct+two-step as bounded expectation, remaining stay blocked until evidence.
        expected = sum(1 for r in rows if r.projected_unlock_state == "DIRECT_UNLOCK")
        partial = sum(
            1
            for r in rows
            if r.projected_unlock_state in {"DIRECT_UNLOCK", "TWO_STEP_UNLOCK"}
        )
        # For wave inventory, rows = full membership (exclusive).
        cumulative_after = cumulative + expected
        owner_heavy = any(r.owner_decision_required == "yes" for r in rows)
        source_heavy = any(r.source_evidence_required == "yes" for r in rows)
        wave_rows.append(
            {
                "wave": wave,
                "rows": len(rows),
                "direct_unlock": sum(1 for r in rows if r.projected_unlock_state == "DIRECT_UNLOCK"),
                "two_step": sum(1 for r in rows if r.projected_unlock_state == "TWO_STEP_UNLOCK"),
                "multi_step": sum(1 for r in rows if r.projected_unlock_state == "MULTI_STEP_UNLOCK"),
                "owner_decision_required": sum(1 for r in rows if r.projected_unlock_state == "OWNER_DECISION_REQUIRED"),
                "source_evidence_required": sum(1 for r in rows if r.projected_unlock_state == "SOURCE_EVIDENCE_REQUIRED"),
                "unresolved": sum(1 for r in rows if r.projected_unlock_state == "UNRESOLVED"),
                "expected_unlock": expected,
                "partial_progress_if_wave_gate_cleared": partial,
                "cumulative_standardized_after_expected": cumulative_after,
                "priority": prioritize_score(wave, len(rows), owner_heavy, source_heavy),
            }
        )
        cumulative = cumulative_after
    write_csv(out_dir / "PHASE3A_WAVE_PLAN.csv", wave_rows)

    # Brand source coverage
    brand_source = [
        {
            "brand": "INSIZE",
            "hold_rows": brand_summary.get("INSIZE", 0) + brand_summary.get("INSIZE_INFERRED", 0),
            "authoritative_local_sources": "108A.pdf;108B.pdf;INSIZE_OEM_PRODUCT_IDENTITY_REGISTRY.csv",
            "source_authority_quality": "HIGH_STRUCTURED_OEM",
            "code_coverage_note": "Identity registry covers subset; accessory-only is common",
            "product_type_inferability": "PARTIAL",
            "variant_fact_coverage": "PARTIAL_FOR_READY_FAMILIES",
            "likely_automatic_resolution": sum(
                1
                for r in matrix
                if r.brand_bucket.startswith("INSIZE")
                and r.projected_unlock_state in {"DIRECT_UNLOCK", "TWO_STEP_UNLOCK"}
            ),
            "manual_or_ambiguous": sum(
                1
                for r in matrix
                if r.brand_bucket.startswith("INSIZE")
                and r.projected_unlock_state == "OWNER_DECISION_REQUIRED"
            ),
            "missing_source": sum(
                1
                for r in matrix
                if r.brand_bucket.startswith("INSIZE")
                and r.projected_unlock_state == "SOURCE_EVIDENCE_REQUIRED"
            ),
        },
        {
            "brand": "DASQUA",
            "hold_rows": brand_summary.get("DASQUA", 0),
            "authoritative_local_sources": "Dasqua-Catalogue-2025-mirror.pdf (external catalogs tree); no structured OEM identity registry in-repo",
            "source_authority_quality": "MEDIUM_UNSTRUCTURED_PDF",
            "code_coverage_note": "No Phase-2D OEM semantic registry coverage",
            "product_type_inferability": "LOW_WITHOUT_EXTRACTION",
            "variant_fact_coverage": "UNKNOWN",
            "likely_automatic_resolution": 0,
            "manual_or_ambiguous": 0,
            "missing_source": brand_summary.get("DASQUA", 0),
        },
        {
            "brand": "TERMA",
            "hold_rows": brand_summary.get("TERMA", 0),
            "authoritative_local_sources": "کاتالوگ ترما.pdf; price list PDF (external Product and Data Complete)",
            "source_authority_quality": "MEDIUM_UNSTRUCTURED_PDF",
            "code_coverage_note": "No Phase-2D OEM semantic registry coverage",
            "product_type_inferability": "LOW_WITHOUT_EXTRACTION",
            "variant_fact_coverage": "UNKNOWN",
            "likely_automatic_resolution": 0,
            "manual_or_ambiguous": 0,
            "missing_source": brand_summary.get("TERMA", 0),
        },
    ]
    write_csv(out_dir / "PHASE3A_BRAND_SOURCE_COVERAGE.csv", brand_source)

    # Owner decisions markdown
    owner_md = [
        "# Phase 3A — owner decisions required",
        "",
        "## Counts",
        f"- Projected OWNER_DECISION_REQUIRED rows: **{projected_counts.get('OWNER_DECISION_REQUIRED', 0)}**",
        f"- Historical variant-policy holds: **{reason_counts['HOLD_VARIANT_POLICY_UNDEFINED']}**",
        f"- Naming-policy holds (governance, often P0): **{reason_counts['HOLD_PRODUCT_TYPE_NAMING_POLICY']}**",
        f"- Authority conflicts: **{reason_counts['HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT']}**",
        f"- Owner title hold: **{reason_counts['HOLD_OWNER_CANONICAL_TITLE_REVIEW']}**",
        f"- Multi-function conflict: **{reason_counts['HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT']}**",
        "",
        "## Canary G — 2223-153 owner title options",
        "",
    ]
    for opt in OWNER_TITLE_OPTIONS:
        owner_md.append(f"- **{opt['option_id']}**: `{opt['canonical_title_fa']}` — {opt['tradeoff']}")
    owner_md += ["", "## Canary H — 0312-TH50 multi-function options", ""]
    for opt in MULTI_FUNCTION_OPTIONS:
        owner_md.append(f"- **{opt['option_id']}**: {opt['proposal']} — {opt['tradeoff']}")
    owner_md += [
        "",
        "## Authority conflicts (F)",
        "",
    ]
    for r in matrix:
        if r.resolution_lane == "F_AUTHORITY_CONFLICT":
            owner_md.append(
                f"- `{r.manufacturer_code}` persisted `{r.current_product_type_code}` "
                f"OEM `{r.OEM_heading}` dependency `{r.dependency}`"
            )
    owner_md += [
        "",
        "## Variant policy groups (D)",
        "",
    ]
    vp = Counter(r.dependency for r in matrix if r.resolution_lane == "D_VARIANT_POLICY")
    for dep, n in vp.most_common():
        owner_md.append(f"- `{dep}`: {n} products")
    (out_dir / "PHASE3A_OWNER_DECISIONS_REQUIRED.md").write_text(
        "\n".join(owner_md) + "\n", encoding="utf-8"
    )

    lane_counts = Counter(r.resolution_lane for r in matrix)
    drift_counter = Counter()
    for row in drift_rows:
        for flag in (row.get("drift_flags") or "").split("|"):
            if flag:
                drift_counter[flag] += 1

    # Executive summary
    top_clusters = cluster_rows[:15]
    exec_lines = [
        "# Phase 3A HOLD resolution — executive summary",
        "",
        f"- Standardized persisted (Phase 2F): **{PHASE2D_EXPECTED_APPLIED_ROWS}**",
        f"- Remaining HOLD: **{PHASE2D_EXPECTED_HOLD_ROWS}**",
        f"- Total governed cohort: **{PHASE2D_EXPECTED_APPLIED_ROWS + PHASE2D_EXPECTED_HOLD_ROWS}**",
        "",
        "## Reason reconciliation",
        "",
    ]
    for reason, n in EXPECTED_REASON_COUNTS.items():
        exec_lines.append(f"- `{reason}`: {n}")
    exec_lines += ["", "## Projected unlockability", ""]
    for k, v in sorted(projected_counts.items()):
        exec_lines.append(f"- `{k}`: {v}")
    exec_lines += ["", "## Waves", ""]
    for w in wave_rows:
        exec_lines.append(
            f"- `{w['wave']}`: rows={w['rows']} expected_unlock={w['expected_unlock']} "
            f"cumulative={w['cumulative_standardized_after_expected']} priority={w['priority']}"
        )
    exec_lines += ["", "## Top clusters", ""]
    for c in top_clusters:
        exec_lines.append(f"- `{c['cluster_key']}`: {c['rows']} ({c['common_wave']})")
    exec_lines += [
        "",
        "## Historical missing brand row",
        "",
        (
            f"Identified product_id `{missing_brand[0]['product_id']}` manufacturer_code "
            f"`{missing_brand[0]['manufacturer_code']}` hold `{missing_brand[0]['hold_reason']}` "
            "with empty HOLD CSV brand field; name/audit indicate INSIZE. This explains "
            "101 HOLD_PRODUCT_TYPE_NAMING_POLICY vs 100 branded-INSIZE rows in surface brand tallies."
            if missing_brand
            else "NONE FOUND"
        ),
        "",
        "## Read-only proof",
        "",
        "- DB mutation SQL executed: 0",
        "- Product / ProductType / KB / policy / OEM authority mutations: 0",
        "- Phase 2F names mutated: 0",
        "- Deploy: no",
        "",
    ]
    (out_dir / "PHASE3A_EXECUTIVE_SUMMARY.md").write_text("\n".join(exec_lines), encoding="utf-8")

    status = "READY_FOR_WAVE_3B"
    report = {
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "logic_git_sha": _git_head(),
        "main_note": "discovery from branch HEAD; behind-main checked at PR time",
        "holds_sha256": PHASE2D_HOLDS_SHA256,
        "candidate_sha256": PHASE2D_CANDIDATE_SHA256,
        "standardized_persisted": PHASE2D_EXPECTED_APPLIED_ROWS,
        "remaining_hold": PHASE2D_EXPECTED_HOLD_ROWS,
        "reason_counts": reason_counts,
        "brand_summary": dict(brand_summary),
        "historical_missing_brand_rows": missing_brand,
        "lane_counts": dict(lane_counts),
        "projected_unlock_counts": dict(projected_counts),
        "wave_plan": wave_rows,
        "live_runtime_identity": runtime,
        "live_drift_summary": dict(drift_counter),
        "read_only_proof": {
            "mutation_sql_executed": mutation_sql_executed,
            "product_mutations": 0,
            "product_type_mutations": 0,
            "kb_mutations": 0,
            "policy_mutations": 0,
            "oem_authority_mutations": 0,
            "phase2f_name_mutations": 0,
            "deploy": False,
        },
        "owner_title_options": OWNER_TITLE_OPTIONS,
        "multi_function_options": MULTI_FUNCTION_OPTIONS,
    }
    write_json(out_dir / "PHASE3A_REPORT.json", report)
    write_sha256sums(out_dir)
    print(json.dumps({"status": status, "holds": PHASE2D_EXPECTED_HOLD_ROWS, "waves": len(wave_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
