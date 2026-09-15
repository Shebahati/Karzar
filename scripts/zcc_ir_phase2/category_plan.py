"""Phase-2 category decision package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from zcc_ir_catalog.categories import category_mapping_rows
from zcc_ir_catalog.models import CategoryMapRow, SourceProduct

PHASE2_DECISIONS = ("MAPPED_EXISTING", "HUMAN_REVIEW_REQUIRED", "NEW_CATEGORY_PROPOSAL")


@dataclass
class CategoryDecisionRow:
    source_category_path: str
    source_product_count: int
    proposed_karzar_category_id: str | None
    proposed_karzar_category_path: str | None
    decision: str
    confidence: str
    technical_reason: str
    representative_products: list[str]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["representative_products"] = list(self.representative_products)
        return data


def _phase2_decision(row: CategoryMapRow) -> str:
    if row.mapping_status in {"SAFE_RULE", "EXACT"} and row.karzar_category_id:
        return "MAPPED_EXISTING"
    if row.mapping_status == "UNMAPPED":
        return "NEW_CATEGORY_PROPOSAL"
    return "HUMAN_REVIEW_REQUIRED"


def build_category_plan(
    products: list[SourceProduct],
    karzar_categories: list[dict[str, Any]],
) -> tuple[list[CategoryDecisionRow], set[str]]:
    """Return category decisions and source URLs that lack a mapped category."""
    phase1_rows = category_mapping_rows(products, karzar_categories)
    samples: dict[str, list[str]] = {}
    for product in products:
        path = " > ".join(product.category_path) if product.category_path else "(missing)"
        samples.setdefault(path, [])
        if len(samples[path]) < 5:
            samples[path].append(product.source_url)
    decisions: list[CategoryDecisionRow] = []
    hold_urls: set[str] = set()
    for row in phase1_rows:
        decision = _phase2_decision(row)
        reps = samples.get(row.source_category_path, [])
        decisions.append(
            CategoryDecisionRow(
                source_category_path=row.source_category_path,
                source_product_count=row.source_product_count,
                proposed_karzar_category_id=row.karzar_category_id,
                proposed_karzar_category_path=row.karzar_category_path,
                decision=decision,
                confidence=row.mapping_confidence,
                technical_reason=row.mapping_reason,
                representative_products=reps,
            )
        )
        if decision != "MAPPED_EXISTING":
            for product in products:
                path = " > ".join(product.category_path) if product.category_path else "(missing)"
                if path == row.source_category_path:
                    hold_urls.add(product.source_url)
    decisions.sort(key=lambda r: (-r.source_product_count, r.source_category_path))
    return decisions, hold_urls


def category_by_url(products: list[SourceProduct], decisions: list[CategoryDecisionRow]) -> dict[str, CategoryDecisionRow]:
    path_map = {d.source_category_path: d for d in decisions}
    out: dict[str, CategoryDecisionRow] = {}
    for product in products:
        path = " > ".join(product.category_path) if product.category_path else "(missing)"
        dec = path_map.get(path)
        if dec:
            out[product.source_url] = dec
    return out
