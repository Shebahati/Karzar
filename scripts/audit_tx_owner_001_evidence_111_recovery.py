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
    boundary_assessment_row,
    collect_source_rows,
    fail_closed_reconciliation,
    load_action_register,
    sha256_file,
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


def owner_review_memo(matrix: list[dict[str, str]], recon: dict) -> str:
    counts = recon["evidence_recovery_status_counts"]
    return f"""# TX-OWNER-001 — Owner review memo (111 evidence recovery)

**Status:** `READY_FOR_OWNER_REVIEW` — research-only; no APPLY; Owner disposition remains `REQUEST_MORE_EVIDENCE` for all 111 SKUs.

## A. Exact OEM documentary evidence recovered (model/page — not physical stock)
Rows with `exact_oem_documentary_recovered=YES`: **{recon["exact_oem_documentary_yes_count"]}** of 111.
OEM product pages prove **manufacturer model class** only until nameplate/packaging confirms the Karzar unit.

## B. Partial or family-level evidence
Rows with `partial_or_family_evidence=YES`: **{recon["partial_family_yes_count"]}**.
Includes distributor listings, OEM category/index tokens, near-model suffix pages, and application-class references.

## C. Conflicting evidence documented
Rows with `conflicting_evidence_flag=YES`: **{recon["conflicting_evidence_count"]}**.
Conflicts include title/family mismatches (e.g. saw-accessory vs air-ratchet kit) and Q-suffix M7 pages vs catalog tokens without Q.

## D. Physical-stock evidence still required
Rows with `physical_stock_evidence_required=YES`: **{recon["physical_stock_required_count"]}**.
See `03-PHYSICAL-EVIDENCE-COLLECTION-MANIFEST.csv` grouped by recommended responsible party.

## E. Remote research unresolved
Rows with `remote_research_unresolved=YES`: **{recon["remote_unresolved_count"]}**.
No conclusive primary OEM article for the Karzar SKU after bounded remote pass (not proof of non-existence).

## Recovery status distribution
```json
{json.dumps(counts, indent=2, ensure_ascii=False)}
```

## Safety (unchanged)
- 151 documentary `APPROVE_CATALOG_EXIT` rows and Owner journals 001–011 are immutable inputs.
- Category **154** and **27** industrial oils under **156** remain protected.
- No Workshop & Hand Tools catch-all; seven approved domains only for exception review.
- `PRODUCTION_MUTATION=NO` — no catalog, Hesabfa, deploy, or Owner auto-approval.

## Register SHA attestation
{recon["register_sha_attestation"]}
On-disk action register SHA256: `{recon["action_register_sha256_on_disk"]}`.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ACTION_REGISTER.is_file() or not PLAN_FA.is_file():
        raise RuntimeError("BLOCKED: missing canonical 111 action register or plan")

    register_rows = load_action_register()
    register_ids = {int(r["product_id"]) for r in register_rows}
    prior_index = build_prior_index(register_ids)

    access_date = datetime.now(UTC).strftime("%Y-%m-%d")
    matrix = build_recovery_matrix(register_rows, prior_index)
    sources = collect_source_rows(register_rows, access_date)
    physical = build_physical_manifest(register_rows, matrix)
    boundary = [boundary_assessment_row(reg, next(m for m in matrix if m["product_id"] == reg["product_id"])) for reg in register_rows]

    write_csv(out_dir / "01-EVIDENCE-RECOVERY-MATRIX-111.csv", list(matrix[0].keys()), matrix)
    write_csv(out_dir / "02-SOURCE-REGISTER.csv", list(sources[0].keys()) if sources else ["source_id"], sources)
    write_csv(
        out_dir / "03-PHYSICAL-EVIDENCE-COLLECTION-MANIFEST.csv",
        list(physical[0].keys()) if physical else ["product_id"],
        physical,
    )
    write_csv(out_dir / "05-SEVEN-DOMAIN-TECHNICAL-BOUNDARY-ASSESSMENT.csv", list(boundary[0].keys()), boundary)

    recon = fail_closed_reconciliation(register_rows, matrix)
    (out_dir / "04-OWNER-REVIEW-MEMO.md").write_text(owner_review_memo(matrix, recon), encoding="utf-8")

    identity = {
        "package_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_generation_git_head_sha": _git_sha(),
        "scope": "TX-OWNER-001 Phase 1B evidence recovery — 111 open Owner evidence requests",
        "base_merge_commit_pr531": "2e37c5de0768a9d85c142b5d9b1f631102aa615c",
        "canonical_action_register_path": str(ACTION_REGISTER.relative_to(ROOT)),
        "canonical_action_register_sha256": sha256_file(ACTION_REGISTER),
        "user_prompt_register_sha256": "bb723a79314314edc080c80c79616f3478e94082",
        "register_sha_attestation": recon["register_sha_attestation"],
        "approved_domain_codes": sorted(APPROVED_DOMAIN_CODES),
        "wave_counts": recon["wave_counts"],
        "workstream_counts": recon["workstream_counts"],
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
        "source_rows": len(sources),
        "physical_manifest_rows": len(physical),
        **{k: recon[k] for k in ("exact_oem_documentary_yes_count", "partial_family_yes_count", "remote_unresolved_count", "physical_stock_required_count")},
    }
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
