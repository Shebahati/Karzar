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
from catalog_target.snapshot import SNAPSHOT_KIND_LIVE, load_current_catalog
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
    "base_price_toman",
    "inventory_status",
    "commerce_ready",
    "media_ready",
    "match_confidence",
    "review_reason",
    "reconciliation_state",
    "current_id",
    "current_slug",
    "provenance",
]


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
    base_price_toman: str = ""
    inventory_status: str = ""
    commerce_ready: bool = False
    media_ready: bool = False
    match_confidence: str = "none"
    review_reason: str = ""
    reconciliation_state: str = "REVIEW"
    current_id: str = ""
    current_slug: str = ""
    provenance: str = ""


@dataclass
class InsizeStats:
    target_sku_count: int = 0
    unique_sku_count: int = 0
    exact_distributor_matches: int = 0
    unmatched_target_skus: list[str] = field(default_factory=list)
    duplicate_matches: list[str] = field(default_factory=list)
    ambiguous_matches: list[str] = field(default_factory=list)
    inventory_without_price: list[str] = field(default_factory=list)
    price_but_unavailable: list[str] = field(default_factory=list)
    available_positive_price: list[str] = field(default_factory=list)
    available_missing_zero_price: list[str] = field(default_factory=list)
    unavailable_positive_price: list[str] = field(default_factory=list)
    commerce_ready: list[str] = field(default_factory=list)
    unresolved_identities: list[dict[str, str]] = field(default_factory=list)
    distributor_row_count: int = 0
    universe_expanded_from_distributor: bool = False


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
    duplicate_scope_skus: list[str]
    tooling_notes: list[dict[str, str]]
    examples: dict[str, list[str]]


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


def _index_by_sku(rows: list[tuple[SourceFile, dict[str, Any]]], sku_headers: list[str]):
    index: dict[str, list[tuple[SourceFile, dict[str, Any]]]] = defaultdict(list)
    for source, row in rows:
        sku = normalize_sku(extract_sku(row, sku_headers))
        if sku:
            index[sku].append((source, row))
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
    reasons = [match.review_reason, extra_review, source_conflict]
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

    price_rows = discovery.load_role_rows("price")
    inventory_rows = discovery.load_role_rows("inventory")
    price_index = _index_by_sku(price_rows, sku_headers)
    inventory_index = _index_by_sku(inventory_rows, sku_headers)
    current_index = index_current_products(current_products)

    target_dupes: dict[tuple[str, str], int] = Counter(
        identity_key(t.brand_key, t.normalized_sku) for t in targets
    )
    current_dupes = {
        key: rows for key, rows in current_index.items() if len(rows) > 1
    }
    target_cross = cross_brand_sku_collisions(targets)
    current_cross = cross_brand_sku_collisions(current_products)

    insize_targets = [t for t in targets if t.brand_key == "INSIZE"]
    insize_stats = InsizeStats(
        target_sku_count=len(insize_targets),
        unique_sku_count=len({t.normalized_sku for t in insize_targets}),
    )
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

    rows: list[ManifestRow] = []
    examples: dict[str, list[str]] = defaultdict(list)

    def add_example(bucket: str, sku: str) -> None:
        bucket_list = examples[bucket]
        if sku not in bucket_list and len(bucket_list) < 8:
            bucket_list.append(sku)

    for target in targets:
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

        price_hits = price_index.get(target.normalized_sku, [])
        inv_hits = inventory_index.get(target.normalized_sku, [])
        price_conv: PriceConversion | None = None
        source_price = ""
        source_inventory = ""
        inventory_available: bool | None = None
        inventory_status = ""

        if len(price_hits) > 1:
            extra_review = extra_review or "duplicate_price_match"
            insize_stats.duplicate_matches.append(target.sku)
            add_example("duplicate_matches", target.sku)
        if len(price_hits) == 1:
            source, prow = price_hits[0]
            source_price = source.path
            price_header = pick_header(prow, price_headers)
            currency_header = pick_header(prow, currency_headers)
            currency_raw = str(prow.get(currency_header) or "")
            markup = source.markup_percent or detect_markup_percent(source.path, currency_raw)
            # Filename +10%/+25% means markup is already in the file — do not apply again.
            currency = canonicalize_currency(currency_raw)
            if currency is None and price_header and "toman" in price_header.lower():
                currency = "toman"
            elif currency is None and price_header and "rial" in price_header.lower():
                currency = "rial"
            elif currency is None and price_header and "دلار" in price_header:
                currency = "usd"
            price_conv = convert_price(
                prow.get(price_header) if price_header else None,
                currency=currency,
                markup_already_present=markup is not None,
                apply_markup_percent=markup,
            )

        if len(inv_hits) > 1:
            extra_review = extra_review or "ambiguous_inventory_match"
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
            # Combined price+inventory workbook: status may live on the price row.
            source, prow = price_hits[0]
            status_header = pick_header(prow, status_headers)
            if status_header:
                source_inventory = source.path
                inventory_status, inventory_available = _available_status(
                    prow.get(status_header), available_values
                )

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
            has_price = bool(price_conv and price_conv.base_price_toman and price_conv.base_price_toman > 0)
            if inventory_available is True and has_price:
                insize_stats.available_positive_price.append(target.sku)
            if inventory_available is True and not has_price:
                insize_stats.inventory_without_price.append(target.sku)
                insize_stats.available_missing_zero_price.append(target.sku)
            if has_price and inventory_available is False:
                insize_stats.price_but_unavailable.append(target.sku)
                insize_stats.unavailable_positive_price.append(target.sku)

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
        current = match.current
        ready = commerce_ready(
            target_member=True,
            base_price_toman=price_conv.base_price_toman if price_conv else None,
            inventory_available=inventory_available,
            review_reason=_join_reasons(*review_bits) if state == "REVIEW" else None,
        )
        # REVIEW never becomes commerce-ready auto-apply.
        if state == "REVIEW":
            ready = False
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
                base_price_toman=""
                if not price_conv or price_conv.base_price_toman is None
                else str(price_conv.base_price_toman),
                inventory_status=inventory_status,
                commerce_ready=ready,
                media_ready=m_ready,
                match_confidence=match.confidence,
                review_reason=_join_reasons(*review_bits),
                reconciliation_state=state,
                current_id="" if not current or not current.id else current.id,
                current_slug="" if not current or not current.slug else current.slug,
                provenance=target.provenance,
            )
        )

    target_keys = {identity_key(t.brand_key, t.normalized_sku) for t in targets}
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

    for key, group in current_dupes.items():
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
            "path": "scripts/insize_sales_activation.py (PR #266, unmerged)",
            "class": "reusable_pieces_unsafe_as_authority",
            "why": "Reusable: conservative normalize_sku, stdlib xlsx, rial/10, exact match, apply gates. Unsafe as Target authority: 10-SKU pilot allowlist must not define membership; APPLY exists.",
        },
        {
            "path": "scripts/azarsanat_import.py",
            "class": "legacy",
            "why": "Placeholder 10_000_000 prices; infers brands/families beyond the approved AST folder set.",
        },
        {
            "path": "scripts/enrich_insize_from_shopmill.py",
            "class": "reusable",
            "why": "Content-only enrichment; must not be used as product-scope membership.",
        },
        {
            "path": "data/imports/insize_products.csv / all_products.csv",
            "class": "legacy",
            "why": "PDF price-list parse (~342 INSIZE rows). Not the approved ~872 product-list universe.",
        },
        {
            "path": "scripts/seed_products_from_csv.py",
            "class": "unsafe_for_new_catalog_authority",
            "why": "Creates products from CSV; this task forbids CREATE/DELETE mutation.",
        },
    ]

    conflicts = [f["reason"] for f in discovery.parse_failures]
    if insize_stats.universe_expanded_from_distributor:
        conflicts.append("insize_universe_expanded_from_distributor")

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
        duplicate_scope_skus=list(getattr(discovery, "duplicate_scope_skus", [])),
        tooling_notes=tooling_notes,
        examples=dict(examples),
    )


def counts(result: ReconciliationResult) -> dict[str, int]:
    counter = Counter(row.reconciliation_state for row in result.rows)
    return {state: int(counter.get(state, 0)) for state in ("KEEP", "UPDATE", "CREATE", "DEACTIVATE", "REVIEW")}


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
    report = {
        "baseline_sha": result.baseline_sha,
        "generated_at": result.generated_at,
        "production_mutation": "ZERO",
        "apply_phase": False,
        "db_evidence": result.evidence_kind,
        "db_evidence_note": result.evidence_note,
        "live_db": result.evidence_kind == SNAPSHOT_KIND_LIVE,
        "total_current_products_observed": len(result.current_products),
        "total_target_skus": len(result.target_skus),
        "target_skus_per_brand": dict(per_brand),
        "counts": state_counts,
        "insize": {
            "target_sku_count": result.insize.target_sku_count,
            "unique_sku_count": result.insize.unique_sku_count,
            "exact_matches_to_distributor": result.insize.exact_distributor_matches,
            "unmatched_target_skus": result.insize.unmatched_target_skus,
            "duplicate_matches": result.insize.duplicate_matches,
            "ambiguous_matches": result.insize.ambiguous_matches,
            "inventory_without_usable_price": result.insize.inventory_without_price,
            "price_but_unavailable": result.insize.price_but_unavailable,
            "available_positive_price": result.insize.available_positive_price,
            "available_missing_zero_price": result.insize.available_missing_zero_price,
            "unavailable_positive_price": result.insize.unavailable_positive_price,
            "commerce_ready": result.insize.commerce_ready,
            "unresolved_identities": result.insize.unresolved_identities,
            "distributor_row_count": result.insize.distributor_row_count,
            "universe_expanded_from_distributor": result.insize.universe_expanded_from_distributor,
        },
        "target_source_completeness": {
            "discovered_files": result.discovered_files,
            "unparsed_files": result.unparsed,
            "unavailable_authoritative_sources": result.unavailable_sources,
            "skipped_duplicate_tree_copies": result.skipped_duplicates,
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
            "note": "Public lists/details hide products without a non-placeholder image when the flag is on (app/utils/public_catalog.py). target_member is independent of media_ready and commerce_ready.",
        },
        "ready_for_apply": False,
        "ready_for_apply_reason": (
            "No APPLY in this node. Authoritative product-scope files were missing or incomplete, "
            "and current-catalog evidence is not live. REVIEW must never auto-promote."
        ),
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
        f"- DB evidence: **{live}** (`{result.evidence_kind}`) — {result.evidence_note}",
        f"- Current products observed: **{len(result.current_products)}**",
        f"- Target SKUs: **{len(result.target_skus)}**",
        "",
        "## A. Target source completeness",
        f"- Discovered files: {len(result.discovered_files)}",
        f"- Unparsed files: {len(result.unparsed)}",
        f"- Unavailable registry sources: {len(result.unavailable_sources)}",
        f"- Duplicate-tree copies skipped: {len(result.skipped_duplicates)}",
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
        "## Reconciliation counts",
        f"- KEEP: {state_counts['KEEP']}",
        f"- UPDATE: {state_counts['UPDATE']}",
        f"- CREATE: {state_counts['CREATE']}",
        f"- DEACTIVATE: {state_counts['DEACTIVATE']}",
        f"- REVIEW: {state_counts['REVIEW']}",
        "",
        "## INSIZE",
        f"- Target SKU count: {result.insize.target_sku_count}",
        f"- Unique SKU count: {result.insize.unique_sku_count}",
        f"- Exact matches to distributor workbook: {result.insize.exact_distributor_matches}",
        f"- Distributor rows seen (price/inventory join only): {result.insize.distributor_row_count}",
        f"- Universe expanded from distributor: {result.insize.universe_expanded_from_distributor}",
        f"- Unmatched target SKUs: {len(result.insize.unmatched_target_skus)}",
        bullets(result.insize.unmatched_target_skus[:8], empty="(none)"),
        f"- Duplicate matches: {len(result.insize.duplicate_matches)}",
        bullets(result.insize.duplicate_matches[:8]),
        f"- Ambiguous matches: {len(result.insize.ambiguous_matches)}",
        bullets(result.insize.ambiguous_matches[:8]),
        f"- Available + positive price: {len(result.insize.available_positive_price)}",
        bullets(result.insize.available_positive_price[:8]),
        f"- Available + missing/zero price: {len(result.insize.available_missing_zero_price)}",
        bullets(result.insize.available_missing_zero_price[:8]),
        f"- Unavailable + positive price: {len(result.insize.unavailable_positive_price)}",
        bullets(result.insize.unavailable_positive_price[:8]),
        f"- Commerce-ready: {len(result.insize.commerce_ready)}",
        bullets(result.insize.commerce_ready[:8]),
        f"- Unresolved identities: {len(result.insize.unresolved_identities)}",
    ]
    if result.insize.unresolved_identities:
        for item in result.insize.unresolved_identities[:8]:
            lines.append(f"- `{item.get('sku')}` near `{item.get('near')}`")
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Other findings (examples, not exhaustive)",
        f"- Duplicate current SKUs: {len(examples.get('duplicate_current_skus', []))}",
        bullets(examples.get("duplicate_current_skus", [])),
        f"- Duplicate target SKUs: {len(examples.get('duplicate_target_skus', []))}",
        bullets(examples.get("duplicate_target_skus", [])),
        f"- Cross-brand SKU collisions: {len(examples.get('cross_brand_sku_collisions', []))}",
        bullets(examples.get("cross_brand_sku_collisions", [])),
        f"- Active non-target products: {len(examples.get('active_non_target_products', []))}",
        bullets(examples.get("active_non_target_products", [])),
        f"- Target missing from current site: {len(examples.get('target_products_missing_from_current_site', []))}",
        bullets(examples.get("target_products_missing_from_current_site", [])),
        f"- Target with no valid price: {len(examples.get('target_products_with_no_valid_price', []))}",
        bullets(examples.get("target_products_with_no_valid_price", [])),
        f"- Target with no valid public image: {len(examples.get('target_products_with_no_valid_public_image', []))}",
        bullets(examples.get("target_products_with_no_valid_public_image", [])),
        f"- Category problems: {len(examples.get('target_products_with_category_problems', []))}",
        bullets(examples.get("target_products_with_category_problems", [])),
        f"- is_available=true with missing/non-positive price: {len(examples.get('is_available_true_with_missing_or_non_positive_price', []))}",
        bullets(examples.get("is_available_true_with_missing_or_non_positive_price", [])),
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
    lines += ["", "## Parse failures / source conflicts"]
    if result.parse_failures or result.source_conflicts:
        for item in result.parse_failures:
            lines.append(f"- `{item.get('path')}`: {item.get('reason')}")
        for item in result.source_conflicts:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")
    lines += [
        "",
        "## Existing tooling (do not delete in this task)",
    ]
    for note in result.tooling_notes:
        lines.append(f"- `{note['path']}` — **{note['class']}**: {note['why']}")
    lines += [
        "",
        "## Storefront readiness",
        "- `target_member`, `commerce_ready`, and `media_ready` are independent.",
        "- `STOREFRONT_HIDE_IMAGELESS_PRODUCTS` defaults True: public catalog hides products without a valid non-placeholder image (`app/utils/public_catalog.py`).",
        "- Images were not fabricated.",
        "",
        "## APPLY readiness",
        "- **Not ready.** This node is reconciliation/audit only.",
        "- Future deactivation of out-of-scope products must be `is_active = false`, never DELETE.",
        "- REVIEW rows must never auto-become UPDATE or CREATE.",
        "- Do not merge or apply PR #266; its 10-SKU pilot is not Target membership.",
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
) -> ReconciliationResult:
    discovery = SourceDiscovery(source_root=source_root)
    discovery.discover()
    current, kind, note = load_current_catalog(snapshot_path=snapshot_path, read_db=read_db)
    result = reconcile(
        discovery=discovery,
        current_products=current,
        evidence_kind=kind,
        evidence_note=note,
        baseline_sha=baseline_sha,
        aliases=aliases,
    )
    write_outputs(result, output_dir)
    return result
