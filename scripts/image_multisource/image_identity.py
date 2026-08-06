"""Retail product-image identity selection (fixture-friendly; no brand-only preference)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote, urlparse

from .sku_norm import (
    brand_aliases,
    conflicting_brand_in_text,
    normalize_sku,
    skus_in_text,
    strip_trailing_variant,
)

_IMG_TAG = re.compile(
    r"<img\b([^>]*)>",
    re.I | re.S,
)
_ATTR = re.compile(
    r"""(?P<k>src|data-src|alt|title|class|id)\s*=\s*(?P<q>['"])(?P<v>.*?)(?P=q)""",
    re.I | re.S,
)
_JSON_LD = re.compile(
    r"""<script[^>]+type=["']application/ld\+json["'][^>]*>(.*?)</script>""",
    re.I | re.S,
)


def _filename_of(url: str) -> str:
    return unquote(urlparse(url).path or "").rsplit("/", 1)[-1]


def _sku_in_filename(filename: str, sku: str) -> bool:
    name = (filename or "").casefold()
    target = normalize_sku(sku)
    if not target or not name:
        return False
    if re.search(rf"(?<![0-9a-z]){re.escape(target)}(?![0-9a-z])", name):
        return True
    base = normalize_sku(strip_trailing_variant(sku))
    return bool(base) and re.search(rf"(?<![0-9a-z]){re.escape(base)}(?![0-9a-z])", name) is not None


def _parse_img_attrs(attr_blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _ATTR.finditer(attr_blob or ""):
        out[m.group("k").casefold()] = m.group("v")
    return out


def _json_ld_image_urls_for_sku(html: str, sku: str) -> set[str]:
    target = normalize_sku(sku)
    urls: set[str] = set()
    for block in _JSON_LD.findall(html or ""):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            text = json.dumps(item, ensure_ascii=False)
            if target not in text.casefold():
                continue
            image = item.get("image")
            if isinstance(image, str):
                urls.add(image)
            elif isinstance(image, list):
                urls.update(u for u in image if isinstance(u, str))
            elif isinstance(image, dict) and isinstance(image.get("url"), str):
                urls.add(image["url"])
    return urls


def _in_main_gallery(attrs: dict[str, str], surrounding_class_hint: str = "") -> bool:
    blob = " ".join(
        [
            attrs.get("class") or "",
            attrs.get("id") or "",
            surrounding_class_hint or "",
        ]
    ).casefold()
    positive = ("woocommerce-product-gallery", "product-gallery", "product-images", "gallery-image")
    negative = ("related", "upsell", "cross-sell", "recommended", "footer", "sidebar", "nav", "menu")
    if any(n in blob for n in negative):
        return False
    return any(p in blob for p in positive)


def select_retail_product_images(
    *,
    expected_brand: str,
    expected_sku: str,
    product_detail_url: str,
    product_page_html: str,
    candidate_url_allowlist: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Select product images only when a governed identity tie exists."""
    html = product_page_html or ""
    sku = expected_sku
    brand = expected_brand
    json_ld_urls = _json_ld_image_urls_for_sku(html, sku)
    selected: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []

    for img in _IMG_TAG.finditer(html):
        attrs = _parse_img_attrs(img.group(1))
        src = (attrs.get("src") or attrs.get("data-src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        if candidate_url_allowlist and not any(
            host in src.casefold() for host in candidate_url_allowlist
        ):
            continue
        fname = _filename_of(src)
        meta = " ".join(filter(None, [attrs.get("alt"), attrs.get("title"), fname]))
        # Drop chrome
        if any(x in fname.casefold() for x in ("logo", "icon", "cropped-", "sprite", "placeholder")):
            rejected.append({"url": src, "reason": "chrome_or_logo"})
            continue
        conflict_brand = conflicting_brand_in_text(meta, brand)
        if conflict_brand:
            rejected.append(
                {
                    "url": src,
                    "reason": "conflicting_image_brand",
                    "conflict_brand": conflict_brand,
                }
            )
            continue
        # Conflicting SKU in filename/meta (other catalog code ≠ governed)
        meta_skus = skus_in_text(meta)
        target = normalize_sku(sku)
        base = normalize_sku(strip_trailing_variant(sku))
        foreign = {
            t
            for t in meta_skus
            if t != target and normalize_sku(strip_trailing_variant(t)) != base
        }
        if foreign and target not in meta_skus and base not in {
            normalize_sku(strip_trailing_variant(t)) for t in meta_skus
        }:
            rejected.append(
                {
                    "url": src,
                    "reason": "conflicting_image_sku",
                    "foreign_skus": "|".join(sorted(foreign)),
                }
            )
            continue

        ties: list[str] = []
        if _sku_in_filename(fname, sku):
            ties.append("exact_sku_in_filename")
        if target in normalize_sku(attrs.get("alt") or "") or target in normalize_sku(
            attrs.get("title") or ""
        ):
            ties.append("exact_sku_in_alt_or_title")
        if src in json_ld_urls:
            ties.append("json_ld_sku_image")
        if _in_main_gallery(attrs) and (
            any(a in meta.casefold() for a in brand_aliases(brand)) or _sku_in_filename(fname, sku)
        ):
            ties.append("scoped_main_product_gallery")

        if not ties:
            rejected.append({"url": src, "reason": "no_governed_identity_tie"})
            continue

        selected.append({"url": src, "ties": "|".join(ties), "filename": fname})

    # Deterministic: prefer filename SKU ties, then json-ld, then gallery
    def rank(row: dict[str, str]) -> tuple[int, str]:
        ties = row.get("ties") or ""
        score = 0
        if "exact_sku_in_filename" in ties:
            score += 40
        if "json_ld_sku_image" in ties:
            score += 30
        if "exact_sku_in_alt_or_title" in ties:
            score += 20
        if "scoped_main_product_gallery" in ties:
            score += 10
        return (-score, row.get("url") or "")

    selected.sort(key=rank)
    return {
        "product_detail_url": product_detail_url,
        "expected_brand": brand,
        "expected_sku": sku,
        "selected": selected,
        "rejected": rejected,
        "image_urls": [r["url"] for r in selected],
    }


def classify_filename_identity(
    *,
    expected_brand: str,
    expected_sku: str,
    source_image_url: str,
) -> dict[str, str]:
    """Deterministic post-hoc filename identity signals for quarantine reporting."""
    fname = _filename_of(source_image_url)
    conflict_brand = conflicting_brand_in_text(fname, expected_brand)
    tokens = skus_in_text(fname)
    target = normalize_sku(expected_sku)
    base = normalize_sku(strip_trailing_variant(expected_sku))
    foreign = {
        t
        for t in tokens
        if t != target and normalize_sku(strip_trailing_variant(t)) != base
    }
    sku_in_name = _sku_in_filename(fname, expected_sku)
    if conflict_brand:
        return {
            "signal": "conflicting_image_brand",
            "reason_code": "conflicting_image_brand",
            "detail": conflict_brand,
            "filename": fname,
        }
    if foreign and not sku_in_name:
        return {
            "signal": "sku_filename_conflict",
            "reason_code": "conflicting_image_sku",
            "detail": "|".join(sorted(foreign)),
            "filename": fname,
        }
    if tokens and not sku_in_name:
        return {
            "signal": "sku_filename_conflict",
            "reason_code": "sku_filename_mismatch",
            "detail": "|".join(sorted(tokens)),
            "filename": fname,
        }
    return {
        "signal": "ok" if sku_in_name else "unproven",
        "reason_code": "",
        "detail": "",
        "filename": fname,
    }
