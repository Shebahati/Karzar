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
from typing import Any

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

import csv  # noqa: E402

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


def fail_closed_reconciliation() -> dict[str, Any]:
    """Verify cohort against frozen baseline, PR499, 176-risk register, Owner batches 001–004."""
    errors: list[str] = []

    with RISK_REGISTER.open(encoding="utf-8", newline="") as handle:
        risk_rows = list(csv.DictReader(handle))
    risk_by_id = {int(r["product_id"]): r for r in risk_rows}
    risk_p0_ids = {pid for pid, r in risk_by_id.items() if r.get("priority") == "P0_BOUNDARY_CHECK"}
    if risk_p0_ids != set(P0_PRODUCT_IDS):
        errors.append(f"p0_id_set_mismatch risk={sorted(risk_p0_ids)} package={P0_PRODUCT_IDS}")
    if len(risk_by_id) != 176:
        errors.append(f"risk_register_row_count expected=176 got={len(risk_by_id)}")

    with PR499_REVIEW.open(encoding="utf-8", newline="") as handle:
        pr499_rows = list(csv.DictReader(handle))
    if len(pr499_rows) != 262:
        errors.append(f"pr499_row_count expected=262 got={len(pr499_rows)}")
    pr499_by_id = {int(r["product_id"]): r for r in pr499_rows}

    census_by_id: dict[int, dict[str, str]] = {}
    with BASELINE_CENSUS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            census_by_id[int(row["product_id"])] = row
    if len(census_by_id) < 262:
        errors.append(f"baseline_census_unique_ids_lt_262 got={len(census_by_id)}")

    batch_overlap: list[str] = []
    for batch_path in BATCH_PATHS:
        with batch_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid = row.get("product_id", "")
                if pid and int(pid) in P0_PRODUCT_IDS:
                    batch_overlap.append(f"{batch_path.name}:{pid}")

    identity_checks: list[dict[str, str]] = []
    for pid in P0_PRODUCT_IDS:
        spec = P0_PRODUCTS[pid]
        census = census_by_id.get(pid)
        pr499 = pr499_by_id.get(pid)
        risk = risk_by_id.get(pid)
        check = {"product_id": str(pid), "status": "PASS"}
        if census is None:
            check["status"] = "FAIL"
            errors.append(f"census_missing product_id={pid}")
        else:
            if census.get("sku", "").strip() != spec["karzar_catalog_sku"]:
                check["status"] = "FAIL"
                errors.append(
                    f"sku_mismatch pid={pid} census={census.get('sku')} spec={spec['karzar_catalog_sku']}"
                )
            name = census.get("product_name", "").strip()
            if name != spec["preserved_title_fa"]:
                check["status"] = "FAIL"
                errors.append(f"title_mismatch pid={pid}")
            cat = str(census.get("category_id", "")).strip()
            if cat != spec["preserved_category_id"]:
                check["status"] = "FAIL"
                errors.append(f"category_mismatch pid={pid}")
        if pr499 is None:
            check["status"] = "FAIL"
            errors.append(f"pr499_missing pid={pid}")
        elif pr499.get("proposed_disposition") != spec["historical_pr499_proposal"]:
            check["status"] = "FAIL"
            errors.append(f"pr499_proposal_mismatch pid={pid}")
        if risk is None or risk.get("priority") != "P0_BOUNDARY_CHECK":
            check["status"] = "FAIL"
            errors.append(f"risk_p0_missing pid={pid}")
        identity_checks.append(check)

    if batch_overlap:
        errors.append(f"owner_batch_overlap={batch_overlap}")

    if errors:
        raise RuntimeError("RECONCILIATION_FAILED: " + "; ".join(errors))

    proposal_counts = {
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
    }
    expected_counts = {
        "CATALOG_EXIT_CANDIDATE": 16,
        "INDUSTRIAL_EXCEPTION_CANDIDATE": 1,
        "NEEDS_MORE_EVIDENCE": 2,
    }
    if proposal_counts != expected_counts:
        raise RuntimeError(f"proposal_count_mismatch got={proposal_counts} expected={expected_counts}")

    return {
        "status": "PASS",
        "p0_product_count": 19,
        "p0_product_ids": list(P0_PRODUCT_IDS),
        "unique_p0_ids_verified": len(set(P0_PRODUCT_IDS)) == 19,
        "frozen_baseline_census_rows_at_least": 262,
        "pr499_frozen_row_count": 262,
        "risk_register_row_count": 176,
        "risk_p0_ids": sorted(risk_p0_ids),
        "subset_of_176_risk_register": set(P0_PRODUCT_IDS) <= risk_p0_ids,
        "subset_of_262_frozen_baseline": all(pid in census_by_id for pid in P0_PRODUCT_IDS),
        "overlap_owner_batches_001_004": 0,
        "identity_checks_pass": sum(1 for c in identity_checks if c["status"] == "PASS"),
        "identity_checks_total": len(identity_checks),
        "post_research_proposal_counts": proposal_counts,
        "all_owner_decisions_pending": True,
    }


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

    recon = fail_closed_reconciliation()
    recon["evidence_gap_rows"] = len(gaps)
    (out_dir / "05-RECONCILIATION.json").write_text(
        json.dumps(recon, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary_fa = """# خلاصه مالک — P0 مرز صنعتی (۱۹ محصول)

**وضعیت:** `READY_FOR_OWNER_REVIEW` — فقط شواهد؛ بدون APPLY؛ Batch 001–004 بدون تغییر.

## تفکیک سطح شواهد (نه همه «اطمینان بالا»)
- **تطبیق دقیق OEM (صفحه mighty-seven.com):** بیشتر مدل‌های SB/SG/SP/SV/SW/SZ و SY-2001M به‌عنوان **مرجع کاتالوگی** — هویت فیزیکی انبار جداگانه تأیید نشده مگر خلافش ذکر شود.
- **خانواده توزیع‌کننده/بازار (Groz SA/*):** فقط IndiaMART/FastenersWEB — **نه** اثبات مستقیم OEM groz-tools.com برای SKU 3106.
- **مرجع نزدیک مدل (QE98L≈QE-98L):** لیست‌های توزیع‌کننده — **موجودی فیزیکی 5227 تأیید نشده**.
- **مرجع کلاس کاربرد (کلمپ موازی):** منبع تحریریه‌ای — **نه** تأیید سازنده.

## گروز (۴ محصول)
| شناسه | SKU | جمع‌بندی | پیشنهاد عامل (تأیید نشده) |
|-------|-----|----------|---------------------------|
| 3008 | 3104 | کلمپ موازی بدون برند؛ fit دامنه Workholding **UNPROVEN** | `NEEDS_MORE_EVIDENCE` |
| 3009 | 3106 | فرضیه Toolholding از عنوان+Groz؛ مقاله Groz **حل‌نشده** | `INDUSTRIAL_EXCEPTION_CANDIDATE` (فرضیه فقط) |
| 3010 | 3109 | خانواده WD/* روی groz-tools.com؛ خارج از ۷ دامنه | `CATALOG_EXIT_CANDIDATE` |
| 3184 | 4318 | خانواده شابر ES/*؛ خارج از ۷ دامنه | `CATALOG_EXIT_CANDIDATE` |

## مایتی سون (۱۵ محصول)
- **5227 QE98L:** تراز حبابی — **نه** اندازه‌سنجی (Metrology)؛ مرجع مدل نزدیک؛ موجودی تأیید نشده → خروج پیشنهادی با شواهد توزیع‌کننده.
- **5259–5261:** بادزن تایر OEM — نه اندازه‌سنجی صنعتی.
- **5267–5268:** کیت/پمپ روغن‌کاری — تجهیزات، نه سیال صنعتی (Metalworking Fluids).
- **5285–5289:** بالانسر فنری — لوازم کارگاه (OEM دقیق روی صفحه M7).
- **5295–5298:** FRL/لوبریکیتور خط باد — لوازم شیرفشار (OEM دقیق).
- **5301 SY-2001M:** OEM = آداپتور SY-2001M؛ **SY-2002M جدا**؛ ناسازگی عنوان «رگولاتور» → `NEEDS_MORE_EVIDENCE` (بدون اصلاح عنوان در این PR).
- **5302 SZ212A:** رگولاتور خط ابزار — OEM دقیق؛ خروج پیشنهادی.

**پیشنهادهای پس از تحقیق (۱۹):** خروج ۱۶ | استثناء فرضی ۱ (3009) | شواهد بیشتر ۲ (3008، 5301).

هیچ تصمیم مالک به‌صورت خودکار ثبت نشده است.
"""
    (out_dir / "00-OWNER-SUMMARY-FA.md").write_text(summary_fa, encoding="utf-8")

    report = """# TX-OWNER-001 — P0 industrial boundary research (19 SKUs)

**Status:** READY_FOR_OWNER_REVIEW — evidence only.

SKU-specific OEM research for PR #507 **P0_BOUNDARY_CHECK** cohort. Owner Batches **001–004** are read-only inputs.

Post-research agent proposals are **not** Owner approvals. `NEEDS_MORE_EVIDENCE` rows: **3008** (brandless parallel clamp), **5301** (title vs OEM adaptor class). Reconciliation is fail-closed against frozen baseline, PR499, 176-risk register, and Owner Batches 001–004.
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
