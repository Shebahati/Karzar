#!/usr/bin/env python3
"""Generate TX-OWNER-001 product-level semantic review artifacts (read-only)."""

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
from catalog_target.tx_owner_001_semantic_review import (  # noqa: E402
    OWNER_QUEUE_FIELDS,
    PRIMARY_DISPOSITIONS,
    REVIEW_FIELDS,
    build_owner_queue,
    build_product_reviews,
    disposition_counts,
    external_source_register_rows,
    industrial_exception_primary_count,
    load_cohort_products,
    proposed_domain_counts,
    semantic_conflict_count,
    validate_primary_partition,
)

BASELINE_DIR = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15"
OUT_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review"
EXPECTED_PR_HEAD = "156e46e4c4d23e470c93108b1d2009571883f969"
CENSUS_COLLECTED_AT = "2026-10-15T09:34:39Z"


def _git_sha() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(out_dir: Path, names: list[str]) -> None:
    lines: list[str] = []
    for name in sorted(names):
        path = out_dir / name
        if path.is_file():
            lines.append(f"{_sha256_file(path)}  {name}")
    (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    head = _git_sha()
    merge_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_PR_HEAD, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    if merge_check.returncode != 0:
        raise RuntimeError("BLOCKED: baseline PR #498 head not in current branch history")

    product_path = BASELINE_DIR / "02-PRODUCT-CATEGORY-CENSUS.csv"
    category_path = BASELINE_DIR / "01-CATEGORY-CENSUS.csv"
    cohort = load_cohort_products(product_path, category_census_path=category_path)
    reviews = build_product_reviews(cohort)
    validate_primary_partition(reviews)

    identity = {
        "review_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository_branch": "audit/taxonomy-phase1b-tx-owner-001-product-review",
        "git_head_sha": head,
        "baseline_pr_498_reviewed_head": EXPECTED_PR_HEAD,
        "historical_evidence": {
            "baseline_audit_dir": str(BASELINE_DIR),
            "product_census_csv": str(product_path),
            "product_census_sha256": _sha256_file(product_path),
            "collected_at_utc": CENSUS_COLLECTED_AT,
            "disclaimer": (
                "Evidence reflects the preserved 2026-10-15 production census observation "
                "window; it is not asserted as today's live catalog state."
            ),
        },
        "governance": [
            "docs/architecture/taxonomy-v1/01-TAXONOMY-CONSTITUTION-V1.md",
            "docs/architecture/taxonomy-v1/13-STEWARD-DECISION-TX-OWNER-001.md",
            "docs/architecture/taxonomy-v1/12-PHASE-1B-ENTRY-GATE.md",
        ],
        "production_mutation": "NO",
        "catalog_exit_apply": "NO",
        "rehome_apply": "NO",
    }
    (out_dir / "00-BASELINE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_csv(out_dir / "01-262-PRODUCT-SEMANTIC-REVIEW.csv", REVIEW_FIELDS, reviews)

    by_disp = {d: [r for r in reviews if r["proposed_disposition"] == d] for d in PRIMARY_DISPOSITIONS}
    write_csv(out_dir / "02-CATALOG-EXIT-CANDIDATES.csv", REVIEW_FIELDS, by_disp["CATALOG_EXIT_CANDIDATE"])
    write_csv(
        out_dir / "03-INDUSTRIAL-EXCEPTION-CANDIDATES.csv",
        REVIEW_FIELDS,
        by_disp["INDUSTRIAL_EXCEPTION_CANDIDATE"],
    )
    write_csv(out_dir / "04-INSUFFICIENT-EVIDENCE.csv", REVIEW_FIELDS, by_disp["NEEDS_MORE_EVIDENCE"])
    queue = build_owner_queue(reviews)
    write_csv(out_dir / "05-OWNER-DECISION-QUEUE.csv", OWNER_QUEUE_FIELDS, queue)

    cat_props: list[dict[str, str]] = []
    with category_path.open(encoding="utf-8", newline="") as handle:
        import csv

        for row in csv.DictReader(handle):
            cid = int(row["category_id"])
            if cid not in {157, 158, 159, 160}:
                continue
            subset = [r for r in reviews if int(r["current_category_id"]) == cid]
            disp = disposition_counts(subset)
            cat_props.append(
                {
                    "category_id": str(cid),
                    "category_name": row["name"],
                    "full_path": row["full_path"],
                    "direct_live_products": row["direct_product_count"],
                    "descendant_live_products": row["descendant_product_count"],
                    "proposed_category_disposition": "DEPRECATE_REMOVE_PER_TX_OWNER_001",
                    "catalog_exit_candidates": str(disp.get("CATALOG_EXIT_CANDIDATE", 0)),
                    "industrial_exception_or_conflict": str(
                        disp.get("INDUSTRIAL_EXCEPTION_CANDIDATE", 0)
                        + disp.get("SEMANTIC_CONFLICT", 0)
                    ),
                    "owner_decision_required": str(disp.get("OWNER_DECISION_REQUIRED", 0)),
                    "needs_more_evidence": str(disp.get("NEEDS_MORE_EVIDENCE", 0)),
                    "notes": (
                        "Category-level DEPRECATE_REMOVE is TX-OWNER-001 target law; "
                        "product-level proposals are in 01-262 CSV."
                    ),
                }
            )
    write_csv(
        out_dir / "06-CATEGORY-DISPOSITION-PROPOSALS.csv",
        list(cat_props[0].keys()),
        cat_props,
    )

    evidence_register = [
        {
            "evidence_id": "EV-001",
            "source": "audit/taxonomy-phase1b-baseline-2026-10-15/02-PRODUCT-CATEGORY-CENSUS.csv",
            "class": "PRESERVED_PRODUCTION_CENSUS",
            "collected_at_utc": CENSUS_COLLECTED_AT,
            "used_for": "SKU identity, title, category assignment, commerce flags",
            "limitations": "No long description or specifications JSON in export",
        },
        {
            "evidence_id": "EV-002",
            "source": "docs/architecture/taxonomy-v1/13-STEWARD-DECISION-TX-OWNER-001.md",
            "class": "KARZAR-GOVERNANCE-DECISION",
            "collected_at_utc": "2026-09-27",
            "used_for": "Scope rejection Workshop/Hand/Woodworking; exit vs rehome rules",
            "limitations": "APPROVED target law; not production APPLY",
        },
        {
            "evidence_id": "EV-003",
            "source": "scripts/catalog_target/tx_owner_001_semantic_review.py",
            "class": "ENGINEERING-INFERENCE",
            "collected_at_utc": identity["review_generated_at_utc"],
            "used_for": "Deterministic title-based classification patterns",
            "limitations": "Inference from Persian/English titles; not OEM datasheet unless cited",
        },
    ]
    write_csv(
        out_dir / "07-EVIDENCE-REGISTER.csv",
        list(evidence_register[0].keys()),
        evidence_register,
    )
    ext_rows = external_source_register_rows()
    write_csv(
        out_dir / "09-EXTERNAL-SOURCE-REGISTER.csv",
        list(ext_rows[0].keys()),
        ext_rows,
    )

    counts = disposition_counts(reviews)
    reconciliation = {
        "unique_product_count": len(reviews),
        "expected_unique_product_count": 262,
        "category_158_products": sum(1 for r in reviews if r["current_category_id"] == "158"),
        "category_160_products": sum(1 for r in reviews if r["current_category_id"] == "160"),
        "disposition_counts": counts,
        "industrial_exception_primary_count": industrial_exception_primary_count(reviews),
        "semantic_conflict_count": semantic_conflict_count(reviews),
        "proposed_domain_tag_counts": proposed_domain_counts(reviews),
        "owner_queue_row_count": len(queue),
        "mutually_exclusive_primary_disposition": True,
        "excluded_category_154_bulk": True,
        "excluded_category_156_industrial_oils": True,
        "checksum_product_census": identity["historical_evidence"]["product_census_sha256"],
    }
    (out_dir / "08-COHORT-RECONCILIATION.json").write_text(
        json.dumps(reconciliation, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    domain_counts = proposed_domain_counts(reviews)
    prev_correction_note = {
        "prior_review_head": "d0ad0a4107af619483f73b220e63a0b0a8f893d7",
        "prior_disposition_counts": {
            "CATALOG_EXIT_CANDIDATE": 204,
            "SEMANTIC_CONFLICT": 35,
            "INDUSTRIAL_EXCEPTION_CANDIDATE": 15,
            "OWNER_DECISION_REQUIRED": 8,
            "NEEDS_MORE_EVIDENCE": 0,
        },
    }

    summary = {
        "status": "READY_FOR_OWNER_REVIEW",
        "population_unique_products": 262,
        "disposition_counts": counts,
        "industrial_exception_primary_count": industrial_exception_primary_count(reviews),
        "semantic_conflict_primary_count": semantic_conflict_count(reviews),
        "proposed_domain_tag_counts": domain_counts,
        "owner_queue_rows": len(queue),
        "correction_delta_note": prev_correction_note,
        "category_scope": {
            "157": {"direct": 0, "role": "parent_hand_tools"},
            "158": {"direct": 196},
            "159": {"direct": 0, "role": "parent_woodworking"},
            "160": {"direct": 66},
        },
        "safety": {
            "PRODUCTION_MUTATION": "NO",
            "PRODUCT_MUTATION": "NO",
            "CATALOG_EXIT_APPLY": "NO",
            "REHOME_APPLY": "NO",
        },
    }
    (out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    fa_summary = f"""
## خلاصه اجرایی (فارسی)

این موج **بررسی معنایی محصول‌محور TX-OWNER-001** است و بر اساس سرشمار تاریخ‌دار **2026-10-15T09:34:39Z** انجام شده؛ وضعیت زندهٔ امروز کاتالوگ را اثبات نمی‌کند.

- **جمعیت بررسی:** {len(reviews)} محصول یکتا در دسته‌های ۱۵۸ و ۱۶۰.
- **پیشنهاد خروج از کاتالوگ:** {counts['CATALOG_EXIT_CANDIDATE']} مورد.
- **تعارض معنایی (primary):** {counts['SEMANTIC_CONFLICT']} مورد.
- **استثناء صنعتی (primary):** {counts['INDUSTRIAL_EXCEPTION_CANDIDATE']} مورد — **بدون مجوز rehome**.
- **نیاز به تصمیم مالک (primary):** {counts['OWNER_DECISION_REQUIRED']} مورد.
- **شواهد ناکافی:** {counts['NEEDS_MORE_EVIDENCE']} مورد.
- **صف تأیید مالک:** {len(queue)} ردیف (شامل همهٔ پیشنهادها).

هیچ APPLY، حذف، یا انتقال خودکار انجام نشده است. گام بعدی: تأیید مالک روی پیشنهادهای سطح محصول.
"""

    report = f"""# TX-OWNER-001 — Product-level semantic review

{fa_summary}

## Identity

- Git HEAD: `{head}`
- Baseline PR #498 reviewed HEAD: `{EXPECTED_PR_HEAD}`
- Historical census: `{product_path}` (collected {CENSUS_COLLECTED_AT})

## Disposition distribution

{json.dumps(counts, indent=2)}

## Owner decision queue

Full queue: `05-OWNER-DECISION-QUEUE.csv` ({len(queue)} rows). Industrial exceptions are **not** auto-approved.

## Correction notes (vs d0ad0a41)

- Removed broad metalworking inference from CNC/تیغ/شیارزن tokens alone.
- Mighty Seven QA-210/211 documented as Air Die Grinders (OEM) → workshop exit, not Toolholding.
- BladeKat-style router bits treated as woodworking CNC tooling (exit), not Cutting Tools inserts.
- Grooving/finishing blades without OEM context → NEEDS_MORE_EVIDENCE.

## Safety

All proposals are review-only. No production mutation, no manifest rewrite, no megamenu/SEO changes.

## Next gate

Owner approval of proposed product-level dispositions before any Phase 1B APPLY authorization.
"""
    (out_dir / "FINAL_REPORT.md").write_text(report, encoding="utf-8")

    artifact_names = [
        "00-BASELINE-IDENTITY.json",
        "01-262-PRODUCT-SEMANTIC-REVIEW.csv",
        "02-CATALOG-EXIT-CANDIDATES.csv",
        "03-INDUSTRIAL-EXCEPTION-CANDIDATES.csv",
        "04-INSUFFICIENT-EVIDENCE.csv",
        "05-OWNER-DECISION-QUEUE.csv",
        "06-CATEGORY-DISPOSITION-PROPOSALS.csv",
        "07-EVIDENCE-REGISTER.csv",
        "09-EXTERNAL-SOURCE-REGISTER.csv",
        "08-COHORT-RECONCILIATION.json",
        "SUMMARY.json",
        "FINAL_REPORT.md",
    ]
    write_sha256sums(out_dir, artifact_names)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
