"""Iranian retailer adapters: abzarham (sitemap) and abzarmarket (brand catalog)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urljoin

from .image_identity import select_retail_product_images
from .sku_norm import (
    brand_aliases,
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
_SKU_IN_SLUG_NUMERIC = re.compile(r"(?i)\d{3,5}-\d{1,5}[a-z0-9]*")
_SKU_IN_SLUG_ALPHA = re.compile(
    r"(?i)[a-z]{2,}[a-z0-9]*-(?:[a-z]{0,4}\d+[a-z0-9]*|\d+[a-z][a-z0-9]*)"
)
_SKU_IN_SLUG_SO = re.compile(r"(?i)SO-\d+")


def parse_sitemap_locs(xml_text: str) -> list[str]:
    return _LOC_RE.findall(xml_text or "")


def _slug_sku_tokens(text: str) -> list[str]:
    """Collect candidate SKU tokens without left-to-right overlap starvation."""
    found: list[str] = []
    found.extend(_SKU_IN_SLUG_NUMERIC.findall(text or ""))
    found.extend(_SKU_IN_SLUG_ALPHA.findall(text or ""))
    found.extend(_SKU_IN_SLUG_SO.findall(text or ""))
    return found


def _best_sku_token(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    scored: list[tuple[int, str]] = []
    for raw in tokens:
        t = raw.strip()
        if not t:
            continue
        score = len(t)
        if re.match(r"(?i)^\d{3,5}-\d{1,5}[a-z0-9]*$", t):
            score += 100
        elif re.match(r"(?i)^[a-z]{2,}[a-z0-9]*-", t):
            score += 40
        scored.append((score, t))
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][1]


def index_product_urls_by_sku(urls: list[str]) -> dict[str, str]:
    """Build SKU→URL index from product permalinks (last path segment preferred)."""
    out: dict[str, str] = {}
    for url in urls:
        path = unquote(url.split("?")[0]).rstrip("/")
        segment = path.split("/")[-1]
        tokens = _slug_sku_tokens(segment) or _slug_sku_tokens(path)
        token = _best_sku_token(tokens)
        if not token:
            continue
        out.setdefault(token.upper(), url)
    return out


def lookup_catalog_url(index: dict[str, str], sku: str) -> tuple[str, str]:
    """Return (url, match_kind) where match_kind is exact|family|''."""
    target = (sku or "").strip().upper()
    if not target:
        return "", ""
    if target in index:
        return index[target], "exact"
    base = strip_trailing_variant(target).upper()
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


def extract_abzarmarket_product_images(
    html: str,
    *,
    expected_brand: str,
    expected_sku: str,
    product_detail_url: str,
) -> list[str]:
    result = select_retail_product_images(
        expected_brand=expected_brand,
        expected_sku=expected_sku,
        product_detail_url=product_detail_url,
        product_page_html=html,
        candidate_url_allowlist=("abzarmarket.com/image-generator/products/",),
    )
    return list(result["image_urls"])


def extract_abzarham_product_images(
    html: str,
    *,
    expected_brand: str,
    expected_sku: str,
    product_detail_url: str,
) -> list[str]:
    result = select_retail_product_images(
        expected_brand=expected_brand,
        expected_sku=expected_sku,
        product_detail_url=product_detail_url,
        product_page_html=html,
        candidate_url_allowlist=("abzarham.com/wp-content/uploads/",),
    )
    return list(result["image_urls"])


# Back-compat thin wrappers used by older call sites / fixtures.
def extract_abzarham_product_images_legacy(html: str, *, sku: str) -> list[str]:
    return extract_abzarham_product_images(
        html,
        expected_brand="insize",
        expected_sku=sku,
        product_detail_url="",
    )


def evaluate_pdp(
    *,
    sku: str,
    brand_key: str,
    final_url: str,
    html: str,
    expected_match_kind: str,
    image_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Strict PDP identity evaluation shared by retailer adapters."""
    path_kind = sku_token_in_path(final_url, sku)
    brand_ok = False
    for alias in brand_aliases(brand_key):
        if alias and alias in (html or "").casefold():
            brand_ok = True
            break

    body_skus = skus_in_text(html)
    sku_cf = normalize_sku(sku)
    sku_in_body = sku_cf in body_skus or sku_cf in (html or "").casefold()

    if image_urls is None:
        image_urls = select_retail_product_images(
            expected_brand=brand_key,
            expected_sku=sku,
            product_detail_url=final_url,
            product_page_html=html,
        )["image_urls"]

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
            "reason_code": "image_identity_unproven",
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
