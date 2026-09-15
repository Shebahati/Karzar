"""Parse zcc.ir sitemaps, listing HTML, and product HTML. No network."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from zcc_ir_catalog import PARSER_VERSION, SOURCE_SITE
from zcc_ir_catalog.models import DiscoveryUrl, SourceProduct
from zcc_ir_catalog.normalize import (
    canonical_product_url,
    canonicalize_brand,
    category_path_from_url,
    detect_brand_from_text,
    extract_model_from_name,
    is_internal_numeric_sku,
    manufacturer_identity_key,
    normalize_source_url,
    price_to_toman,
    slug_from_product_url,
)

_LOC_RE = re.compile(r"<loc>\s*([^<]+)\s*</loc>", re.I)
_URL_BLOCK_RE = re.compile(r"<url>(.*?)</url>", re.I | re.S)
_LASTMOD_RE = re.compile(r"<lastmod>\s*([^<]+)\s*</lastmod>", re.I)
_IMAGE_LOC_RE = re.compile(r"<image:loc>\s*([^<]+)\s*</image:loc>", re.I)
_SITEMAP_LOC_RE = re.compile(r"<sitemap>\s*<loc>\s*([^<]+)\s*</loc>", re.I | re.S)
_JSONLD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_PRODUCT_HREF_RE = re.compile(
    r"""href=["'](https?://(?:www\.)?zcc\.ir/product/[^"'?#]+)["']""",
    re.I,
)
_RELATIVE_PRODUCT_HREF_RE = re.compile(r"""href=["'](/product/[^"'?#]+)["']""", re.I)
_PAGE_HREF_RE = re.compile(
    r"""href=["'](https?://(?:www\.)?zcc\.ir/[^"'?#]*?/page/(\d+)/?)["']""",
    re.I,
)
_BODY_CLASS_RE = re.compile(r"""<body[^>]*class=["']([^"']+)""", re.I)
_POSTID_RE = re.compile(r"postid-(\d+)", re.I)
_TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.I)
_LARGE_IMAGE_RE = re.compile(r"""data-large_image=["']([^"']+)["']""", re.I)
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PAGINATION_MAX = 500

PLACEHOLDER_IMAGE_MARKERS = (
    "enamad",
    "logo",
    "placeholder",
    "untitled",
    "zcc-intro",
    "/bg.jpg",
    "cropped-untitled",
)


def parse_sitemap_index(xml: str) -> list[str]:
    return [unescape(m).strip() for m in _SITEMAP_LOC_RE.findall(xml)]


def parse_urlset(xml: str, *, kind: str, evidence_method: str = "sitemap") -> list[DiscoveryUrl]:
    rows: list[DiscoveryUrl] = []
    seen: set[str] = set()
    for block in _URL_BLOCK_RE.findall(xml):
        loc_match = _LOC_RE.search(block)
        if not loc_match:
            continue
        url = canonical_product_url(unescape(loc_match.group(1)).strip()) or normalize_source_url(
            unescape(loc_match.group(1)).strip()
        )
        if not url or url in seen:
            continue
        seen.add(url)
        lastmod_match = _LASTMOD_RE.search(block)
        images = [unescape(u).strip() for u in _IMAGE_LOC_RE.findall(block)]
        rows.append(
            DiscoveryUrl(
                url=url,
                kind=kind,
                lastmod=lastmod_match.group(1).strip() if lastmod_match else None,
                sitemap_image_urls=images,
                evidence_method=evidence_method,
            )
        )
    if not rows:
        for loc in _LOC_RE.findall(xml):
            url = normalize_source_url(unescape(loc).strip())
            if url and url not in seen:
                seen.add(url)
                rows.append(DiscoveryUrl(url=url, kind=kind, evidence_method=evidence_method))
    return rows


def classify_sitemap_url(url: str) -> str:
    path = url.lower()
    if "/product-sitemap" in path:
        return "product_sitemap"
    if "product_brand" in path or "product-brand" in path:
        return "brand_sitemap"
    if "product_cat" in path:
        return "category_sitemap"
    if "product_tag" in path:
        return "tag_sitemap"
    if path.endswith("sitemap_index.xml") or "sitemap_index" in path:
        return "index"
    return "other_sitemap"


def extract_product_urls_from_html(html: str, *, base: str = "https://zcc.ir") -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for raw in _PRODUCT_HREF_RE.findall(html):
        url = canonical_product_url(raw)
        if url and url not in seen:
            seen.add(url)
            found.append(url)
    for raw in _RELATIVE_PRODUCT_HREF_RE.findall(html):
        url = canonical_product_url(urljoin(base, raw))
        if url and url not in seen:
            seen.add(url)
            found.append(url)
    return found


def listing_page_numbers(html: str) -> list[int]:
    nums = [int(n) for _, n in _PAGE_HREF_RE.findall(html)]
    return sorted({n for n in nums if 1 <= n <= _PAGINATION_MAX})


def max_listing_page(html: str) -> int:
    nums = listing_page_numbers(html)
    return max(nums) if nums else 1


def _load_jsonld_blocks(html: str) -> list[Any]:
    blocks: list[Any] = []
    for raw in _JSONLD_RE.findall(html):
        text = unescape(raw.strip())
        if not text:
            continue
        try:
            blocks.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return blocks


def _iter_jsonld_nodes(blocks: list[Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return
        if not isinstance(obj, dict):
            return
        nodes.append(obj)
        if "@graph" in obj:
            walk(obj["@graph"])

    for block in blocks:
        walk(block)
    return nodes


def _types_of(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    if raw is None:
        return set()
    if isinstance(raw, list):
        return {str(x) for x in raw}
    return {str(raw)}


def _jsonld_product(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for node in nodes:
        if "Product" in _types_of(node):
            return node
    return None


def _breadcrumb_names(nodes: list[dict[str, Any]]) -> list[str]:
    best: list[str] = []
    for node in nodes:
        if "BreadcrumbList" not in _types_of(node):
            continue
        elements = node.get("itemListElement") or []
        names: list[str] = []
        for el in elements:
            if not isinstance(el, dict):
                continue
            name = el.get("name")
            item = el.get("item")
            if not name and isinstance(item, dict):
                name = item.get("name")
            if name:
                names.append(_clean_text(str(name)))
        # Prefer the longest product-page trail (skip Home/Shop noise later).
        if len(names) > len(best):
            best = names
    return best


def _webpage_node(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for node in nodes:
        if "WebPage" in _types_of(node):
            return node
    return None


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(_STRIP_TAGS_RE.sub(" ", str(value)))
    return _WS_RE.sub(" ", text).replace("\xa0", " ").strip()


def _offer_field(product: dict[str, Any], key: str) -> Any:
    offers = product.get("offers")
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if isinstance(offers, dict):
        return offers.get(key)
    return None


def _normalize_availability(raw: str | None, html: str) -> tuple[str | None, str | None]:
    blob = (raw or "") + " " + html
    lower = blob.lower()
    if "outofstock" in lower or "out-of-stock" in lower or "ناموجود" in html:
        return raw, "unavailable"
    if "instock" in lower or "in-stock" in lower:
        return raw, "available"
    if "preorder" in lower or "backorder" in lower:
        return raw, "other"
    if "inquiry" in lower or "استعلام" in html:
        return raw, "inquiry"
    if raw:
        return raw, "unknown"
    return None, None


def _is_placeholder_image(url: str) -> bool:
    lowered = url.lower()
    return any(marker in lowered for marker in PLACEHOLDER_IMAGE_MARKERS)


def _collect_images(
    product: dict[str, Any],
    html: str,
    sitemap_images: list[str],
) -> tuple[str | None, list[str], str | None, list[str]]:
    flags: list[str] = []
    ordered: list[str] = []
    seen: set[str] = set()
    source: str | None = None

    def add(url: str | None, origin: str) -> None:
        nonlocal source
        if not url:
            return
        cleaned = unescape(url.strip())
        if not cleaned.startswith("http"):
            return
        # Drop srcset leftovers.
        cleaned = cleaned.split()[0]
        if cleaned in seen:
            return
        seen.add(cleaned)
        ordered.append(cleaned)
        if source is None:
            source = origin

    image = product.get("image")
    if isinstance(image, str):
        add(image, "jsonld")
    elif isinstance(image, list):
        for item in image:
            if isinstance(item, str):
                add(item, "jsonld")
            elif isinstance(item, dict):
                add(item.get("url") or item.get("contentUrl"), "jsonld")
    elif isinstance(image, dict):
        add(image.get("url") or image.get("contentUrl"), "jsonld")

    for url in _LARGE_IMAGE_RE.findall(html):
        add(url, "data-large_image")
    for url in sitemap_images:
        add(url, "sitemap")

    usable = [u for u in ordered if not _is_placeholder_image(u)]
    placeholders = [u for u in ordered if _is_placeholder_image(u)]
    if placeholders:
        flags.append("placeholder_or_chrome_images")
    if not usable and ordered:
        flags.append("only_suspicious_images")
        return ordered[0], ordered, source, flags
    main = usable[0] if usable else None
    if not main:
        flags.append("missing_image")
    return main, usable, source, flags


def parse_product_html(
    html: str,
    *,
    source_url: str,
    sitemap_lastmod: str | None = None,
    sitemap_images: list[str] | None = None,
    crawl_timestamp: str | None = None,
) -> SourceProduct:
    flags: list[str] = []
    methods = ["html"]
    nodes = _iter_jsonld_nodes(_load_jsonld_blocks(html))
    product = _jsonld_product(nodes)
    if product:
        methods.append("jsonld")
    else:
        flags.append("missing_jsonld_product")

    webpage = _webpage_node(nodes)
    title_match = _TITLE_RE.search(html)
    html_title = _clean_text(title_match.group(1) if title_match else "")
    name = _clean_text(str(product.get("name") if product else "")) or html_title
    if name.endswith(" - zcc.ir"):
        name = name[: -len(" - zcc.ir")].strip()

    jsonld_brand_raw = None
    if product:
        brand_node = product.get("brand")
        if isinstance(brand_node, dict):
            jsonld_brand_raw = _clean_text(str(brand_node.get("name") or ""))
        elif isinstance(brand_node, str):
            jsonld_brand_raw = _clean_text(brand_node)

    name_brand, name_brand_evidence = detect_brand_from_text(name, slug_from_product_url(source_url))
    jsonld_brand = canonicalize_brand(jsonld_brand_raw)
    brand_normalized = name_brand
    brand_evidence = name_brand_evidence
    if name_brand_evidence and name_brand_evidence.startswith("brand_token_conflict"):
        flags.append(name_brand_evidence)
        brand_normalized = None
        brand_evidence = name_brand_evidence
    elif jsonld_brand and name_brand and jsonld_brand != name_brand:
        flags.append("jsonld_brand_conflicts_name")
        brand_evidence = f"{name_brand_evidence};jsonld={jsonld_brand}"
    elif not name_brand and jsonld_brand:
        # JSON-LD on zcc.ir labels SAN OU / STC products as brand ZCC. Do not trust it.
        flags.append("jsonld_brand_untrusted_without_name_token")
        brand_normalized = None
        brand_evidence = "jsonld_untrusted"

    if not brand_normalized:
        flags.append("missing_brand")

    internal_sku = None
    jsonld_sku = _clean_text(str(product.get("sku") or "")) if product else ""
    if jsonld_sku:
        if is_internal_numeric_sku(jsonld_sku):
            internal_sku = jsonld_sku
            flags.append("sku_is_internal_numeric")
        else:
            flags.append("jsonld_sku_non_numeric")

    body_class = ""
    body_match = _BODY_CLASS_RE.search(html)
    if body_match:
        body_class = body_match.group(1)
    postids = _POSTID_RE.findall(body_class) or _POSTID_RE.findall(html)
    source_product_id = postids[0] if postids else internal_sku

    model = extract_model_from_name(name)
    manufacturer_key = manufacturer_identity_key(model)
    sku = model  # manufacturer-facing identity; internal numeric kept separate
    if not model:
        flags.append("missing_manufacturer_code")

    crumbs = _breadcrumb_names(nodes)
    # Drop leading Home / Shop / product title.
    skip = {"خانه", "فروشگاه", name}
    category_names = [c for c in crumbs if c and c not in skip]
    source_category = category_names[0] if category_names else None
    source_subcategory = category_names[-1] if len(category_names) >= 2 else None
    source_category_url = None
    for node in nodes:
        if "BreadcrumbList" not in _types_of(node):
            continue
        for el in node.get("itemListElement") or []:
            if not isinstance(el, dict):
                continue
            item = el.get("item")
            url = None
            if isinstance(item, str):
                url = item
            elif isinstance(item, dict):
                url = item.get("@id") or item.get("url")
            if url and "/product-category/" in str(url):
                source_category_url = normalize_source_url(str(url))
    if not category_names:
        flags.append("missing_category")
        if source_category_url:
            category_names = category_path_from_url(source_category_url)

    offer_url = _offer_field(product, "url") if product else None
    canonical = canonical_product_url(str(offer_url or (webpage or {}).get("url") or source_url))
    slug = slug_from_product_url(canonical or source_url)

    price_raw = None
    price_currency = None
    if product:
        price_raw = _offer_field(product, "price")
        price_currency = _offer_field(product, "priceCurrency")
        if price_raw is not None:
            price_raw = str(price_raw)
        if price_currency is not None:
            price_currency = str(price_currency)
    toman, price_status, price_reason = price_to_toman(price_raw, price_currency)
    if price_reason:
        flags.append(price_reason)
    if price_raw is None:
        flags.append("missing_price")

    avail_raw = _offer_field(product, "availability") if product else None
    if avail_raw is not None:
        avail_raw = str(avail_raw)
    avail_raw, avail_norm = _normalize_availability(avail_raw, html + " " + body_class)
    if not avail_norm:
        flags.append("missing_availability")

    main_image, gallery, image_source, image_flags = _collect_images(
        product or {}, html, sitemap_images or []
    )
    flags.extend(image_flags)

    description = _clean_text(str(product.get("description") or "")) if product else ""
    if not description:
        description = None

    lastmod = sitemap_lastmod
    if webpage and webpage.get("dateModified"):
        lastmod = str(webpage.get("dateModified"))
        methods.append("webpage_dateModified")

    product_type = None
    if "product-type-variable" in body_class:
        product_type = "variable"
        flags.append("variable_product")
    elif "product-type-simple" in body_class:
        product_type = "simple"

    confidence = "high"
    if "missing_jsonld_product" in flags or "missing_manufacturer_code" in flags:
        confidence = "low"
    elif any(f.startswith("jsonld_brand") or f.startswith("brand_token") for f in flags):
        confidence = "medium"
    elif "missing_category" in flags or "missing_price" in flags:
        confidence = "medium"

    identity_sku = model
    parse_flags = sorted(set(flags))
    return SourceProduct(
        source_site=SOURCE_SITE,
        source_url=canonical_product_url(source_url) or source_url,
        canonical_url=canonical or None,
        source_product_id=str(source_product_id) if source_product_id else None,
        source_slug=slug,
        source_internal_sku=internal_sku,
        brand=name_brand or jsonld_brand_raw,
        brand_normalized=brand_normalized,
        brand_evidence=brand_evidence,
        sku=identity_sku,
        manufacturer_code=model,
        model=model,
        part_number=manufacturer_key or None,
        name_fa=name or None,
        name_original=name or None,
        category_path=category_names,
        source_category=source_category,
        source_subcategory=source_subcategory,
        source_category_url=source_category_url,
        short_description=description,
        description=description,
        price_raw=price_raw,
        price_currency=price_currency,
        price_normalized=str(toman) if toman is not None else None,
        price_status=price_status,
        availability_raw=avail_raw,
        availability_normalized=avail_norm,
        main_image_url=main_image,
        gallery_image_urls=gallery,
        technical_specs={},
        attributes={},
        weight=None,
        dimensions=None,
        source_last_modified=lastmod,
        crawl_timestamp=crawl_timestamp,
        evidence_method="+".join(methods),
        parse_confidence=confidence,
        parse_flags=parse_flags,
        jsonld_brand=jsonld_brand_raw,
        image_source=image_source,
        gallery_count=len(gallery),
        commerce_authority="SOURCE_VALUE_OBSERVED;AUTHORITY_NOT_YET_APPROVED",
        parser_version=PARSER_VERSION,
        product_type=product_type,
    )


def parse_robots(text: str) -> dict[str, list[str]]:
    """Minimal robots parser for the '*' group used by zcc.ir."""
    disallow: list[str] = []
    allow: list[str] = []
    sitemaps: list[str] = []
    in_star = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            in_star = agent == "*"
            continue
        if line.lower().startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
            continue
        if not in_star:
            continue
        if line.lower().startswith("disallow:"):
            disallow.append(line.split(":", 1)[1].strip())
        elif line.lower().startswith("allow:"):
            allow.append(line.split(":", 1)[1].strip())
    return {"disallow": disallow, "allow": allow, "sitemaps": sitemaps}


def robots_allows(path_and_query: str, rules: dict[str, list[str]]) -> bool:
    """Conservative allow: longest matching Disallow/Allow prefix, plus /*?* query ban."""
    from urllib.parse import urlsplit

    split = urlsplit(path_and_query)
    path = split.path or "/"
    query = split.query
    # Explicit zcc.ir rule Disallow: /*?* and /?*
    if query:
        return False
    target = path
    matched_disallow = ""
    matched_allow = ""
    for rule in rules.get("disallow") or []:
        if not rule:
            continue
        prefix = rule.replace("*", "")
        if rule.endswith("*") and prefix and target.startswith(prefix.rstrip("*")):
            if len(rule) >= len(matched_disallow):
                matched_disallow = rule
        elif target.startswith(rule):
            if len(rule) >= len(matched_disallow):
                matched_disallow = rule
    for rule in rules.get("allow") or []:
        if rule and target.startswith(rule):
            if len(rule) >= len(matched_allow):
                matched_allow = rule
    if matched_allow and len(matched_allow) >= len(matched_disallow):
        return True
    if matched_disallow:
        return False
    return True
