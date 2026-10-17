"""TX-OWNER-001 product-level semantic review (read-only proposals, no APPLY)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import (
    TARGET_DOMAINS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    is_live_product,
    is_tx_owner_scope_category,
    normalize_taxonomy_text,
    tx_owner_scope_product_ids,
    write_csv,
)
from catalog_target.tx_owner_001_external_sources import (
    APPROVED_DOMAIN_CODES,
    EXTERNAL_SOURCES,
    sources_for_product,
)

PRIMARY_DISPOSITIONS = frozenset(
    {
        "CATALOG_EXIT_CANDIDATE",
        "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "NEEDS_MORE_EVIDENCE",
        "SEMANTIC_CONFLICT",
        "OWNER_DECISION_REQUIRED",
    }
)

DOMAIN_BY_CODE = {d["code"]: d["en"] for d in TARGET_DOMAINS}

# Narrow workshop / woodworking signals (title only — not category path labels).
WOODWORKING_MARKERS = re.compile(
    r"چوب|نجار|wood|رنده\s*چوب|رنده\s*نجار|تیغه\s*رنده|تیشه|مغار|"
    r"براده\s*شکن.*رنده|کبوتری|لیسه\s*چوب|JN3\d{2}|فاق\s*و\s*زبونه|"
    r"ربع\s*دایره|پرفیل\s*لبه|تونیک|بلیدکات|bladekat",
    re.I,
)
HAND_WORKSHOP_MARKERS = re.compile(
    r"انبر|آچار|چکش|پیچ.?گوشتی|شابر|کلمپ\s*مواز|گیره\s*دستی|سوهان|قداره|"
    r"سنبه|پانچ|درآر|نشان|بادپاش|تفنگ\s*باد|بکس\s*بادی|"
    r"سوکت|آلن\s*بکس|اره\s*موئی|کمان\s*اره|قرقره\s*سنگ|"
    r"رگولاتور|لوبریکاتور|فیلتر\s*هوا|فیلتر\s*رطوبت|"
    r"hand\s*tool|pliers|wrench|hammer|chisel",
    re.I,
)
PNEUMATIC_POWER_TOOL = re.compile(
    r"فرز\s*انگشتی\s*بادی|میکرو\s*فرز\s*قلمی\s*بادی|سنگ\s*فرز\s*بادی|"
    r"سنباده\s*زن\s*بادی|فرز\s*قلمی\s*حکاکی\s*بادی|QA\d{3}|QB\d{3}|QC\d{3}",
    re.I,
)
DEBURR_HAND = re.compile(r"پلیسه|deburr|CP-GRAT", re.I)
METAL_TURNING_INSERT = re.compile(
    r"تیغچه\s*رنده\s*تراش|تراشکار|turning\s*insert|lathe\s*insert",
    re.I,
)
GROOVING_AMBIGUOUS = re.compile(r"شیارزن", re.I)
WOOD_CNC_ROUTER_BIT = re.compile(
    r"بلیدکات|bladekat|اور\s*فرز\s*بلید|تیغ\s+V\s*شکل|تیغ\s*انگشتی|"
    r"تیغ\s*پرفیل|تیغ\s*تونیک|تیغ\s*دو\s*راهه|تیغ\s*بانکی",
    re.I,
)
FINISHING_BLADE_AMBIGUOUS = re.compile(r"تیغ\s*پرداخت", re.I)
GENERIC_TITLE = re.compile(
    r"^\s*مایتی\s*سون\s*\(Mighty Seven\)\s*مدل\s+[A-Z0-9]+$",
    re.I,
)
MACHINE_JACK = re.compile(r"جک\s*ماشین", re.I)


@dataclass
class Classification:
    disposition: str
    meaning: str
    function: str
    application: str
    domain_code: str
    domain_name: str
    rationale: str
    evidence_strength: str
    confidence: str
    confidence_basis: str
    evidence_source: str
    owner_required: str = "YES"


@dataclass(frozen=True)
class ReviewRow:
    product_id: int
    sku: str
    manufacturer_code: str
    current_name: str
    brand: str
    category_id: int
    category_path: str
    is_active: str
    is_available: str
    is_priced: str
    image_present: str
    storefront_visible: str
    sellable: str
    product_type_code: str
    product_type_name: str
    actual_product_meaning: str
    engineering_function: str
    industrial_application: str
    evidence_source: str
    evidence_strength: str
    scope_assessment: str
    proposed_disposition: str
    proposed_industrial_domain_code: str
    proposed_industrial_domain_name: str
    decision_rationale: str
    confidence: str
    confidence_basis: str
    owner_review_required: str
    review_status: str


def load_cohort_products(
    product_census_path: Path,
    *,
    category_census_path: Path | None = None,
) -> list[dict[str, str]]:
    with product_census_path.open(encoding="utf-8", newline="") as handle:
        products = list(csv.DictReader(handle))
    cohort = [
        row
        for row in products
        if is_live_product(row)
        and str(row.get("category_id") or "").strip()
        and is_tx_owner_scope_category(int(row["category_id"]))
    ]
    expected_ids = tx_owner_scope_product_ids(products)
    found_ids = {int(r["product_id"]) for r in cohort}
    if found_ids != expected_ids:
        raise RuntimeError(
            f"cohort_id_mismatch expected={len(expected_ids)} found={len(found_ids)}"
        )
    if len(found_ids) != 262:
        raise RuntimeError(f"cohort_count_expected_262 got={len(found_ids)}")
    by_cat: dict[int, int] = {}
    for row in cohort:
        cid = int(row["category_id"])
        by_cat[cid] = by_cat.get(cid, 0) + 1
    if by_cat.get(158) != 196 or by_cat.get(160) != 66:
        raise RuntimeError(f"cohort_category_counts_invalid by_cat={by_cat}")
    if category_census_path and category_census_path.is_file():
        with category_census_path.open(encoding="utf-8", newline="") as handle:
            cats = {int(r["category_id"]): r for r in csv.DictReader(handle)}
        for cid in (157, 159):
            if int(cats[cid]["direct_product_count"]) != 0:
                raise RuntimeError(f"parent_category_expected_zero_direct cid={cid}")
        if int(cats[158]["direct_product_count"]) != 196:
            raise RuntimeError("category_158_direct_count_mismatch")
        if int(cats[160]["direct_product_count"]) != 66:
            raise RuntimeError("category_160_direct_count_mismatch")
    return sorted(cohort, key=lambda r: int(r["product_id"]))


def _priced_flag(row: dict[str, str]) -> str:
    try:
        return "true" if float(row.get("base_price") or 0) > 0 else "false"
    except ValueError:
        return "false"


def _base_evidence(row: dict[str, str]) -> str:
    parts = [
        "PRESERVED_PRODUCTION_CENSUS_2026-10-15",
        "fields=product_name,category_full_path,commerce_flags,product_type",
    ]
    for src in sources_for_product(int(row["product_id"])):
        parts.append(src["source_id"])
    return ";".join(parts)


def _exit_tx_owner(
    *,
    meaning: str,
    function: str,
    rationale: str,
    evidence_strength: str,
    confidence: str,
    confidence_basis: str,
    evidence_source: str,
    application: str = "",
) -> Classification:
    return Classification(
        disposition="CATALOG_EXIT_CANDIDATE",
        meaning=meaning,
        function=function,
        application=application,
        domain_code="",
        domain_name="",
        rationale=rationale,
        evidence_strength=evidence_strength,
        confidence=confidence,
        confidence_basis=confidence_basis,
        evidence_source=evidence_source,
    )


def _needs_more(
    *,
    meaning: str,
    function: str,
    rationale: str,
    evidence_source: str,
) -> Classification:
    return Classification(
        disposition="NEEDS_MORE_EVIDENCE",
        meaning=meaning,
        function=function,
        application="",
        domain_code="",
        domain_name="",
        rationale=rationale,
        evidence_strength="LOW",
        confidence="LOW",
        confidence_basis="CENSUS_ONLY",
        evidence_source=evidence_source,
    )


def _industrial_exception(
    *,
    domain_code: str,
    meaning: str,
    function: str,
    rationale: str,
    evidence_strength: str,
    confidence: str,
    confidence_basis: str,
    evidence_source: str,
    application: str = "",
) -> Classification:
    if domain_code not in APPROVED_DOMAIN_CODES:
        raise RuntimeError(f"invalid_domain_code {domain_code}")
    return Classification(
        disposition="INDUSTRIAL_EXCEPTION_CANDIDATE",
        meaning=meaning,
        function=function,
        application=application,
        domain_code=domain_code,
        domain_name=DOMAIN_BY_CODE[domain_code],
        rationale=rationale + " Not an approved rehome; explicit Owner SKU override required.",
        evidence_strength=evidence_strength,
        confidence=confidence,
        confidence_basis=confidence_basis,
        evidence_source=evidence_source,
    )


def _classify(row: dict[str, str]) -> ReviewRow:
    pid = int(row["product_id"])
    cid = int(row["category_id"])
    name = row.get("product_name", "")
    path = row.get("category_full_path", "")
    sku = (row.get("sku") or "").strip()
    title = name
    evidence_source = _base_evidence(row)

    # --- OEM-backed pneumatic die grinders (5194–5200 and family) ---
    if pid in {5194, 5195} or (
        PNEUMATIC_POWER_TOOL.search(title) and "کولت" in title
    ):
        oem_note = ""
        if pid == 5194:
            oem_note = " OEM QA-210 Air Die Grinder (EXT-M7-158)."
        elif pid == 5195:
            oem_note = " OEM QA-211 Air Die Grinder (EXT-M7-159)."
        clf = _exit_tx_owner(
            meaning="Handheld pneumatic die grinder (air tool).",
            function="Rotary pneumatic grinding with collet spindle interface",
            application="Workshop deburring/grinding (OEM air tool class)",
            rationale=(
                "Collet names spindle interface of a die grinder, not Toolholding Product Type."
                + oem_note
                + " TX-OWNER-001 workshop/hand scope → CATALOG_EXIT proposal."
            ),
            evidence_strength="MEDIUM" if oem_note else "LOW",
            confidence="MEDIUM" if oem_note else "LOW",
            confidence_basis="OEM_DOCUMENTED" if oem_note else "HEURISTIC",
            evidence_source=evidence_source,
        )
    elif PNEUMATIC_POWER_TOOL.search(title):
        clf = _exit_tx_owner(
            meaning="Handheld pneumatic power tool (grinder/sander class).",
            function="Pneumatic rotary/abrasive power tool",
            application="Workshop air tool",
            rationale=(
                "Complete handheld pneumatic grinder/sander — not a Cutting Tool insert or "
                "industrial machine. Aligns with M7 Air Tools family (see EXT-M7-AIR-TOOLS-CLASS). "
                "Proposed CATALOG_EXIT under TX-OWNER-001."
            ),
            evidence_strength="LOW",
            confidence="LOW",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif METAL_TURNING_INSERT.search(title):
        clf = _industrial_exception(
            domain_code="KZ.DOM.CUTTING",
            meaning="Indexable turning insert for metal lathe (title states تراشکاری).",
            function="Metal turning / insert cutting",
            application="CNC/manual lathe metal removal",
            rationale=(
                "Title explicitly references turning machining (تراشکاری), not woodworking. "
                "Misplaced under woodworking category; industrial Cutting exception candidate."
            ),
            evidence_strength="MEDIUM",
            confidence="MEDIUM",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif GROOVING_AMBIGUOUS.search(title):
        clf = _needs_more(
            meaning="Grooving tool — material/application not established from census title alone.",
            function="Grooving (wood router vs metal lathe insert undetermined)",
            rationale=(
                "«شیارزن»/grooving with CNC in title does not prove metalworking vs woodworking "
                "application without geometry/OEM docs. Preserve unresolved status."
            ),
            evidence_source=evidence_source,
        )
    elif FINISHING_BLADE_AMBIGUOUS.search(title) and not WOOD_CNC_ROUTER_BIT.search(title):
        clf = _needs_more(
            meaning="Finishing blade — substrate and machine context unknown.",
            function="Edge finishing blade (application unclear)",
            rationale=(
                "«تیغ پرداخت» without verified BladeKat/wood or metal lathe context. "
                "Do not infer metalworking from bearing count alone."
            ),
            evidence_source=evidence_source,
        )
    elif WOOD_CNC_ROUTER_BIT.search(title):
        clf = _exit_tx_owner(
            meaning="CNC woodworking router profile bit / cutter (BladeKat-style naming).",
            function="Wood panel/profile routing",
            application="Woodworking CNC router",
            rationale=(
                "BladeKat/profile-router naming (V-groove, finger-joint, profile) indicates "
                "woodworking CNC tooling — TX-OWNER-001 woodworking scope. "
                "CNC here does not imply metalworking Cutting Tools domain."
            ),
            evidence_strength="MEDIUM",
            confidence="MEDIUM",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif WOODWORKING_MARKERS.search(title) and not METAL_TURNING_INSERT.search(title):
        clf = _exit_tx_owner(
            meaning="Woodworking hand or bench tool / consumable.",
            function="Woodworking operation",
            application="Carpentry / wood shop",
            rationale="Woodworking markers in product title; TX-OWNER-001 CATALOG_EXIT proposal.",
            evidence_strength="MEDIUM",
            confidence="MEDIUM",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif DEBURR_HAND.search(title):
        clf = _exit_tx_owner(
            meaning="Manual deburring tool or blade.",
            function="Hand deburring",
            rationale=(
                "CP-GRAT / deburring hand tools are workshop tools, not approved industrial domains."
            ),
            evidence_strength="MEDIUM",
            confidence="MEDIUM",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif MACHINE_JACK.search(title):
        clf = Classification(
            disposition="OWNER_DECISION_REQUIRED",
            meaning="Machine shop jack / support — workholding vs general accessory.",
            function="Machine support / lifting",
            application="Unclear from title",
            domain_code="",
            domain_name="",
            rationale=(
                "Could be workshop accessory or workholding support. "
                "No OEM sheet in preserved census; Owner must decide exit vs industrial exception."
            ),
            evidence_strength="LOW",
            confidence="LOW",
            confidence_basis="CENSUS_ONLY",
            evidence_source=evidence_source,
        )
    elif HAND_WORKSHOP_MARKERS.search(title):
        clf = _exit_tx_owner(
            meaning="General hand or workshop tool / pneumatic accessory.",
            function="Manual or workshop pneumatic operation",
            rationale=(
                "Title matches workshop/hand patterns (clamp, air prep, punch, etc.). "
                "Proposed CATALOG_EXIT — heuristic only, not HIGH strength from regex alone."
            ),
            evidence_strength="LOW",
            confidence="LOW",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif GENERIC_TITLE.search(title):
        clf = _needs_more(
            meaning="Marketing title is model code only.",
            function="Unknown",
            rationale="Insufficient technical identity in preserved census; need OEM listing or specs.",
            evidence_source=evidence_source,
        )
    elif cid == 158:
        clf = _exit_tx_owner(
            meaning="Listed under general hand-tool category scope (TX-OWNER-001).",
            function="General hand tool (category placement)",
            rationale=(
                "Category 158 is TX-OWNER-001 scope. Without contrary industrial evidence, "
                "default exit proposal with LOW heuristic confidence."
            ),
            evidence_strength="LOW",
            confidence="LOW",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    elif cid == 160:
        clf = _exit_tx_owner(
            meaning="Listed under woodworking-tool category scope (TX-OWNER-001).",
            function="Woodworking category placement",
            rationale="Category 160 woodworking scope; exit proposal unless industrial evidence added.",
            evidence_strength="LOW",
            confidence="LOW",
            confidence_basis="HEURISTIC",
            evidence_source=evidence_source,
        )
    else:
        clf = Classification(
            disposition="OWNER_DECISION_REQUIRED",
            meaning="Ambiguous scope",
            function="Unknown",
            application="",
            domain_code="",
            domain_name="",
            rationale="Unable to classify from census; Owner review required.",
            evidence_strength="LOW",
            confidence="LOW",
            confidence_basis="CENSUS_ONLY",
            evidence_source=evidence_source,
        )

    if clf.disposition not in PRIMARY_DISPOSITIONS:
        raise RuntimeError(f"invalid_disposition {clf.disposition}")

    return ReviewRow(
        product_id=pid,
        sku=row.get("sku", ""),
        manufacturer_code=row.get("manufacturer_code", ""),
        current_name=name,
        brand=row.get("brand", ""),
        category_id=cid,
        category_path=path,
        is_active=row.get("is_active", ""),
        is_available=row.get("is_available", ""),
        is_priced=_priced_flag(row),
        image_present=row.get("image_present", ""),
        storefront_visible=row.get("storefront_visible", ""),
        sellable=row.get("sellable", ""),
        product_type_code=row.get("product_type_code", ""),
        product_type_name=row.get("product_type_name", ""),
        actual_product_meaning=clf.meaning,
        engineering_function=clf.function,
        industrial_application=clf.application,
        evidence_source=clf.evidence_source,
        evidence_strength=clf.evidence_strength,
        scope_assessment="TX_OWNER_001_IN_SCOPE",
        proposed_disposition=clf.disposition,
        proposed_industrial_domain_code=clf.domain_code,
        proposed_industrial_domain_name=clf.domain_name,
        decision_rationale=clf.rationale,
        confidence=clf.confidence,
        confidence_basis=clf.confidence_basis,
        owner_review_required=clf.owner_required,
        review_status="PROPOSED",
    )


def review_row_to_dict(row: ReviewRow) -> dict[str, str]:
    return {
        "product_id": str(row.product_id),
        "sku": row.sku,
        "manufacturer_code": row.manufacturer_code,
        "current_name": row.current_name,
        "brand": row.brand,
        "current_category_id": str(row.category_id),
        "current_category_path": row.category_path,
        "is_active": row.is_active,
        "is_available": row.is_available,
        "is_priced": row.is_priced,
        "image_present": row.image_present,
        "storefront_visible": row.storefront_visible,
        "sellable": row.sellable,
        "product_type_code": row.product_type_code,
        "product_type_name": row.product_type_name,
        "actual_product_meaning": row.actual_product_meaning,
        "engineering_function": row.engineering_function,
        "industrial_application": row.industrial_application,
        "evidence_source": row.evidence_source,
        "evidence_strength": row.evidence_strength,
        "scope_assessment": row.scope_assessment,
        "proposed_disposition": row.proposed_disposition,
        "proposed_industrial_domain_code": row.proposed_industrial_domain_code,
        "proposed_industrial_domain_name": row.proposed_industrial_domain_name,
        "decision_rationale": row.decision_rationale,
        "confidence": row.confidence,
        "confidence_basis": row.confidence_basis,
        "owner_review_required": row.owner_review_required,
        "review_status": row.review_status,
    }


REVIEW_FIELDS = list(
    review_row_to_dict(
        ReviewRow(
            product_id=0,
            sku="",
            manufacturer_code="",
            current_name="",
            brand="",
            category_id=0,
            category_path="",
            is_active="",
            is_available="",
            is_priced="",
            image_present="",
            storefront_visible="",
            sellable="",
            product_type_code="",
            product_type_name="",
            actual_product_meaning="",
            engineering_function="",
            industrial_application="",
            evidence_source="",
            evidence_strength="",
            scope_assessment="",
            proposed_disposition="NEEDS_MORE_EVIDENCE",
            proposed_industrial_domain_code="",
            proposed_industrial_domain_name="",
            decision_rationale="",
            confidence="LOW",
            confidence_basis="CENSUS_ONLY",
            owner_review_required="YES",
            review_status="PROPOSED",
        )
    ).keys()
)

OWNER_QUEUE_FIELDS = [
    "product_id",
    "sku",
    "current_name",
    "proposed_disposition",
    "proposed_industrial_domain_code",
    "queue_category",
    "proposed_owner_action",
    "rationale_summary",
    "evidence_strength",
    "confidence_basis",
]


def queue_category_for(row: dict[str, str]) -> str:
    disp = row["proposed_disposition"]
    basis = row.get("confidence_basis", "")
    if disp == "NEEDS_MORE_EVIDENCE":
        return "OEM_EVIDENCE_MISSING"
    if disp == "SEMANTIC_CONFLICT":
        return "GENUINE_SEMANTIC_CONFLICT"
    if disp == "INDUSTRIAL_EXCEPTION_CANDIDATE":
        return "INDUSTRIAL_EXCEPTION_PENDING_OWNER_OVERRIDE"
    if disp == "OWNER_DECISION_REQUIRED":
        return "ENGINEERING_REVIEW_PENDING"
    if disp == "CATALOG_EXIT_CANDIDATE":
        if basis == "OEM_DOCUMENTED":
            return "EXIT_CANDIDATE_OEM_BACKED_CONFIRMATION"
        return "EXIT_CANDIDATE_HEURISTIC_CONFIRMATION"
    return "OWNER_REVIEW_REQUIRED"


def proposed_owner_action(row: dict[str, str]) -> str:
    disp = row["proposed_disposition"]
    if disp == "CATALOG_EXIT_CANDIDATE":
        return "CONFIRM_OR_REJECT_CATALOG_EXIT"
    if disp == "INDUSTRIAL_EXCEPTION_CANDIDATE":
        return "APPROVE_OR_REJECT_INDUSTRIAL_EXCEPTION (no automatic rehome)"
    if disp == "NEEDS_MORE_EVIDENCE":
        return "PROVIDE_OEM_OR_SPEC_EVIDENCE"
    if disp == "SEMANTIC_CONFLICT":
        return "RESOLVE_CONFLICTING_EVIDENCE"
    return "OWNER_ENGINEERING_DECISION"


def build_owner_queue(reviews: list[dict[str, str]]) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    for row in reviews:
        if row.get("owner_review_required") != "YES":
            continue
        queue.append(
            {
                "product_id": row["product_id"],
                "sku": row["sku"],
                "current_name": row["current_name"],
                "proposed_disposition": row["proposed_disposition"],
                "proposed_industrial_domain_code": row["proposed_industrial_domain_code"],
                "queue_category": queue_category_for(row),
                "proposed_owner_action": proposed_owner_action(row),
                "rationale_summary": row["decision_rationale"][:500],
                "evidence_strength": row["evidence_strength"],
                "confidence_basis": row["confidence_basis"],
            }
        )
    if len(queue) != 262:
        raise RuntimeError(f"owner_queue_must_cover_all_262 got={len(queue)}")
    return queue


def build_product_reviews(cohort: list[dict[str, str]]) -> list[dict[str, str]]:
    return [review_row_to_dict(_classify(row)) for row in cohort]


def disposition_counts(reviews: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {d: 0 for d in PRIMARY_DISPOSITIONS}
    for row in reviews:
        disp = row["proposed_disposition"]
        if disp not in counts:
            raise RuntimeError(f"unexpected_disposition {disp}")
        counts[disp] += 1
    return counts


def industrial_exception_primary_count(reviews: list[dict[str, str]]) -> int:
    return sum(
        1
        for r in reviews
        if r["proposed_disposition"] == "INDUSTRIAL_EXCEPTION_CANDIDATE"
    )


def semantic_conflict_count(reviews: list[dict[str, str]]) -> int:
    return sum(1 for r in reviews if r["proposed_disposition"] == "SEMANTIC_CONFLICT")


def proposed_domain_counts(reviews: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in reviews:
        code = row.get("proposed_industrial_domain_code") or ""
        if not code:
            continue
        if code not in APPROVED_DOMAIN_CODES:
            raise RuntimeError(f"invalid_proposed_domain {code}")
        counts[code] = counts.get(code, 0) + 1
    return counts


def validate_primary_partition(reviews: list[dict[str, str]]) -> None:
    if len(reviews) != 262:
        raise RuntimeError(f"review_row_count {len(reviews)}")
    ids = [int(r["product_id"]) for r in reviews]
    if len(set(ids)) != 262:
        raise RuntimeError("duplicate_product_ids_in_review")
    counts = disposition_counts(reviews)
    if sum(counts.values()) != 262:
        raise RuntimeError("disposition_sum_mismatch")
    if semantic_conflict_count(reviews) > 0:
        for row in reviews:
            if row["proposed_disposition"] == "SEMANTIC_CONFLICT":
                if row["proposed_industrial_domain_code"]:
                    raise RuntimeError(
                        "semantic_conflict_must_not_carry_approved_domain_tag"
                    )


def external_source_register_rows() -> list[dict[str, str]]:
    return list(EXTERNAL_SOURCES)
