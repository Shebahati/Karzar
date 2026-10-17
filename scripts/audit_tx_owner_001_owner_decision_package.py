#!/usr/bin/env python3
"""Generate TX-OWNER-001 Owner decision package (read-only, no APPLY)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_baseline import write_csv  # noqa: E402
from catalog_target.tx_owner_001_owner_post_research import (  # noqa: E402
    M7_POST_RESEARCH_EXIT_IDS,
    PR499_ANCHOR_DISPOSITIONS,
    POST_RESEARCH_EXPECTED,
    disposition_counts,
    enrich_row,
    historical_pr499_proposal,
    post_research_proposal,
    validate_post_research_counts,
)
from catalog_target.tx_owner_001_owner_research import (  # noqa: E402
    CRITICAL_CASE_ASSESSMENTS,
    OEM_TECHNICAL_SOURCES,
    resolve_m7_sku_exact,
    sources_for_product_id,
)


REVIEW_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review"
BASELINE_DIR = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15"
OUT_DIR = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
PR499_HEAD = "5581b2d54fe5b06418032f8ce23bdc1a2c9904c8"
CENSUS_AT = "2026-10-15T09:34:39Z"

OWNER_RESPONSES = (
    "APPROVE_CATALOG_EXIT",
    "REJECT_EXIT_REQUEST_EXCEPTION_REVIEW",
    "APPROVE_INDUSTRIAL_EXCEPTION",
    "REQUEST_MORE_EVIDENCE",
    "DEFER_DECISION",
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


def load_reviews() -> list[dict[str, str]]:
    path = REVIEW_DIR / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 262:
        raise RuntimeError(f"expected_262_review_rows got={len(rows)}")
    return rows


def family_group(name: str, brand: str, sku: str) -> str:
    blob = f"{name} {brand}"
    if re.search(r"CP-GRAT|پلیسه", blob, re.I):
        return "DEBURR_CP_GRAT"
    if re.search(r"بلیدکات|bladekat|تیغ\s*V|تیغ\s*پرفیل|اور\s*فرز", blob, re.I):
        return "WOOD_CNC_ROUTER_BLADEKAT"
    if re.search(r"رنده\s*چوب|رنده\s*نجار|تیشه|مغار|JN3", blob, re.I):
        return "WOOD_HAND_PLANE_CHISEL"
    if re.search(r"فرز\s*انگشتی\s*بادی|سنگ\s*فرز\s*بادی|میکرو\s*فرز|سنباده\s*زن\s*بادی", blob, re.I):
        return "M7_PNEUMATIC_GRINDER"
    if re.search(r"بکس\s*بادی|سوکت|آلن\s*بکس|گایکور|impact", blob, re.I) or sku.upper().startswith("NC"):
        return "M7_PNEUMATIC_IMPACT_SOCKET"
    if re.search(r"تفنگ\s*باد|بادپاش|JC\d", blob, re.I):
        return "M7_AIR_BLOW_GUN"
    if re.search(r"رگولاتور|لوبریکاتور|فیلتر|SY-|FR-|L\d{2}", blob, re.I):
        return "PNEUMATIC_AIR_PREP"
    if re.search(r"مایتی\s*سون.*مدل", blob, re.I):
        return "M7_GENERIC_MODEL_TITLE"
    if re.search(r"انبر|آچار|چکش|پیچ.?گوشتی", blob, re.I):
        return "HAND_TOOLS_PLIERS_WRENCH"
    if re.search(r"سنبه|پانچ|درآر", blob, re.I):
        return "PUNCH_MARKING_SETS"
    if re.search(r"کلمپ|گیره", blob, re.I):
        return "CLAMPS_VICES"
    if re.search(r"اره|فرز\s*اره", blob, re.I):
        return "SAW_ACCESSORIES"
    if re.search(r"گروز|Groz", blob, re.I):
        return "GROZ_GENERAL"
    return "OTHER_WORKSHOP_HEURISTIC"


def build_critical_matrix(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {int(r["product_id"]): r for r in reviews}
    matrix: list[dict[str, str]] = []
    needs_more = sorted(
        int(r["product_id"])
        for r in reviews
        if r["proposed_disposition"] == "NEEDS_MORE_EVIDENCE"
    )
    if len(needs_more) != 18:
        raise RuntimeError(f"expected_18_needs_more got={len(needs_more)}")
    critical_ids = sorted(needs_more + [2915, 3238])
    for pid in critical_ids:
        row = by_id[pid]
        enriched = enrich_row(row)
        assess = CRITICAL_CASE_ASSESSMENTS.get(pid, {})
        m7 = resolve_m7_sku_exact(row.get("sku", ""))
        oem_sources = sources_for_product_id(pid)
        oem_urls = "|".join(s["source_url"] for s in oem_sources)
        oem_status = assess.get("oem_status", "")
        if m7:
            oem_status = "OEM_EXACT_SKU_PAGE"
        matrix.append(
            {
                "product_id": str(pid),
                "sku": row["sku"],
                "current_name": row["current_name"],
                "historical_pr499_proposal": enriched["historical_pr499_proposal"],
                "post_research_proposal": enriched["post_research_proposal"],
                "post_research_evidence_basis": enriched["post_research_evidence_basis"],
                "application_class": assess.get("application_class", ""),
                "oem_status": oem_status,
                "oem_source_urls": oem_urls,
                "evidence_assessment": assess.get(
                    "evidence_assessment",
                    m7.get("identity", "") if m7 else "",
                ),
                "investigation_summary": assess.get("investigation_summary", ""),
                "allowed_owner_responses": assess.get(
                    "recommended_owner_options", "|".join(OWNER_RESPONSES)
                ),
                "owner_decision": "",
                "authorization_status": "PENDING",
                "owner_authorized_by": "",
                "owner_decision_at_utc": "",
            }
        )
    if len(matrix) != 20:
        raise RuntimeError(f"critical_matrix_expected_20 got={len(matrix)}")
    return matrix


def build_exit_families(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    exits = [r for r in reviews if r["proposed_disposition"] == "CATALOG_EXIT_CANDIDATE"]
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in exits:
        groups[family_group(row["current_name"], row["brand"], row["sku"])].append(row)
    out: list[dict[str, str]] = []
    for fam, rows in sorted(groups.items(), key=lambda x: -len(x[1])):
        conf = Counter(r["confidence"] for r in rows)
        basis = Counter(r["confidence_basis"] for r in rows)
        out.append(
            {
                "family_code": fam,
                "product_count": str(len(rows)),
                "low_confidence_count": str(sum(1 for r in rows if r["confidence"] == "LOW")),
                "medium_confidence_count": str(
                    sum(1 for r in rows if r["confidence"] == "MEDIUM")
                ),
                "oem_documented_count": str(
                    sum(1 for r in rows if r["confidence_basis"] == "OEM_DOCUMENTED")
                ),
                "confidence_distribution": json.dumps(dict(conf), ensure_ascii=False),
                "confidence_basis_distribution": json.dumps(dict(basis), ensure_ascii=False),
                "sample_product_ids": "|".join(r["product_id"] for r in rows[:8]),
                "tx_owner_scope_note": (
                    "Category 158/160 placement supports TX-OWNER-001 scope review; "
                    "not sole proof of engineering identity."
                ),
                "recommended_owner_action": "APPROVE_CATALOG_EXIT (batch) or REQUEST_MORE_EVIDENCE per SKU",
            }
        )
    return out


def build_low_confidence_register(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    reg: list[dict[str, str]] = []
    for row in reviews:
        if row["proposed_disposition"] != "CATALOG_EXIT_CANDIDATE":
            continue
        if row["evidence_strength"] != "LOW":
            continue
        reg.append(
            {
                "product_id": row["product_id"],
                "sku": row["sku"],
                "current_name": row["current_name"],
                "family_code": family_group(row["current_name"], row["brand"], row["sku"]),
                "pr499_proposal": row["proposed_disposition"],
                "confidence_basis": row["confidence_basis"],
                "review_path": (
                    "Owner confirms APPROVE_CATALOG_EXIT or REQUEST_MORE_EVIDENCE; "
                    "REJECT_EXIT triggers exception review — not auto rehome."
                ),
                "owner_decision": "",
            }
        )
    if len(reg) != 176:
        raise RuntimeError(f"low_confidence_register_expected_176 got={len(reg)}")
    return reg


def build_decision_sheet(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    sheet: list[dict[str, str]] = []
    for row in reviews:
        enriched = enrich_row(row)
        pid = int(row["product_id"])
        assess = CRITICAL_CASE_ASSESSMENTS.get(pid)
        m7 = resolve_m7_sku_exact(row.get("sku", ""))
        evidence_note = "PR499 proposal unchanged"
        if m7:
            evidence_note = f"OEM exact SKU page: {m7.get('identity', '')}"
        if assess:
            evidence_note = assess.get("evidence_assessment", evidence_note)
        sheet.append(
            {
                "product_id": row["product_id"],
                "sku": row["sku"],
                "current_name": row["current_name"],
                "historical_pr499_proposal": enriched["historical_pr499_proposal"],
                "post_research_proposal": enriched["post_research_proposal"],
                "post_research_evidence_basis": enriched["post_research_evidence_basis"],
                "pr499_proposed_domain": row.get("proposed_industrial_domain_code", ""),
                "oem_source_ids": enriched["oem_source_ids"],
                "evidence_assessment_for_owner": evidence_note,
                "proposal_status": enriched["proposal_status"],
                "allowed_owner_responses": "|".join(OWNER_RESPONSES),
                "owner_decision": "",
                "authorization_status": "PENDING",
            }
        )
    return sheet


def build_owner_journal_template(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    journal: list[dict[str, str]] = []
    for row in reviews:
        enriched = enrich_row(row)
        journal.append(
            {
                "product_id": row["product_id"],
                "sku": row["sku"],
                "historical_pr499_proposal": enriched["historical_pr499_proposal"],
                "post_research_proposal": enriched["post_research_proposal"],
                "post_research_evidence_basis": enriched["post_research_evidence_basis"],
                "agent_proposal_domain": row.get("proposed_industrial_domain_code", ""),
                "evidence_assessment": row["evidence_strength"],
                "confidence_basis": row["confidence_basis"],
                "oem_source_ids": enriched["oem_source_ids"],
                "owner_decision": "",
                "owner_authorized_by": "",
                "owner_decision_at_utc": "",
                "authorization_status": "PENDING",
                "notes": "",
            }
        )
    return journal


def build_family_membership(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    """One row per product: family + evidence level + effective post-research proposal."""
    rows: list[dict[str, str]] = []
    for row in reviews:
        enriched = enrich_row(row)
        fam = family_group(row["current_name"], row["brand"], row["sku"])
        hist_exit = historical_pr499_proposal(row) == "CATALOG_EXIT_CANDIDATE"
        post_exit = enriched["post_research_proposal"] == "CATALOG_EXIT_CANDIDATE"
        cohort = "PRIORITY_B_HISTORICAL_EXIT" if hist_exit else "NON_HISTORICAL_EXIT_COHORT"
        if post_exit and not hist_exit:
            cohort = "POST_RESEARCH_EXIT_DELTA"
        rows.append(
            {
                "product_id": row["product_id"],
                "sku": row["sku"],
                "family_code": fam,
                "evidence_level": enriched["post_research_evidence_basis"],
                "historical_pr499_proposal": enriched["historical_pr499_proposal"],
                "post_research_proposal": enriched["post_research_proposal"],
                "exit_cohort_tag": cohort,
            }
        )
    return rows


def exit_cohort_checksum(product_ids: list[int]) -> str:
    payload = ",".join(str(pid) for pid in sorted(product_ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    merge_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PR499_HEAD, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    if merge_check.returncode != 0:
        raise RuntimeError("BLOCKED: PR #499 head not in branch history")

    reviews = load_reviews()
    enriched_all = [enrich_row(r) for r in reviews]
    validate_post_research_counts(enriched_all)
    pr499_counts = disposition_counts(enriched_all, field="historical_pr499_proposal")
    for key, expected in PR499_ANCHOR_DISPOSITIONS.items():
        if pr499_counts.get(key, 0) != expected:
            raise RuntimeError(
                f"pr499_anchor_mismatch {key} expected={expected} got={pr499_counts.get(key)}"
            )
    post_counts = disposition_counts(enriched_all, field="post_research_proposal")

    review_sha = _sha256_file(REVIEW_DIR / "01-262-PRODUCT-SEMANTIC-REVIEW.csv")
    census_sha = _sha256_file(BASELINE_DIR / "02-PRODUCT-CATEGORY-CENSUS.csv")
    generation_head = _git_sha()

    identity = {
        "package_generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_pr499_semantic_review_csv_sha256": review_sha,
        "frozen_baseline_product_census_csv_sha256": census_sha,
        "package_generation_git_head_sha": generation_head,
        "pr_500_branch_head_at_package_generation": generation_head,
        "note": (
            "Frozen input SHAs fingerprint PR #499 review + baseline census; "
            "package_generation_git_head_sha is the git commit that produced this package "
            "(PR #500 branch HEAD at generation time)."
        ),
        "pr_499_reviewed_head": PR499_HEAD,
        "pr_499_merge_on_main": "919782bfcf85a1524f9cca30abcf8d967d00d0b6",
        "historical_census_collected_at_utc": CENSUS_AT,
        "disposition_counts_historical_pr499_anchor": pr499_counts,
        "disposition_counts_post_research_effective": post_counts,
        "proposal_status": "ALL_PROPOSALS_UNAPPROVED",
        "owner_journal_policy": (
            "07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv is regenerated; "
            "Owner-completed decisions must be stored in a separate immutable file "
            "(e.g. OWNER-AUTHORIZATION-JOURNAL-COMPLETED.csv) never overwritten by this script."
        ),
        "safety": {
            "PRODUCTION_MUTATION": "NO",
            "CATALOG_EXIT_APPLY": "NO",
            "REHOME_APPLY": "NO",
            "MASTER_MANIFEST_REWRITE": "NO",
        },
        "protected_scope": {
            "category_154_bulk_exit": "FORBIDDEN",
            "category_156_industrial_oils_27": "FORBIDDEN_BULK_ACTION",
        },
    }
    (out_dir / "00-PACKAGE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    critical = build_critical_matrix(reviews)
    write_csv(
        out_dir / "01-CRITICAL-20-EVIDENCE-MATRIX.csv",
        list(critical[0].keys()),
        critical,
    )

    families = build_exit_families(reviews)
    write_csv(
        out_dir / "02-EXIT-CANDIDATE-FAMILY-GROUPS.csv",
        list(families[0].keys()),
        families,
    )

    low_reg = build_low_confidence_register(reviews)
    write_csv(
        out_dir / "03-LOW-CONFIDENCE-EXIT-RISK-REGISTER.csv",
        list(low_reg[0].keys()),
        low_reg,
    )

    write_csv(
        out_dir / "04-OEM-TECHNICAL-SOURCE-REGISTER.csv",
        list(OEM_TECHNICAL_SOURCES[0].keys()),
        OEM_TECHNICAL_SOURCES,
    )

    decision_sheet = build_decision_sheet(reviews)
    write_csv(
        out_dir / "05-PROPOSED-DECISION-SHEET-262.csv",
        list(decision_sheet[0].keys()),
        decision_sheet,
    )

    hist_exit_ids = sorted(
        int(r["product_id"])
        for r in reviews
        if historical_pr499_proposal(r) == "CATALOG_EXIT_CANDIDATE"
    )
    post_exit_ids = sorted(
        int(r["product_id"])
        for r in enriched_all
        if r["post_research_proposal"] == "CATALOG_EXIT_CANDIDATE"
    )
    delta_exit = sorted(set(post_exit_ids) - set(hist_exit_ids))

    membership = build_family_membership(reviews)
    write_csv(
        out_dir / "08-FAMILY-MEMBERSHIP-COMPLETE-262.csv",
        list(membership[0].keys()),
        membership,
    )

    reconciliation = {
        "unique_product_ids": 262,
        "product_ids_accounted": sorted(int(r["product_id"]) for r in reviews),
        "pr499_review_csv_sha256": review_sha,
        "immutable_census_sha256": census_sha,
        "disposition_counts_historical_pr499_anchor": pr499_counts,
        "disposition_counts_post_research_effective": post_counts,
        "post_research_expected": POST_RESEARCH_EXPECTED,
        "m7_post_research_exit_product_ids": sorted(M7_POST_RESEARCH_EXIT_IDS),
        "post_research_exit_delta_product_ids": delta_exit,
        "historical_pr499_exit_cohort_product_ids_checksum_sha256": exit_cohort_checksum(
            hist_exit_ids
        ),
        "post_research_exit_cohort_product_ids_checksum_sha256": exit_cohort_checksum(
            post_exit_ids
        ),
        "critical_case_count": 20,
        "low_confidence_exit_count": len(low_reg),
        "family_membership_rows": len(membership),
        "owner_journal_rows": 262,
        "category_154_included": False,
        "category_156_oils_included": False,
    }
    (out_dir / "06-RECONCILIATION-262.json").write_text(
        json.dumps(reconciliation, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    journal = build_owner_journal_template(reviews)
    write_csv(
        out_dir / "07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv",
        list(journal[0].keys()),
        journal,
    )

    memo_fa = f"""# یادداشت اجرایی تصمیم‌گیری مالک — TX-OWNER-001

**وضعیت:** پیشنهادها تأیید نشده‌اند — این بسته فقط برای تصمیم مالک است.  
**شواهد تاریخی سرشمار:** {CENSUS_AT} (وضعیت زندهٔ امروز نیست).  
**ورودی بررسی:** PR #499 (`{PR499_HEAD[:12]}…`)

## جمعیت
- **۲۶۲** محصول یکتا در دسته‌های ۱۵۸ و ۱۶۰ (دامنهٔ TX-OWNER-001).
- دسته **۱۵۴** و **۲۷** محصول روغن صنعتی زیر **۱۵۶** از اقدام گروهی خارج هستند.

## اولویت A — ۲۰ مورد بحرانی
- **۱۸** مورد `NEEDS_MORE_EVIDENCE` (شیارزن / تیغ پرداخت و مدل‌های M7 بدون عنوان فنی).
- **۲۹۱۵** — پیشنهاد استثناء Cutting (تراشکاری در عنوان؛ بدون OEM در این پاس).
- **۳۲۳۸** — جک ماشین‌کاری Groz؛ مرز Workholding در مقابل لوازم کارگاهی.

هیچ استثناء صنعتی یا خروج کاتالوگ **به‌صورت خودکار تأیید نشده** است.

## اولویت B — ۲۴۲ پیشنهاد خروج
- **۱۷۶** مورد با اطمینان شواهد **LOW** (ثبت ریسک در `03-LOW-CONFIDENCE-EXIT-RISK-REGISTER.csv`).
- **۶۴** مورد MEDIUM heuristic؛ **۲** مورد OEM-documented (QA-210/211).

## پاسخ‌های مجاز مالک (هر محصول)
`APPROVE_CATALOG_EXIT` | `REJECT_EXIT_REQUEST_EXCEPTION_REVIEW` | `APPROVE_INDUSTRIAL_EXCEPTION` | `REQUEST_MORE_EVIDENCE` | `DEFER_DECISION`

## گام بعد
پس از تکمیل `07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv` توسط مالک، می‌توان به دروازهٔ APPLY (در صورت صدور مجوز صریح) رفت — **نه در این PR**.
"""
    (out_dir / "00-OWNER-DECISION-MEMO-FA.md").write_text(memo_fa, encoding="utf-8")

    summary = {
        "status": "READY_FOR_OWNER_REVIEW",
        "population": 262,
        "disposition_counts_historical_pr499": pr499_counts,
        "disposition_counts_post_research": post_counts,
        "critical_matrix_rows": len(critical),
        "exit_family_groups": len(families),
        "family_membership_rows": len(membership),
        "low_confidence_exit_register_rows": len(low_reg),
        "oem_source_rows": len(OEM_TECHNICAL_SOURCES),
        "decision_sheet_rows": len(decision_sheet),
        "owner_journal_template_rows": len(journal),
    }
    (out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    names = [
        "00-PACKAGE-IDENTITY.json",
        "00-OWNER-DECISION-MEMO-FA.md",
        "01-CRITICAL-20-EVIDENCE-MATRIX.csv",
        "02-EXIT-CANDIDATE-FAMILY-GROUPS.csv",
        "03-LOW-CONFIDENCE-EXIT-RISK-REGISTER.csv",
        "04-OEM-TECHNICAL-SOURCE-REGISTER.csv",
        "05-PROPOSED-DECISION-SHEET-262.csv",
        "06-RECONCILIATION-262.json",
        "07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv",
        "08-FAMILY-MEMBERSHIP-COMPLETE-262.csv",
        "SUMMARY.json",
    ]
    write_sha256sums(out_dir, names)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
