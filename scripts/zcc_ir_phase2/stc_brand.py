"""Proposed STC brand package (no create)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from zcc_ir_catalog.models import SourceProduct


def build_stc_brand_proposal(sources: list[SourceProduct]) -> dict[str, Any]:
    stc = [p for p in sources if p.brand_normalized == "STC"]
    display_names = Counter(str(p.brand or "STC") for p in stc)
    canonical = "STC"
    display = display_names.most_common(1)[0][0] if display_names else "STC"
    sample_urls = sorted({p.source_url for p in stc})[:10]
    logo_candidates = [p.main_image_url for p in stc if p.main_image_url][:3]
    jsonld_conflicts = sum(1 for p in stc if "jsonld_brand_conflicts_name" in p.parse_flags)
    return {
        "canonical_name": canonical,
        "display_name": display,
        "display_name_fa": None,
        "slug": "stc",
        "source_brand_name": display,
        "source_url": "https://zcc.ir/product-tag/stc/",
        "logo_source_candidate": logo_candidates[0] if logo_candidates else None,
        "product_count": len(stc),
        "representative_product_urls": sample_urls,
        "evidence": {
            "shop_tag_structure": "STC products use dedicated STC shop/tag pages on zcc.ir",
            "jsonld_brand_unreliable": jsonld_conflicts,
            "note": "Do not treat JSON-LD brand=ZCC as authoritative on STC PDPs",
        },
        "proposed_karzar_brand_payload": {
            "canonical_name": canonical,
            "display_name": display,
            "display_name_fa": None,
            "slug": "stc",
            "source_brand_name": display,
            "source_url": "https://zcc.ir/product-tag/stc/",
            "logo_source_candidate": logo_candidates[0] if logo_candidates else None,
            "product_count": len(stc),
        },
        "decision_status": "READY_FOR_OWNER_APPROVAL" if stc else "REVIEW_REQUIRED",
    }
