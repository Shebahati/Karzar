"""Canonical asset grouping and deterministic sequential batch selection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .contracts import (
    PILOT_SHARED_COUNT,
    PILOT_SINGLETON_COUNT,
    PILOT_UNIQUE_ASSETS,
    ReviewError,
)


def is_valid_local_row(row: dict[str, Any]) -> bool:
    return (
        row.get("audit_status") == "ok"
        and row.get("local_entry_status") == "regular_image"
        and row.get("decode_status") == "ok"
        and row.get("local_exists") is True
        and bool(row.get("sha256"))
    )


def is_remote_row(row: dict[str, Any]) -> bool:
    return row.get("audit_status") == "remote_unverified"


def _norm_brand(name: str | None) -> str:
    text = (name or "").strip()
    return text.casefold() if text else "__unknown__"


def group_assets(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Group valid local rows by sha256; return (assets, remote_deferred)."""
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    remote: list[dict[str, Any]] = []
    for row in rows:
        if is_remote_row(row):
            remote.append(
                {
                    "image_id": row.get("image_id"),
                    "product_id": row.get("product_id"),
                    "sku": row.get("sku"),
                    "image_url": row.get("image_url"),
                    "reason": "remote_unverified_out_of_scope",
                }
            )
            continue
        if not is_valid_local_row(row):
            continue
        sha = str(row["sha256"]).lower()
        by_sha[sha].append(row)

    assets: list[dict[str, Any]] = []
    for sha in sorted(by_sha.keys()):
        group = sorted(
            by_sha[sha],
            key=lambda r: (
                int(r.get("product_id") or 0),
                int(r.get("image_id") or 0),
            ),
        )
        image_ids = [int(r["image_id"]) for r in group if r.get("image_id") is not None]
        product_ids = sorted({int(r["product_id"]) for r in group if r.get("product_id") is not None})
        brands = sorted(
            {
                (r.get("brand_name") or "").strip()
                for r in group
                if (r.get("brand_name") or "").strip()
            }
        )
        brand_ids = {r.get("brand_id") for r in group if r.get("brand_id") is not None}
        ref = group[0]
        product_count = len(product_ids)
        assets.append(
            {
                "asset_id": sha,
                "sha256": sha,
                "source_relative_path": ref.get("mapped_local_relative_path") or "",
                "byte_size": ref.get("byte_size"),
                "mime_type": ref.get("mime_type"),
                "detected_format": ref.get("detected_format"),
                "width": ref.get("width"),
                "height": ref.get("height"),
                "reference_count": len(group),
                "product_count": product_count,
                "brand_count": len(brand_ids) if brand_ids else (1 if brands else 0),
                "image_ids": image_ids,
                "product_ids": product_ids,
                "brands": brands,
                "is_exact_duplicate_group": len(group) > 1,
                "is_cross_product_shared": product_count > 1,
                "is_cross_brand_shared": len(brand_ids) > 1,
                "assignments": group,
            }
        )
    return assets, remote


def _shared_ordered(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shared = [a for a in assets if int(a["product_count"]) > 1]
    return sorted(
        shared,
        key=lambda a: (
            -int(a["product_count"]),
            -int(a["reference_count"]),
            str(a["sha256"]),
        ),
    )


def _singleton_brand_round_robin_full(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Full deterministic brand round-robin over all singleton assets (no early restart)."""
    singletons = [a for a in assets if int(a["product_count"]) == 1]
    by_brand: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in singletons:
        brand = _norm_brand(a["brands"][0] if a["brands"] else None)
        by_brand[brand].append(a)
    for brand in by_brand:
        by_brand[brand].sort(key=lambda a: str(a["sha256"]))
    brand_names = sorted(by_brand.keys())
    selected: list[dict[str, Any]] = []
    indices = {b: 0 for b in brand_names}
    while brand_names:
        progressed = False
        remaining_brands: list[str] = []
        for brand in brand_names:
            idx = indices[brand]
            bucket = by_brand[brand]
            if idx < len(bucket):
                selected.append(bucket[idx])
                indices[brand] = idx + 1
                progressed = True
                if indices[brand] < len(bucket):
                    remaining_brands.append(brand)
        brand_names = remaining_brands if progressed else []
        if not progressed:
            break
    return selected


def select_review_batch_assets(
    assets: list[dict[str, Any]],
    *,
    excluded_asset_ids: Iterable[str] = (),
    shared_count: int = PILOT_SHARED_COUNT,
    singleton_count: int = PILOT_SINGLETON_COUNT,
    total: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Deterministic sequential batch selection after prior-batch exclusions.

    Canonical shared/singleton pools are built on the full inventory, then prior
    Asset IDs are removed, then the next window of quotas is taken (fallback fills
    shortfalls in SHA-256 ascending order among remaining eligible assets).
    """
    want_total = shared_count + singleton_count if total is None else total
    if want_total != shared_count + singleton_count:
        raise ReviewError("selection", "batch total must equal shared+singleton quotas")

    excluded = {str(x).lower() for x in excluded_asset_ids}
    source_unique = len(assets)
    eligible_assets = [a for a in assets if str(a["sha256"]).lower() not in excluded]
    eligible_before = len(eligible_assets)

    shared_pool = [
        a for a in _shared_ordered(assets) if str(a["sha256"]).lower() not in excluded
    ]
    singleton_pool = [
        a
        for a in _singleton_brand_round_robin_full(assets)
        if str(a["sha256"]).lower() not in excluded
    ]

    shared_selected = list(shared_pool[:shared_count])
    singleton_selected = list(singleton_pool[:singleton_count])

    fallback_used = False
    fallback_from: list[str] = []

    if len(shared_selected) < shared_count:
        fallback_used = True
        need = shared_count - len(shared_selected)
        taken = {a["sha256"] for a in shared_selected} | {a["sha256"] for a in singleton_selected}
        fillers = sorted(
            [a for a in eligible_assets if a["sha256"] not in taken],
            key=lambda a: str(a["sha256"]),
        )
        shared_selected.extend(fillers[:need])
        fallback_from.append("shared")

    if len(singleton_selected) < singleton_count:
        fallback_used = True
        need = singleton_count - len(singleton_selected)
        taken = {a["sha256"] for a in shared_selected} | {a["sha256"] for a in singleton_selected}
        fillers = sorted(
            [a for a in eligible_assets if a["sha256"] not in taken],
            key=lambda a: str(a["sha256"]),
        )
        singleton_selected.extend(fillers[:need])
        fallback_from.append("singleton")

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, asset in enumerate(shared_selected, start=1):
        sha = asset["sha256"]
        if sha in seen:
            raise ReviewError("selection", f"duplicate asset selection: {sha}")
        if sha in excluded:
            raise ReviewError("selection", f"selected excluded prior asset: {sha}")
        seen.add(sha)
        row = dict(asset)
        row["selection_segment"] = "shared"
        row["selection_rank"] = rank
        selected.append(row)
    for rank, asset in enumerate(singleton_selected, start=1):
        sha = asset["sha256"]
        if sha in seen:
            raise ReviewError("selection", f"duplicate asset selection: {sha}")
        if sha in excluded:
            raise ReviewError("selection", f"selected excluded prior asset: {sha}")
        seen.add(sha)
        row = dict(asset)
        row["selection_segment"] = "singleton"
        row["selection_rank"] = rank
        selected.append(row)

    if len(selected) != want_total:
        raise ReviewError(
            "selection",
            f"batch must contain exactly {want_total} unique assets, got {len(selected)}",
        )
    if len({a["sha256"] for a in selected}) != want_total:
        raise ReviewError("selection", "duplicate asset IDs in batch selection")

    remaining_after = eligible_before - len(selected)
    meta = {
        "shared_requested": shared_count,
        "singleton_requested": singleton_count,
        "shared_selected": sum(1 for a in selected if a["selection_segment"] == "shared"),
        "singleton_selected": sum(1 for a in selected if a["selection_segment"] == "singleton"),
        "fallback_used": fallback_used,
        "fallback_from": fallback_from,
        "selected_asset_ids": [a["sha256"] for a in selected],
        "source_unique_assets": source_unique,
        "excluded_prior_asset_count": len(excluded),
        "eligible_assets_before_selection": eligible_before,
        "remaining_unique_assets_after_selection": remaining_after,
        "prior_overlap_count": 0,
    }
    return selected, meta


def select_pilot_assets(
    assets: list[dict[str, Any]],
    *,
    shared_count: int = PILOT_SHARED_COUNT,
    singleton_count: int = PILOT_SINGLETON_COUNT,
    total: int = PILOT_UNIQUE_ASSETS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Backward-compatible Pilot 001 selection (no prior-batch exclusions)."""
    return select_review_batch_assets(
        assets,
        excluded_asset_ids=(),
        shared_count=shared_count,
        singleton_count=singleton_count,
        total=total,
    )


def assignments_for_assets(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten all ProductImage assignments for selected assets (stable order)."""
    out: list[dict[str, Any]] = []
    for asset in selected:
        for row in asset["assignments"]:
            image_id = int(row["image_id"])
            product_id = int(row["product_id"])
            out.append(
                {
                    "assignment_id": f"{asset['sha256']}:{image_id}:{product_id}",
                    "asset_id": asset["sha256"],
                    "image_id": image_id,
                    "product_id": product_id,
                    "sku": row.get("sku") or "",
                    "product_slug": row.get("product_slug") or "",
                    "product_name": row.get("product_name") or "",
                    "brand_id": row.get("brand_id"),
                    "brand_name": row.get("brand_name") or "",
                    "category_id": row.get("category_id"),
                    "category_name": row.get("category_name") or "",
                    "is_primary": row.get("is_primary"),
                    "display_order": row.get("display_order"),
                    "image_url": row.get("image_url") or "",
                }
            )
    out.sort(key=lambda r: (r["asset_id"], r["product_id"], r["image_id"]))
    return out
