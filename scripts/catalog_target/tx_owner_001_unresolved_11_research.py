"""Research corpus for TX-OWNER-001 remaining 11 NEEDS_MORE products (evidence only)."""

from __future__ import annotations

from typing import Any

EXACT_MANUFACTURER_IDENTITY_STATUS = "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH"
OEM_FAMILY_EVIDENCE_VERIFIED = "VERIFIED_OEM_OR_MARKET_REFERENCE_PAGES"
KARZAR_PRODUCT_OEM_IDENTITY_UNVERIFIED = "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH"

UNRESOLVED_11_PRODUCT_IDS: tuple[int, ...] = (
    3090,
    3091,
    3093,
    3095,
    3096,
    3097,
    3098,
    3099,
    3101,
    5146,
    5147,
)

OEM_AND_MARKET_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "MARKET-CMT-ROUTER-GROOVE-WOOD",
        "source_url": "https://sazokar.com/product/cmt-706-095-11-router-bit",
        "manufacturer": "CMT (distributor listing — reference class only)",
        "model_identity": "Woodworking router / CNC grooving & finishing bits",
        "evidence_class": "DISTRIBUTOR_PRODUCT_PAGE",
        "evidence_match_type": "APPLICATION_CLASS_REFERENCE",
        "supported_claim": (
            "Iranian market documents «تیغ اورفرز پرداخت» / grooving on wood & MDF for CNC/router; "
            "not linked to Karzar SKUs 3865–3876."
        ),
        "related_karzar_product_ids": "3090,3091,3093,3095,3096,3097,3098,3099,3101",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "MARKET-FA-FINISHING-BEARING-LOWER",
        "source_url": "https://www.choobiner.ir/%d8%aa%db%8c%d8%ba-%d9%be%d8%b1%d8%af%d8%a7%d8%ae%d8%aa-%d8%a8%d9%84%d8%a8%d8%b1%db%8c%d9%86%da%af-%d9%be%d8%a7%db%8c%db%8c%d9%86-arden-%d8%b3%d8%b1%db%8c-152",
        "manufacturer": "ARDEN (reference class via distributor)",
        "model_identity": "Lower-bearing woodworking finishing router bit",
        "evidence_class": "DISTRIBUTOR_PRODUCT_PAGE",
        "evidence_match_type": "APPLICATION_CLASS_REFERENCE",
        "supported_claim": (
            "«تیغ پرداخت بلبرینگ پایین» is a standard woodworking router bit form factor "
            "(TCT, shank 8/12 mm) — aligns with census titles for 3095/3101, not metal lathe inserts."
        ),
        "related_karzar_product_ids": "3095,3097,3098,3099,3101",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "MARKET-FA-GROOVING-ROUTER-PROUCUT",
        "source_url": "https://proucut.com/pc/finishing-razor/",
        "manufacturer": "Proucut (woodworking tools retailer)",
        "model_identity": "CNC woodworking finishing / grooving router bits",
        "evidence_class": "RETAIL_CATEGORY_PAGE",
        "evidence_match_type": "APPLICATION_CLASS_REFERENCE",
        "supported_claim": (
            "Persian «شیارزن»/finishing router tooling sold for wood CNC — contextual only."
        ),
        "related_karzar_product_ids": "3090,3091,3093,3096",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-NC4277Q-EXACT-MODEL",
        "source_url": "https://www.mighty-seven.com/product/36",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "NC-4277Q Air Impact Wrench",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "NEAR_MODEL_SUFFIX_VARIANT",
        "supported_claim": (
            "OEM documents NC-4277Q (Q suffix). Karzar lists NC4277 without Q — "
            "do not treat as exact identity match for product 5146."
        ),
        "related_karzar_product_ids": "5146",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-NC4299Q-EXACT-MODEL",
        "source_url": "https://www.mighty-seven.com/product/37",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "NC-4299Q Air Impact Wrench",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "evidence_match_type": "NEAR_MODEL_SUFFIX_VARIANT",
        "supported_claim": (
            "OEM documents NC-4299Q (Q suffix). Karzar lists NC4299 without Q — "
            "do not treat as exact identity match for product 5147."
        ),
        "related_karzar_product_ids": "5147",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
    {
        "source_id": "M7-OEM-IMPACT-WRENCH-CATEGORY",
        "source_url": "https://www.mighty-seven.com/product_list/4",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "Air impact wrench product family",
        "evidence_class": "OEM_CATEGORY_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "If identity were confirmed as M7 impact wrench, it would be workshop pneumatic "
            "tool (TX-OWNER-001 exit scope), not an approved industrial domain insert."
        ),
        "related_karzar_product_ids": "5146,5147",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-17",
    },
]

# Frozen census titles (2026-10-15) — do not mutate
_PRODUCT_ROWS: list[dict[str, Any]] = [
    {
        "product_id": 3090,
        "karzar_catalog_sku": "3865",
        "preserved_title_fa": "شیارزن cnc",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3091,
        "karzar_catalog_sku": "3866",
        "preserved_title_fa": "شیارزن بلند cnc",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3093,
        "karzar_catalog_sku": "3868",
        "preserved_title_fa": "شیارزن کف بردار (کفتراش)cnc",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3095,
        "karzar_catalog_sku": "3870",
        "preserved_title_fa": "تیغ پرداخت بلبرینگ پایین",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3096,
        "karzar_catalog_sku": "3871",
        "preserved_title_fa": "شیارزن دو تیغ مرکزی (کف بردار) cnc",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3097,
        "karzar_catalog_sku": "3872",
        "preserved_title_fa": "تیغ پرداخت",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3098,
        "karzar_catalog_sku": "3873",
        "preserved_title_fa": "تیغ پرداخت 4 پر",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3099,
        "karzar_catalog_sku": "3874",
        "preserved_title_fa": "تیغ پرداخت بلند",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 3101,
        "karzar_catalog_sku": "3876",
        "preserved_title_fa": "تیغ پرداخت 2 بلبرینگ",
        "preserved_category_id": "160",
        "cohort": "GROOVING_FINISHING",
    },
    {
        "product_id": 5146,
        "karzar_catalog_sku": "NC4277",
        "preserved_title_fa": "مایتی سون (Mighty Seven) مدل NC4277",
        "preserved_category_id": "158",
        "cohort": "M7_PNEUMATIC",
    },
    {
        "product_id": 5147,
        "karzar_catalog_sku": "NC4299",
        "preserved_title_fa": "مایتی سون (Mighty Seven) مدل NC4299",
        "preserved_category_id": "158",
        "cohort": "M7_PNEUMATIC",
    },
]


def _grooving_spec(row: dict[str, Any]) -> dict[str, Any]:
    title = row["preserved_title_fa"]
    if "تیغ پرداخت" in title:
        app = "WOODWORKING_CNC_ROUTER_FINISHING_BIT_HYPOTHESIS"
        competing = (
            "A) Woodworking router finishing bit (bearing-guided TCT) per title/category 160. "
            "B) Metalworking lathe/parting insert — no geometry, grade, or shank specs in census. "
            "C) UNRESOLVED — brandless SKU; no OEM article."
        )
    else:
        app = "WOODWORKING_CNC_ROUTER_GROOVING_BIT_HYPOTHESIS"
        competing = (
            "A) Woodworking CNC/router grooving cutter («شیارزن») per title + cat 160. "
            "B) Metalworking grooving insert — CNC token in title is insufficient alone. "
            "C) UNRESOLVED — brandless SKU; no OEM article."
        )
    return {
        **row,
        "historical_pr499_proposal": "NEEDS_MORE_EVIDENCE",
        "historical_pr499_domain": "",
        "exact_manufacturer_identity_status": EXACT_MANUFACTURER_IDENTITY_STATUS,
        "exact_manufacturer_article": "",
        "oem_family_evidence_verification": OEM_FAMILY_EVIDENCE_VERIFIED,
        "karzar_product_oem_identity_verification": KARZAR_PRODUCT_OEM_IDENTITY_UNVERIFIED,
        "proposed_application_class": app,
        "competing_interpretations": competing,
        "confidence_level": "LOW",
        "confidence_basis": "APPLICATION_HYPOTHESIS_TITLE_AND_CATEGORY_ONLY",
        "confidence_scope_note": (
            "LOW confidence in woodworking-router hypothesis; does not verify manufacturer "
            "or map internal SKU to any OEM article."
        ),
        "proposed_industrial_domain": "",
        "agent_proposal": "NEEDS_MORE_EVIDENCE",
        "recommended_owner_review_option": "REQUEST_MORE_EVIDENCE",
        "unresolved_questions": (
            "Brand; shank diameter; cutter diameter/length; photo; packing slip; "
            "confirm wood vs metal application before any industrial exception."
        ),
        "owner_options": (
            "APPROVE_CATALOG_EXIT | REQUEST_MORE_EVIDENCE | "
            "APPROVE_INDUSTRIAL_EXCEPTION (only if OEM metal-cutting proof supplied) | DEFER_DECISION"
        ),
    }


def _m7_spec(row: dict[str, Any]) -> dict[str, Any]:
    sku = row["karzar_catalog_sku"]
    q_variant = "NC-4277Q" if sku == "NC4277" else "NC-4299Q"
    return {
        **row,
        "historical_pr499_proposal": "NEEDS_MORE_EVIDENCE",
        "historical_pr499_domain": "",
        "exact_manufacturer_identity_status": EXACT_MANUFACTURER_IDENTITY_STATUS,
        "exact_manufacturer_article": "",
        "oem_family_evidence_verification": OEM_FAMILY_EVIDENCE_VERIFIED,
        "karzar_product_oem_identity_verification": KARZAR_PRODUCT_OEM_IDENTITY_UNVERIFIED,
        "proposed_application_class": "PNEUMATIC_IMPACT_WRENCH_WORKSHOP_HYPOTHESIS",
        "competing_interpretations": (
            f"A) M7 air impact wrench if catalog typo omits «Q» ({q_variant} on OEM site). "
            f"B) Different M7 model without «Q» — not listed on OEM catalog crawl. "
            "C) UNRESOLVED — Karzar SKU must not be equated to Q-suffix OEM page without proof."
        ),
        "confidence_level": "LOW",
        "confidence_basis": "NEAR_MODEL_OEM_PAGE_NOT_EXACT_SKU",
        "confidence_scope_note": (
            f"M7 OEM page is for {q_variant}; Karzar SKU {sku} has no verified exact match."
        ),
        "proposed_industrial_domain": "",
        "agent_proposal": "NEEDS_MORE_EVIDENCE",
        "recommended_owner_review_option": "REQUEST_MORE_EVIDENCE",
        "unresolved_questions": (
            f"Confirm engraved model (NC4277 vs NC4277Q / NC4299 vs NC4299Q); photo of nameplate; "
            "importer invoice with M7 article number."
        ),
        "owner_options": (
            "APPROVE_CATALOG_EXIT | REQUEST_MORE_EVIDENCE | "
            "APPROVE_INDUSTRIAL_EXCEPTION (only with exact M7 article proof) | DEFER_DECISION"
        ),
    }


def build_product_specs() -> dict[int, dict[str, Any]]:
    specs: dict[int, dict[str, Any]] = {}
    for row in _PRODUCT_ROWS:
        pid = int(row["product_id"])
        if row["cohort"] == "M7_PNEUMATIC":
            specs[pid] = _m7_spec(row)
        else:
            specs[pid] = _grooving_spec(row)
    return specs


UNRESOLVED_11_PRODUCTS: dict[int, dict[str, Any]] = build_product_specs()


def sources_for_product(product_id: int) -> list[dict[str, str]]:
    pid = str(product_id)
    return [
        s
        for s in OEM_AND_MARKET_SOURCES
        if pid in {x.strip() for x in s.get("related_karzar_product_ids", "").split(",")}
    ]


def evidence_gaps() -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for pid, spec in UNRESOLVED_11_PRODUCTS.items():
        gaps.append(
            {
                "product_id": str(pid),
                "karzar_catalog_sku": spec["karzar_catalog_sku"],
                "gap_code": "NO_OEM_ARTICLE_MATCH",
                "gap_description": spec["unresolved_questions"],
                "blocks_disposition_upgrade": "YES",
            }
        )
        if spec["cohort"] == "GROOVING_FINISHING":
            gaps.append(
                {
                    "product_id": str(pid),
                    "karzar_catalog_sku": spec["karzar_catalog_sku"],
                    "gap_code": "NO_BRAND_OR_GEOMETRY",
                    "gap_description": "Census lacks brand, shank, diameter, material grade.",
                    "blocks_disposition_upgrade": "YES",
                }
            )
        if spec["cohort"] == "M7_PNEUMATIC":
            gaps.append(
                {
                    "product_id": str(pid),
                    "karzar_catalog_sku": spec["karzar_catalog_sku"],
                    "gap_code": "MODEL_SUFFIX_AMBIGUITY",
                    "gap_description": "OEM lists Q-suffix models; catalog SKU omits Q.",
                    "blocks_disposition_upgrade": "YES",
                }
            )
    return gaps
