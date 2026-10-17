"""Curated OEM / technical research for TX-OWNER-001 Owner decision package."""

from __future__ import annotations

from typing import Any

# evidence_match_type: EXACT_SKU_OEM_PAGE | EXACT_OEM_MODEL_PAGE | UNRESOLVED | HEURISTIC
OEM_TECHNICAL_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "OEM-M7-158",
        "source_url": "https://www.mighty-seven.com/product/158",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "QA-210 A/B Air Die Grinder",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_MODEL_PAGE",
        "supported_claim": "Handheld pneumatic die grinder (air tool).",
        "product_ids": "5194",
        "sku_match": "QA210A",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-159",
        "source_url": "https://www.mighty-seven.com/product/159",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "QA-211 A/B Air Die Grinder",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_MODEL_PAGE",
        "supported_claim": "Handheld pneumatic die grinder with collet sizes.",
        "product_ids": "5195",
        "sku_match": "QA211A",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-NC4233Q",
        "source_url": "https://www.mighty-seven.com/product/19",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "NC-4233Q Air Impact Wrench",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "1/2in pneumatic impact wrench (workshop air tool).",
        "product_ids": "5139",
        "sku_match": "NC4233Q",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-NC4233QH",
        "source_url": "https://www.mighty-seven.com/product/20",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "NC-4233QH Air Impact Wrench",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "1/2in pneumatic impact wrench variant (workshop air tool).",
        "product_ids": "5140",
        "sku_match": "NC4233QH",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA201",
        "source_url": "https://www.mighty-seven.com/product/443",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "PA-201 Air Hydraulic Riveter",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "Pneumatic hydraulic blind riveter (assembly air tool).",
        "product_ids": "5174",
        "sku_match": "PA201",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA211",
        "source_url": "https://www.mighty-seven.com/product/445",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "PA-211 Air Hydraulic Riveter",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "Pneumatic hydraulic blind riveter (assembly air tool).",
        "product_ids": "5176",
        "sku_match": "PA211",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA301",
        "source_url": "https://www.mighty-seven.com/product/449",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "PA-301 Air Hydraulic Riveter",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "Pneumatic hydraulic blind riveter.",
        "product_ids": "5177",
        "sku_match": "PA301",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA301V",
        "source_url": "https://www.mighty-seven.com/product/448",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "PA-301V Air Hydraulic Riveter",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "Pneumatic hydraulic blind riveter variant.",
        "product_ids": "5178",
        "sku_match": "PA301V",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA203N",
        "source_url": "https://www.mighty-seven.com/product/452",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "PA-203N Air Hydraulic Riveter",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "supported_claim": "Pneumatic hydraulic blind riveter (assembly air tool).",
        "product_ids": "5175",
        "sku_match": "PA203N",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-JC304",
        "source_url": "https://www.mighty-seven.com/product_category/Air%20Blow%20Gun",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "JC-series air blow guns",
        "evidence_class": "OEM_CATEGORY_PAGE",
        "evidence_match_type": "FAMILY_LEVEL_INFERENCE",
        "supported_claim": "JC304/JC405 SKUs are air blow guns per OEM category listing.",
        "product_ids": "5124,5125,5126,5127",
        "sku_match": "JC*",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
]

CRITICAL_CASE_ASSESSMENTS: dict[int, dict[str, Any]] = {
    2915: {
        "investigation_summary": (
            "Title «تیغچه رنده تراشکارى» indicates lathe turning insert (metalworking). "
            "Mis-categorized under woodworking category 160."
        ),
        "application_class": "METALWORKING_TURNING_INSERT",
        "oem_status": "NO_OEM_SHEET_IN_AUDIT",
        "pr499_proposal": "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "post_research_disposition": "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "evidence_assessment": (
            "MEDIUM heuristic from Persian title (تراشکاری); not OEM-verified in this pass."
        ),
        "recommended_owner_options": (
            "APPROVE_INDUSTRIAL_EXCEPTION | REJECT_EXIT_REQUEST_EXCEPTION_REVIEW | REQUEST_MORE_EVIDENCE"
        ),
    },
    3238: {
        "investigation_summary": (
            "Groz SKU 4457 «جک ماشین کارى» — machine shop jack/lift accessory. "
            "No Groz OEM page verified in this pass."
        ),
        "application_class": "MACHINE_SHOP_JACK_AMBIGUOUS",
        "oem_status": "UNRESOLVED",
        "pr499_proposal": "OWNER_DECISION_REQUIRED",
        "post_research_disposition": "OWNER_DECISION_REQUIRED",
        "evidence_assessment": "LOW — census title only.",
        "recommended_owner_options": (
            "APPROVE_CATALOG_EXIT | APPROVE_INDUSTRIAL_EXCEPTION | REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
    },
}

for pid in (5146, 5147):
    CRITICAL_CASE_ASSESSMENTS[pid] = {
        "investigation_summary": (
            "M7 model code in census only; no verified OEM page for this exact SKU "
            "(do not infer NC4277Q / NC4299Q or other suffix variants)."
        ),
        "application_class": "M7_PNEUMATIC_TOOL_UNRESOLVED_SKU",
        "oem_status": "UNRESOLVED",
        "pr499_proposal": "NEEDS_MORE_EVIDENCE",
        "post_research_disposition": "NEEDS_MORE_EVIDENCE",
        "evidence_assessment": "UNRESOLVED — exact SKU OEM page not matched.",
        "recommended_owner_options": (
            "APPROVE_CATALOG_EXIT | APPROVE_INDUSTRIAL_EXCEPTION | REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
    }

for pid in (3090, 3091, 3093, 3095, 3096, 3097, 3098, 3099, 3101):
    CRITICAL_CASE_ASSESSMENTS[pid] = {
        "investigation_summary": (
            "Grooving/finishing blade — material/application not established from census title alone."
        ),
        "application_class": "GROOVING_OR_FINISHING_BLADE_UNRESOLVED",
        "oem_status": "UNRESOLVED",
        "pr499_proposal": "NEEDS_MORE_EVIDENCE",
        "post_research_disposition": "NEEDS_MORE_EVIDENCE",
        "evidence_assessment": "UNRESOLVED — do not infer metalworking from CNC token alone.",
        "recommended_owner_options": (
            "APPROVE_CATALOG_EXIT | APPROVE_INDUSTRIAL_EXCEPTION | REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
    }

# Exact SKU → post-research upgrade (M7 workshop air tools with verified OEM product pages)
M7_SKU_OEM_RESOLUTION: dict[str, dict[str, str]] = {
    "NC4233Q": {
        "oem_source_id": "OEM-M7-NC4233Q",
        "identity": "NC-4233Q Air Impact Wrench",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
    "NC4233QH": {
        "oem_source_id": "OEM-M7-NC4233QH",
        "identity": "NC-4233QH Air Impact Wrench",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
    "PA201": {
        "oem_source_id": "OEM-M7-PA201",
        "identity": "PA-201 Air Hydraulic Riveter",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
    "PA211": {
        "oem_source_id": "OEM-M7-PA211",
        "identity": "PA-211 Air Hydraulic Riveter",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
    "PA301": {
        "oem_source_id": "OEM-M7-PA301",
        "identity": "PA-301 Air Hydraulic Riveter",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
    "PA301V": {
        "oem_source_id": "OEM-M7-PA301V",
        "identity": "PA-301V Air Hydraulic Riveter",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
    "PA203N": {
        "oem_source_id": "OEM-M7-PA203N",
        "identity": "PA-203N Air Hydraulic Riveter",
        "evidence_match_type": "EXACT_SKU_OEM_PAGE",
        "post_research_disposition": "CATALOG_EXIT_CANDIDATE",
    },
}


def sources_for_product_id(product_id: int) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    pid = str(product_id)
    for src in OEM_TECHNICAL_SOURCES:
        ids = src.get("product_ids", "")
        if pid in {x.strip() for x in ids.split(",")}:
            hits.append(src)
    return hits


def resolve_m7_sku_exact(sku: str) -> dict[str, str] | None:
    """Exact catalog SKU match only — no suffix inference (NC4277 ≠ NC4277Q)."""
    key = (sku or "").strip().upper()
    return M7_SKU_OEM_RESOLUTION.get(key)


def resolve_m7_sku(sku: str) -> dict[str, str] | None:
    return resolve_m7_sku_exact(sku)
