"""Evidence packets for Phase-1 REVIEW rows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from catalog_target.core import CurrentProduct, index_current_products
from zcc_ir_catalog.models import ReconcileRow, SourceProduct
from zcc_ir_catalog.reconcile import match_source_to_karzar


@dataclass
class ReviewDecision:
    source_url: str
    outcome: str
    confidence: str
    recommended_decision: str
    reason: str
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _possible_matches(product: SourceProduct, karzar: list[CurrentProduct]) -> list[dict[str, str]]:
    index = index_current_products(karzar)
    pending, method, current, candidates, reason = match_source_to_karzar(product, index)
    matches: list[dict[str, str]] = []
    if current:
        matches.append(
            {
                "karzar_id": current.id or "",
                "karzar_sku": current.sku or "",
                "method": method or "",
            }
        )
    for sku in candidates:
        matches.append({"karzar_sku": sku, "method": "candidate"})
    if not matches and reason:
        matches.append({"note": reason})
    return matches


def resolve_review_records(
    sources: list[SourceProduct],
    phase1_reconcile: list[ReconcileRow],
    karzar: list[CurrentProduct],
) -> list[ReviewDecision]:
    by_url = {p.source_url: p for p in sources}
    decisions: list[ReviewDecision] = []
    for row in phase1_reconcile:
        if row.status != "REVIEW":
            continue
        product = by_url.get(row.source_url)
        if product is None:
            continue
        flags = set(product.parse_flags)
        evidence = {
            "source_url": product.source_url,
            "source_name": product.name_fa,
            "shop_tag_membership": product.source_category,
            "breadcrumbs": product.category_path,
            "category_path": product.category_path,
            "jsonld_brand": product.jsonld_brand,
            "visible_title_brand_token": product.brand,
            "manufacturer_model_code": product.manufacturer_code,
            "sku": product.sku,
            "canonical_url": product.canonical_url,
            "source_internal_sku": product.source_internal_sku,
            "related_listing_evidence": product.source_category_url,
            "possible_karzar_matches": _possible_matches(product, karzar),
            "parse_flags": product.parse_flags,
        }
        outcome = "HUMAN_REVIEW_REQUIRED"
        confidence = "low"
        recommended = "HOLD"
        reason = row.review_reason or "phase1_review"
        if reason == "missing_brand" and product.brand_normalized:
            outcome = "AUTO_RESOLVED_EXACT"
            confidence = "medium"
            recommended = "IMPORT_WITH_RESOLVED_BRAND"
            reason = f"brand_normalized={product.brand_normalized} despite missing_brand flag"
        elif reason == "missing_manufacturer_code" and product.manufacturer_code:
            outcome = "AUTO_RESOLVED_EXACT"
            confidence = "medium"
            recommended = "IMPORT_WITH_MANUFACTURER_CODE"
            reason = "manufacturer code present on re-parse"
        elif reason == "missing_usable_identity" and not product.manufacturer_code and not product.source_internal_sku:
            outcome = "SOURCE_RECORD_NOT_IMPORTABLE"
            confidence = "high"
            recommended = "EXCLUDE"
            reason = "no manufacturer code or internal sku"
        elif "jsonld_brand_conflicts_name" in flags and product.brand_normalized == "STC":
            outcome = "HUMAN_REVIEW_REQUIRED"
            confidence = "high"
            recommended = "USE_TITLE_BRAND_STC_NOT_JSONLD"
            reason = "JSON-LD ZCC brand is unreliable on STC pages (Phase-1 finding)"
        decisions.append(
            ReviewDecision(
                source_url=product.source_url,
                outcome=outcome,
                confidence=confidence,
                recommended_decision=recommended,
                reason=reason,
                evidence=evidence,
            )
        )
    decisions.sort(key=lambda d: d.source_url)
    return decisions
