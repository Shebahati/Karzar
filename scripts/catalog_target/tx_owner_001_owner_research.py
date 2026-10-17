"""Curated OEM / technical research for TX-OWNER-001 Owner decision package."""

from __future__ import annotations

from typing import Any

# verification_status: HUMAN_VERIFIED_URL | INFERRED_FROM_OEM_DOC | UNRESOLVED
OEM_TECHNICAL_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "OEM-M7-158",
        "source_url": "https://www.mighty-seven.com/product/158",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "QA-210 A/B Air Die Grinder",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "supported_claim": "Handheld pneumatic die grinder (air tool).",
        "product_ids": "5194",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-159",
        "source_url": "https://www.mighty-seven.com/product/159",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "QA-211 A/B Air Die Grinder",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "supported_claim": "Handheld pneumatic die grinder with collet sizes.",
        "product_ids": "5195",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-NC4233Q",
        "source_url": "https://www.mighty-seven.com/product/19",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "NC-4233Q Air Impact Wrench 1/2in",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "supported_claim": "Pneumatic impact wrench (assembly/maintenance air tool).",
        "product_ids": "5139,5140",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA301",
        "source_url": "https://www.mighty-seven.com/product/449",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "PA-301 Air Hydraulic Riveter",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "supported_claim": "Blind riveter for fastening; portable workshop assembly tool.",
        "product_ids": "5177,5178",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-PA201-PDF",
        "source_url": "https://extranet.mykingtony.com/Shared/Notices/PA301.pdf",
        "manufacturer": "Mighty Seven / King Tony lineage",
        "model_identity": "PA-201 / PA-211 riveter family specs",
        "evidence_class": "OEM_SPEC_SHEET",
        "supported_claim": "PA-201 and PA-211 are pneumatic riveter models in riveter capacity table.",
        "product_ids": "5174,5176",
        "verification_status": "HUMAN_VERIFIED_URL",
    },
    {
        "source_id": "OEM-M7-JC304",
        "source_url": "https://www.mighty-seven.com/product_category/Air%20Blow%20Gun",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "JC-series air blow guns",
        "evidence_class": "OEM_CATEGORY_PAGE",
        "supported_claim": "JC304/JC405 etc. are air blow guns (workshop pneumatic).",
        "product_ids": "5124,5125,5126,5127",
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
        "evidence_assessment": (
            "MEDIUM heuristic from Persian title (تراشکاری); not OEM-verified in this pass."
        ),
        "recommended_owner_options": (
            "APPROVE_INDUSTRIAL_EXCEPTION | REJECT_EXIT_REQUEST_EXCEPTION_REVIEW | REQUEST_MORE_EVIDENCE"
        ),
        "default_if_no_owner_input": "REQUEST_MORE_EVIDENCE",
    },
    3238: {
        "investigation_summary": (
            "Groz SKU 4457 «جک ماشین کارى» — machine shop jack/lift accessory. "
            "Could be workshop support or workholding-adjacent; no Groz OEM page verified here."
        ),
        "application_class": "MACHINE_SHOP_JACK_AMBIGUOUS",
        "oem_status": "UNRESOLVED",
        "pr499_proposal": "OWNER_DECISION_REQUIRED",
        "evidence_assessment": "LOW — census title only.",
        "recommended_owner_options": (
            "APPROVE_CATALOG_EXIT | APPROVE_INDUSTRIAL_EXCEPTION | REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
        "default_if_no_owner_input": "REQUEST_MORE_EVIDENCE",
    },
}

# Priority-B spotlight (not part of the 20 critical matrix unless in NEEDS_MORE set)
EXIT_SPOTLIGHT_NOTES: dict[int, dict[str, str]] = {
    3008: {
        "note": "Parallel clamp — workshop; LOW-confidence exit in PR499.",
        "review_path": "APPROVE_CATALOG_EXIT or REQUEST_MORE_EVIDENCE",
    },
    3009: {
        "note": "Band-saw mill arbor extension (Groz) — workshop saw accessory.",
        "review_path": "APPROVE_CATALOG_EXIT or REQUEST_MORE_EVIDENCE",
    },
}

# Grooving / finishing blades: insufficient OEM in audit pass — retain NEEDS_MORE_EVIDENCE
for pid in (
    3090, 3091, 3093, 3095, 3096, 3097, 3098, 3099, 3101,
):
    CRITICAL_CASE_ASSESSMENTS[pid] = {
        "investigation_summary": (
            "Title suggests grooving or finishing blade; material (wood router vs metal lathe) "
            "not established from preserved census and no SKU-matched OEM page in this pass."
        ),
        "application_class": "GROOVING_OR_FINISHING_BLADE_UNRESOLVED",
        "oem_status": "UNRESOLVED",
        "pr499_proposal": "NEEDS_MORE_EVIDENCE",
        "evidence_assessment": "UNRESOLVED — do not infer metalworking from CNC token alone.",
        "recommended_owner_options": (
            "APPROVE_CATALOG_EXIT | APPROVE_INDUSTRIAL_EXCEPTION | REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
        "default_if_no_owner_input": "REQUEST_MORE_EVIDENCE",
    }

# M7 models resolved via OEM where matched
M7_SKU_OEM_RESOLUTION: dict[str, dict[str, str]] = {
    "NC4233Q": {
        "oem_source_id": "OEM-M7-NC4233Q",
        "identity": "NC-4233Q Air Impact Wrench",
        "workshop_scope": "YES",
        "updates_disposition_proposal": "CATALOG_EXIT_CANDIDATE",
        "evidence_assessment": "OEM_DOCUMENTED workshop air tool",
    },
    "NC4233QH": {
        "oem_source_id": "OEM-M7-NC4233Q",
        "identity": "NC-4233QH variant (impact wrench family)",
        "workshop_scope": "YES",
        "updates_disposition_proposal": "CATALOG_EXIT_CANDIDATE",
        "evidence_assessment": "OEM family match; variant not individually fetched",
    },
    "PA301": {
        "oem_source_id": "OEM-M7-PA301",
        "identity": "PA-301 Air Hydraulic Riveter",
        "workshop_scope": "YES",
        "updates_disposition_proposal": "CATALOG_EXIT_CANDIDATE",
        "evidence_assessment": "OEM_DOCUMENTED",
    },
    "PA301V": {
        "oem_source_id": "OEM-M7-PA301",
        "identity": "PA-301V riveter variant",
        "workshop_scope": "YES",
        "updates_disposition_proposal": "CATALOG_EXIT_CANDIDATE",
        "evidence_assessment": "OEM family (PA-301V in spec PDF table)",
    },
    "PA201": {
        "oem_source_id": "OEM-M7-PA201-PDF",
        "identity": "PA-201 pneumatic riveter",
        "workshop_scope": "YES",
        "updates_disposition_proposal": "CATALOG_EXIT_CANDIDATE",
        "evidence_assessment": "OEM spec sheet table",
    },
    "PA211": {
        "oem_source_id": "OEM-M7-PA201-PDF",
        "identity": "PA-211 pneumatic riveter",
        "workshop_scope": "YES",
        "updates_disposition_proposal": "CATALOG_EXIT_CANDIDATE",
        "evidence_assessment": "OEM spec sheet table",
    },
}



def sources_for_product_id(product_id: int) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    pid = str(product_id)
    for src in OEM_TECHNICAL_SOURCES:
        ids = src.get("product_ids", "")
        if pid in {x.strip() for x in ids.split(",")}:
            hits.append(src)
            continue
        for part in ids.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-", 1)
                if lo.isdigit() and hi.isdigit() and int(lo) <= product_id <= int(hi):
                    hits.append(src)
    return hits


def resolve_m7_sku(sku: str) -> dict[str, str] | None:
    key = (sku or "").strip().upper()
    return M7_SKU_OEM_RESOLUTION.get(key)
