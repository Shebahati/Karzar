#!/usr/bin/env python3
"""TX-OWNER-001 — 111-row remote-first evidence recovery package (research-only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_baseline import write_csv  # noqa: E402
from catalog_target.tx_owner_001_evidence_111_recovery import (  # noqa: E402
    ACTION_REGISTER,
    APPROVED_DOMAIN_CODES,
    build_physical_manifest,
    build_prior_index,
    build_recovery_matrix,
    build_source_catalog,
    boundary_assessment_row,
    collect_source_rows,
    fail_closed_reconciliation,
    finalize_source_register,
    load_action_register,
    sha256_file,
    verify_action_register_identity,
)

OUT_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-evidence-111-recovery-2026-10-18"
PLAN_FA = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-evidence-111-action-2026-10-18"
    / "00-OWNER-111-EVIDENCE-ACTION-PLAN-FA.md"
)


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_sha256sums(out_dir: Path, names: list[str]) -> None:
    lines = [
        f"{sha256_file(out_dir / name)}  {name}"
        for name in sorted(names)
        if (out_dir / name).is_file()
    ]
    (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def owner_review_memo(matrix: list[dict[str, str]], recon: dict, source_rows: list[dict[str, str]]) -> str:
    counts = recon["evidence_recovery_status_counts"]
    with_url = sum(1 for r in source_rows if r.get("source_url"))
    without_url = len(source_rows) - with_url
    prov = {}
    for r in source_rows:
        prov[r["provenance_class"]] = prov.get(r["provenance_class"], 0) + 1
    return f"""# TX-OWNER-001 — Owner review memo (111 evidence recovery)

**Status:** `READY_FOR_OWNER_REVIEW` — research-only; no APPLY; Owner disposition remains `REQUEST_MORE_EVIDENCE` for all 111 SKUs.

## Source inventory (honest scope)
- **{len(source_rows)}** rows in `02-SOURCE-REGISTER.csv` (re-indexed prior audit sources + supplemental Groz category pass).
- **{with_url}** rows carry a URL; **{without_url}** are explicitly `PRIOR_INDEXED_REFERENCE_NO_URL` (not live recoveries).
- Provenance mix: `{json.dumps(prov, ensure_ascii=False)}`
- HTTP transport probes (when enabled) indicate reachability only — **not** verified model-content concordance with Karzar stock.

## A. Exact OEM documentary evidence recovered (model/page — not physical stock)
Rows with `exact_oem_documentary_recovered=YES`: **{recon["exact_oem_documentary_yes_count"]}** of 111.

## B. Partial or family-level evidence
Rows with `partial_or_family_evidence=YES`: **{recon["partial_family_yes_count"]}**.

## C. Conflicting evidence documented
Rows with `conflicting_evidence_flag=YES`: **{recon["conflicting_evidence_count"]}**.

## D. Physical-stock evidence still required
Rows with `physical_stock_evidence_required=YES`: **{recon["physical_stock_required_count"]}**.

## E. Remote research unresolved
Rows with `remote_research_unresolved=YES`: **{recon["remote_unresolved_count"]}**.

## Recovery status distribution
```json
{json.dumps(counts, indent=2, ensure_ascii=False)}
```

## Register identity (Git blob vs raw digest)
- Git blob SHA-1 (canonical): `{recon["canonical_action_register_git_blob_sha1"]}`
- Raw file SHA-256: `{recon["canonical_action_register_raw_sha256"]}`
- Attestation: **{recon["register_identity_attestation"]}**

## Safety (unchanged)
- 151 documentary `APPROVE_CATALOG_EXIT` rows and Owner journals 001–011 are immutable inputs.
- Category **154** and **27** industrial oils under **156** remain protected.
- `PRODUCTION_MUTATION=NO` — no catalog, Hesabfa, deploy, or Owner auto-approval.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--live-probe",
        action="store_true",
        help="Perform live HTTP transport probes (optional; default skips for reproducible builds).",
    )
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ACTION_REGISTER.is_file() or not PLAN_FA.is_file():
        raise RuntimeError("BLOCKED: missing canonical 111 action register or plan")

    register_identity = verify_action_register_identity()
    register_rows = load_action_register()
    register_ids = {int(r["product_id"]) for r in register_rows}
    prior_index = build_prior_index(register_ids)
    catalog = build_source_catalog(register_rows)

    access_date = datetime.now(UTC).strftime("%Y-%m-%d")
    matrix = build_recovery_matrix(register_rows, prior_index, catalog)
    sources = finalize_source_register(catalog, access_date, live_probe=args.live_probe)
    physical = build_physical_manifest(register_rows, matrix)
    boundary = [
        boundary_assessment_row(
            reg,
            next(m for m in matrix if m["product_id"] == reg["product_id"]),
            prior_index.by_product[int(reg["product_id"])],
        )
        for reg in register_rows
    ]

    write_csv(out_dir / "01-EVIDENCE-RECOVERY-MATRIX-111.csv", list(matrix[0].keys()), matrix)
    write_csv(out_dir / "02-SOURCE-REGISTER.csv", list(sources[0].keys()) if sources else ["source_id"], sources)
    write_csv(
        out_dir / "03-PHYSICAL-EVIDENCE-COLLECTION-MANIFEST.csv",
        list(physical[0].keys()) if physical else ["product_id"],
        physical,
    )
    write_csv(out_dir / "05-SEVEN-DOMAIN-TECHNICAL-BOUNDARY-ASSESSMENT.csv", list(boundary[0].keys()), boundary)

    recon = fail_closed_reconciliation(register_rows, matrix, physical, register_identity)
    (out_dir / "04-OWNER-REVIEW-MEMO.md").write_text(
        owner_review_memo(matrix, recon, sources),
        encoding="utf-8",
    )

    identity = {
        "package_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_generation_git_head_sha": _git_sha(),
        "scope": "TX-OWNER-001 Phase 1B evidence recovery — 111 open Owner evidence requests",
        "base_merge_commit_pr531": "2e37c5de0768a9d85c142b5d9b1f631102aa615c",
        "canonical_action_register_path": str(ACTION_REGISTER.relative_to(ROOT)),
        "canonical_action_register_git_blob_sha1": register_identity["canonical_action_register_git_blob_sha1"],
        "canonical_action_register_raw_sha256": register_identity["canonical_action_register_raw_sha256"],
        "register_identity_attestation": register_identity["register_identity_attestation"],
        "approved_domain_codes": sorted(APPROVED_DOMAIN_CODES),
        "wave_counts": recon["wave_counts"],
        "workstream_counts": recon["workstream_counts"],
        "live_http_probe_enabled": args.live_probe,
        "safety": recon["zero_mutation"],
    }
    (out_dir / "00-PACKAGE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "06-RECONCILIATION.json").write_text(json.dumps(recon, indent=2, ensure_ascii=False), encoding="utf-8")

    artifact_names = [
        "00-PACKAGE-IDENTITY.json",
        "01-EVIDENCE-RECOVERY-MATRIX-111.csv",
        "02-SOURCE-REGISTER.csv",
        "03-PHYSICAL-EVIDENCE-COLLECTION-MANIFEST.csv",
        "04-OWNER-REVIEW-MEMO.md",
        "05-SEVEN-DOMAIN-TECHNICAL-BOUNDARY-ASSESSMENT.csv",
        "06-RECONCILIATION.json",
    ]
    write_sha256sums(out_dir, artifact_names)

    summary = {
        "STATUS": "READY_FOR_OWNER_REVIEW",
        "matrix_rows": len(matrix),
        "source_register_rows": len(sources),
        "source_rows_with_url": sum(1 for r in sources if r.get("source_url")),
        "source_rows_without_url": sum(1 for r in sources if not r.get("source_url")),
        "physical_manifest_rows": len(physical),
        "live_http_probe_enabled": args.live_probe,
        "evidence_recovery_status_counts": recon["evidence_recovery_status_counts"],
        "exact_oem_documentary_yes_count": recon["exact_oem_documentary_yes_count"],
        "partial_family_yes_count": recon["partial_family_yes_count"],
        "remote_unresolved_count": recon["remote_unresolved_count"],
        "physical_stock_required_count": recon["physical_stock_required_count"],
    }
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
