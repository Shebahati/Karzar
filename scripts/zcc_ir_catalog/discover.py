"""Discover the zcc.ir product universe from sitemaps and listing pages."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from zcc_ir_catalog.crawl import ReadOnlyFetcher
from zcc_ir_catalog.models import DiscoveryUrl
from zcc_ir_catalog.normalize import canonical_product_url, normalize_source_url
from zcc_ir_catalog.parse import (
    classify_sitemap_url,
    extract_product_urls_from_html,
    max_listing_page,
    parse_robots,
    parse_sitemap_index,
    parse_urlset,
)

SITEMAP_INDEX = "https://zcc.ir/sitemap_index.xml"
ROBOTS_URL = "https://zcc.ir/robots.txt"
KNOWN_TAG_SHOPS = (
    "https://zcc.ir/product-tag/zcc/",
    "https://zcc.ir/product-tag/stc/",
    "https://zcc.ir/product-tag/sanou/",
)


def fetch_robots(fetcher: ReadOnlyFetcher) -> dict[str, list[str]]:
    result = fetcher.fetch(ROBOTS_URL)
    if not result.ok:
        # Fail closed to the observed zcc.ir robots.txt shape rather than crawling wp-json.
        return {
            "disallow": [
                "/wp-admin/",
                "/wp-json/",
                "/my-account/",
                "/wishlist/",
                "/cart/",
                "/checkout/",
                "/search/",
            ],
            "allow": ["/wp-admin/admin-ajax.php"],
            "sitemaps": [SITEMAP_INDEX],
        }
    return parse_robots(result.body)


def discover_sitemaps(fetcher: ReadOnlyFetcher) -> dict[str, list[DiscoveryUrl]]:
    index = fetcher.fetch(SITEMAP_INDEX)
    if not index.ok:
        raise RuntimeError(f"sitemap_index_failed:{index.error}")
    sitemap_urls = parse_sitemap_index(index.body)
    grouped: dict[str, list[DiscoveryUrl]] = {
        "index": [
            DiscoveryUrl(url=SITEMAP_INDEX, kind="index", evidence_method="robots+sitemap")
        ]
    }
    for sm_url in sitemap_urls:
        kind = classify_sitemap_url(sm_url)
        fetched = fetcher.fetch(sm_url)
        if not fetched.ok:
            grouped.setdefault("failures", []).append(
                DiscoveryUrl(url=sm_url, kind=kind, evidence_method=f"failed:{fetched.error}")
            )
            continue
        child_kind = {
            "product_sitemap": "product",
            "brand_sitemap": "brand",
            "category_sitemap": "category",
            "tag_sitemap": "tag",
        }.get(kind, "other")
        grouped.setdefault(child_kind, []).extend(
            parse_urlset(fetched.body, kind=child_kind, evidence_method=f"sitemap:{sm_url}")
        )
    return grouped


def _with_page(url: str, page: int) -> str:
    base = normalize_source_url(url).rstrip("/") + "/"
    if page <= 1:
        return base
    return base + f"page/{page}/"


def discover_listing_products(
    fetcher: ReadOnlyFetcher,
    listing_url: str,
    *,
    max_pages: int = 80,
) -> tuple[list[str], int]:
    """Paginate /page/N/ (no query string). Stop on empty/404 or max_pages."""
    found: list[str] = []
    seen: set[str] = set()
    first = fetcher.fetch(listing_url)
    if not first.ok:
        return [], 0
    pages = min(max_listing_page(first.body), max_pages)
    scanned = 0
    for page in range(1, pages + 1):
        url = listing_url if page == 1 else _with_page(listing_url, page)
        result = first if page == 1 else fetcher.fetch(url)
        scanned += 1
        if not result.ok:
            break
        urls = extract_product_urls_from_html(result.body)
        new = 0
        for product_url in urls:
            if product_url not in seen:
                seen.add(product_url)
                found.append(product_url)
                new += 1
        if page > 1 and new == 0:
            break
    return found, scanned


def merge_product_universe(
    sitemap_products: list[DiscoveryUrl],
    extra_urls: list[str],
    *,
    extra_method: str,
) -> list[DiscoveryUrl]:
    by_url: dict[str, DiscoveryUrl] = {}
    for row in sitemap_products:
        url = canonical_product_url(row.url)
        if "/product/" not in url:
            continue
        by_url[url] = DiscoveryUrl(
            url=url,
            kind="product",
            lastmod=row.lastmod,
            sitemap_image_urls=list(row.sitemap_image_urls),
            evidence_method=row.evidence_method,
        )
    for raw in extra_urls:
        url = canonical_product_url(raw)
        if "/product/" not in url:
            continue
        if url in by_url:
            if extra_method not in by_url[url].evidence_method:
                by_url[url].evidence_method += f"+{extra_method}"
            continue
        by_url[url] = DiscoveryUrl(
            url=url,
            kind="product",
            evidence_method=extra_method,
        )
    return [by_url[k] for k in sorted(by_url)]


def brand_slugs_from_sitemap(brand_urls: list[DiscoveryUrl]) -> list[str]:
    slugs: list[str] = []
    for row in brand_urls:
        parts = [p for p in urlparse(row.url).path.split("/") if p]
        if parts:
            slugs.append(parts[-1])
    return slugs


ProgressFn = Callable[[str], None]


def discover_universe(
    fetcher: ReadOnlyFetcher,
    *,
    include_listings: bool = True,
    progress: ProgressFn | None = None,
) -> dict[str, object]:
    log = progress or (lambda _m: None)
    grouped = discover_sitemaps(fetcher)
    sitemap_products = grouped.get("product") or []
    extra: list[str] = []
    listing_pages_scanned = 0
    if include_listings:
        listing_seeds: list[str] = list(KNOWN_TAG_SHOPS)
        for cat in grouped.get("category") or []:
            listing_seeds.append(cat.url)
        listing_seeds.append("https://zcc.ir/shop/")
        seen_listings: set[str] = set()
        for listing in listing_seeds:
            norm = normalize_source_url(listing).rstrip("/") + "/"
            if norm in seen_listings:
                continue
            seen_listings.add(norm)
            log(f"listing {norm}")
            urls, scanned = discover_listing_products(fetcher, norm)
            extra.extend(urls)
            listing_pages_scanned += scanned
    products = merge_product_universe(sitemap_products, extra, extra_method="listing_html")
    return {
        "grouped": grouped,
        "products": products,
        "listing_pages_scanned": listing_pages_scanned,
        "listing_extra_urls": extra,
    }
