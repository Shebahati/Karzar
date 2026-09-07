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

from catalog_target.core import (
    INSIZE_UNIQUE_SANITY_HIGH,
    INSIZE_UNIQUE_SANITY_LOW,
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
    suffix_near_miss,
)
from catalog_target.snapshot import SNAPSHOT_KIND_FILE, SNAPSHOT_KIND_LIVE, SNAPSHOT_KIND_UNAVAILABLE, load_current_catalog
from catalog_target.sources import SourceDiscovery, extract_sku, pick_header

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
    "parser_confidence",
    "match_confidence",
    "review_reason",
    "reconciliation_state",
    "current_id",
    "current_slug",
    "provenance",
]

SITE_EVIDENCE_READY_KINDS = {SNAPSHOT_KIND_LIVE, SNAPSHOT_KIND_FILE, "test"}


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
    parser_confidence: str = ""
    match_confidence: str = "none"
    review_reason: str = ""
    reconciliation_state: str = "REVIEW"
    current_id: str = ""
    current_slug: str = ""
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


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


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
) -> str:
    if duplicate_target:
        return "REVIEW"
    if match.review_reason in {
        "duplicate_current_sku",
        "ambiguous_alias",
        "cross_brand_collision",
        "malformed_sku",
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

        price_hits = price_index.get((target.brand_key, target.normalized_sku), [])
        inv_hits = inventory_index.get((target.brand_key, target.normalized_sku), [])
        price_conv: PriceConversion | None = None
        source_price = ""
        source_inventory = ""
        inventory_available: bool | None = None
        inventory_status = ""
        markup_note = ""

        if len(price_hits) > 1:
            extra_review = extra_review or "duplicate_price_match"
            if target.brand_key == "INSIZE":
                insize_stats.duplicate_matches.append(target.sku)
            add_example("duplicate_matches", target.sku)
        if len(price_hits) == 1:
            source, prow = price_hits[0]
            source_price = source.path
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
        )
        if not site_ready and state in {"KEEP", "UPDATE", "CREATE", "DEACTIVATE"}:
            extra_review = extra_review or "site_evidence_unavailable"
            review_bits.append("site_evidence_unavailable")
            state = "REVIEW"
        current = match.current
        ready = commerce_ready(
            target_member=True,
            base_price_toman=price_conv.base_price_toman if price_conv else None,
            inventory_available=inventory_available,
            review_reason=_join_reasons(*review_bits) if state == "REVIEW" else None,
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
                base_price_toman=""
                if not price_conv or price_conv.base_price_toman is None
                else str(price_conv.base_price_toman),
                inventory_status=inventory_status,
                commerce_ready=ready,
                media_ready=m_ready,
                parser_confidence=target.parser_confidence,
                match_confidence=match.confidence,
                review_reason=_join_reasons(*review_bits),
                reconciliation_state=state,
                current_id="" if not current or not current.id else current.id,
                current_slug="" if not current or not current.slug else current.slug,
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
                continue
            if product.is_active is True:
                add_example("active_non_target_products", product.sku)
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
                    match_confidence="none",
                    review_reason="active_non_target" if product.is_active else "non_target",
                    reconciliation_state="DEACTIVATE",
                    current_id=product.id or "",
                    current_slug=product.slug or "",
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
    unparsed_blockers = bool(discovery.parse_failures) and not parsed_members
    target_manifest_ready = (
        real_source_validation == "ok"
        and discovery.source_root is not None
        and product_scope_ok
        and parsed_members
        and not unparsed_blockers
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
        current_site_reconciliation_ready=site_ready and evidence_kind != "test",
        apply_ready=False,
        real_source_validation=real_source_validation,
        price_unit_conflicts=price_unit_conflicts,
    )


def source_has_role_safe(source: SourceFile) -> bool:
    roles = source.roles or ([source.role] if source.role else [])
    return "product_scope" in roles and source.parse_status in {"ok", ""}


def counts(result: ReconciliationResult) -> dict[str, int]:
    counter = Counter(row.reconciliation_state for row in result.rows)
    return {state: int(counter.get(state, 0)) for state in ("KEEP", "UPDATE", "CREATE", "DEACTIVATE", "REVIEW")}


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
            writer.writerow(payload)

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
        "TARGET_MANIFEST_READY": result.target_manifest_ready,
        "CURRENT_SITE_RECONCILIATION_READY": result.current_site_reconciliation_ready,
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
        "ready_for_apply": False,
        "ready_for_apply_reason": "APPLY_READY = FALSE. This pass is READ-ONLY Target Catalog construction.",
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
        f"- TARGET_MANIFEST_READY: `{str(result.target_manifest_ready).upper()}`",
        f"- CURRENT_SITE_RECONCILIATION_READY: `{str(result.current_site_reconciliation_ready).upper()}`",
        "- APPLY_READY: `FALSE`",
        f"- DB evidence: **{live}** (`{result.evidence_kind}`) — {result.evidence_note}",
        f"- Current products observed: **{len(result.current_products)}**",
        f"- Target SKUs: **{len(result.target_skus)}**",
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
        "## APPLY readiness",
        "- **APPLY_READY = FALSE.** This node is reconciliation/audit only.",
        "- REVIEW rows must never auto-become UPDATE or CREATE.",
        "- Future deactivation of out-of-scope products must be `is_active = false`, never DELETE.",
        "",
        "PRODUCTION MUTATION: ZERO",
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
) -> ReconciliationResult:
    discovery = SourceDiscovery(source_root=source_root)
    discovery.discover()
    current, kind, note = load_current_catalog(snapshot_path=snapshot_path, read_db=read_db)
    validation = real_source_validation or ("ok" if source_root is not None else "BLOCKED_SOURCE_NOT_MOUNTED")
    result = reconcile(
        discovery=discovery,
        current_products=current,
        evidence_kind=kind,
        evidence_note=note,
        baseline_sha=baseline_sha,
        aliases=aliases,
        real_source_validation=validation,
    )
    if write:
        write_outputs(result, output_dir)
    return result
