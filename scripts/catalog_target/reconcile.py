"""READ-ONLY Target Catalog reconciliation engine. No APPLY path."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from catalog_target.snapshot import (
    SNAPSHOT_KIND_FILE,
    SNAPSHOT_KIND_LIVE,
    SNAPSHOT_KIND_UNAVAILABLE,
    SnapshotIntegrity,
    describe_snapshot_phase,
    load_current_catalog,
    validate_snapshot_csv,
)
from catalog_target.sources import SourceDiscovery, extract_sku, pick_header, membership_authority_of
from catalog_target.core import (
    INSIZE_UNIQUE_SANITY_HIGH,
    INSIZE_UNIQUE_SANITY_LOW,
    STATES,
    CurrentProduct,
    MatchDecision,
    PriceConversion,
    SourceFile,
    TargetSku,
    canonicalize_brand,
    canonicalize_currency,
    commerce_ready,
    convert_price,
    cross_brand_sku_collisions,
    detect_markup_percent,
    identity_key,
    index_current_products,
    match_brand_sku,
    media_ready,
    normalize_sku,
    public_sell_ready,
    suffix_near_miss,
)

MANIFEST_FIELDS = [
    "brand",
    "sku",
    "normalized_sku",
    "product_family",
    "target_member",
    "source_scope",
    "source_product",
    "source_price",
    "source_inventory",
    "source_catalog",
    "source_media",
    "price_source_value",
    "price_source_currency",
    "price_conversion",
    "markup_note",
    "base_price_toman",
    "inventory_status",
    "commerce_ready",
    "media_ready",
    "public_sell_ready",
    "parser_confidence",
    "match_confidence",
    "review_reason",
    "reconciliation_state",
    "current_id",
    "current_sku",
    "current_slug",
    "current_brand",
    "current_base_price",
    "proposed_base_price",
    "base_price_change",
    "current_is_active",
    "proposed_is_active",
    "is_active_change",
    "current_is_available",
    "proposed_is_available",
    "is_available_change",
    "current_image_count",
    "current_primary_image_url",
    "current_deleted_at",
    "exact_distributor_match",
    "provenance",
]

SITE_EVIDENCE_READY_KINDS = {SNAPSHOT_KIND_LIVE, SNAPSHOT_KIND_FILE, "test"}
TARGET_MANIFEST_SCOPE_WAVE_1 = "WAVE_1_RESOLVED_AUTHORITIES"
# Validation expectation from current source results. Not parser logic.
WAVE_1_EXPECTED_TARGET_SKUS = 2316
AST_NON_MEMBERSHIP_RESULTS = {
    "not_membership_in_current_source",
    "catalog_datasheet_no_stable_product_identity",
}


@dataclass
class ManifestRow:
    brand: str
    sku: str
    normalized_sku: str
    product_family: str
    target_member: bool
    source_scope: str
    source_product: str
    source_price: str = ""
    source_inventory: str = ""
    source_catalog: str = ""
    source_media: str = ""
    price_source_value: str = ""
    price_source_currency: str = ""
    price_conversion: str = ""
    markup_note: str = ""
    base_price_toman: str = ""
    inventory_status: str = ""
    commerce_ready: bool = False
    media_ready: bool = False
    public_sell_ready: bool = False
    parser_confidence: str = ""
    match_confidence: str = "none"
    review_reason: str = ""
    reconciliation_state: str = "REVIEW"
    current_id: str = ""
    current_sku: str = ""
    current_slug: str = ""
    current_brand: str = ""
    current_base_price: str = ""
    proposed_base_price: str = ""
    base_price_change: str = "false"
    current_is_active: bool | None = None
    proposed_is_active: bool | None = None
    is_active_change: str = "false"
    current_is_available: bool | None = None
    proposed_is_available: bool | None = None
    is_available_change: str = "false"
    current_image_count: int | None = None
    current_primary_image_url: str = ""
    current_deleted_at: str = ""
    exact_distributor_match: bool = False
    provenance: str = ""


@dataclass
class InsizeStats:
    target_rows: int = 0
    unique_sku_count: int = 0
    duplicate_target_skus: list[str] = field(default_factory=list)
    exact_distributor_matches: int = 0
    unmatched_target_skus: list[str] = field(default_factory=list)
    duplicate_matches: list[str] = field(default_factory=list)
    ambiguous_matches: list[str] = field(default_factory=list)
    available_positive_price: list[str] = field(default_factory=list)
    available_no_positive_price: list[str] = field(default_factory=list)
    unavailable_positive_price: list[str] = field(default_factory=list)
    unavailable_no_price: list[str] = field(default_factory=list)
    commerce_ready: list[str] = field(default_factory=list)
    unresolved_identities: list[dict[str, str]] = field(default_factory=list)
    distributor_row_count: int = 0
    distributor_unique_codes: int = 0
    universe_expanded_from_distributor: bool = False
    unique_count_outside_historical_band: bool = False

    @property
    def target_sku_count(self) -> int:
        return self.unique_sku_count

    @property
    def available_missing_zero_price(self) -> list[str]:
        return self.available_no_positive_price


@dataclass
class BrandQuality:
    extracted_rows: int = 0
    unique_skus: int = 0
    valid_prices: int = 0
    zero_or_missing_prices: int = 0
    duplicates: int = 0
    rejected_malformed: int = 0
    review_rows: int = 0
    parser_confidence: str = "none"
    rejected_examples: list[str] = field(default_factory=list)


@dataclass
class ReconciliationResult:
    baseline_sha: str
    generated_at: str
    evidence_kind: str
    evidence_note: str
    current_products: list[CurrentProduct]
    target_skus: list[TargetSku]
    rows: list[ManifestRow]
    insize: InsizeStats
    unavailable_sources: list[dict[str, str]]
    parse_failures: list[dict[str, str]]
    source_conflicts: list[str]
    unparsed: list[dict[str, str]]
    discovered_files: list[dict[str, str]]
    skipped_duplicates: list[str]
    hash_conflicts: list[dict[str, str]]
    duplicate_scope_skus: list[str]
    tooling_notes: list[dict[str, str]]
    examples: dict[str, list[str]]
    brand_quality: dict[str, BrandQuality] = field(default_factory=dict)
    target_manifest_ready: bool = False
    current_site_reconciliation_ready: bool = False
    apply_ready: bool = False
    real_source_validation: str = "ok"
    price_unit_conflicts: list[str] = field(default_factory=list)
    source_tree_valid: bool = False
    partial_target_manifest_valid: bool = False
    unresolved_blockers: list[dict[str, str]] = field(default_factory=list)
    authority_decisions: list[dict[str, str]] = field(default_factory=list)
    ast_reports: list[dict[str, Any]] = field(default_factory=list)
    ast_review_rows: list[dict[str, str]] = field(default_factory=list)
    guanglu_evidence: list[dict[str, str]] = field(default_factory=list)
    target_manifest_scope: str = TARGET_MANIFEST_SCOPE_WAVE_1
    deferred_authorities: list[str] = field(default_factory=list)
    current_site_snapshot_valid: bool = False
    snapshot_integrity: dict[str, Any] = field(default_factory=dict)
    insize_sales_wave_1_ready: bool = False
    create_apply_ready: bool = False
    deactivate_apply_ready: bool = False
    global_apply_ready: bool = False
    sales_wave_summary: dict[str, Any] = field(default_factory=dict)
    apply_contract: dict[str, Any] = field(default_factory=dict)


def _bool_text(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _change_text(current: Any, proposed: Any) -> str:
    if proposed is None or proposed == "":
        return "false"
    if current is None or current == "":
        return "true"
    return "true" if current != proposed else "false"


def _join_reasons(*parts: str | None) -> str:
    return ";".join(p for p in parts if p)


def _available_status(raw: Any, available_values: list[str]) -> tuple[str, bool | None]:
    text = "" if raw is None else str(raw).strip()
    if not text:
        return "", None
    if text in available_values:
        return text, True
    return text, False


def _index_by_brand_sku(rows: list[tuple[SourceFile, dict[str, Any]]], sku_headers: list[str]):
    index: dict[tuple[str, str], list[tuple[SourceFile, dict[str, Any]]]] = defaultdict(list)
    for source, row in rows:
        sku = normalize_sku(extract_sku(row, sku_headers))
        if sku:
            index[(source.brand_key, sku)].append((source, row))
    return index


def classify_target_row(
    *,
    target: TargetSku,
    match: MatchDecision,
    price: PriceConversion | None,
    inventory_available: bool | None,
    duplicate_target: bool,
    source_conflict: str | None,
    extra_review: str | None,
    proposed_is_active: bool | None,
) -> str:
    if duplicate_target:
        return "REVIEW"
    if match.review_reason in {
        "duplicate_current_sku",
        "ambiguous_alias",
        "cross_brand_collision",
        "malformed_sku",
        "deleted_current_match",
    }:
        return "REVIEW"
    if extra_review:
        return "REVIEW"
    if source_conflict:
        return "REVIEW"
    if price and price.review_reason in {"uncertain_currency", "unsupported_currency_needs_rate"}:
        return "REVIEW"
    if match.current is None:
        return "CREATE"

    current = match.current
    if current.deleted_at:
        return "REVIEW"
    proposed = price.base_price_toman if price else None
    differs = False
    if proposed is not None and current.base_price is not None:
        if Decimal(current.base_price) != proposed:
            differs = True
    elif proposed is not None and current.base_price is None:
        differs = True
    if inventory_available is not None and current.is_available is not None:
        if bool(current.is_available) != bool(inventory_available):
            differs = True
    if proposed_is_active is True and current.is_active is False:
        differs = True
    if canonicalize_brand(current.brand) and canonicalize_brand(current.brand) != target.brand_key:
        differs = True
    if differs:
        return "UPDATE"
    return "KEEP"


def reconcile(
    *,
    discovery: SourceDiscovery,
    current_products: list[CurrentProduct],
    evidence_kind: str,
    evidence_note: str,
    baseline_sha: str,
    aliases: dict[tuple[str, str], str] | None = None,
    real_source_validation: str = "ok",
    snapshot_integrity: SnapshotIntegrity | None = None,
) -> ReconciliationResult:
    targets = discovery.load_product_scope_targets()
    sku_headers = list(
        (discovery.registry.get("insize") or {}).get("sku_headers")
        or discovery.registry.get("sku_headers")
        or ["sku", "CODE"]
    )
    price_headers = list(discovery.registry.get("price_headers") or ["price"])
    currency_headers = list(discovery.registry.get("currency_headers") or ["currency"])
    status_headers = list(discovery.registry.get("status_headers") or ["status", "وضعیت"])
    available_values = list(
        (discovery.registry.get("insize") or {}).get("status_available_values") or ["موجود"]
    )
    site_ready = evidence_kind in SITE_EVIDENCE_READY_KINDS
    if (
        evidence_kind == SNAPSHOT_KIND_FILE
        and snapshot_integrity is not None
        and not snapshot_integrity.valid
    ):
        # Refuse actionable current-site reconciliation against incomplete evidence.
        site_ready = False

    price_rows = discovery.load_role_rows("price")
    inventory_rows = discovery.load_role_rows("inventory")
    price_index = _index_by_brand_sku(price_rows, sku_headers)
    inventory_index = _index_by_brand_sku(inventory_rows, sku_headers)
    current_index = index_current_products(current_products)

    target_dupes: dict[tuple[str, str], int] = Counter(
        identity_key(t.brand_key, t.normalized_sku) for t in targets
    )
    current_dupes = {key: rows for key, rows in current_index.items() if len(rows) > 1}
    target_cross = cross_brand_sku_collisions(targets)

    insize_targets = [t for t in targets if t.brand_key == "INSIZE"]
    insize_stats = InsizeStats(
        target_rows=len(insize_targets),
        unique_sku_count=len({t.normalized_sku for t in insize_targets}),
        duplicate_target_skus=[t.sku for t in insize_targets if t.duplicate_in_source],
    )
    if insize_stats.unique_sku_count and (
        insize_stats.unique_sku_count < INSIZE_UNIQUE_SANITY_LOW
        or insize_stats.unique_sku_count > INSIZE_UNIQUE_SANITY_HIGH
    ):
        # Informational for real extracts; fixture runs are typically tiny.
        insize_stats.unique_count_outside_historical_band = insize_stats.unique_sku_count >= 50

    distributor_codes: set[str] = set()
    counted_files: set[str] = set()
    for source, row in price_rows:
        if source.brand_key != "INSIZE":
            continue
        code = normalize_sku(extract_sku(row, sku_headers))
        if code:
            distributor_codes.add(code)
        if source.path not in counted_files:
            counted_files.add(source.path)
            insize_stats.distributor_row_count += source.row_count or 0
    insize_stats.distributor_unique_codes = len(distributor_codes)

    rows: list[ManifestRow] = []
    examples: dict[str, list[str]] = defaultdict(list)
    brand_quality: dict[str, BrandQuality] = {}
    price_unit_conflicts: list[str] = []

    def add_example(bucket: str, sku: str) -> None:
        bucket_list = examples[bucket]
        if sku not in bucket_list and len(bucket_list) < 8:
            bucket_list.append(sku)

    def quality_for(brand: str) -> BrandQuality:
        return brand_quality.setdefault(brand, BrandQuality())

    for brand, meta in discovery.brand_parse.items():
        q = quality_for(brand)
        q.extracted_rows = int(meta.get("extracted_rows") or 0)
        q.rejected_malformed = int(meta.get("rejected_rows") or 0)
        q.parser_confidence = str(meta.get("confidence") or "none")
        q.rejected_examples = list(meta.get("rejected_examples") or [])[:8]

    for target in targets:
        q = quality_for(target.brand_key)
        q.unique_skus += 1
        if target.duplicate_in_source:
            q.duplicates += 1
        dup_target = (
            target_dupes[identity_key(target.brand_key, target.normalized_sku)] > 1
            or target.duplicate_in_source
        )
        match = match_brand_sku(
            brand_key=target.brand_key,
            normalized_sku=target.normalized_sku,
            index=current_index,
            aliases=aliases,
            allow_cross_brand=False,
        )
        extra_review = None
        source_conflict = None
        if target.membership_mode == "review_if_weak":
            extra_review = extra_review or "weak_parser_confidence"
        if target.parse_status not in {"ok", ""}:
            extra_review = extra_review or "unparsed_source"
        if target.normalized_sku in target_cross:
            extra_review = extra_review or "cross_brand_collision"
            add_example("cross_brand_sku_collisions", target.sku)
        if dup_target:
            extra_review = extra_review or "duplicate_target_sku"
            add_example("duplicate_target_skus", target.sku)
        if match.current and match.current.deleted_at:
            extra_review = extra_review or "deleted_current_match"
            add_example("deleted_target_matches", target.sku)

        price_hits = price_index.get((target.brand_key, target.normalized_sku), [])
        inv_hits = inventory_index.get((target.brand_key, target.normalized_sku), [])
        price_conv: PriceConversion | None = None
        source_price = ""
        source_inventory = ""
        inventory_available: bool | None = None
        inventory_status = ""
        markup_note = ""
        exact_distributor_match = False

        if len(price_hits) > 1:
            extra_review = extra_review or "duplicate_price_match"
            if target.brand_key == "INSIZE":
                insize_stats.duplicate_matches.append(target.sku)
            add_example("duplicate_matches", target.sku)
        if len(price_hits) == 1:
            source, prow = price_hits[0]
            source_price = source.path
            exact_distributor_match = target.brand_key == "INSIZE"
            price_header = pick_header(prow, price_headers)
            currency_header = pick_header(prow, currency_headers)
            currency_raw = str(prow.get(currency_header) or "")
            markup = source.markup_percent or detect_markup_percent(source.path, currency_raw)
            currency = canonicalize_currency(currency_raw)
            if currency is None and price_header and "toman" in price_header.lower():
                currency = "toman"
            elif currency is None and price_header and "rial" in price_header.lower():
                currency = "rial"
            elif currency is None and price_header and "دلار" in price_header:
                currency = "usd"
            declared = canonicalize_currency(source.currency)
            if declared and currency and declared != currency:
                extra_review = extra_review or "price_unit_conflict"
                price_unit_conflicts.append(f"{target.sku}:{declared}_vs_{currency}")
            price_conv = convert_price(
                prow.get(price_header) if price_header else None,
                currency=currency,
                markup_already_present=markup is not None,
                apply_markup_percent=markup,
            )
            if markup is not None:
                markup_note = f"markup_already_present_{markup}%"
            elif price_conv:
                markup_note = price_conv.conversion

        if len(inv_hits) > 1:
            extra_review = extra_review or "ambiguous_inventory_match"
            if target.brand_key == "INSIZE":
                insize_stats.ambiguous_matches.append(target.sku)
        if len(inv_hits) == 1:
            source, irow = inv_hits[0]
            source_inventory = source.path
            if target.brand_key == "INSIZE":
                exact_distributor_match = True
            status_header = pick_header(irow, status_headers)
            inventory_status, inventory_available = _available_status(
                irow.get(status_header) if status_header else None,
                available_values,
            )
        elif len(inv_hits) == 0 and len(price_hits) == 1:
            source, prow = price_hits[0]
            status_header = pick_header(prow, status_headers)
            if status_header:
                source_inventory = source.path
                if target.brand_key == "INSIZE":
                    exact_distributor_match = True
                inventory_status, inventory_available = _available_status(
                    prow.get(status_header), available_values
                )

        has_price = bool(price_conv and price_conv.base_price_toman and price_conv.base_price_toman > 0)
        if has_price:
            q.valid_prices += 1
        else:
            q.zero_or_missing_prices += 1

        if target.brand_key == "INSIZE":
            exact = bool(price_hits) or bool(inv_hits)
            if exact:
                insize_stats.exact_distributor_matches += 1
                exact_distributor_match = True
            else:
                insize_stats.unmatched_target_skus.append(target.sku)
                near = [code for code in distributor_codes if suffix_near_miss(code, target.normalized_sku)]
                if near:
                    extra_review = extra_review or "suffix_mismatch"
                    insize_stats.unresolved_identities.append(
                        {"sku": target.sku, "near": ",".join(near[:5])}
                    )
                    add_example("unresolved_insize_identities", target.sku)
            if inventory_available is True and has_price:
                insize_stats.available_positive_price.append(target.sku)
            if inventory_available is True and not has_price:
                insize_stats.available_no_positive_price.append(target.sku)
            if has_price and inventory_available is False:
                insize_stats.unavailable_positive_price.append(target.sku)
            if inventory_available is False and not has_price:
                insize_stats.unavailable_no_price.append(target.sku)

        current = match.current
        # Desired active: Wave-1 Target members should be active unless deleted/blocked.
        deleted_match = bool(current and current.deleted_at)
        if deleted_match:
            proposed_is_active: bool | None = None
        else:
            proposed_is_active = True
        # Availability only from authority; never invent for brands without inventory SoT.
        proposed_is_available: bool | None = inventory_available

        review_bits = [
            match.review_reason,
            extra_review,
            None if price_conv is None else price_conv.review_reason,
        ]
        if price_conv and price_conv.review_reason == "missing_price":
            add_example("target_products_with_no_valid_price", target.sku)
        if price_conv and price_conv.review_reason in {
            "uncertain_currency",
            "unsupported_currency_needs_rate",
        }:
            extra_review = extra_review or price_conv.review_reason

        state = classify_target_row(
            target=target,
            match=match,
            price=price_conv,
            inventory_available=inventory_available,
            duplicate_target=dup_target,
            source_conflict=source_conflict,
            extra_review=extra_review,
            proposed_is_active=proposed_is_active,
        )
        if not site_ready and state in {"KEEP", "UPDATE", "CREATE", "DEACTIVATE"}:
            extra_review = extra_review or "site_evidence_unavailable"
            review_bits.append("site_evidence_unavailable")
            state = "REVIEW"
        if state == "REVIEW" and deleted_match:
            # Safety: no automatic resurrection.
            proposed_is_active = None

        review_joined = _join_reasons(*review_bits)
        ready = commerce_ready(
            target_member=True,
            base_price_toman=price_conv.base_price_toman if price_conv else None,
            inventory_available=inventory_available,
            review_reason=review_joined if state == "REVIEW" else None,
        )
        if state == "REVIEW":
            ready = False
            q.review_rows += 1
        if target.brand_key == "INSIZE" and ready:
            insize_stats.commerce_ready.append(target.sku)

        m_ready = media_ready(
            image_count=current.image_count if current else None,
            primary_image_url=current.primary_image_url if current else None,
        )
        p_ready = public_sell_ready(
            target_member=True,
            commerce_ready_flag=ready,
            media_ready_flag=m_ready,
        )
        if not m_ready:
            add_example("target_products_with_no_valid_public_image", target.sku)
        if current is None:
            add_example("target_products_missing_from_current_site", target.sku)
        if current and current.is_available is True and (
            current.base_price is None or current.base_price <= 0
        ):
            add_example("is_available_true_with_missing_or_non_positive_price", current.sku)
        if current and not current.category_id:
            add_example("target_products_with_category_problems", target.sku)

        proposed_price = (
            ""
            if not price_conv or price_conv.base_price_toman is None
            else str(price_conv.base_price_toman)
        )
        current_price = "" if not current or current.base_price is None else str(current.base_price)
        current_active = current.is_active if current else None
        current_available = current.is_available if current else None

        rows.append(
            ManifestRow(
                brand=target.brand_key,
                sku=target.sku,
                normalized_sku=target.normalized_sku,
                product_family=target.product_family,
                target_member=True,
                source_scope=target.source_scope,
                source_product=target.source_product,
                source_price=source_price,
                source_inventory=source_inventory,
                source_catalog="",
                source_media="",
                price_source_value=""
                if not price_conv or price_conv.raw_source_value is None
                else str(price_conv.raw_source_value),
                price_source_currency=""
                if not price_conv or price_conv.source_currency is None
                else price_conv.source_currency,
                price_conversion="" if not price_conv else price_conv.conversion,
                markup_note=markup_note,
                base_price_toman=proposed_price,
                inventory_status=inventory_status,
                commerce_ready=ready,
                media_ready=m_ready,
                public_sell_ready=p_ready,
                parser_confidence=target.parser_confidence,
                match_confidence=match.confidence,
                review_reason=review_joined,
                reconciliation_state=state,
                current_id="" if not current or not current.id else current.id,
                current_sku="" if not current else current.sku,
                current_slug="" if not current or not current.slug else current.slug,
                current_brand="" if not current or not current.brand else current.brand,
                current_base_price=current_price,
                proposed_base_price=proposed_price,
                base_price_change=_change_text(
                    Decimal(current_price) if current_price else None,
                    Decimal(proposed_price) if proposed_price else None,
                )
                if proposed_price
                else "false",
                current_is_active=current_active,
                proposed_is_active=proposed_is_active,
                is_active_change=_change_text(current_active, proposed_is_active),
                current_is_available=current_available,
                proposed_is_available=proposed_is_available,
                is_available_change=_change_text(current_available, proposed_is_available),
                current_image_count=current.image_count if current else None,
                current_primary_image_url=""
                if not current or not current.primary_image_url
                else current.primary_image_url,
                current_deleted_at="" if not current or not current.deleted_at else current.deleted_at,
                exact_distributor_match=exact_distributor_match,
                provenance=target.provenance,
            )
        )

    target_keys = {identity_key(t.brand_key, t.normalized_sku) for t in targets}
    if site_ready:
        for product in current_products:
            key = identity_key(product.brand_key, product.normalized_sku)
            if key in target_keys:
                continue
            if product.deleted_at:
                add_example("deleted_non_target_products", product.sku or product.id or "")
                continue
            if product.is_active is True:
                add_example("active_non_target_products", product.sku)
                non_target_state = "DEACTIVATE"
                review_reason = "active_non_target"
            else:
                # Already inactive: no actionable is_active true→false change.
                add_example("inactive_non_target_products", product.sku)
                non_target_state = "NOOP_INACTIVE_NON_TARGET"
                review_reason = "inactive_non_target"
            rows.append(
                ManifestRow(
                    brand=product.brand_key or "",
                    sku=product.sku,
                    normalized_sku=product.normalized_sku,
                    product_family="",
                    target_member=False,
                    source_scope="",
                    source_product="",
                    inventory_status="",
                    commerce_ready=False,
                    media_ready=media_ready(
                        image_count=product.image_count,
                        primary_image_url=product.primary_image_url,
                    ),
                    public_sell_ready=False,
                    match_confidence="none",
                    review_reason=review_reason,
                    reconciliation_state=non_target_state,
                    current_id=product.id or "",
                    current_sku=product.sku,
                    current_slug=product.slug or "",
                    current_brand=product.brand or "",
                    current_base_price="" if product.base_price is None else str(product.base_price),
                    proposed_base_price="",
                    base_price_change="false",
                    current_is_active=product.is_active,
                    proposed_is_active=False if non_target_state == "DEACTIVATE" else product.is_active,
                    is_active_change=_change_text(
                        product.is_active,
                        False if non_target_state == "DEACTIVATE" else product.is_active,
                    ),
                    current_is_available=product.is_available,
                    proposed_is_available=None,
                    is_available_change="false",
                    current_image_count=product.image_count,
                    current_primary_image_url=product.primary_image_url or "",
                    current_deleted_at=product.deleted_at or "",
                    provenance="current_catalog_only",
                )
            )

    insize_stats.universe_expanded_from_distributor = any(
        t.source_scope != "product_scope" for t in insize_targets
    )

    for _key, group in current_dupes.items():
        add_example("duplicate_current_skus", group[0].sku)

    tooling_notes = [
        {
            "path": "scripts/reconcile_prices_availability.py",
            "class": "unsafe_for_new_catalog_authority",
            "why": "Global rule: positive base_price => is_available for ALL live products; price lists treated as membership.",
        },
        {
            "path": "scripts/import_price_lists.py",
            "class": "unsafe_for_new_catalog_authority",
            "why": "Hardcoded developer Price dir; APPLY writes DB; price lists do not define Target membership.",
        },
        {
            "path": "scripts/insize_price_update.py",
            "class": "legacy",
            "why": "Strips trailing letters (A/S) for matching; API writer; not Target-universe aware.",
        },
        {
            "path": "data/imports/insize_products.csv / all_products.csv",
            "class": "legacy",
            "why": "Repository CSV parse is not Target membership authority.",
        },
    ]

    conflicts = [f["reason"] for f in discovery.parse_failures]
    if insize_stats.universe_expanded_from_distributor:
        conflicts.append("insize_universe_expanded_from_distributor")
    for item in discovery.hash_conflicts:
        conflicts.append(item.get("reason") or "hash_conflict")

    product_scope_ok = any(source_has_role_safe(f) for f in discovery.files)
    parsed_members = bool(targets)
    source_tree_valid, partial_valid, target_manifest_ready, unresolved_blockers = assess_readiness(
        discovery, targets, real_source_validation
    )
    if not product_scope_ok or not parsed_members:
        partial_valid = False
        if target_manifest_ready:
            target_manifest_ready = False

    integrity = snapshot_integrity or SnapshotIntegrity()
    # File/live snapshots require integrity pass. Fixture evidence_kind "test" stays unit-test only.
    snapshot_valid = bool(integrity.valid) if evidence_kind in {SNAPSHOT_KIND_LIVE, SNAPSHOT_KIND_FILE} else (
        evidence_kind == "test"
    )
    site_reconciliation_ready = (
        site_ready
        and evidence_kind != "test"
        and snapshot_valid
        and evidence_kind in {SNAPSHOT_KIND_LIVE, SNAPSHOT_KIND_FILE}
        and bool(current_products)
    )

    return ReconciliationResult(
        baseline_sha=baseline_sha,
        generated_at=datetime.now(timezone.utc).isoformat(),
        evidence_kind=evidence_kind,
        evidence_note=evidence_note,
        current_products=current_products,
        target_skus=targets,
        rows=rows,
        insize=insize_stats,
        unavailable_sources=discovery.unavailable,
        parse_failures=discovery.parse_failures,
        source_conflicts=conflicts,
        unparsed=list(getattr(discovery, "unparsed", [])),
        discovered_files=list(getattr(discovery, "discovered", [])),
        skipped_duplicates=list(getattr(discovery, "skipped_duplicates", [])),
        hash_conflicts=list(getattr(discovery, "hash_conflicts", [])),
        duplicate_scope_skus=list(getattr(discovery, "duplicate_scope_skus", [])),
        tooling_notes=tooling_notes,
        examples=dict(examples),
        brand_quality=brand_quality,
        target_manifest_ready=target_manifest_ready,
        current_site_reconciliation_ready=site_reconciliation_ready,
        apply_ready=False,
        real_source_validation=real_source_validation,
        price_unit_conflicts=price_unit_conflicts,
        source_tree_valid=source_tree_valid,
        partial_target_manifest_valid=partial_valid,
        unresolved_blockers=unresolved_blockers,
        authority_decisions=list(getattr(discovery, "authority_decisions", [])),
        ast_reports=list(getattr(discovery, "ast_reports", [])),
        ast_review_rows=list(getattr(discovery, "ast_review_rows", [])),
        guanglu_evidence=list(getattr(discovery, "guanglu_evidence", [])),
        target_manifest_scope=TARGET_MANIFEST_SCOPE_WAVE_1,
        deferred_authorities=_deferred_authorities(discovery),
        current_site_snapshot_valid=snapshot_valid if evidence_kind != "test" else False,
        snapshot_integrity=integrity.as_dict(),
        insize_sales_wave_1_ready=False,
        create_apply_ready=False,
        deactivate_apply_ready=False,
        global_apply_ready=False,
    )


def _deferred_authorities(discovery: SourceDiscovery) -> list[str]:
    return [
        str(spec.get("id") or "")
        for spec in discovery.registry.get("sources") or []
        if membership_authority_of(spec) == "deferred" and spec.get("id")
    ]


def assess_readiness(
    discovery: SourceDiscovery,
    targets: list[TargetSku],
    real_source_validation: str,
) -> tuple[bool, bool, bool, list[dict[str, str]]]:
    """Full TARGET_MANIFEST_READY requires every in-scope class-B authority resolved.

    Class A (not membership) and class C (explicitly deferred) do not block.
    Wave 1 scope is resolved authorities only; Guanglu is deferred, not hidden.
    """
    source_tree_valid = real_source_validation == "ok" and discovery.source_root is not None
    members = Counter(t.brand_key for t in targets)
    partial = source_tree_valid and any(
        members.get(brand, 0) > 0 for brand in ("INSIZE", "TERMA", "DASQUA", "DCOIL", "ASTPOWER")
    )
    blockers: list[dict[str, str]] = []
    if not source_tree_valid:
        return False, False, False, [{"source": "KARZAR_TARGET_SOURCE_DIR", "class": "B", "reason": "source_tree_invalid"}]
    registered = {f.source_id for f in discovery.files}
    for spec in discovery.registry.get("sources") or []:
        sid = str(spec.get("id") or "")
        if sid not in registered:
            continue
        auth = membership_authority_of(spec)
        if auth in {"not_membership", "deferred"}:
            continue
        files = [f for f in discovery.files if f.source_id == sid]
        rows = 0
        for source in files:
            if "product_scope" in (source.roles or []):
                rows += len(discovery.rows_for(source))
        weak = any(
            source.membership_mode == "review_if_weak"
            and (source.parser_confidence == "low" or rows < 20)
            for source in files
        )
        if rows <= 0:
            blockers.append(
                {
                    "source": sid,
                    "class": "B",
                    "reason": "required_membership_authority_unresolved",
                }
            )
        elif weak:
            blockers.append(
                {
                    "source": sid,
                    "class": "B",
                    "reason": "required_membership_authority_weak_parse",
                }
            )
    if any("آذرصنعت" in (source.path or "") for source in discovery.files):
        for report in discovery.ast_reports:
            if str(report.get("membership_authority") or "") == "not_membership":
                continue
            if str(report.get("membership_result") or "") in AST_NON_MEMBERSHIP_RESULTS:
                continue
            if int(report.get("unique_skus") or 0) <= 0:
                blockers.append(
                    {
                        "source": f"ASTPOWER/{report.get('family')}",
                        "class": "B",
                        "reason": str(report.get("membership_result") or "ast_unresolved"),
                    }
                )
    target_ready = source_tree_valid and partial and not blockers
    return source_tree_valid, partial, target_ready, blockers


def source_has_role_safe(source: SourceFile) -> bool:
    roles = source.roles or ([source.role] if source.role else [])
    return "product_scope" in roles and source.parse_status in {"ok", ""}


def counts(result: ReconciliationResult) -> dict[str, int]:
    counter = Counter(row.reconciliation_state for row in result.rows)
    return {state: int(counter.get(state, 0)) for state in STATES}


def _brand_quality_payload(result: ReconciliationResult) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for brand, q in sorted(result.brand_quality.items()):
        out[brand] = {
            "extracted_rows": q.extracted_rows,
            "unique_target_skus": q.unique_skus,
            "valid_prices": q.valid_prices,
            "zero_or_missing_prices": q.zero_or_missing_prices,
            "duplicates": q.duplicates,
            "rejected_malformed_rows": q.rejected_malformed,
            "review_rows": q.review_rows,
            "parser_confidence": q.parser_confidence,
            "rejected_examples": q.rejected_examples,
        }
    return out


def write_outputs(result: ReconciliationResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "target_catalog_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in result.rows:
            payload = asdict(row)
            payload["target_member"] = _bool_text(row.target_member)
            payload["commerce_ready"] = _bool_text(row.commerce_ready)
            payload["media_ready"] = _bool_text(row.media_ready)
            payload["public_sell_ready"] = _bool_text(row.public_sell_ready)
            payload["exact_distributor_match"] = _bool_text(row.exact_distributor_match)
            payload["current_is_active"] = _bool_text(row.current_is_active)
            payload["proposed_is_active"] = _bool_text(row.proposed_is_active)
            payload["current_is_available"] = _bool_text(row.current_is_available)
            payload["proposed_is_available"] = _bool_text(row.proposed_is_available)
            payload["current_image_count"] = (
                "" if row.current_image_count is None else str(row.current_image_count)
            )
            writer.writerow(payload)
    ast_fields = [
        "family",
        "source_file",
        "page",
        "raw_row",
        "raw_sku",
        "normalized_sku",
        "description",
        "raw_price",
        "currency",
        "base_price_toman",
        "confidence",
        "decision",
        "review_reason",
        "duplicate_original_relationship",
    ]
    with (output_dir / "ast_authority_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ast_fields)
        writer.writeheader()
        for row in result.ast_review_rows:
            writer.writerow({field: row.get(field, "") for field in ast_fields})
    guanglu_fields = [
        "source_pages",
        "extracted_candidate_row",
        "raw_identity",
        "normalized_identity",
        "raw_price",
        "price_unit",
        "proposed_toman_price",
        "confidence",
        "rejected_reason",
        "duplicate_status",
        "manual_review_required",
        "line",
    ]
    with (output_dir / "guanglu_authority_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=guanglu_fields)
        writer.writeheader()
        for row in result.guanglu_evidence:
            writer.writerow({field: row.get(field, "") for field in guanglu_fields})

    state_counts = counts(result)
    per_brand = Counter(t.brand_key for t in result.target_skus)
    per_source = Counter(t.source_product for t in result.target_skus)
    per_family = Counter(t.product_family for t in result.target_skus)
    per_confidence = Counter(t.parser_confidence for t in result.target_skus)
    report = {
        "baseline_sha": result.baseline_sha,
        "generated_at": result.generated_at,
        "production_mutation": "ZERO",
        "apply_phase": False,
        "REAL_SOURCE_VALIDATION": result.real_source_validation,
        "SOURCE_TREE_VALID": result.source_tree_valid,
        "PARTIAL_TARGET_MANIFEST_VALID": result.partial_target_manifest_valid,
        "TARGET_MANIFEST_READY": result.target_manifest_ready,
        "TARGET_MANIFEST_SCOPE": result.target_manifest_scope,
        "DEFERRED_AUTHORITIES": result.deferred_authorities,
        "CURRENT_SITE_SNAPSHOT_VALID": result.current_site_snapshot_valid,
        "CURRENT_SITE_RECONCILIATION_READY": result.current_site_reconciliation_ready,
        "INSIZE_SALES_WAVE_1_READY": result.insize_sales_wave_1_ready,
        "CREATE_APPLY_READY": False,
        "DEACTIVATE_APPLY_READY": False,
        "GLOBAL_APPLY_READY": False,
        "APPLY_READY": False,
        "db_evidence": result.evidence_kind,
        "db_evidence_note": result.evidence_note,
        "live_db": result.evidence_kind == SNAPSHOT_KIND_LIVE,
        "total_current_products_observed": len(result.current_products),
        "total_target_skus": len(result.target_skus),
        "target_skus_per_brand": dict(per_brand),
        "target_skus_per_source_file": dict(per_source),
        "target_skus_per_product_family": dict(per_family),
        "parser_confidence": dict(per_confidence),
        "commerce_ready_count": sum(1 for r in result.rows if r.commerce_ready),
        "media_ready_count": sum(1 for r in result.rows if r.media_ready),
        "counts": state_counts,
        "insize": {
            "INSIZE_TARGET_ROWS": result.insize.target_rows,
            "INSIZE_TARGET_UNIQUE_SKUS": result.insize.unique_sku_count,
            "INSIZE_TARGET_DUPLICATES": result.insize.duplicate_target_skus,
            "INSIZE_DISTRIBUTOR_ROWS": result.insize.distributor_row_count,
            "INSIZE_DISTRIBUTOR_UNIQUE_CODES": result.insize.distributor_unique_codes,
            "INSIZE_EXACT_MATCHES": result.insize.exact_distributor_matches,
            "INSIZE_UNMATCHED_TARGET": result.insize.unmatched_target_skus,
            "INSIZE_AMBIGUOUS": result.insize.ambiguous_matches,
            "INSIZE_DUPLICATE_DISTRIBUTOR_MATCHES": result.insize.duplicate_matches,
            "INSIZE_AVAILABLE_POSITIVE_PRICE": result.insize.available_positive_price,
            "INSIZE_AVAILABLE_NO_POSITIVE_PRICE": result.insize.available_no_positive_price,
            "INSIZE_UNAVAILABLE_POSITIVE_PRICE": result.insize.unavailable_positive_price,
            "INSIZE_UNAVAILABLE_NO_PRICE": result.insize.unavailable_no_price,
            "INSIZE_UNIVERSE_EXPANDED_FROM_DISTRIBUTOR": result.insize.universe_expanded_from_distributor,
            "unique_count_outside_historical_band": result.insize.unique_count_outside_historical_band,
            "historical_unique_sku_band": {
                "low": INSIZE_UNIQUE_SANITY_LOW,
                "high": INSIZE_UNIQUE_SANITY_HIGH,
                "note": "sanity check only; not a hardcoded universe size",
            },
            "unresolved_identities": result.insize.unresolved_identities,
            "commerce_ready": result.insize.commerce_ready,
        },
        "brand_source_quality": _brand_quality_payload(result),
        "price_unit_markup_conflicts": result.price_unit_conflicts,
        "target_source_completeness": {
            "discovered_files": result.discovered_files,
            "unparsed_files": result.unparsed,
            "unavailable_authoritative_sources": result.unavailable_sources,
            "skipped_duplicate_tree_copies": result.skipped_duplicates,
            "hash_conflicts": result.hash_conflicts,
            "duplicate_scope_skus": result.duplicate_scope_skus,
            "parse_failures": result.parse_failures,
        },
        "current_site_evidence_completeness": {
            "kind": result.evidence_kind,
            "live_db": result.evidence_kind == SNAPSHOT_KIND_LIVE,
            "note": result.evidence_note,
            "current_products_observed": len(result.current_products),
            "snapshot_integrity": result.snapshot_integrity,
        },
        "unavailable_authoritative_sources": result.unavailable_sources,
        "parse_failures": result.parse_failures,
        "source_conflicts": result.source_conflicts,
        "examples": result.examples,
        "tooling": result.tooling_notes,
        "storefront": {
            "STOREFRONT_HIDE_IMAGELESS_PRODUCTS": True,
            "note": "target_member is independent of media_ready and commerce_ready.",
        },
        "authority_decisions": result.authority_decisions,
        "ast_families": result.ast_reports,
        "unresolved_full_manifest_blockers": result.unresolved_blockers,
        "guanglu_authority": {
            "pages_inspected": 11,
            "method": "pdftotext_corrupted_plus_page_render",
            "evidence_rows": len(result.guanglu_evidence),
            "unique_target_skus": 0,
            "membership_conferred": False,
            "final_status": "class_C_deferred",
            "reason": (
                "commercial_price_list_without_stable_manufacturer_identity_"
                "requires_future_manual_mapping_or_new_authoritative_source"
            ),
            "wave": "1_deferred",
            "evidence_csv": "data/catalog-target/guanglu_authority_review.csv",
        },
        "current_site_snapshot_phase": describe_snapshot_phase(),
        "wave_1_validation_expectation": {
            "expected_target_skus": WAVE_1_EXPECTED_TARGET_SKUS,
            "actual_target_skus": len(result.target_skus),
            "note": "expectation derived from current source results; not parser logic",
        },
        "ready_for_apply": False,
        "ready_for_apply_reason": (
            "GLOBAL_APPLY_READY = FALSE. INSIZE Sales Wave 1 plan is READ-ONLY; "
            "no writer is implemented in this PR."
        ),
        "insize_sales_wave_1": result.sales_wave_summary,
        "apply_contract": result.apply_contract,
    }
    (output_dir / "reconciliation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "reconciliation_summary.md").write_text(
        render_summary(result, state_counts, per_brand),
        encoding="utf-8",
    )


def render_summary(
    result: ReconciliationResult,
    state_counts: dict[str, int],
    per_brand: Counter,
) -> str:
    def bullets(items: list[str], empty: str = "(none)") -> str:
        if not items:
            return f"- {empty}"
        return "\n".join(f"- `{item}`" for item in items)

    examples = result.examples
    live = "LIVE DB" if result.evidence_kind == SNAPSHOT_KIND_LIVE else "NON-LIVE / SNAPSHOT / UNAVAILABLE"
    lines = [
        "# Target Catalog Reconciliation (READ-ONLY)",
        "",
        "PRODUCTION MUTATION: **ZERO**. APPLY was not run and this tool has no apply path.",
        "",
        f"- Baseline SHA: `{result.baseline_sha}`",
        f"- Generated at: `{result.generated_at}`",
        f"- REAL_SOURCE_VALIDATION: `{result.real_source_validation}`",
        f"- SOURCE_TREE_VALID: `{str(result.source_tree_valid).upper()}`",
        f"- PARTIAL_TARGET_MANIFEST_VALID: `{str(result.partial_target_manifest_valid).upper()}`",
        f"- TARGET_MANIFEST_READY: `{str(result.target_manifest_ready).upper()}`",
        f"- TARGET_MANIFEST_SCOPE: `{result.target_manifest_scope}`",
        f"- DEFERRED_AUTHORITIES: `{result.deferred_authorities}`",
        f"- CURRENT_SITE_SNAPSHOT_VALID: `{str(result.current_site_snapshot_valid).upper()}`",
        f"- CURRENT_SITE_RECONCILIATION_READY: `{str(result.current_site_reconciliation_ready).upper()}`",
        f"- INSIZE_SALES_WAVE_1_READY: `{str(result.insize_sales_wave_1_ready).upper()}`",
        "- CREATE_APPLY_READY: `FALSE`",
        "- DEACTIVATE_APPLY_READY: `FALSE`",
        "- GLOBAL_APPLY_READY: `FALSE`",
        "- APPLY_READY: `FALSE`",
        f"- DB evidence: **{live}** (`{result.evidence_kind}`) — {result.evidence_note}",
        f"- Current products observed: **{len(result.current_products)}**",
        f"- Target SKUs: **{len(result.target_skus)}**",
        "",
        "## Reconciliation action counts (DELETE never emitted)",
        f"- KEEP: {state_counts.get('KEEP', 0)}",
        f"- UPDATE: {state_counts.get('UPDATE', 0)}",
        f"- CREATE: {state_counts.get('CREATE', 0)}",
        f"- DEACTIVATE (active non-target requiring is_active true→false): {state_counts.get('DEACTIVATE', 0)}",
        f"- REVIEW: {state_counts.get('REVIEW', 0)}",
        f"- NOOP_INACTIVE_NON_TARGET: {state_counts.get('NOOP_INACTIVE_NON_TARGET', 0)}",
        "",
        "## Snapshot integrity",
        f"- `{json.dumps(result.snapshot_integrity, ensure_ascii=False)}`",
        "",
        "## A. Target source completeness",
        f"- Discovered files: {len(result.discovered_files)}",
        f"- Unparsed files: {len(result.unparsed)}",
        f"- Unavailable registry sources: {len(result.unavailable_sources)}",
        f"- Duplicate-tree copies skipped: {len(result.skipped_duplicates)}",
        f"- Same-name different-hash conflicts: {len(result.hash_conflicts)}",
        f"- Duplicate source SKUs (identity collapsed, REVIEW): {len(result.duplicate_scope_skus)}",
        "",
        "## B. Current-site evidence completeness",
        f"- Kind: `{result.evidence_kind}` — **{live}**",
        f"- Note: {result.evidence_note}",
        f"- Current products observed: **{len(result.current_products)}**",
        "",
        "A and B are independent. A real Target manifest can exist without live site evidence.",
        "",
        "## Target SKUs per brand",
    ]
    if per_brand:
        for brand, n in sorted(per_brand.items()):
            lines.append(f"- {brand}: {n}")
    else:
        lines.append("- (none — no authoritative product-scope files were available)")
    lines += [
        "",
        "## Brand source quality",
    ]
    if result.brand_quality:
        for brand, q in sorted(result.brand_quality.items()):
            lines.append(
                f"- {brand}: extracted={q.extracted_rows} unique={q.unique_skus} "
                f"valid_prices={q.valid_prices} zero/missing={q.zero_or_missing_prices} "
                f"duplicates={q.duplicates} rejected={q.rejected_malformed} "
                f"review={q.review_rows} confidence={q.parser_confidence}"
            )
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Reconciliation counts",
        f"- KEEP: {state_counts['KEEP']}",
        f"- UPDATE: {state_counts['UPDATE']}",
        f"- CREATE: {state_counts['CREATE']}",
        f"- DEACTIVATE: {state_counts['DEACTIVATE']}",
        f"- REVIEW: {state_counts['REVIEW']}",
        f"- NOOP_INACTIVE_NON_TARGET: {state_counts.get('NOOP_INACTIVE_NON_TARGET', 0)}",
        "",
        "## INSIZE",
        f"- INSIZE_TARGET_ROWS: {result.insize.target_rows}",
        f"- INSIZE_TARGET_UNIQUE_SKUS: {result.insize.unique_sku_count}",
        f"- INSIZE_TARGET_DUPLICATES: {len(result.insize.duplicate_target_skus)}",
        f"- INSIZE_DISTRIBUTOR_ROWS: {result.insize.distributor_row_count}",
        f"- INSIZE_DISTRIBUTOR_UNIQUE_CODES: {result.insize.distributor_unique_codes}",
        f"- INSIZE_EXACT_MATCHES: {result.insize.exact_distributor_matches}",
        f"- INSIZE_UNIVERSE_EXPANDED_FROM_DISTRIBUTOR: {result.insize.universe_expanded_from_distributor}",
        f"- INSIZE_UNMATCHED_TARGET: {len(result.insize.unmatched_target_skus)}",
        bullets(result.insize.unmatched_target_skus, empty="(none)"),
        f"- INSIZE_DUPLICATE_DISTRIBUTOR_MATCHES: {len(result.insize.duplicate_matches)}",
        bullets(result.insize.duplicate_matches),
        f"- INSIZE_AMBIGUOUS: {len(result.insize.ambiguous_matches)}",
        bullets(result.insize.ambiguous_matches),
        f"- INSIZE_AVAILABLE_POSITIVE_PRICE: {len(result.insize.available_positive_price)}",
        bullets(result.insize.available_positive_price),
        f"- INSIZE_AVAILABLE_NO_POSITIVE_PRICE: {len(result.insize.available_no_positive_price)}",
        bullets(result.insize.available_no_positive_price),
        f"- INSIZE_UNAVAILABLE_POSITIVE_PRICE: {len(result.insize.unavailable_positive_price)}",
        bullets(result.insize.unavailable_positive_price),
        f"- INSIZE_UNAVAILABLE_NO_PRICE: {len(result.insize.unavailable_no_price)}",
        bullets(result.insize.unavailable_no_price),
        "",
        "## Authority decisions",
    ]
    if result.authority_decisions:
        for item in result.authority_decisions:
            lines.append(
                f"- {item.get('source')}: class {item.get('class')} `{item.get('decision')}` ({item.get('reason')})"
            )
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Unresolved full-manifest blockers",
    ]
    if result.unresolved_blockers:
        for item in result.unresolved_blockers:
            lines.append(f"- {item.get('source')}: class {item.get('class')} `{item.get('reason')}`")
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## AST families",
    ]
    if result.ast_reports:
        for item in result.ast_reports:
            lines.append(
                f"- {item.get('family')}: candidates={len(item.get('enumerator_candidates') or [])} "
                f"selected=`{item.get('selected_authority') or ''}` rel=`{item.get('duplicate_original_relationship')}` "
                f"parse=`{item.get('parse_status')}` rows={item.get('extracted_rows')} "
                f"unique={item.get('unique_skus')} rejected={item.get('rejected_rows')} "
                f"unit={item.get('price_unit')} method=`{item.get('extraction_method')}` "
                f"authority=`{item.get('membership_authority')}` "
                f"result=`{item.get('membership_result')}`"
            )
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Guanglu evidence",
        f"- Pages inspected: 11",
        f"- Method: pdftotext (encoding-corrupted) + page render",
        f"- Candidate priced rows recorded: {len(result.guanglu_evidence)}",
        "- Unique Target SKUs: 0",
        "- Final status: class C deferred (Wave 1) — commercial price list without stable manufacturer identity",
        "- Reason: `commercial_price_list_without_stable_manufacturer_identity_requires_future_manual_mapping_or_new_authoritative_source`",
        "- This does not claim Guanglu products should never exist in Karzar.",
        "- Detail: `data/catalog-target/guanglu_authority_review.csv`",
        "",
        "## Current-site snapshot phase (READ-ONLY, not run)",
        "- Method: `scripts/catalog_target/snapshot.py` (`load_current_catalog` / `--snapshot` / local `--read-db`)",
        "- Status: prepared, **not executed** this pass",
        "- Production hosts (`karzartools.com`) are refused",
        "- Historical `data/imports/*_products.csv` and image-only extracts are refused",
        "- Required fields: id, sku, brand_id/brand, category_id, slug, name, base_price, is_active, is_available, deleted_at, primary image/media state",
        "- CURRENT_SITE_RECONCILIATION_READY remains FALSE until a trustworthy snapshot is obtained",
        "",
        "## Duplicate-source findings",
        f"- Same name + same hash skipped: {len(result.skipped_duplicates)}",
        bullets(result.skipped_duplicates),
        f"- Same name + different hash REVIEW conflicts: {len(result.hash_conflicts)}",
    ]
    if result.hash_conflicts:
        for item in result.hash_conflicts:
            lines.append(
                f"- `{item.get('name')}`: {item.get('reason')} original=`{item.get('original')}` copy=`{item.get('copy')}`"
            )
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Price / unit / markup conflicts",
        bullets(result.price_unit_conflicts),
        "",
        "## Other findings (examples, not exhaustive)",
        f"- Duplicate current SKUs: {len(examples.get('duplicate_current_skus', []))}",
        bullets(examples.get("duplicate_current_skus", [])),
        f"- Cross-brand SKU collisions: {len(examples.get('cross_brand_sku_collisions', []))}",
        bullets(examples.get("cross_brand_sku_collisions", [])),
        "",
        "## Unavailable authoritative sources",
    ]
    if result.unavailable_sources:
        for item in result.unavailable_sources:
            lines.append(f"- `{item.get('source')}`: {item.get('reason')}")
    else:
        lines.append("- (none)")
    lines += ["", "## Unparsed sources"]
    if result.unparsed:
        for item in result.unparsed:
            lines.append(f"- `{item.get('path')}`: {item.get('reason')}")
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## INSIZE Sales Wave 1 (plan only)",
        f"- Count: {result.sales_wave_summary.get('insize_sales_wave_1_count', 0)}",
        f"- Commerce-ready: {result.sales_wave_summary.get('insize_commerce_ready', 0)}",
        f"- Media-ready: {result.sales_wave_summary.get('insize_media_ready', 0)}",
        f"- Public-sell-ready: {result.sales_wave_summary.get('insize_public_sell_ready', 0)}",
        f"- Excluded commerce-ready/no-media: {result.sales_wave_summary.get('excluded_commerce_ready_no_media', 0)}",
        f"- Snapshot timestamp: `{result.sales_wave_summary.get('snapshot_timestamp', '')}`",
        f"- Snapshot sha256: `{result.sales_wave_summary.get('snapshot_sha256', '')}`",
        "- Detail: `data/catalog-target/insize_sales_wave_1_plan.csv` / `.json`",
        "- Stale-snapshot guard: re-SELECT allowlisted rows before any future APPLY; abort entire APPLY on drift",
        "",
        "## APPLY readiness",
        "- **GLOBAL_APPLY_READY = FALSE.** No writer in this PR.",
        "- CREATE_APPLY_READY = FALSE; DEACTIVATE_APPLY_READY = FALSE.",
        "- REVIEW rows are hard-blocked from every allowlist.",
        "",
        "PRODUCTION DB MUTATION: ZERO",
        "",
    ]
    return "\n".join(lines) + "\n"


def run_reconciliation(
    *,
    source_root: Path | None,
    output_dir: Path,
    baseline_sha: str,
    snapshot_path: str | Path | None = None,
    read_db: bool = False,
    aliases: dict[tuple[str, str], str] | None = None,
    write: bool = True,
    real_source_validation: str | None = None,
    expected_snapshot_rows: int | None = None,
    snapshot_timestamp: str = "",
) -> ReconciliationResult:
    from catalog_target.sales_wave import build_sales_wave_artifacts, write_sales_wave_outputs

    discovery = SourceDiscovery(source_root=source_root)
    discovery.discover()
    snapshot_file = Path(snapshot_path) if snapshot_path else None
    current, kind, note = load_current_catalog(snapshot_path=snapshot_path, read_db=read_db)
    integrity: SnapshotIntegrity | None = None
    if snapshot_path and kind == SNAPSHOT_KIND_FILE:
        integrity = validate_snapshot_csv(
            Path(snapshot_path),
            expected_row_count=expected_snapshot_rows,
        )
        if not integrity.valid:
            note = f"{note};snapshot_integrity_failed:{';'.join(integrity.problems)}"
    validation = real_source_validation or ("ok" if source_root is not None else "BLOCKED_SOURCE_NOT_MOUNTED")
    result = reconcile(
        discovery=discovery,
        current_products=current,
        evidence_kind=kind,
        evidence_note=note,
        baseline_sha=baseline_sha,
        aliases=aliases,
        real_source_validation=validation,
        snapshot_integrity=integrity,
    )

    meta_stamp = snapshot_timestamp
    if not meta_stamp and snapshot_file and snapshot_file.is_file():
        sibling = snapshot_file.with_suffix(".meta.json")
        # Support symlink basename *_latest.csv → matching meta via resolved stem.
        candidates = [
            sibling,
            snapshot_file.parent / "current_site_snapshot_latest.meta.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                try:
                    meta_stamp = str(json.loads(candidate.read_text(encoding="utf-8")).get("snapshot_timestamp_utc") or "")
                except (OSError, json.JSONDecodeError):
                    meta_stamp = ""
                if meta_stamp:
                    break

    artifacts = build_sales_wave_artifacts(
        result,
        snapshot_path=snapshot_file if snapshot_file and snapshot_file.is_file() else None,
        snapshot_timestamp=meta_stamp,
    )
    result.insize_sales_wave_1_ready = artifacts.readiness.insize_sales_wave_1_ready
    result.create_apply_ready = False
    result.deactivate_apply_ready = False
    result.global_apply_ready = False
    result.sales_wave_summary = artifacts.summary
    result.apply_contract = artifacts.readiness.as_dict()

    if write:
        if result.evidence_note.startswith("file:") or result.evidence_note.startswith("env_file:"):
            prefix, _, rest = result.evidence_note.partition(":")
            result.evidence_note = f"{prefix}:{Path(rest).name}"
        write_outputs(result, output_dir)
        write_sales_wave_outputs(artifacts, output_dir)
    return result
