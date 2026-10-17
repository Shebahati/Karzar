"""Curated OEM evidence for TX-OWNER-001 P0 industrial boundary research (19 SKUs)."""

from __future__ import annotations

from typing import Any

from catalog_target.tx_owner_001_external_sources import APPROVED_DOMAIN_CODES

P0_PRODUCT_IDS: list[int] = [
    3008,
    3009,
    3010,
    3184,
    5227,
    5259,
    5260,
    5261,
    5267,
    5268,
    5285,
    5287,
    5289,
    5295,
    5296,
    5297,
    5298,
    5301,
    5302,
]

OWNER_OPTIONS = (
    "APPROVE_CATALOG_EXIT | REJECT_EXIT_REQUEST_EXCEPTION_REVIEW | "
    "APPROVE_INDUSTRIAL_EXCEPTION | REQUEST_MORE_EVIDENCE | DEFER_DECISION"
)

# evidence_match_type: EXACT_OEM_ARTICLE_MATCH | OEM_FAMILY_REFERENCE | NEAR_MODEL_REFERENCE | UNRESOLVED
OEM_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "MARKET-PARALLEL-CLAMP-WOOD",
        "source_url": "https://www.thespruce.com/types-of-clamps-6827232",
        "manufacturer": "Trade reference (woodworking)",
        "model_identity": "Parallel clamp — woodworking joinery",
        "evidence_class": "MARKET_REFERENCE",
        "evidence_match_type": "OEM_FAMILY_REFERENCE",
        "supported_claim": (
            "Parallel clamps are primarily documented for wood joinery/panel glue-ups; "
            "not machine-tool workholding fixtures."
        ),
        "related_karzar_product_ids": "3008",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-SLITTING-SAW-ARBOR-FAMILY",
        "source_url": "https://www.indiamart.com/groz-tools/machine-tool-accessories.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "SA/1, SA/2, SA/R8 Slitting Saw Arbors",
        "evidence_class": "OEM_DISTRIBUTOR_PAGE",
        "evidence_match_type": "OEM_FAMILY_REFERENCE",
        "supported_claim": (
            "Groz slitting/slotting saw arbors mount saw blades on milling/collet interfaces — "
            "machine-tool toolholding accessory."
        ),
        "related_karzar_product_ids": "3009",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-WHEEL-DRESSER-WD",
        "source_url": "https://groz-tools.com/precision-tools/cutting-tools/wheel-dressers-wd-2.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "WD/00–WD/02 Wheel Dressers",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "OEM_FAMILY_REFERENCE",
        "supported_claim": (
            "Emery wheel dressers true/sharpen solid abrasive grinding wheels — "
            "bench grinder maintenance accessory."
        ),
        "related_karzar_product_ids": "3010",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "GROZ-OEM-HAND-SCRAPER-ES",
        "source_url": "https://groz-tools.com/precision-tools/set-up-tools/hand-scrapers-half-round-type-es-hr-3.html",
        "manufacturer": "Groz Engineering Tools (India)",
        "model_identity": "ES/HR/*, ES/F/* Engineers Hand Scrapers",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "OEM_FAMILY_REFERENCE",
        "supported_claim": (
            "Groz engineers hand scrapers for slideways, bearings, surface plates — "
            "precision fitting hand tool (setup/scraping), not a measuring instrument."
        ),
        "related_karzar_product_ids": "3184",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-QE98L-LEVEL-ACCESSORY",
        "source_url": "https://www.itmtools.com.au/product/225-m7-double-axis-bubble-spirit-level-gradienter-suit-all-m7-air-drills",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "M7A-QE98L / QE-98L drill-mounted spirit level",
        "evidence_class": "DISTRIBUTOR_PRODUCT_PAGE",
        "evidence_match_type": "NEAR_MODEL_REFERENCE",
        "supported_claim": (
            "Bubble spirit level gradienter for M7 air drills — workshop alignment aid, "
            "not calibrated metrology."
        ),
        "related_karzar_product_ids": "5227",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SB201-TYRE-INFLATOR",
        "source_url": "https://www.mighty-seven.com/product/544",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SB-201 Digital Tyre Inflator",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Digital tyre inflator with tyre-valve clip; OEM classifies as tyre inflator, not metrology.",
        "related_karzar_product_ids": "5259",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SB423-TYRE-INFLATOR",
        "source_url": "https://mighty-seven.com/product/543",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SB-423 Tyre Inflator",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Analog tyre inflator/gauge for tyre valve inflation — automotive/service workshop.",
        "related_karzar_product_ids": "5260",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SB710-TYRE-INFLATOR",
        "source_url": "https://www.mighty-seven.com/product/546",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SB-710 Tyre Inflator Tyre Valve Clip",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Tyre inflator with dial gauge — tyre service, not industrial metrology.",
        "related_karzar_product_ids": "5261",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SG101-LUBRICATION-KIT",
        "source_url": "https://www.mighty-seven.com/product/2835",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SG-101 Lubrication Kit",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": (
            "Air-tool lubricant kit (tube + applicator) — maintenance consumable kit, "
            "not a metalworking fluid product listing."
        ),
        "related_karzar_product_ids": "5267",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SG400-GREASE-GUN",
        "source_url": "https://www.mighty-seven.com/product/496",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SG-400 Air Grease Gun (400 c.c.)",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Pneumatic grease gun/dispensing tool — equipment, not bulk metalworking fluid.",
        "related_karzar_product_ids": "5268",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SP102-BALANCER",
        "source_url": "https://www.mighty-seven.com/product/2918",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SP-102 Spring Balancer 0.6–1.5 kg",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Spring balancer for hanging pneumatic tools above workstation — shop air-tool accessory.",
        "related_karzar_product_ids": "5285",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SP104-BALANCER",
        "source_url": "https://mighty-seven.com/product/2920",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SP-104 Spring Balancer 1.5–3.0 kg",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Spring tool balancer with rated load band — workshop ergonomics, not machine workholding.",
        "related_karzar_product_ids": "5287",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SP105-BALANCER",
        "source_url": "https://mighty-seven.com/product/2921",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SP-105 Spring Balancer 3.0–5.0 kg",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Spring balancer for pneumatic tools — rated capacity documented on OEM page.",
        "related_karzar_product_ids": "5289",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SV1360-FILTER-REG",
        "source_url": "https://www.mighty-seven.com/product/582",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SV-1360 Filter, Regulator (not lubricator)",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "3/8 in compressed-air filter/regulator unit — shop air prep, not CNC machine component by itself.",
        "related_karzar_product_ids": "5295",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SV2220-FRL",
        "source_url": "https://www.mighty-seven.com/product/580",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SV-2220 Filter, Regulator, Lubricator",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "1/4 in FRL combo — general pneumatic line conditioning for air tools.",
        "related_karzar_product_ids": "5296",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SV2380-FRL",
        "source_url": "https://www.mighty-seven.com/product/587",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SV-2380 Filter, Regulator, Lubricator",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "3/8 in FRL unit — compressed-air accessory; does not constitute metalworking fluid domain.",
        "related_karzar_product_ids": "5297",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SW12-MINI-LUBRICATOR",
        "source_url": "https://www.mighty-seven.com/product/605",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SW-12 Mini Lubricator",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "In-line mini lubricator for air hose — pneumatic tool maintenance accessory.",
        "related_karzar_product_ids": "5298",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SY2001M-ROTARY-ADAPTOR",
        "source_url": "https://www.mighty-seven.com/product/2851",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SY-2001M 360° Rotatable Adaptor",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": (
            "OEM documents SY-2001M as 360° rotatable air adaptor (1/4 in) — "
            "not a pressure regulator despite Karzar title wording."
        ),
        "related_karzar_product_ids": "5301",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-SZ212A-REGULATOR",
        "source_url": "https://www.mighty-seven.com/product/2829",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "SZ-212A Air Regulator",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "EXACT_OEM_ARTICLE_MATCH",
        "supported_claim": "Inline air flow regulator for pneumatic tools — workshop air accessory.",
        "related_karzar_product_ids": "5302",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
]

P0_PRODUCTS: dict[int, dict[str, Any]] = {
    3008: {
        "karzar_catalog_sku": "3104",
        "preserved_title_fa": "کلمپ موازى",
        "preserved_brand": "",
        "preserved_category_id": "158",
        "research_priority": "PARALLEL_CLAMP_WORKHOLDING",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "Brandless parallel clamp (internal SKU 3104). Market references classify parallel "
            "clamps primarily as woodworking assembly clamps, not CNC/metal machine workholding "
            "(vises, fixture plates, toggle clamps). No OEM article for SKU 3104."
        ),
        "exact_manufacturer_identity_status": "UNRESOLVED",
        "exact_manufacturer_article": "",
        "oem_match_classification": "UNRESOLVED",
        "karzar_product_oem_identity_verification": "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH",
        "proposed_application_class": "WOODWORKING_OR_GENERAL_PARALLEL_CLAMP_HYPOTHESIS",
        "competing_interpretations": (
            "A) Woodworking/general parallel jaw clamp per title «کلمپ موازى». "
            "B) Metal shop bar clamp for welding/fabrication — still general workshop, not precision "
            "machine workholding domain. C) UNRESOLVED — no brand, size, or jaw capacity in census."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "LOW",
        "confidence_basis": "TITLE_SEMANTIC_PLUS_MARKET_REFERENCE_ONLY",
        "confidence_scope_note": "Does not verify physical unit or map to any workholding OEM article.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "REQUEST_MORE_EVIDENCE",
        "unresolved_questions": "Jaw opening, bar length, brand, photos; confirm not Bessey/Irwin woodworking SKU misfiled.",
    },
    3009: {
        "karzar_catalog_sku": "3106",
        "preserved_title_fa": "دنباله فرز اره اى گروز هند",
        "preserved_brand": "Groz | گروز",
        "preserved_category_id": "158",
        "research_priority": "SAW_MILLING_ARBOR_TOOLHOLDING",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "Persian title indicates Groz slitting/saw arbor («دنباله فرز اره‌ای»). Groz OEM documents "
            "SA/* slitting saw arbors for milling/collet mounting — KZ.DOM.TOOLHOLDING class accessory. "
            "Karzar internal SKU 3106 is not a Groz catalog number; exact SA/* variant unproven."
        ),
        "exact_manufacturer_identity_status": "UNRESOLVED",
        "exact_manufacturer_article": "",
        "oem_match_classification": "OEM_FAMILY_REFERENCE",
        "karzar_product_oem_identity_verification": "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH",
        "proposed_application_class": "SLITTING_SAW_ARBOR_METALWORKING_TOOLHOLDING",
        "competing_interpretations": (
            "A) Groz slitting saw arbor (toolholding for saw blade on mill/collet). "
            "B) Hole-saw arbor or woodworking saw arbor — no specs in census. "
            "C) UNRESOLVED — SKU 3106 not mapped to Groz SA/1, SA/2, or SA/R8."
        ),
        "industrial_domain_hypothesis": "KZ.DOM.TOOLHOLDING",
        "approved_domain_fit_assessment": "UNPROVEN",
        "confidence_level": "MEDIUM",
        "confidence_basis": "APPLICATION_HYPOTHESIS_OEM_FAMILY_PLUS_GROZ_BRAND_TITLE",
        "confidence_scope_note": "MEDIUM applies to application class only; exact Groz article for Karzar row unverified.",
        "post_research_agent_proposal": "INDUSTRIAL_EXCEPTION_CANDIDATE",
        "recommended_owner_review_option": "REQUEST_MORE_EVIDENCE",
        "unresolved_questions": "Shank type (straight vs R8), saw bore range, Groz article on label/packing slip, photo.",
    },
    3010: {
        "karzar_catalog_sku": "3109",
        "preserved_title_fa": "قرقره سنگ صاف کن گروز هند",
        "preserved_brand": "Groz | گروز",
        "preserved_category_id": "158",
        "research_priority": "GRINDING_WHEEL_DRESSER",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "Title matches Groz emery/wheel dresser («قرقره سنگ صاف‌کن»). Groz WD/* dressers maintain "
            "bench grinding wheels — industrial maintenance accessory but not one of the seven target "
            "product domains (not cutting insert, toolholder, workholding, machine, metrology, thread, fluid)."
        ),
        "exact_manufacturer_identity_status": "UNRESOLVED",
        "exact_manufacturer_article": "",
        "oem_match_classification": "OEM_FAMILY_REFERENCE",
        "karzar_product_oem_identity_verification": "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH",
        "proposed_application_class": "BENCH_GRINDER_WHEEL_DRESSER_MAINTENANCE",
        "competing_interpretations": (
            "A) Groz WD wheel dresser for solid abrasive wheels. "
            "B) Handheld generic dresser — brand Groz supports A. "
            "C) UNRESOLVED size (WD/00 vs WD/02) — internal SKU 3109 not Groz article."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "MEDIUM",
        "confidence_basis": "APPLICATION_HYPOTHESIS_OEM_FAMILY_PLUS_TITLE",
        "confidence_scope_note": "Domain fit negative; application hypothesis does not authorize exception without Owner policy.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "Confirm WD size on unit; photo for Groz article stamp.",
    },
    3184: {
        "karzar_catalog_sku": "4318",
        "preserved_title_fa": "شابر دستی گروز",
        "preserved_brand": "Groz | گروز",
        "preserved_category_id": "158",
        "research_priority": "HAND_SCRAPER_FITTING",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "Groz engineers hand scrapers (ES/F, ES/HR, ES/T) are precision metalworking fitting tools "
            "for slideways and surface plates — not generic paint scrapers. Still not metrology and not "
            "clearly mapped to an approved domain code (workholding/cutting/toolholding/machines/thread/fluid)."
        ),
        "exact_manufacturer_identity_status": "UNRESOLVED",
        "exact_manufacturer_article": "",
        "oem_match_classification": "OEM_FAMILY_REFERENCE",
        "karzar_product_oem_identity_verification": "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH",
        "proposed_application_class": "PRECISION_MACHINE_FITTING_HAND_SCRAPER",
        "competing_interpretations": (
            "A) Groz engineers scraper for machine fitting/scraping. "
            "B) General hand scraper — contradicted by Groz brand + «شابر» toolroom term. "
            "C) UNRESOLVED ES/* size and type for SKU 4318."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "MEDIUM",
        "confidence_basis": "APPLICATION_HYPOTHESIS_OEM_FAMILY_PLUS_TITLE",
        "confidence_scope_note": "Industrial craft use does not equal approved-domain catalog eligibility.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "REJECT_EXIT_REQUEST_EXCEPTION_REVIEW",
        "unresolved_questions": "Flat vs half-round vs triangular; blade length; Groz article on product.",
    },
    5227: {
        "karzar_catalog_sku": "QE98L",
        "preserved_title_fa": "تراز نصب شونده روی دریل مدل QE98L مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "QE98L_METROLOGY_VS_ACCESSORY",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "Distributor/OEM-adjacent evidence for M7A-QE98L / QE-98L: double-axis bubble spirit level "
            "mounting on M7 air drills. Workshop alignment accessory — not a calibrated metrology instrument "
            "(KZ.DOM.METROLOGY)."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "QE-98L / M7A-QE98L",
        "oem_match_classification": "NEAR_MODEL_REFERENCE",
        "karzar_product_oem_identity_verification": "EXACT_SKU_NORMALIZED_HYPHEN_VARIANT",
        "proposed_application_class": "PNEUMATIC_DRILL_SPIRIT_LEVEL_ACCESSORY",
        "competing_interpretations": (
            "A) Drill-mounted bubble level (confirmed by ITM/National Welding listings). "
            "B) Metrology level — rejected; no calibration/traceability claims. "
            "C) UNRESOLVED if Karzar unit is a different suffix than QE-98L."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_MODEL_DISTRIBUTOR_PLUS_OEM_FAMILY",
        "confidence_scope_note": "High confidence product class is not metrology; hyphen normalization QE98L≈QE-98L unconfirmed on nameplate.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "Photo of engraved model; confirm not a different M7 QE accessory.",
    },
    5259: {
        "karzar_catalog_sku": "SB201",
        "preserved_title_fa": "گیج دیجیتال و باد زن مدل SB201 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SB201_PRESSURE_MEASUREMENT",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SB-201 digital tyre inflator with tyre-valve clip and digital pressure readout for "
            "inflation — tyre service tool, not traceable industrial pressure metrology."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SB-201",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "TYRE_INFLATOR_WITH_DIGITAL_GAUGE",
        "competing_interpretations": (
            "A) M7 digital tyre inflator (OEM product/544). "
            "B) Industrial test gauge — rejected; OEM specifies tyre valve clip and tyre inflator class."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Gauge function is for tyre inflation convenience, not KZ.DOM.METROLOGY.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None for OEM class; optional photo to confirm SB-201 marking on received stock.",
    },
    5260: {
        "karzar_catalog_sku": "SB423",
        "preserved_title_fa": "گیج باد زن مدل SB423 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SB423_PRESSURE_MEASUREMENT",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SB-423 analogue tyre inflator, 0–220 psi, tyre valve clip — workshop tyre/service equipment."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SB-423",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "TYRE_INFLATOR_ANALOG_GAUGE",
        "competing_interpretations": "A) Tyre inflator (OEM). B) Industrial calibration gauge — rejected.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Same boundary as SB-201; not metrology domain.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "Optional nameplate photo for SB-423.",
    },
    5261: {
        "karzar_catalog_sku": "SB710",
        "preserved_title_fa": "گیج باد زن مدل SB710 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SB710_PRESSURE_MEASUREMENT",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SB-710 tyre inflator with valve clip and dial gauge — tyre maintenance, not metrology."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SB-710",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "TYRE_INFLATOR_ANALOG_GAUGE",
        "competing_interpretations": "A) Tyre inflator (OEM product/546). B) Metrology — rejected.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "OEM lists tyre inflator category explicitly.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "Optional stock photo.",
    },
    5267: {
        "karzar_catalog_sku": "SG101",
        "preserved_title_fa": "کیت گریس زن مدل SG101 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SG101_LUBRICATION_EQUIPMENT",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SG-101 lubrication kit: 100 ml air-tool oil tube plus applicator — maintenance kit. "
            "Selling the kit is not listing a metalworking fluid product (KZ.DOM.FLUIDS)."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SG-101",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "AIR_TOOL_LUBRICATION_KIT_WITH_APPLICATOR",
        "competing_interpretations": (
            "A) M7 maintenance kit (equipment + consumable). "
            "B) Bulk metalworking fluid — rejected; OEM defines lubrication kit for air tools."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Fluid in kit does not reclassify SKU as KZ.DOM.FLUIDS catalog line.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None for OEM identity.",
    },
    5268: {
        "karzar_catalog_sku": "SG400",
        "preserved_title_fa": "گریس پمپ بادی مخزن 400 سی سی مدل SG400 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SG400_GREASE_DISPENSING",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SG-400 pneumatic grease gun, 400 cc capacity — lubrication dispensing equipment, "
            "not a metalworking fluid SKU."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SG-400",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "PNEUMATIC_GREASE_DISPENSING_EQUIPMENT",
        "competing_interpretations": (
            "A) Air grease gun equipment. B) Grease fluid product — rejected; census sells the pump."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Matches Karzar title tank volume with OEM 400 c.c. spec.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "Confirm SG-400 vs SG-400C variant on nameplate if mixed stock.",
    },
    5285: {
        "karzar_catalog_sku": "SP102",
        "preserved_title_fa": "بالانسر تحمل وزن 0/6 تا 1/5 کیلوگرم مدل SP102 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SP102_TOOL_BALANCER",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SP-102 spring balancer, 0.6–1.5 kg capacity — supports hanging pneumatic tools; "
            "workshop ergonomics accessory, not machine tool balancing or workholding domain."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SP-102",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "PNEUMATIC_TOOL_SPRING_BALANCER",
        "competing_interpretations": (
            "A) M7 tool balancer per OEM load rating. "
            "B) Industrial crane/load balancer — rejected by sub-2 kg OEM capacity band."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Karzar title load range matches OEM SP-102 specifications.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None for OEM match.",
    },
    5287: {
        "karzar_catalog_sku": "SP104",
        "preserved_title_fa": "بالانسر تحمل وزن 1/5 تا 3 کیلوگرم مدل SP104 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SP104_TOOL_BALANCER",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": "OEM SP-104 spring balancer 1.5–3.0 kg — same workshop accessory class as SP-102.",
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SP-104",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "PNEUMATIC_TOOL_SPRING_BALANCER",
        "competing_interpretations": "A) OEM tool balancer. B) Machine spindle balancer — rejected.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Title load band aligns with OEM capacity.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None.",
    },
    5289: {
        "karzar_catalog_sku": "SP105",
        "preserved_title_fa": "بالانسر تحمل وزن 3 تا 5 کیلوگرم مدل SP105 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SP105_TOOL_BALANCER",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": "OEM SP-105 spring balancer 3.0–5.0 kg capacity for hanging air tools.",
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SP-105",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "PNEUMATIC_TOOL_SPRING_BALANCER",
        "competing_interpretations": "A) OEM balancer. B) Heavy industrial hoist — rejected by 5 kg max OEM rating.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Title matches OEM SP-105 load band.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None.",
    },
    5295: {
        "karzar_catalog_sku": "SV1360",
        "preserved_title_fa": "واحد مراقبت تکی رطوبت گیر مدل SV1360 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SV1360_AIR_PREP",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SV-1360 is filter+regulator (moisture separator/regulator function) — general shop "
            "compressed-air prep; not a machine OEM component line and outside seven domains."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SV-1360",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "SHOP_AIR_FILTER_REGULATOR_UNIT",
        "competing_interpretations": (
            "A) M7 F/R unit (OEM). B) CNC machine integrated FRL — would need machine OEM linkage; none cited."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Karzar title «رطوبت‌گیر» aligns with filter/regulator, not lubricator variant.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None for model match.",
    },
    5296: {
        "karzar_catalog_sku": "SV2220",
        "preserved_title_fa": "واحد مراقبت دوقلو رطوبت گیر مدل SV2220 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SV2220_AIR_PREP",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": "OEM SV-2220 1/4 in filter/regulator/lubricator — pneumatic line accessory for air tools.",
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SV-2220",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "SHOP_AIR_FRL_UNIT",
        "competing_interpretations": "A) M7 FRL (OEM). B) Machine tool OEM part — unproven.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "«دوقلو» in title may mean dual-function FRL, not two physical units.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None.",
    },
    5297: {
        "karzar_catalog_sku": "SV2380",
        "preserved_title_fa": "واحد مراقبت دوقلو رطوبت گیر مدل SV2380 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SV2380_AIR_PREP",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": "OEM SV-2380 3/8 in FRL — shop air preparation, same boundary as SV-2220.",
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SV-2380",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "SHOP_AIR_FRL_UNIT",
        "competing_interpretations": "A) M7 FRL. B) Industrial machine subsystem — unproven.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Exact model hyphen normalization SV2380≈SV-2380.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None.",
    },
    5298: {
        "karzar_catalog_sku": "SW12",
        "preserved_title_fa": "مینی لوبریکیتور 1/4 اینچ مدل SW12 مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SW12_PNEUMATIC_LUBRICATOR",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SW-12 mini in-line lubricator (1/4 in) for air-tool lines — maintenance accessory, "
            "not machine pneumatic subsystem in an approved domain."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SW-12",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "INLINE_AIR_TOOL_MINI_LUBRICATOR",
        "competing_interpretations": "A) M7 mini lubricator. B) Central machine mist system — unproven.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "Title 1/4 inch matches OEM port size.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None.",
    },
    5301: {
        "karzar_catalog_sku": "SY-2001M",
        "preserved_title_fa": "رگولاتور 360 درجه مدل SY-2001M مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SY2001M_REGULATOR",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SY-2001M is documented as 360° rotatable adaptor (1/4 in), not a pressure regulator. "
            "Karzar Persian title says «رگولاتور» — listing/title mismatch vs OEM product class."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SY-2001M",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE_WITH_TITLE_MISMATCH",
        "proposed_application_class": "ROTATABLE_PNEUMATIC_ADAPTOR_NOT_REGULATOR",
        "competing_interpretations": (
            "A) SY-2001M rotatable adaptor (OEM product/2851). "
            "B) SY-2002M regulator+adaptor combo — different OEM SKU. "
            "C) UNRESOLVED if warehouse stock is actually a regulator variant."
        ),
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "High confidence on OEM article class; physical stock vs title still needs confirmation.",
        "post_research_agent_proposal": "NEEDS_MORE_EVIDENCE",
        "recommended_owner_review_option": "REQUEST_MORE_EVIDENCE",
        "unresolved_questions": "Photo/nameplate; confirm not SY-2002M; fix title if adaptor-only.",
    },
    5302: {
        "karzar_catalog_sku": "SZ212A",
        "preserved_title_fa": "رگولاتور بادی مدل SZ212A مایتی سون (Mighty Seven)",
        "preserved_brand": "Mighty Seven | مایتی سون",
        "preserved_category_id": "158",
        "research_priority": "SZ212A_REGULATOR",
        "historical_pr499_proposal": "CATALOG_EXIT_CANDIDATE",
        "historical_pr499_evidence_basis": "HEURISTIC",
        "new_technical_research_finding": (
            "OEM SZ-212A inline air regulator for pneumatic tool inlet flow — workshop accessory, "
            "outside seven approved domains."
        ),
        "exact_manufacturer_identity_status": "VERIFIED",
        "exact_manufacturer_article": "SZ-212A",
        "oem_match_classification": "EXACT_OEM_ARTICLE_MATCH",
        "karzar_product_oem_identity_verification": "EXACT_SKU_OEM_PAGE",
        "proposed_application_class": "INLINE_PNEUMATIC_TOOL_AIR_REGULATOR",
        "competing_interpretations": "A) M7 tool regulator (OEM). B) Machine main air regulator — unproven.",
        "industrial_domain_hypothesis": "",
        "approved_domain_fit_assessment": "DOES_NOT_FIT",
        "confidence_level": "HIGH",
        "confidence_basis": "EXACT_SKU_OEM_PAGE",
        "confidence_scope_note": "OEM describes tool inlet flow adjustment, not plant infrastructure.",
        "post_research_agent_proposal": "CATALOG_EXIT_CANDIDATE",
        "recommended_owner_review_option": "APPROVE_CATALOG_EXIT",
        "unresolved_questions": "None for OEM class.",
    },
}


def sources_for_product(product_id: int) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    pid = str(product_id)
    for src in OEM_SOURCES:
        related = src.get("related_karzar_product_ids", "")
        if pid in {p.strip() for p in related.split("|")}:
            hits.append(src)
    return hits


def evidence_gaps() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in P0_PRODUCT_IDS:
        spec = P0_PRODUCTS[pid]
        base_gap = spec.get("unresolved_questions", "")
        rows.append(
            {
                "product_id": str(pid),
                "gap_id": f"GAP-{pid}-IDENTITY",
                "gap_category": "OEM_IDENTITY_OR_STOCK_PROOF",
                "gap_description": base_gap,
                "blocks_disposition": "YES" if "UNRESOLVED" in spec["karzar_product_oem_identity_verification"] else "NO",
            }
        )
        if spec["approved_domain_fit_assessment"] == "UNPROVEN":
            rows.append(
                {
                    "product_id": str(pid),
                    "gap_id": f"GAP-{pid}-DOMAIN",
                    "gap_category": "APPROVED_DOMAIN_FIT",
                    "gap_description": (
                        f"Domain hypothesis {spec.get('industrial_domain_hypothesis', '')} requires "
                        "Groz article proof and Owner policy for industrial exception."
                    ),
                    "blocks_disposition": "YES",
                }
            )
        elif spec["industrial_domain_hypothesis"] and spec["industrial_domain_hypothesis"] not in APPROVED_DOMAIN_CODES:
            rows.append(
                {
                    "product_id": str(pid),
                    "gap_id": f"GAP-{pid}-DOMAIN-CODE",
                    "gap_category": "INVALID_DOMAIN_CODE",
                    "gap_description": "Hypothesis must map to one of seven approved domain codes.",
                    "blocks_disposition": "YES",
                }
            )
    return rows


def industrial_boundary_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in P0_PRODUCT_IDS:
        spec = P0_PRODUCTS[pid]
        domain = spec.get("industrial_domain_hypothesis", "")
        rows.append(
            {
                "product_id": str(pid),
                "karzar_catalog_sku": spec["karzar_catalog_sku"],
                "research_priority_code": spec["research_priority"],
                "workshop_vs_industrial_function": spec["proposed_application_class"],
                "industrial_domain_hypothesis": domain,
                "approved_domain_fit_assessment": spec["approved_domain_fit_assessment"],
                "boundary_rationale": spec["new_technical_research_finding"],
                "factory_use_alone_insufficient": "YES",
                "post_research_agent_proposal": spec["post_research_agent_proposal"],
            }
        )
    return rows
