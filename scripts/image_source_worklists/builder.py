"""Build deterministic IMG-02B product-level source worklists."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .contracts import (
    SCHEMA_VERSION,
    SOURCE_PATH_CONTRACTS,
    TASK_ID,
    WORK_TYPE_PRECEDENCE,
    WorklistError,
    brand_display,
    normalize_brand,
    split_pipe_list,
    stable_work_item_id,
)


def _as_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _missing_priority(product: dict[str, str]) -> str:
    active = _as_bool(product.get("is_active"))
    available = _as_bool(product.get("is_available"))
    if active and available:
        return "P0"
    if active and not available:
        return "P1"
    return "P2"


def _base_item(product: dict[str, str], brand_key: str) -> dict[str, Any]:
    contract = SOURCE_PATH_CONTRACTS[brand_key]
    return {
        "schema_version": str(SCHEMA_VERSION),
        "task_id": TASK_ID,
        "product_key": f"product_id:{product['product_id']}",
        "product_id": str(product["product_id"]),
        "sku": (product.get("sku") or "").strip(),
        "product_name": product.get("name") or "",
        "brand_key": brand_key,
        "brand_name": brand_display(brand_key),
        "category_name": product.get("category") or "",
        "active": "true" if _as_bool(product.get("is_active")) else "false",
        "available": "true" if _as_bool(product.get("is_available")) else "false",
        "current_image_id": "",
        "current_asset_id": "",
        "source_assignment_id": "",
        "review_batch_id": "",
        "review_decision": "",
        "suitability_status": "",
        "has_third_party_watermark": "false",
        "rights_status": "review_required",
        "source_adapter_candidate": contract["source_adapter_candidate"],
        "source_class": contract["source_class"],
        "eligible_for_automatic_discovery": "true",
        "status": "queued",
        "notes": "",
        "work_reasons": [],
    }


def _candidate(
    *,
    product: dict[str, str],
    brand_key: str,
    work_type: str,
    priority: str,
    reason: str,
    **fields: Any,
) -> dict[str, Any]:
    item = _base_item(product, brand_key)
    item["work_type"] = work_type
    item["priority"] = priority
    item["work_reasons"] = [reason]
    for key, value in fields.items():
        if value is None:
            continue
        item[key] = value
    return item


def _merge_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        by_product[item["product_id"]].append(item)

    merged: list[dict[str, Any]] = []
    stats = {
        "input_candidates": len(candidates),
        "unique_products": len(by_product),
        "merged_multi_reason": 0,
        "conflicts_rejected": 0,
    }
    for product_id, group in by_product.items():
        skus = {g["sku"] for g in group}
        brands = {g["brand_key"] for g in group}
        if len(skus) != 1 or len(brands) != 1:
            raise WorklistError(
                "dedupe",
                f"conflicting identity for product_id:{product_id} skus={skus} brands={brands}",
            )
        primary = min(group, key=lambda g: WORK_TYPE_PRECEDENCE[g["work_type"]])
        reasons = sorted({r for g in group for r in g["work_reasons"]})
        if len(group) > 1:
            stats["merged_multi_reason"] += 1
        out = dict(primary)
        out["work_reasons"] = reasons
        if any(g.get("has_third_party_watermark") == "true" for g in group):
            out["has_third_party_watermark"] = "true"
        # Prefer richer identity fields from higher-signal work types when present
        for g in sorted(group, key=lambda x: WORK_TYPE_PRECEDENCE[x["work_type"]]):
            for field in (
                "current_image_id",
                "current_asset_id",
                "source_assignment_id",
                "review_batch_id",
                "review_decision",
                "suitability_status",
                "notes",
            ):
                if g.get(field) and not out.get(field):
                    out[field] = g[field]
        if out["work_type"] == "manual_review_hold":
            out["eligible_for_automatic_discovery"] = "false"
            out["status"] = "manual_hold"
        out["work_reasons"] = "|".join(reasons)
        out["work_item_id"] = stable_work_item_id(
            [
                TASK_ID,
                out["product_id"],
                out["work_type"],
                out["sku"],
                out["brand_key"],
                out["work_reasons"],
            ]
        )
        merged.append(out)

    def sort_key(item: dict[str, Any]) -> tuple:
        from .contracts import PRIORITY_ORDER

        return (
            PRIORITY_ORDER.get(item["priority"], 99),
            item["brand_key"],
            WORK_TYPE_PRECEDENCE[item["work_type"]],
            item["sku"].casefold(),
            int(item["product_id"]),
        )

    merged.sort(key=sort_key)
    return merged, stats


def build_worklists(
    inventory: dict[str, Any],
    review_data: dict[str, Any],
) -> dict[str, Any]:
    products_by_id: dict[str, dict[str, str]] = inventory["products_by_id"]
    brand_sku_index: dict[tuple[str, str], str] = inventory["brand_sku_index"]
    candidates: list[dict[str, Any]] = []
    unmatched: list[dict[str, str]] = []
    ambiguous: list[dict[str, str]] = []

    counts = {
        "missing_image_by_brand": Counter(),
        "replace_required_by_brand": Counter(),
        "watermark_cleaner_by_brand": Counter(),
        "manual_review_hold_by_brand": Counter(),
        "replace_required_skipped_other_brand": 0,
        "watermark_skipped_other_brand": 0,
        "manual_skipped_other_brand": 0,
    }

    # missing_image
    for product in inventory["products"]:
        brand_key = normalize_brand(product.get("brand"))
        if brand_key is None:
            continue
        if _as_bool(product.get("has_any_image_row")):
            continue
        if (product.get("total_image_rows") or "0") not in {"0", ""}:
            # fail closed on contradictory presence evidence
            if not _as_bool(product.get("has_any_image_row")):
                pass
        item = _candidate(
            product=product,
            brand_key=brand_key,
            work_type="missing_image",
            priority=_missing_priority(product),
            reason="missing_image",
        )
        candidates.append(item)
        counts["missing_image_by_brand"][brand_key] += 1

    # replace_required
    for bundle in review_data["bundles"]:
        batch_id = bundle["spec"]["batch_id"]
        for row in bundle["replace_rows"]:
            brand_key = normalize_brand(row.get("brand_name"))
            if brand_key is None:
                counts["replace_required_skipped_other_brand"] += 1
                continue
            product_id = str(row["product_id"])
            product = products_by_id.get(product_id)
            if product is None:
                unmatched.append(
                    {"kind": "replace_required", "product_id": product_id, "batch_id": batch_id}
                )
                continue
            if (product.get("sku") or "").strip() != (row.get("sku") or "").strip():
                raise WorklistError(
                    "replace",
                    f"SKU drift product_id={product_id} inventory={product.get('sku')!r} "
                    f"review={row.get('sku')!r}",
                )
            inv_brand = normalize_brand(product.get("brand"))
            if inv_brand != brand_key:
                raise WorklistError(
                    "replace",
                    f"brand drift product_id={product_id}: inventory={inv_brand} review={brand_key}",
                )
            item = _candidate(
                product=product,
                brand_key=brand_key,
                work_type="replace_required",
                priority="P0",
                reason=f"replace_required:{batch_id}",
                current_image_id=str(row.get("image_id") or ""),
                current_asset_id=str(row.get("asset_id") or ""),
                source_assignment_id=str(row.get("assignment_id") or ""),
                review_batch_id=batch_id,
                review_decision=str(row.get("assignment_decision") or "REPLACE_REQUIRED"),
                suitability_status=str(row.get("suitability_status") or ""),
                notes=str(row.get("assignment_notes") or ""),
            )
            candidates.append(item)
            counts["replace_required_by_brand"][brand_key] += 1

    # watermark_cleaner
    for bundle in review_data["bundles"]:
        batch_id = bundle["spec"]["batch_id"]
        for row in bundle["watermark_rows"]:
            if "brand_name" in row:
                brand_raw = row.get("brand_name")
                skus = [(row.get("sku") or "").strip()] if row.get("sku") else []
            else:
                brand_raw = row.get("brands")
                skus = split_pipe_list(row.get("skus"))
            brand_key = normalize_brand(brand_raw)
            if brand_key is None:
                counts["watermark_skipped_other_brand"] += 1
                continue
            if str(row.get("rights_status") or "review_required") != "review_required":
                raise WorklistError("watermark", "rights_status must remain review_required")
            for sku in skus:
                if not sku:
                    continue
                pid = brand_sku_index.get((brand_key, sku))
                if pid is None:
                    unmatched.append(
                        {
                            "kind": "watermark_cleaner",
                            "brand_key": brand_key,
                            "sku": sku,
                            "asset_id": row.get("asset_id", ""),
                            "batch_id": batch_id,
                        }
                    )
                    continue
                product = products_by_id[pid]
                item = _candidate(
                    product=product,
                    brand_key=brand_key,
                    work_type="watermark_cleaner",
                    priority="P1",
                    reason=f"watermark_cleaner:{batch_id}",
                    current_asset_id=str(row.get("asset_id") or ""),
                    review_batch_id=batch_id,
                    review_decision=str(row.get("asset_decision") or ""),
                    has_third_party_watermark="true",
                    notes=str(row.get("asset_notes") or ""),
                )
                candidates.append(item)
                counts["watermark_cleaner_by_brand"][brand_key] += 1

    # manual_review_hold (target brands only)
    for bundle in review_data["bundles"]:
        batch_id = bundle["spec"]["batch_id"]
        for row in bundle["manual_rows"]:
            product_id = str(row["product_id"])
            product = products_by_id.get(product_id)
            if product is None:
                unmatched.append(
                    {"kind": "manual_review_hold", "product_id": product_id, "batch_id": batch_id}
                )
                continue
            brand_key = normalize_brand(product.get("brand"))
            if brand_key is None:
                counts["manual_skipped_other_brand"] += 1
                continue
            if row.get("sku") and (product.get("sku") or "").strip() != (row.get("sku") or "").strip():
                raise WorklistError(
                    "manual",
                    f"SKU drift on manual hold product_id={product_id}",
                )
            item = _candidate(
                product=product,
                brand_key=brand_key,
                work_type="manual_review_hold",
                priority="P0",
                reason=f"manual_review_hold:{batch_id}",
                current_image_id=str(row.get("image_id") or ""),
                current_asset_id=str(row.get("asset_id") or ""),
                source_assignment_id=str(row.get("assignment_id") or ""),
                review_batch_id=batch_id,
                review_decision="MANUAL_REVIEW",
                suitability_status=str(row.get("suitability_status") or ""),
                notes=str(row.get("assignment_notes") or ""),
                eligible_for_automatic_discovery="false",
                status="manual_hold",
            )
            candidates.append(item)
            counts["manual_review_hold_by_brand"][brand_key] += 1

    work_items, dedupe_stats = _merge_candidates(candidates)
    manual_hold_items = [w for w in work_items if w["work_type"] == "manual_review_hold"]

    by_brand = Counter(w["brand_key"] for w in work_items)
    by_type = Counter(w["work_type"] for w in work_items)
    by_priority = Counter(w["priority"] for w in work_items)

    return {
        "work_items": work_items,
        "manual_hold_items": manual_hold_items,
        "unmatched": unmatched,
        "ambiguous": ambiguous,
        "counts": {
            "missing_image_by_brand": dict(counts["missing_image_by_brand"]),
            "replace_required_by_brand": dict(counts["replace_required_by_brand"]),
            "watermark_cleaner_by_brand": dict(counts["watermark_cleaner_by_brand"]),
            "manual_review_hold_by_brand": dict(counts["manual_review_hold_by_brand"]),
            "replace_required_skipped_other_brand": counts[
                "replace_required_skipped_other_brand"
            ],
            "watermark_skipped_other_brand": counts["watermark_skipped_other_brand"],
            "manual_skipped_other_brand": counts["manual_skipped_other_brand"],
            "by_brand": dict(by_brand),
            "by_work_type": dict(by_type),
            "by_priority": dict(by_priority),
            "dedupe": dedupe_stats,
            "unmatched_rows": len(unmatched),
            "ambiguous_rows": len(ambiguous),
        },
    }
