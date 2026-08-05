"""Iranian retailer adapters: abzarham (sitemap) and abzarmarket (brand catalog)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urljoin

from .sku_norm import (
    exact_or_family_slug_match,
    normalize_sku,
    sku_token_in_path,
    skus_in_text,
    strip_trailing_variant,
)

_LOC_RE = re.compile(r"<loc>([^<]+)</loc>", re.I)
_HREF_PRODUCT_ABZ = re.compile(
    r"""href=["'](https?://abzarmarket\.com/product/[^"']+)["']""",
    re.I,
)
_HREF_PRODUCT_REL = re.compile(r"""href=["'](/product/[^"']+)["']""", re.I)
_IMG_ABZARMARKET = re.compile(
    r"""(https?://abzarmarket\.com/image-generator/products/\d+\.(?:jpg|jpeg|png|webp))""",
    re.I,
)
_IMG_ABZARHAM = re.compile(
    r"""(https?://abzarham\.com/wp-content/uploads/[^"' \s>]+\.(?:jpg|jpeg|png|webp))""",
    re.I,
)
_SKU_IN_SLUG = re.compile(r"(?i)(\d{3,5}-\d{2,5}[a-z0-9]*|SO-\d+)")


def parse_sitemap_locs(xml_text: str) -> list[str]:
    return _LOC_RE.findall(xml_text or "")


def index_product_urls_by_sku(urls: list[str]) -> dict[str, str]:
    """Build SKU→URL index from product permalinks (last path segment preferred)."""
    out: dict[str, str] = {}
    for url in urls:
        path = unquote(url.split("?")[0]).rstrip("/")
        segment = path.split("/")[-1]
        tokens = list(_SKU_IN_SLUG.findall(segment)) or list(_SKU_IN_SLUG.findall(path))
        if not tokens:
            continue
        # Prefer the last sku-like token in the slug (usually the model code).
        token = tokens[-1].upper()
        out.setdefault(token, url)
    return out


def lookup_catalog_url(index: dict[str, str], sku: str) -> tuple[str, str]:
    """Return (url, match_kind) where match_kind is exact|family|''."""
    target = (sku or "").strip().upper()
    if not target:
        return "", ""
    if target in index:
        return index[target], "exact"
    base = strip_trailing_variant(target).upper()
    # catalog may store variant letter
    for cat_sku, url in index.items():
        kind = exact_or_family_slug_match(cat_sku, target)
        if kind == "exact":
            return url, "exact"
        if kind == "family" and strip_trailing_variant(cat_sku).upper() == base:
            return url, "family"
    return "", ""


def parse_abzarmarket_brand_catalog(html: str, *, base: str = "https://abzarmarket.com") -> dict[str, str]:
    links = list(_HREF_PRODUCT_ABZ.findall(html or ""))
    links.extend(urljoin(base, path) for path in _HREF_PRODUCT_REL.findall(html or ""))
    return index_product_urls_by_sku(links)


def extract_abzarmarket_product_images(html: str) -> list[str]:
    return list(dict.fromkeys(_IMG_ABZARMARKET.findall(html or "")))


def extract_abzarham_product_images(html: str, *, sku: str) -> list[str]:
    imgs = list(dict.fromkeys(_IMG_ABZARHAM.findall(html or "")))
    sku_cf = normalize_sku(sku)
    base = normalize_sku(strip_trailing_variant(sku))
    preferred = [
        u
        for u in imgs
        if sku_cf in u.casefold()
        or (base and base in u.casefold())
        or "insize" in u.casefold()
        or "dasqua" in u.casefold()
    ]
    # Drop logos / icons
    preferred = [
        u
        for u in preferred
        if "logo" not in u.casefold() and "cropped-" not in u.casefold() and "icon" not in u.casefold()
    ]
    return preferred or [
        u
        for u in imgs
        if "logo" not in u.casefold() and "cropped-" not in u.casefold()
    ]


def evaluate_pdp(
    *,
    sku: str,
    brand_key: str,
    final_url: str,
    html: str,
    expected_match_kind: str,
    image_urls: list[str],
) -> dict[str, Any]:
    """Strict PDP identity evaluation shared by retailer adapters."""
    path_kind = sku_token_in_path(final_url, sku)
    brand_ok = brand_key.replace("_", " ").casefold() in (html or "").casefold() or (
        brand_key.casefold() in (html or "").casefold()
    )
    # Persian/English brand aliases
    aliases = {
        "insize": ("insize", "اینسایز"),
        "dasqua": ("dasqua", "داسکا", "داسکوا"),
        "san_ou": ("san ou", "sanou", "san-ou", "سان او"),
    }
    for alias in aliases.get(brand_key.casefold(), ()):
        if alias in (html or "").casefold():
            brand_ok = True
            break

    body_skus = skus_in_text(html)
    sku_cf = normalize_sku(sku)
    sku_in_body = sku_cf in body_skus or sku_cf in (html or "").casefold()

    if path_kind == "conflict":
        return {
            "status": "false_match",
            "exact_sku_ok": False,
            "false_match": True,
            "page_identity_ok": False,
            "parser_drift": False,
            "redirect_ok": True,
            "asset_host_ok": False,
            "final_url": final_url,
            "notes": "url_path_contains_conflicting_sku",
        }

    if expected_match_kind == "family" or path_kind == "family":
        return {
            "status": "family_only",
            "exact_sku_ok": False,
            "false_match": False,
            "page_identity_ok": brand_ok and sku_in_body,
            "parser_drift": False,
            "redirect_ok": True,
            "asset_host_ok": bool(image_urls),
            "final_url": final_url,
            "discovery_status": "manual_review",
            "eligible_for_automatic_acceptance": "false",
            "match_basis": "family_variant_slug",
            "notes": "family_or_variant_slug_only",
            "image_urls": image_urls[:5],
        }

    if path_kind != "exact" and expected_match_kind != "exact":
        return {
            "status": "not_found",
            "exact_sku_ok": False,
            "false_match": False,
            "page_identity_ok": False,
            "parser_drift": False,
            "redirect_ok": True,
            "asset_host_ok": False,
            "final_url": final_url,
            "notes": "sku_not_confirmed_on_pdp",
        }

    if not sku_in_body:
        return {
            "status": "rejected",
            "exact_sku_ok": False,
            "false_match": False,
            "page_identity_ok": False,
            "parser_drift": True,
            "redirect_ok": True,
            "asset_host_ok": False,
            "final_url": final_url,
            "notes": "exact_slug_but_sku_absent_from_body",
        }

    if not image_urls:
        return {
            "status": "rejected",
            "exact_sku_ok": True,
            "false_match": False,
            "page_identity_ok": True,
            "parser_drift": False,
            "redirect_ok": True,
            "asset_host_ok": False,
            "final_url": final_url,
            "notes": "exact_sku_ok_but_no_bounded_product_image",
        }

    return {
        "status": "matched",
        "exact_sku_ok": True,
        "false_match": False,
        "page_identity_ok": True,
        "parser_drift": False,
        "redirect_ok": True,
        "asset_host_ok": True,
        "final_url": final_url,
        "brand_confirmed": brand_ok,
        "discovery_status": "retailer_review",
        "eligible_for_automatic_acceptance": "false",
        "match_basis": "exact_sku_product_page",
        "source_detail_url": final_url,
        "source_image_url": image_urls[0],
        "image_urls": image_urls[:8],
        "notes": "retailer_exact_sku_pdp",
    }
