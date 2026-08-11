"""Load IMG-02A-01 inventory + IMG-02A-02 human-review watermark labels."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .contracts import (
    DEFAULT_HR_ASSET_REVIEWS,
    DEFAULT_INVENTORY_CSV,
    DEFAULT_PREVIEW_ROOTS,
    HR_WATERMARK_POSITIVE,
)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _strip_bom(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        return []
    return [f.lstrip("\ufeff") for f in fieldnames]


@dataclass(frozen=True)
class ImageRecord:
    image_id: str
    product_id: str
    sku: str
    product_slug: str
    product_name: str
    product_is_active: bool
    product_deleted: bool
    product_is_available: bool
    brand_name: str
    category_name: str
    image_url: str
    is_primary: bool
    display_order: str
    mapped_local_relative_path: str
    sha256: str
    width: str
    height: str
    byte_size: str
    mime_type: str
    detected_format: str


def load_inventory(path: Path | str = DEFAULT_INVENTORY_CSV) -> list[ImageRecord]:
    rows: list[ImageRecord] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = _strip_bom(list(reader.fieldnames or []))
        for raw in reader:
            row = {k.lstrip("\ufeff"): v for k, v in raw.items()}
            rows.append(
                ImageRecord(
                    image_id=str(row.get("image_id") or ""),
                    product_id=str(row.get("product_id") or ""),
                    sku=str(row.get("sku") or ""),
                    product_slug=str(row.get("product_slug") or ""),
                    product_name=str(row.get("product_name") or ""),
                    product_is_active=_truthy(row.get("product_is_active")),
                    product_deleted=_truthy(row.get("product_deleted")),
                    product_is_available=_truthy(row.get("product_is_available")),
                    brand_name=str(row.get("brand_name") or ""),
                    category_name=str(row.get("category_name") or ""),
                    image_url=str(row.get("image_url") or ""),
                    is_primary=_truthy(row.get("is_primary")),
                    display_order=str(row.get("display_order") or ""),
                    mapped_local_relative_path=str(
                        row.get("mapped_local_relative_path") or ""
                    ),
                    sha256=str(row.get("sha256") or ""),
                    width=str(row.get("width") or ""),
                    height=str(row.get("height") or ""),
                    byte_size=str(row.get("byte_size") or ""),
                    mime_type=str(row.get("mime_type") or ""),
                    detected_format=str(row.get("detected_format") or ""),
                )
            )
    return rows


def active_public_images(rows: list[ImageRecord]) -> list[ImageRecord]:
    return [r for r in rows if r.product_is_active and not r.product_deleted]


def load_hr_watermark_assets(
    paths: tuple[str, ...] | list[str] = DEFAULT_HR_ASSET_REVIEWS,
) -> dict[str, dict[str, str]]:
    """asset_id (sha256) -> latest human-review row for distributor_or_retailer."""
    out: dict[str, dict[str, str]] = {}
    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        with p.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                row = {k.lstrip("\ufeff"): v for k, v in raw.items()}
                if row.get("watermark_status") != HR_WATERMARK_POSITIVE:
                    continue
                aid = str(row.get("asset_id") or "").strip()
                if aid:
                    out[aid] = row
    return out


def resolve_preview_path(
    sha256: str, preview_roots: tuple[str, ...] | list[str] = DEFAULT_PREVIEW_ROOTS
) -> Path | None:
    for root in preview_roots:
        base = Path(root)
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            cand = base / f"{sha256}{ext}"
            if cand.is_file():
                return cand
    return None


def index_by_sha(rows: list[ImageRecord]) -> dict[str, list[ImageRecord]]:
    out: dict[str, list[ImageRecord]] = defaultdict(list)
    for row in rows:
        if row.sha256:
            out[row.sha256].append(row)
    return out
