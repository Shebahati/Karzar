"""Verified external sources for TX-OWNER-001 semantic review (audit trail)."""

from __future__ import annotations

from typing import Any

# Each entry is auditable; verification_status is HUMAN_VERIFIED for URLs fetched in review pass.
EXTERNAL_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "EXT-M7-158",
        "source_url": "https://www.mighty-seven.com/product/158",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "QA-210 A/B Air Die Grinder",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "supported_claim": (
            "QA-210 family is classified by OEM as Air Die Grinder (Air Tools), "
            "not a toolholding Product Type."
        ),
        "affected_product_ids": "5194",
        "verification_status": "HUMAN_VERIFIED_2026-10-17",
    },
    {
        "source_id": "EXT-M7-159",
        "source_url": "https://www.mighty-seven.com/product/159",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "QA-211 A/B Air Die Grinder",
        "evidence_class": "OEM_PRODUCT_PAGE",
        "supported_claim": (
            "QA-211 family is classified by OEM as Air Die Grinder with collet sizes; "
            "collet is interface of a handheld pneumatic grinder."
        ),
        "affected_product_ids": "5195",
        "verification_status": "HUMAN_VERIFIED_2026-10-17",
    },
    {
        "source_id": "EXT-M7-AIR-TOOLS-CLASS",
        "source_url": "https://www.mighty-seven.com/",
        "manufacturer": "Mighty Seven (M7)",
        "model_identity": "Air Tools product family",
        "evidence_class": "OEM_CATEGORY_TAXONOMY",
        "supported_claim": (
            "Die grinders and angle grinders are marketed under Air Tools, "
            "consistent with workshop pneumatic power tools rather than Cutting Tool inserts."
        ),
        "affected_product_ids": "5190-5207,5209,5215-5216",
        "verification_status": "INFERRED_FROM_OEM_SITE_STRUCTURE",
    },
]

APPROVED_DOMAIN_CODES = frozenset(
    {
        "KZ.DOM.METROLOGY",
        "KZ.DOM.CUTTING",
        "KZ.DOM.TOOLHOLDING",
        "KZ.DOM.WORKHOLDING",
        "KZ.DOM.MACHINES",
        "KZ.DOM.THREAD_REPAIR",
        "KZ.DOM.FLUIDS",
    }
)


def sources_for_product(product_id: int) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    pid = str(product_id)
    for src in EXTERNAL_SOURCES:
        affected = src.get("affected_product_ids", "")
        if pid in affected:
            hits.append(src)
            continue
        for part in affected.split(","):
            part = part.strip()
            if "-" in part and part.replace("-", "").isdigit():
                lo, hi = part.split("-", 1)
                if lo.isdigit() and hi.isdigit() and int(lo) <= product_id <= int(hi):
                    hits.append(src)
    return hits
