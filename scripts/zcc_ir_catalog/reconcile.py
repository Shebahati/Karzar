"""Conservative reconciliation of zcc.ir products against a Karzar snapshot.

No fuzzy name matching. No silent merges. No deactivation plan.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from catalog_target.core import CurrentProduct, identity_key, index_current_products, match_brand_sku
from zcc_ir_catalog.models import BrandRow, ReconcileRow, SourceProduct
from zcc_ir_catalog.normalize import KARZAR_BRAND_IDS, canonicalize_brand, karzar_alias_candidates

PRIMARY_STATUSES = (
    "INVALID_SOURCE_RECORD",
    "AMBIGUOUS",
    "REVIEW",
    "EXISTING_DIFFERENT_AVAILABILITY",
    "EXISTING_DIFFERENT_PRICE",
    "EXISTING_DIFFERENT_CONTENT",
    "EXISTING_EXACT",
    "CREATE_CANDIDATE",
)

BRAND_STATUSES = ("EXACT_EXISTING", "ALIAS_EXISTING", "NEW_BRAND_CANDIDATE", "REVIEW")


def _price_close(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return left == right


def _avail_token(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "available" if value else "unavailable"
    text = str(value).strip().lower()
    if text in {"available", "unavailable", "inquiry", "unknown", "other"}:
        return text
    if text in {"true", "1"}:
        return "available"
    if text in {"false", "0"}:
        return "unavailable"
    return text or None


def _content_differs(source: SourceProduct, current: CurrentProduct) -> bool:
    src_name = (source.name_fa or "").strip()
    cur_name = (current.name or "").strip()
    if src_name and cur_name and src_name != cur_name:
        return True
    src_img = bool(source.main_image_url)
    cur_img = bool(current.primary_image_url) or (current.image_count or 0) > 0
    if src_img != cur_img:
        return True
    return False


def _invalid_reason(product: SourceProduct) -> str | None:
    if not product.source_url or not product.source_url.startswith("https://"):
        return "malformed_source_url"
    if not product.name_fa and not product.manufacturer_code:
        return "empty_name_and_identity"
    return None


def match_source_to_karzar(
    product: SourceProduct,
    index: dict[tuple[str, str], list[CurrentProduct]],
) -> tuple[str, str | None, CurrentProduct | None, list[str], str | None]:
    """Return (status_or_pending, method, current, candidate_skus, review_reason)."""
    invalid = _invalid_reason(product)
    if invalid:
        return "INVALID_SOURCE_RECORD", None, None, [], invalid

    brand_key = product.brand_normalized
    manufacturer = product.part_number or ""
    if not brand_key:
        return "REVIEW", None, None, [], "missing_brand"
    if not manufacturer and not product.source_internal_sku:
        return "REVIEW", None, None, [], "missing_usable_identity"

    if manufacturer:
        decision = match_brand_sku(
            brand_key=brand_key,
            normalized_sku=manufacturer,
            index=index,
        )
        if decision.method == "exact_brand_sku" and decision.current:
            return "MATCHED", "exact_brand_manufacturer", decision.current, [], None
        if decision.method == "duplicate_current_sku":
            return "AMBIGUOUS", "duplicate_current_sku", None, decision.candidates, "duplicate_current_sku"

        for alias_sku in karzar_alias_candidates(
            brand_key=brand_key,
            manufacturer_key=manufacturer,
            internal_sku=product.source_internal_sku,
        ):
            hits = list(index.get(identity_key(brand_key, alias_sku), []))
            if len(hits) == 1:
                return "MATCHED", "proven_prefix_alias", hits[0], [], None
            if len(hits) > 1:
                return "AMBIGUOUS", "duplicate_prefixed_sku", None, [p.sku for p in hits], "duplicate_current_sku"

    if product.source_internal_sku:
        for alias_sku in karzar_alias_candidates(
            brand_key=brand_key,
            manufacturer_key="",
            internal_sku=product.source_internal_sku,
        ):
            hits = list(index.get(identity_key(brand_key, alias_sku), []))
            if len(hits) == 1:
                return "MATCHED", "internal_sku_prefix_alias", hits[0], [], None
            if len(hits) > 1:
                return "AMBIGUOUS", "duplicate_internal_alias", None, [p.sku for p in hits], "duplicate_current_sku"

    if not manufacturer:
        return "REVIEW", None, None, [], "missing_manufacturer_code"

    return "CREATE_CANDIDATE", "none", None, [], None


def classify_match(product: SourceProduct, current: CurrentProduct) -> str:
    src_price = Decimal(product.price_normalized) if product.price_normalized else None
    if product.availability_normalized and current.is_available is not None:
        src_avail = product.availability_normalized
        cur_avail = _avail_token(current.is_available)
        if src_avail in {"available", "unavailable"} and cur_avail and src_avail != cur_avail:
            return "EXISTING_DIFFERENT_AVAILABILITY"
    if product.price_status == "ok" and not _price_close(src_price, current.base_price):
        return "EXISTING_DIFFERENT_PRICE"
    if _content_differs(product, current):
        return "EXISTING_DIFFERENT_CONTENT"
    return "EXISTING_EXACT"


def reconcile_products(
    sources: list[SourceProduct],
    karzar: list[CurrentProduct],
) -> tuple[list[ReconcileRow], list[CurrentProduct]]:
    index = index_current_products(karzar)
    rows: list[ReconcileRow] = []
    matched_ids: set[str] = set()
    for product in sources:
        pending, method, current, candidates, reason = match_source_to_karzar(product, index)
        status = pending
        if pending == "MATCHED" and current is not None:
            status = classify_match(product, current)
            if current.id:
                matched_ids.add(current.id)
        if candidates and status not in {"AMBIGUOUS", "INVALID_SOURCE_RECORD"}:
            status = "AMBIGUOUS"
            reason = reason or "multiple_candidates"
        rows.append(
            ReconcileRow(
                source_url=product.source_url,
                brand_normalized=product.brand_normalized,
                manufacturer_code=product.manufacturer_code,
                source_internal_sku=product.source_internal_sku,
                name_fa=product.name_fa,
                status=status,
                match_method=method,
                karzar_id=current.id if current else None,
                karzar_sku=current.sku if current else (";".join(candidates) if candidates else None),
                karzar_name=current.name if current else None,
                karzar_brand=current.brand if current else None,
                source_price_toman=product.price_normalized,
                karzar_price_toman=str(current.base_price) if current and current.base_price is not None else None,
                source_availability=product.availability_normalized,
                karzar_availability=_avail_token(current.is_available) if current else None,
                review_reason=reason,
                commerce_authority=product.commerce_authority,
                parse_flags="|".join(product.parse_flags),
            )
        )

    corresponding = {p.brand_normalized for p in sources if p.brand_normalized} | {
        "ZCC.CT",
        "SAN OU",
        "STC",
    }
    karzar_only = [
        product
        for product in karzar
        if product.brand_key in corresponding
        and (product.id not in matched_ids)
        and not product.deleted_at
    ]
    return rows, karzar_only


def brand_inventory(
    sources: list[SourceProduct],
    karzar_brands: list[dict[str, Any]] | None = None,
) -> list[BrandRow]:
    counts: dict[str, int] = defaultdict(int)
    source_names: dict[str, set[str]] = defaultdict(set)
    for product in sources:
        key = product.brand_normalized or "(unknown)"
        counts[key] += 1
        if product.brand:
            source_names[key].add(product.brand)
    karzar_by_key: dict[str, dict[str, Any]] = {}
    for brand in karzar_brands or []:
        name = str(brand.get("name") or "")
        key = canonicalize_brand(name)
        if key:
            karzar_by_key[key] = brand
    rows: list[BrandRow] = []
    for key, count in sorted(counts.items(), key=lambda kv: kv[0]):
        names = sorted(source_names.get(key, []))
        display = names[0] if names else key
        if key == "(unknown)":
            rows.append(
                BrandRow(
                    brand_source_name=display,
                    normalized_brand=None,
                    karzar_brand_match=None,
                    karzar_brand_id=None,
                    confidence="none",
                    status="REVIEW",
                    product_count=count,
                    evidence="missing or conflicting brand tokens",
                )
            )
            continue
        karzar = karzar_by_key.get(key)
        if karzar:
            status = "EXACT_EXISTING" if canonicalize_brand(str(karzar.get("name"))) == key else "ALIAS_EXISTING"
            rows.append(
                BrandRow(
                    brand_source_name=display,
                    normalized_brand=key,
                    karzar_brand_match=str(karzar.get("name")),
                    karzar_brand_id=str(karzar.get("id")) if karzar.get("id") is not None else KARZAR_BRAND_IDS.get(key),
                    confidence="high",
                    status=status,
                    product_count=count,
                    evidence="name token + Karzar brand list",
                )
            )
            continue
        known_id = KARZAR_BRAND_IDS.get(key)
        if known_id:
            rows.append(
                BrandRow(
                    brand_source_name=display,
                    normalized_brand=key,
                    karzar_brand_match=key,
                    karzar_brand_id=known_id,
                    confidence="high",
                    status="ALIAS_EXISTING",
                    product_count=count,
                    evidence="seed/known Karzar brand id",
                )
            )
            continue
        rows.append(
            BrandRow(
                brand_source_name=display,
                normalized_brand=key,
                karzar_brand_match=None,
                karzar_brand_id=None,
                confidence="high" if key == "STC" else "medium",
                status="NEW_BRAND_CANDIDATE",
                product_count=count,
                evidence="present on zcc.ir; not in Karzar brand list",
            )
        )
    return rows
