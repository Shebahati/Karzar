#!/usr/bin/env python3
"""TX-OWNER-001 P0 industrial boundary research — 19-product evidence package."""

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
from catalog_target.tx_owner_001_p0_industrial_boundary_research import (  # noqa: E402
    OEM_SOURCES,
    OWNER_OPTIONS,
    P0_PRODUCT_IDS,
    P0_PRODUCTS,
    evidence_gaps,
    industrial_boundary_rows,
    sources_for_product,
)

OUT_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-p0-industrial-boundary-2026-10-17"
OWNER_PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
RISK_TRIAGE = (
    ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-low-confidence-risk-triage-2026-10-17"
)
BASELINE_CENSUS = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15" / "02-PRODUCT-CATEGORY-CENSUS.csv"
PR499_REVIEW = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review" / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
RISK_REGISTER = RISK_TRIAGE / "01-PRIORITIZED-RISK-REGISTER-176.csv"
BATCH_PATHS = tuple(
    OWNER_PKG / f"OWNER-AUTHORIZATION-BATCH-00{i}-2026-10-17.csv" for i in range(1, 5)
)


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


def build_matrix() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in P0_PRODUCT_IDS:
        spec = P0_PRODUCTS[pid]
        srcs = sources_for_product(pid)
        rows.append(
            {
                "product_id": str(pid),
                "karzar_catalog_sku": spec["karzar_catalog_sku"],
                "preserved_title_fa": spec["preserved_title_fa"],
                "preserved_brand": spec["preserved_brand"],
                "preserved_category_id": spec["preserved_category_id"],
                "research_priority_code": spec["research_priority"],
                "historical_pr499_proposal": spec["historical_pr499_proposal"],
                "historical_pr499_evidence_basis": spec["historical_pr499_evidence_basis"],
                "new_technical_research_finding": spec["new_technical_research_finding"],
                "exact_manufacturer_identity_status": spec["exact_manufacturer_identity_status"],
                "exact_manufacturer_article": spec["exact_manufacturer_article"],
                "oem_match_classification": spec["oem_match_classification"],
                "karzar_product_oem_identity_verification": spec["karzar_product_oem_identity_verification"],
                "proposed_application_class": spec["proposed_application_class"],
                "competing_interpretations": spec["competing_interpretations"],
                "industrial_domain_hypothesis": spec.get("industrial_domain_hypothesis", ""),
                "approved_domain_fit_assessment": spec["approved_domain_fit_assessment"],
                "confidence_level": spec["confidence_level"],
                "confidence_basis": spec["confidence_basis"],
                "confidence_scope_note": spec["confidence_scope_note"],
                "post_research_agent_proposal_not_owner_approved": spec["post_research_agent_proposal"],
                "recommended_owner_review_option": spec["recommended_owner_review_option"],
                "unresolved_questions": spec["unresolved_questions"],
                "oem_source_ids": "|".join(s["source_id"] for s in srcs),
                "oem_source_urls": "|".join(s["source_url"] for s in srcs),
                "allowed_owner_options": OWNER_OPTIONS,
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

    for path in (BASELINE_CENSUS, PR499_REVIEW, RISK_REGISTER, *BATCH_PATHS):
        if not path.is_file():
            raise RuntimeError(f"BLOCKED: missing input {path}")

    matrix = build_matrix()
    if len(matrix) != 19:
        raise RuntimeError(f"expected_19_matrix_rows got={len(matrix)}")

    boundary = industrial_boundary_rows()
    gaps = evidence_gaps()

    write_csv(
        out_dir / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv",
        list(matrix[0].keys()),
        matrix,
    )
    write_csv(out_dir / "02-OEM-SOURCE-REGISTER.csv", list(OEM_SOURCES[0].keys()), OEM_SOURCES)
    write_csv(out_dir / "03-EVIDENCE-GAP-REGISTER.csv", list(gaps[0].keys()), gaps)
    write_csv(
        out_dir / "04-INDUSTRIAL-BOUNDARY-ANALYSIS.csv",
        list(boundary[0].keys()),
        boundary,
    )

    identity = {
        "package_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_generation_git_head_sha": _git_sha(),
        "scope": "TX-OWNER-001 P0 industrial boundary research (19 SKUs)",
        "frozen_baseline_product_census_csv_sha256": _sha256_file(BASELINE_CENSUS),
        "frozen_pr499_semantic_review_csv_sha256": _sha256_file(PR499_REVIEW),
        "frozen_pr507_risk_register_csv_sha256": _sha256_file(RISK_REGISTER),
        "owner_batch_001_sha256": _sha256_file(BATCH_PATHS[0]),
        "owner_batch_002_sha256": _sha256_file(BATCH_PATHS[1]),
        "owner_batch_003_sha256": _sha256_file(BATCH_PATHS[2]),
        "owner_batch_004_sha256": _sha256_file(BATCH_PATHS[3]),
        "owner_batches_mutated": False,
        "product_ids": list(P0_PRODUCT_IDS),
        "approved_domain_codes": sorted(
            {
                "KZ.DOM.METROLOGY",
                "KZ.DOM.CUTTING",
                "KZ.DOM.TOOLHOLDING",
                "KZ.DOM.WORKHOLDING",
                "KZ.DOM.MACHINES",
                "KZ.DOM.THREAD_REPAIR",
                "KZ.DOM.FLUIDS",
            }
        ),
        "safety": {
            "PRODUCTION_MUTATION": "NO",
            "CATALOG_EXIT_APPLY": "NO",
            "INDUSTRIAL_EXCEPTION_APPLY": "NO",
            "REHOME_APPLY": "NO",
            "CATEGORY_MUTATION": "NO",
            "PRODUCT_MUTATION": "NO",
            "MASTER_MANIFEST_REWRITE": "NO",
            "OWNER_BATCH_JOURNALS_TOUCHED": "NO",
            "OWNER_DECISION_AUTO_APPROVAL": "NO",
        },
    }
    (out_dir / "00-PACKAGE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    recon = {
        "p0_product_count": 19,
        "p0_product_ids": list(P0_PRODUCT_IDS),
        "subset_of_176_risk_register": True,
        "subset_of_262_frozen_baseline": True,
        "overlap_owner_batches_001_004": 0,
        "post_research_proposal_counts": {
            "CATALOG_EXIT_CANDIDATE": sum(
                1 for p in P0_PRODUCT_IDS if P0_PRODUCTS[p]["post_research_agent_proposal"] == "CATALOG_EXIT_CANDIDATE"
            ),
            "INDUSTRIAL_EXCEPTION_CANDIDATE": sum(
                1
                for p in P0_PRODUCT_IDS
                if P0_PRODUCTS[p]["post_research_agent_proposal"] == "INDUSTRIAL_EXCEPTION_CANDIDATE"
            ),
            "NEEDS_MORE_EVIDENCE": sum(
                1 for p in P0_PRODUCT_IDS if P0_PRODUCTS[p]["post_research_agent_proposal"] == "NEEDS_MORE_EVIDENCE"
            ),
        },
        "evidence_gap_rows": len(gaps),
        "all_owner_decisions_pending": True,
    }
    (out_dir / "05-RECONCILIATION.json").write_text(
        json.dumps(recon, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_fa = """# خلاصه مالک — P0 مرز صنعتی (۱۹ محصول)

**وضعیت:** `READY_FOR_OWNER_REVIEW` — فقط شواهد؛ بدون APPLY؛ Batch 001–004 بدون تغییر.

## گروز (۴ محصول)
| شناسه | SKU | جمع‌بندی شواهد | پیشنهاد عامل (تأیید نشده) |
|-------|-----|----------------|---------------------------|
| 3008 | 3104 | کلمپ موازی بدون برند — بیشتر کارگاهی/نجاری؛ نه Workholding صنعتی اثبات‌شده | خروج کاتالوگ + `REQUEST_MORE_EVIDENCE` |
| 3009 | 3106 | دنباله اره‌فرز گروز — خانواده SA/* Toolholding؛ SKU داخلی ≠ مقاله Groz | استثناء صنعتی محتمل + شواهد مقاله |
| 3010 | 3109 | صاف‌کن سنگ گروز WD/* — ابزار نگهداری سنگ، خارج از ۷ دامنه | خروج کاتالوگ |
| 3184 | 4318 | شابر دستی گروز — فیتینگ دقیق؛ خارج از ۷ دامنه تأیید‌شده | خروج کاتالوگ (بازبینی استثناء در صورت سیاست مالک) |

## مایتی سون (۱۵ محصول)
- **5227 QE98L:** تراز حبابی روی دریل — **نه** متالورژی؛ خروج کاتالوگ.
- **5259–5261 SB201/SB423/SB710:** بادزن/گیج لاستیک OEM — خدمات تایر، نه متالورژی.
- **5267 SG101:** کیت روغن/گریس ابزار بادی — تجهیزات، نه سیال صنعتی.
- **5268 SG400:** پمپ گریس بادی ۴۰۰ سی‌سی — تجهیزات پخش.
- **5285–5289 SP102/104/105:** بالانسر فنری ابزار بادی — لوازم کارگاه.
- **5295–5297 SV1360/2220/2380:** واحد مراقبت/FRL خط باد — لوازم شیر فشرده.
- **5298 SW12:** مینی لوبریکیتور خط باد.
- **5301 SY-2001M:** OEM = آداپتور چرخان ۳۶۰° — **عنوان کاتالوگ «رگولاتور» ناسازگار** → `REQUEST_MORE_EVIDENCE`.
- **5302 SZ212A:** رگولاتور خط ابزار بادی — خروج کاتالوگ.

هیچ تصمیم مالک به‌صورت خودکار ثبت نشده است.
"""
    (out_dir / "00-OWNER-SUMMARY-FA.md").write_text(summary_fa, encoding="utf-8")

    report = """# TX-OWNER-001 — P0 industrial boundary research (19 SKUs)

**Status:** READY_FOR_OWNER_REVIEW — evidence only.

SKU-specific OEM research for PR #507 **P0_BOUNDARY_CHECK** cohort. Owner Batches **001–004** are read-only inputs.

Post-research agent proposals are **not** Owner approvals. One row (`5301`) retains `NEEDS_MORE_EVIDENCE` due to catalog title vs OEM product-class mismatch.
"""
    (out_dir / "FINAL_REPORT.md").write_text(report, encoding="utf-8")

    summary = {
        "status": "READY_FOR_OWNER_REVIEW",
        "matrix_rows": 19,
        "evidence_gap_rows": len(gaps),
    }
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    names = [
        "00-PACKAGE-IDENTITY.json",
        "00-OWNER-SUMMARY-FA.md",
        "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv",
        "02-OEM-SOURCE-REGISTER.csv",
        "03-EVIDENCE-GAP-REGISTER.csv",
        "04-INDUSTRIAL-BOUNDARY-ANALYSIS.csv",
        "05-RECONCILIATION.json",
        "FINAL_REPORT.md",
        "SUMMARY.json",
    ]
    write_sha256sums(out_dir, names)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
