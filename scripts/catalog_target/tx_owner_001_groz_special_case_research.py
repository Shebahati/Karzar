"""Curated OEM / market evidence for TX-OWNER-001 Groz special cases (2915, 3238)."""

from __future__ import annotations

from typing import Any

# evidence_match_type: EXACT_SKU_OEM_PAGE | OEM_PRODUCT_FAMILY | TITLE_SEMANTIC_ONLY | UNRESOLVED
GROZ_OEM_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "GROZ-OEM-COB-CUTOFF",
        "source_url": "https://groz-tools.com/precision-tools/cutting-tools/cut-off-blades-cob-h-0-4.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "COB/H/* Cut Off Blades (HSS Grade B)",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Groz cut-off blades for lathe turning/cutting; suitable for lathe machines per OEM."
        ),
        "related_karzar_product_ids": "2915",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-TB-TOOLBIT",
        "source_url": "https://groz-tools.com/precision-tools/cutting-tools/tool-bit-tb-0-1.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "TB-* Square Tool Bits (cobalt HSS Grade A)",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Square HSS/cobalt tool bits for lathe, planer, shaper metal removal (OEM Cutting Tools)."
        ),
        "related_karzar_product_ids": "2915",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-WW-PLANE",
        "source_url": "https://groz-tools.com/hand-tools/woodworking-tools/woodworking-planes.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "SP/JP/FP Woodworking bench planes",
        "evidence_class": "OEM_CATEGORY_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Separate Groz line: spring-steel plane cutter blades for woodworking bench planes "
            "(not indexed CNC inserts)."
        ),
        "related_karzar_product_ids": "2915",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-MARKET-PARTING-HOLDER-FA",
        "source_url": "https://azarsanat.net/product/%d9%87%d9%84%d8%af%d8%b1-%d8%aa%db%8c%d8%ba%da%86%d9%87-%d8%a8%d8%b1%d8%b4-%d8%aa%d8%b1%d8%a7%d8%b4%da%a9%d8%a7%d8%b1%d9%89-%da%af%d8%b1%d9%88%d8%b2-%d9%87%d9%86%d8%af/",
        "manufacturer": "Groz (India) — distributor listing",
        "model_identity": "PT/* parting tool holders (holders sold without blade)",
        "evidence_class": "DISTRIBUTOR_PRODUCT_PAGE",
        "evidence_match_type": "TITLE_SEMANTIC_ONLY",
        "supported_claim": (
            "Iranian distributor documents Groz «تیغچه برش تراشکاری» / parting-off tooling family; "
            "does not map Karzar SKU 2064 to a Groz article."
        ),
        "related_karzar_product_ids": "2915",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-MJ-MACHINIST-JACK",
        "source_url": "https://groz-tools.com/precision-tools/set-up-tools/machinist-sjack-mj-01.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "MJ/01 Machinist's Jack (Ord Nr. 14100)",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "TITLE_SEMANTIC_ONLY",
        "supported_claim": (
            "Machinist jack for leveling/adjusting drill presses, milling machines, planers; "
            "metalworking setup tool — not a hydraulic vehicle jack."
        ),
        "related_karzar_product_ids": "3238",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-HYDRAULIC-JACK-BT",
        "source_url": "https://groz-tools.com/services-tools-jack-bt-4w.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "JACK/BT/* Hydraulic bottle jacks",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Competing Groz product class: automotive/industrial lifting jacks — outside "
            "precision machine setup workholding."
        ),
        "related_karzar_product_ids": "3238",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
]

SPECIAL_CASE_PRODUCTS: dict[int, dict[str, Any]] = {
    2915: {
        "karzar_catalog_sku": "2064",
        "manufacturer_code_in_census": "",
        "preserved_title_fa": "تیغچه رنده تراشکارى گروز هند",
        "preserved_category_id": "160",
        "historical_pr499_proposal": "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "historical_pr499_domain": "KZ.DOM.CUTTING",
        "application_primary": "LATHE_CUTOFF_OR_TURNING_TOOL_BLADE_METALWORKING",
        "application_competing": "WOODWORKING_BENCH_PLANE_REPLACEMENT_BLADE",
        "confidence_level": "MEDIUM",
        "confidence_basis": "OEM_PRODUCT_FAMILY_PLUS_TITLE",
        "proposed_industrial_domain": "KZ.DOM.CUTTING",
        "agent_proposal": "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "competing_interpretations": (
            "A) Metal lathe cut-off / square tool bit (Groz COB/TB Cutting Tools) — title uses "
            "تراشکاری and Iranian distributors label Groz parting blades as تیغچه برش تراشکاری. "
            "B) Woodworking bench plane blade (Groz SP/JP planes) — current category 160 woodworking; "
            "«رنده» can mean plane in Persian. "
            "C) UNRESOLVED SKU — Karzar internal SKU 2064 is not a Groz article number; no dimensions."
        ),
        "unresolved_questions": (
            "Physical dimensions and grade; which Groz article (COB/*, TB/*, or plane spare); "
            "photograph or packing slip; confirm not woodworking-only consumable."
        ),
        "owner_options": (
            "APPROVE_INDUSTRIAL_EXCEPTION_KZ.DOM.CUTTING | "
            "REJECT_INDUSTRIAL_EXCEPTION_APPROVE_CATALOG_EXIT | "
            "REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
    },
    3238: {
        "karzar_catalog_sku": "4457",
        "manufacturer_code_in_census": "",
        "preserved_title_fa": "جک ماشین کارى گروز هند",
        "preserved_category_id": "158",
        "historical_pr499_proposal": "OWNER_DECISION_REQUIRED",
        "historical_pr499_domain": "",
        "application_primary": "MACHINIST_SETUP_JACK_METALWORKING",
        "application_competing": "HYDRAULIC_LIFTING_JACK_GENERAL_WORKSHOP",
        "confidence_level": "MEDIUM",
        "confidence_basis": "OEM_TITLE_SEMANTIC_MATCH",
        "proposed_industrial_domain": "KZ.DOM.WORKHOLDING",
        "agent_proposal": "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "competing_interpretations": (
            "A) Groz MJ/01 class machinist jack — leveling drill/mill/planer (setup/workholding). "
            "B) Groz JACK/BT hydraulic bottle jack — vehicle/heavy load lifting (workshop, not "
            "machine setup). "
            "C) UNRESOLVED SKU — Karzar SKU 4457 ≠ Groz Ord Nr.; same numeric SKU exists for "
            "unrelated San OU morse taper product in census."
        ),
        "unresolved_questions": (
            "Confirm unit is MJ/01 (or Groz setup jack) vs hydraulic jack; load rating; "
            "photograph; importer invoice with Groz article."
        ),
        "owner_options": (
            "APPROVE_INDUSTRIAL_EXCEPTION_KZ.DOM.WORKHOLDING | "
            "APPROVE_CATALOG_EXIT | "
            "REQUEST_MORE_EVIDENCE | DEFER_DECISION"
        ),
    },
}


def sources_for_product(product_id: int) -> list[dict[str, str]]:
    pid = str(product_id)
    return [s for s in GROZ_OEM_SOURCES if pid in s.get("related_karzar_product_ids", "")]
