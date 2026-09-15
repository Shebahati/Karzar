"""Phase-2 reconciliation states (identity + commerce dimensions)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from catalog_target.core import CurrentProduct, index_current_products
from zcc_ir_catalog.models import SourceProduct
from zcc_ir_catalog.reconcile import classify_match, match_source_to_karzar

PRIMARY_STATES = (
    "NOOP_EXISTING_EXACT",
    "UPDATE_CONTENT_CANDIDATE",
    "CREATE_CANDIDATE",
    "HOLD_BRAND_REVIEW",
    "HOLD_IDENTITY_REVIEW",
    "HOLD_CATEGORY_REVIEW",
    "HOLD_SOURCE_CONFLICT",
    "HOLD_DUPLICATE",
    "HOLD_OTHER",
)

PRICE_STATES = ("PRICE_SAME", "PRICE_DIFFERENT", "PRICE_SOURCE_INVALID", "PRICE_UNKNOWN")
AVAIL_STATES = ("AVAILABILITY_SAME", "AVAILABILITY_DIFFERENT", "AVAILABILITY_UNKNOWN")


@dataclass
class Phase2ReconcileRow:
    source_url: str
    brand_normalized: str | None
    manufacturer_code: str | None
    source_internal_sku: str | None
    primary_state: str
    match_method: str | None
    karzar_id: str | None
    karzar_sku: str | None
    price_state: str
    availability_state: str
    phase1_status: str | None
    review_reason: str | None
    blocking_flags: list[str]
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocking_flags"] = list(self.blocking_flags)
        return data


def _price_state(product: SourceProduct, current: CurrentProduct | None) -> str:
    if product.price_status != "ok":
        return "PRICE_SOURCE_INVALID"
    src = Decimal(product.price_normalized) if product.price_normalized else None
    if src is None or src <= 0:
        return "PRICE_SOURCE_INVALID"
    if current is None:
        return "PRICE_UNKNOWN"
    if current.base_price is None:
        return "PRICE_UNKNOWN"
    return "PRICE_SAME" if src == current.base_price else "PRICE_DIFFERENT"


def _availability_state(product: SourceProduct, current: CurrentProduct | None) -> str:
    src = product.availability_normalized
    if not src:
        return "AVAILABILITY_UNKNOWN"
    if current is None or current.is_available is None:
        return "AVAILABILITY_UNKNOWN"
    cur = "available" if current.is_available else "unavailable"
    if src in {"available", "unavailable"} and src != cur:
        return "AVAILABILITY_DIFFERENT"
    return "AVAILABILITY_SAME"


def _map_primary(
    product: SourceProduct,
    phase1_status: str,
    pending: str,
    current: CurrentProduct | None,
    review_reason: str | None,
    category_hold: bool,
) -> tuple[str, list[str]]:
    flags: list[str] = []
    if product.brand_normalized == "STC":
        flags.append("stc_brand_not_in_karzar")
    if "missing_brand" in (product.parse_flags or []) or not product.brand_normalized:
        return "HOLD_BRAND_REVIEW", flags + ["missing_or_untrusted_brand"]
    if "jsonld_brand_conflicts_name" in (product.parse_flags or []):
        flags.append("jsonld_brand_conflict")
    if product.brand_normalized and product.brand_normalized not in {"ZCC.CT", "SAN OU", "STC"}:
        if "missing_brand" in (product.parse_flags or []):
            return "HOLD_BRAND_REVIEW", flags

    if pending == "INVALID_SOURCE_RECORD":
        return "HOLD_SOURCE_CONFLICT", flags + ["invalid_source_record"]
    if pending == "AMBIGUOUS":
        return "HOLD_DUPLICATE", flags + ["ambiguous_match"]
    if pending == "REVIEW":
        reason = review_reason or "review"
        if reason == "missing_brand":
            return "HOLD_BRAND_REVIEW", flags + [reason]
        if reason in {"missing_manufacturer_code", "missing_usable_identity"}:
            return "HOLD_IDENTITY_REVIEW", flags + [reason]
        return "HOLD_IDENTITY_REVIEW", flags + [reason]

    if pending == "CREATE_CANDIDATE":
        if product.brand_normalized == "STC":
            return "HOLD_BRAND_REVIEW", flags + ["stc_brand_pending_owner"]
        if category_hold:
            return "HOLD_CATEGORY_REVIEW", flags + ["category_not_mapped"]
        return "CREATE_CANDIDATE", flags

    if pending == "MATCHED" and current is not None:
        detail = classify_match(product, current)
        if detail == "EXISTING_EXACT":
            return "NOOP_EXISTING_EXACT", flags
        if detail == "EXISTING_DIFFERENT_CONTENT":
            if category_hold:
                return "HOLD_CATEGORY_REVIEW", flags + ["category_not_mapped"]
            return "UPDATE_CONTENT_CANDIDATE", flags
        if detail in {"EXISTING_DIFFERENT_PRICE", "EXISTING_DIFFERENT_AVAILABILITY"}:
            return "NOOP_EXISTING_EXACT", flags
        return "UPDATE_CONTENT_CANDIDATE", flags

    if category_hold:
        return "HOLD_CATEGORY_REVIEW", flags + ["category_not_mapped"]
    return "HOLD_OTHER", flags + [f"unmapped_pending:{pending}"]


def reconcile_phase2(
    sources: list[SourceProduct],
    karzar: list[CurrentProduct],
    *,
    category_hold_urls: set[str],
    phase1_by_url: dict[str, str],
) -> list[Phase2ReconcileRow]:
    index = index_current_products(karzar)
    rows: list[Phase2ReconcileRow] = []
    for product in sources:
        pending, method, current, _cands, reason = match_source_to_karzar(product, index)
        phase1_status = phase1_by_url.get(product.source_url)
        category_hold = product.source_url in category_hold_urls
        primary, flags = _map_primary(product, phase1_status or "", pending, current, reason, category_hold)
        rows.append(
            Phase2ReconcileRow(
                source_url=product.source_url,
                brand_normalized=product.brand_normalized,
                manufacturer_code=product.manufacturer_code,
                source_internal_sku=product.source_internal_sku,
                primary_state=primary,
                match_method=method,
                karzar_id=current.id if current else None,
                karzar_sku=current.sku if current else None,
                price_state=_price_state(product, current),
                availability_state=_availability_state(product, current),
                phase1_status=phase1_status,
                review_reason=reason,
                blocking_flags=flags,
                evidence={
                    "name_fa": product.name_fa,
                    "parse_flags": product.parse_flags,
                    "category_path": product.category_path,
                },
            )
        )
    rows.sort(key=lambda r: r.source_url)
    return rows
