"""Proposed create/update payloads (plan only)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from zcc_ir_catalog.models import SourceProduct

from zcc_ir_phase2.category_plan import CategoryDecisionRow
from zcc_ir_phase2.reconcile import Phase2ReconcileRow


def _slug_proposal(product: SourceProduct) -> str:
    base = product.source_slug or product.manufacturer_code or product.source_internal_sku or "product"
    text = re.sub(r"[^a-zA-Z0-9\-]+", "-", str(base).lower()).strip("-")
    return text[:120] or "zcc-product"


def _sku_proposal(product: SourceProduct) -> str:
    brand = product.brand_normalized or "ZCC"
    code = product.part_number or product.manufacturer_code or product.source_internal_sku or "UNKNOWN"
    prefix = {"ZCC.CT": "ZCC", "SAN OU": "SANOU", "STC": "STC"}.get(brand, brand.replace(" ", ""))
    return f"{prefix}-{code}".replace(" ", "-")


def classify_description(product: SourceProduct) -> str:
    desc = (product.description or "") + (product.short_description or "")
    if not desc.strip():
        return "FACTUAL_TECHNICAL_CONTENT"
    marketing_markers = ("بهترین", "فوق", "عالی", "تضمین", "ویژه")
    if any(m in desc for m in marketing_markers) and len(desc) > 400:
        return "MIXED"
    if len(desc) > 600:
        return "MARKETING_COPY"
    return "FACTUAL_TECHNICAL_CONTENT"


@dataclass
class CreatePlanRow:
    source_url: str
    identity: dict[str, Any]
    classification: dict[str, Any]
    factual_content: dict[str, Any]
    images: dict[str, Any]
    commerce_observations: dict[str, Any]
    description_class: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UpdatePlanRow:
    product_id: str
    sku: str
    field: str
    karzar_value: str
    zcc_source_value: str
    source_url: str
    source_timestamp: str | None
    recommended_action: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_create_plans(
    products: list[SourceProduct],
    reconcile: list[Phase2ReconcileRow],
    categories: dict[str, CategoryDecisionRow],
) -> list[CreatePlanRow]:
    by_url = {p.source_url: p for p in products}
    plans: list[CreatePlanRow] = []
    for row in reconcile:
        if row.primary_state != "CREATE_CANDIDATE":
            continue
        product = by_url[row.source_url]
        cat = categories.get(product.source_url)
        plans.append(
            CreatePlanRow(
                source_url=product.source_url,
                identity={
                    "brand": product.brand_normalized,
                    "manufacturer_code": product.manufacturer_code,
                    "sku_proposal": _sku_proposal(product),
                    "name": product.name_fa,
                    "slug_proposal": _slug_proposal(product),
                    "source_url": product.source_url,
                },
                classification={
                    "category_id": cat.proposed_karzar_category_id if cat else None,
                    "category_path": cat.proposed_karzar_category_path if cat else None,
                    "classification_confidence": cat.confidence if cat else "none",
                },
                factual_content={
                    "model": product.model,
                    "part_number": product.part_number,
                    "technical_specs": product.technical_specs,
                    "dimensions": product.dimensions,
                    "attributes": product.attributes,
                },
                images={
                    "main_image_source_url": product.main_image_url,
                    "gallery_source_urls": product.gallery_image_urls,
                    "image_count": product.gallery_count,
                    "image_flags": product.parse_flags,
                },
                commerce_observations={
                    "observed_price": product.price_normalized,
                    "observed_currency": product.price_currency,
                    "observed_availability": product.availability_normalized,
                    "crawl_timestamp": product.crawl_timestamp,
                    "commerce_authority": product.commerce_authority,
                },
                description_class=classify_description(product),
            )
        )
    plans.sort(key=lambda p: p.source_url)
    return plans


def build_update_plans(
    products: list[SourceProduct],
    reconcile: list[Phase2ReconcileRow],
    karzar_by_id: dict[str, Any],
) -> list[UpdatePlanRow]:
    by_url = {p.source_url: p for p in products}
    updates: list[UpdatePlanRow] = []
    for row in reconcile:
        if row.primary_state not in {"UPDATE_CONTENT_CANDIDATE", "NOOP_EXISTING_EXACT"}:
            continue
        product = by_url.get(row.source_url)
        if not product or not row.karzar_id:
            continue
        current = karzar_by_id.get(row.karzar_id)
        if not current:
            continue
        if product.name_fa and current.name and product.name_fa.strip() != current.name.strip():
            updates.append(
                UpdatePlanRow(
                    product_id=row.karzar_id,
                    sku=row.karzar_sku or "",
                    field="name",
                    karzar_value=current.name or "",
                    zcc_source_value=product.name_fa or "",
                    source_url=product.source_url,
                    source_timestamp=product.crawl_timestamp,
                    recommended_action="UPDATE_CONTENT_CANDIDATE"
                    if row.primary_state == "UPDATE_CONTENT_CANDIDATE"
                    else "HUMAN_REVIEW_REQUIRED",
                    reason="title differs",
                )
            )
        if row.availability_state == "AVAILABILITY_DIFFERENT":
            updates.append(
                UpdatePlanRow(
                    product_id=row.karzar_id,
                    sku=row.karzar_sku or "",
                    field="availability_observed",
                    karzar_value=str(current.is_available),
                    zcc_source_value=str(product.availability_normalized),
                    source_url=product.source_url,
                    source_timestamp=product.crawl_timestamp,
                    recommended_action="COMMERCE_DIFF_ONLY",
                    reason="availability observation differs; not an approved write",
                )
            )
    updates.sort(key=lambda u: (u.product_id, u.field))
    return updates
