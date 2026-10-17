#!/usr/bin/env python3
"""TX-OWNER-001 Groz special-case technical resolution package (evidence only)."""

from __future__ import annotations

import argparse
import hashlib
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
from catalog_target.tx_owner_001_groz_special_case_research import (  # noqa: E402
    GROZ_OEM_SOURCES,
    SPECIAL_CASE_PRODUCTS,
    sources_for_product,
)

OUT_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-special-case-groz-2026-10-17"
BASELINE_CENSUS = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15" / "02-PRODUCT-CATEGORY-CENSUS.csv"
PR499_REVIEW = (
    ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review" / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
)
BATCH_001 = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
    / "OWNER-AUTHORIZATION-BATCH-001-2026-10-17.csv"
)
BATCH_002 = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
    / "OWNER-AUTHORIZATION-BATCH-002-2026-10-17.csv"
)

PRODUCT_IDS = (2915, 3238)


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(out_dir: Path, names: list[str]) -> None:
    lines = [
        f"{_sha256_file(out_dir / name)}  {name}"
        for name in sorted(names)
        if (out_dir / name).is_file()
    ]
    (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_evidence_matrix() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in PRODUCT_IDS:
        spec = SPECIAL_CASE_PRODUCTS[pid]
        srcs = sources_for_product(pid)
        rows.append(
            {
                "product_id": str(pid),
                "karzar_catalog_sku": spec["karzar_catalog_sku"],
                "manufacturer_code_in_census": spec["manufacturer_code_in_census"],
                "preserved_title_fa": spec["preserved_title_fa"],
                "preserved_category_id": spec["preserved_category_id"],
                "historical_pr499_proposal": spec["historical_pr499_proposal"],
                "historical_pr499_domain": spec["historical_pr499_domain"],
                "exact_product_identity_statement": spec["application_primary"],
                "competing_interpretations": spec["competing_interpretations"],
                "confidence_level": spec["confidence_level"],
                "confidence_basis": spec["confidence_basis"],
                "proposed_industrial_domain": spec["proposed_industrial_domain"],
                "agent_proposal_not_owner_approved": spec["agent_proposal"],
                "unresolved_questions": spec["unresolved_questions"],
                "oem_source_ids": "|".join(s["source_id"] for s in srcs),
                "oem_source_urls": "|".join(s["source_url"] for s in srcs),
                "allowed_owner_options": spec["owner_options"],
                "owner_decision": "",
                "authorization_status": "PENDING",
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for path in (BASELINE_CENSUS, PR499_REVIEW, BATCH_001, BATCH_002):
        if not path.is_file():
            raise RuntimeError(f"BLOCKED: missing input {path}")

    matrix = build_evidence_matrix()
    write_csv(out_dir / "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv", list(matrix[0].keys()), matrix)
    write_csv(
        out_dir / "02-OEM-SOURCE-REGISTER.csv",
        list(GROZ_OEM_SOURCES[0].keys()),
        GROZ_OEM_SOURCES,
    )

    identity = {
        "package_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_generation_git_head_sha": _git_sha(),
        "scope": "TX-OWNER-001 special-case technical resolution (Groz 2915, 3238)",
        "frozen_baseline_census_csv_sha256": _sha256_file(BASELINE_CENSUS),
        "frozen_pr499_review_csv_sha256": _sha256_file(PR499_REVIEW),
        "owner_batch_001_sha256": _sha256_file(BATCH_001),
        "owner_batch_002_sha256": _sha256_file(BATCH_002),
        "owner_batches_mutated": False,
        "product_ids": list(PRODUCT_IDS),
        "safety": {
            "PRODUCTION_MUTATION": "NO",
            "CATALOG_EXIT_APPLY": "NO",
            "CATEGORY_MUTATION": "NO",
            "PRODUCT_MUTATION": "NO",
            "MASTER_MANIFEST_REWRITE": "NO",
            "OWNER_BATCH_JOURNALS_TOUCHED": "NO",
        },
    }
    (out_dir / "00-PACKAGE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    recon = {
        "product_count": len(PRODUCT_IDS),
        "product_ids": list(PRODUCT_IDS),
        "karzar_catalog_skus": {str(pid): SPECIAL_CASE_PRODUCTS[pid]["karzar_catalog_sku"] for pid in PRODUCT_IDS},
        "sku_not_manufacturer_model_note": (
            "Karzar catalog SKUs 2064 and 4457 are internal identifiers; "
            "not inferred to equal Groz Ord Nr. or article numbers."
        ),
        "historical_pr499_unchanged": True,
    }
    (out_dir / "03-RECONCILIATION.json").write_text(
        json.dumps(recon, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    options_md = """# Owner decision options (not pre-approved)

Evidence-only package for **Product 2915** (SKU **2064**) and **Product 3238** (SKU **4457**).

Batches **001** and **002** owner authorization journals are **unchanged**.

## Product 2915 — Groz blade (تیغچه رنده تراشکاری)

| Option | Meaning |
|--------|---------|
| `APPROVE_INDUSTRIAL_EXCEPTION_KZ.DOM.CUTTING` | Keep in catalog under explicit Cutting Tools industrial exception (no category APPLY in this PR). |
| `REJECT_INDUSTRIAL_EXCEPTION_APPROVE_CATALOG_EXIT` | Confirm TX-OWNER-001 catalog exit (workshop/woodworking scope). |
| `REQUEST_MORE_EVIDENCE` | Require dimensions, Groz article, or photo before decision. |
| `DEFER_DECISION` | Hold pending procurement/OEM confirmation. |

## Product 3238 — Groz jack (جک ماشینکاری)

| Option | Meaning |
|--------|---------|
| `APPROVE_INDUSTRIAL_EXCEPTION_KZ.DOM.WORKHOLDING` | Treat as machinist setup/workholding exception (if physical unit matches setup jack class). |
| `APPROVE_CATALOG_EXIT` | Confirm catalog exit as general workshop/hand tool. |
| `REQUEST_MORE_EVIDENCE` | Require photo, load rating, Groz article (e.g. MJ/01) before decision. |
| `DEFER_DECISION` | Hold pending verification. |

All `owner_decision` fields remain **blank**; `authorization_status` **PENDING**.
"""
    (out_dir / "04-OWNER-DECISION-OPTIONS.md").write_text(options_md, encoding="utf-8")

    report = """# TX-OWNER-001 — Groz special-case technical resolution

**Status:** EVIDENCE_ONLY — no APPLY, no Owner journal mutation.

## Summary

| Product ID | Karzar SKU | PR #499 proposal | Research agent proposal | Proposed domain | Confidence |
|------------|------------|------------------|-------------------------|-----------------|------------|
| 2915 | 2064 | INDUSTRIAL_EXCEPTION_CANDIDATE | INDUSTRIAL_EXCEPTION_CANDIDATE | KZ.DOM.CUTTING | MEDIUM |
| 3238 | 4457 | OWNER_DECISION_REQUIRED | INDUSTRIAL_EXCEPTION_CANDIDATE | KZ.DOM.WORKHOLDING | MEDIUM |

SKU **4457** on product **3238** must not be confused with unrelated catalog product **4457** (San OU morse taper) or Groz hydraulic jack order numbers.

## Safety

No production, catalog, category, Hesabfa, or manifest changes. Owner batches 001/002 preserved.
"""
    (out_dir / "FINAL_REPORT.md").write_text(report, encoding="utf-8")

    summary = {"status": "READY_FOR_OWNER_REVIEW", "matrix_rows": len(matrix), "oem_sources": len(GROZ_OEM_SOURCES)}
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    names = [
        "00-PACKAGE-IDENTITY.json",
        "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv",
        "02-OEM-SOURCE-REGISTER.csv",
        "03-RECONCILIATION.json",
        "04-OWNER-DECISION-OPTIONS.md",
        "FINAL_REPORT.md",
        "SUMMARY.json",
    ]
    write_sha256sums(out_dir, names)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
