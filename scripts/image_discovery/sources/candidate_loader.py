"""Shared governed candidate CSV loader for SourceAdapters."""

from __future__ import annotations

import csv
from pathlib import Path

from ..contracts import ImageCandidate, derive_source_candidate_key


def load_candidates_from_csv(
    *,
    adapter_name: str,
    brand: str,
    candidates_csv: Path,
    products_csv: Path | None,
    sku_filters: list[str] | None,
    limit: int | None,
    offset: int,
    max_images_per_product: int,
    normalize_sku,
) -> list[ImageCandidate]:
    if max_images_per_product <= 0:
        raise SystemExit("ERROR: --max-images-per-product must be > 0")
    product_skus: set[str] | None = None
    if products_csv is not None:
        product_skus = set()
        with products_csv.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                s = normalize_sku(row.get("sku") or "")
                if s:
                    product_skus.add(s)

    filters = {normalize_sku(s) for s in (sku_filters or [])}
    by_sku: dict[str, list[ImageCandidate]] = {}
    seen_source: dict[str, set[tuple[str, str]]] = {}
    with candidates_csv.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sku = normalize_sku(row.get("sku") or "")
            if not sku:
                continue
            if filters and sku not in filters:
                continue
            if product_skus is not None and sku not in product_skus:
                continue
            detail = (row.get("detail_url") or row.get("source_detail_url") or "").strip()
            image = (row.get("image_url") or row.get("source_image_url") or "").strip()
            if not detail or not image:
                continue
            key = (detail, image)
            if key in seen_source.setdefault(sku, set()):
                continue
            seen_source[sku].add(key)
            product_id = (row.get("product_id") or "").strip()
            cand = ImageCandidate(
                sku=sku,
                product_name=(row.get("product_name") or "").strip(),
                brand=(row.get("brand") or brand).strip() or brand,
                detail_url=detail,
                image_url=image,
                source_adapter=adapter_name,
                source_class=(
                    (row.get("source_class") or "").strip()
                    or "authorized_distributor_candidate"
                ),
                confidence=(row.get("confidence") or "very_high").strip() or "very_high",
                image_role="primary",
                source_rank=1,
                display_order_candidate=1,
                source_image_index=0,
                product_id=product_id,
            )
            cand.source_candidate_key = derive_source_candidate_key(
                detail_url=detail,
                image_url=image,
                source_image_index=0,
            )
            by_sku.setdefault(sku, []).append(cand)

    ordered_skus: list[str] = []
    seen: set[str] = set()
    with candidates_csv.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sku = normalize_sku(row.get("sku") or "")
            if sku in by_sku and sku not in seen:
                ordered_skus.append(sku)
                seen.add(sku)

    if offset:
        ordered_skus = ordered_skus[offset:]
    if limit is not None:
        ordered_skus = ordered_skus[:limit]

    out: list[ImageCandidate] = []
    for sku in ordered_skus:
        cands = by_sku[sku][:max_images_per_product]
        for i, c in enumerate(cands):
            c.source_image_index = i
            c.display_order_candidate = i + 1
            c.source_rank = i + 1
            c.image_role = "primary" if i == 0 else "alternate"
            c.source_candidate_key = derive_source_candidate_key(
                detail_url=c.detail_url,
                image_url=c.image_url,
                source_image_index=0,
            )
            c.ensure_identity()
            out.append(c)
    return out
