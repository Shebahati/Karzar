#!/usr/bin/env python3
"""TX-OWNER-001 remaining 11 NEEDS_MORE products — technical evidence package."""

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
from catalog_target.tx_owner_001_unresolved_11_research import (  # noqa: E402
    OEM_AND_MARKET_SOURCES,
    UNRESOLVED_11_PRODUCT_IDS,
    UNRESOLVED_11_PRODUCTS,
    evidence_gaps,
    sources_for_product,
)

OUT_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-unresolved-11-2026-10-17"
OWNER_PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
BASELINE_CENSUS = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15" / "02-PRODUCT-CATEGORY-CENSUS.csv"
PR499_REVIEW = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review" / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
BATCH_PATHS = (
    OWNER_PKG / "OWNER-AUTHORIZATION-BATCH-001-2026-10-17.csv",
    OWNER_PKG / "OWNER-AUTHORIZATION-BATCH-002-2026-10-17.csv",
    OWNER_PKG / "OWNER-AUTHORIZATION-BATCH-003-2026-10-17.csv",
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
    for pid in UNRESOLVED_11_PRODUCT_IDS:
        spec = UNRESOLVED_11_PRODUCTS[pid]
        srcs = sources_for_product(pid)
        rows.append(
            {
                "product_id": str(pid),
                "karzar_catalog_sku": spec["karzar_catalog_sku"],
                "preserved_title_fa": spec["preserved_title_fa"],
                "preserved_category_id": spec["preserved_category_id"],
                "cohort": spec["cohort"],
                "historical_pr499_proposal": spec["historical_pr499_proposal"],
                "historical_pr499_domain": spec["historical_pr499_domain"],
                "exact_manufacturer_identity_status": spec["exact_manufacturer_identity_status"],
                "exact_manufacturer_article": spec["exact_manufacturer_article"],
                "oem_family_evidence_verification": spec["oem_family_evidence_verification"],
                "karzar_product_oem_identity_verification": spec[
                    "karzar_product_oem_identity_verification"
                ],
                "proposed_application_class": spec["proposed_application_class"],
                "competing_interpretations": spec["competing_interpretations"],
                "confidence_level": spec["confidence_level"],
                "confidence_basis": spec["confidence_basis"],
                "confidence_scope_note": spec["confidence_scope_note"],
                "proposed_industrial_domain": spec["proposed_industrial_domain"],
                "agent_proposal_not_owner_approved": spec["agent_proposal"],
                "recommended_owner_review_option": spec["recommended_owner_review_option"],
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

    for path in (BASELINE_CENSUS, PR499_REVIEW, *BATCH_PATHS):
        if not path.is_file():
            raise RuntimeError(f"BLOCKED: missing input {path}")

    matrix = build_matrix()
    if len(matrix) != 11:
        raise RuntimeError(f"expected_11_matrix_rows got={len(matrix)}")

    write_csv(out_dir / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv", list(matrix[0].keys()), matrix)
    write_csv(
        out_dir / "02-OEM-SOURCE-REGISTER.csv",
        list(OEM_AND_MARKET_SOURCES[0].keys()),
        OEM_AND_MARKET_SOURCES,
    )
    gaps = evidence_gaps()
    write_csv(out_dir / "03-EVIDENCE-GAP-REGISTER.csv", list(gaps[0].keys()), gaps)

    identity = {
        "package_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_generation_git_head_sha": _git_sha(),
        "scope": "TX-OWNER-001 remaining 11 NEEDS_MORE technical evidence review",
        "frozen_baseline_product_census_csv_sha256": _sha256_file(BASELINE_CENSUS),
        "frozen_pr499_semantic_review_csv_sha256": _sha256_file(PR499_REVIEW),
        "owner_batch_001_sha256": _sha256_file(BATCH_PATHS[0]),
        "owner_batch_002_sha256": _sha256_file(BATCH_PATHS[1]),
        "owner_batch_003_sha256": _sha256_file(BATCH_PATHS[2]),
        "owner_batches_mutated": False,
        "product_ids": list(UNRESOLVED_11_PRODUCT_IDS),
        "post_research_effective_disposition_all_eleven": "NEEDS_MORE_EVIDENCE",
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
        "unique_product_ids": 11,
        "product_ids": list(UNRESOLVED_11_PRODUCT_IDS),
        "all_agent_proposals": "NEEDS_MORE_EVIDENCE",
        "all_exact_manufacturer_identity": "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH",
        "evidence_gap_rows": len(gaps),
    }
    (out_dir / "04-RECONCILIATION.json").write_text(
        json.dumps(recon, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_fa = """# خلاصه مالک — ۱۱ محصول نیازمند شواهد بیشتر (TX-OWNER-001)

**وضعیت:** فقط شواهد — بدون APPLY، بدون تغییر در ژورنال‌های تأیید Batch 001–003.

## گروه شیارزن / تیغ پرداخت (۹ محصول، دسته ۱۶۰)
- شناسه‌ها: 3090، 3091، 3093، 3095، 3096، 3097، 3098، 3099، 3101
- **شناسه سازنده دقیق:** `UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH` (SKUهای داخلی 3865–3876؛ بدون برند در سرشمار)
- **فرضیه کاربرد (اعتماد LOW):** تیغ/شیارزن فرز چوب و CNC — **نه** ابزار تراش فلز صنعتی مگر با OEM/عکس/ابعاد
- **پیشنهاد عامل (تأیید نشده):** `NEEDS_MORE_EVIDENCE`
- **اقدام پیشنهادی مالک:** `REQUEST_MORE_EVIDENCE` (برند، قطر شفت، عکس، فاکتور)

## گروه مایتی سون (۲ محصول)
- 5146 (SKU کاتالوگ NC4277)، 5147 (SKU کاتالوگ NC4299)
- OEM فقط **NC-4277Q** و **NC-4299Q** را مستند کرده — **بدون Q در کاتالوگ = بدون تطبیق دقیق**
- **پیشنهاد عامل:** `NEEDS_MORE_EVIDENCE`
- **اقدام پیشنهادی مالک:** `REQUEST_MORE_EVIDENCE` (پلاک مدل، فاکتور با Article No)

هیچ استثناء صنعتی یا خروج کاتالوگ به‌صورت خودکار تأیید نشده است.
"""
    (out_dir / "00-OWNER-SUMMARY-FA.md").write_text(summary_fa, encoding="utf-8")

    report = """# TX-OWNER-001 — Remaining 11 NEEDS_MORE technical evidence

**Status:** READY_FOR_OWNER_REVIEW — evidence only.

All eleven products retain **NEEDS_MORE_EVIDENCE** agent proposals. Exact Groz/M7/article identity remains **UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH** for every row.

Owner Batches **001**, **002**, and **003** are read-only inputs; not modified.
"""
    (out_dir / "FINAL_REPORT.md").write_text(report, encoding="utf-8")

    summary = {"status": "READY_FOR_OWNER_REVIEW", "matrix_rows": 11, "evidence_gap_rows": len(gaps)}
    (out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    names = [
        "00-PACKAGE-IDENTITY.json",
        "00-OWNER-SUMMARY-FA.md",
        "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv",
        "02-OEM-SOURCE-REGISTER.csv",
        "03-EVIDENCE-GAP-REGISTER.csv",
        "04-RECONCILIATION.json",
        "FINAL_REPORT.md",
        "SUMMARY.json",
    ]
    write_sha256sums(out_dir, names)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
