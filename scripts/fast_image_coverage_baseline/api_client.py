"""Public storefront API client (list + detail)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .contracts import BaselineError, DetailImage, ProductListItem, RunCounters
from .http_transport import RateLimitedTransport

DEFAULT_API_BASE = "https://api.karzartools.com"
PRODUCT_LIST_PATH = "/api/v1/products/"
PRODUCT_DETAIL_PATH = "/api/v1/products/{product_id}"


def brand_key_from_payload(brand: dict[str, Any] | None) -> str | None:
    if not brand:
        return None
    slug = brand.get("slug")
    name = brand.get("name")
    if slug:
        return str(slug)
    if name:
        return str(name)
    bid = brand.get("id")
    return str(bid) if bid is not None else None


def parse_list_item(row: dict[str, Any]) -> ProductListItem:
    brand = row.get("brand") if isinstance(row.get("brand"), dict) else None
    category = row.get("category") if isinstance(row.get("category"), dict) else None
    return ProductListItem(
        product_id=int(row["id"]),
        sku=str(row.get("sku") or ""),
        slug=str(row["slug"]) if row.get("slug") is not None else None,
        name=str(row.get("name") or ""),
        brand_key=brand_key_from_payload(brand),
        brand_id=int(brand["id"]) if brand and brand.get("id") is not None else None,
        category_id=int(category["id"]) if category and category.get("id") is not None else None,
        category_slug=str(category["slug"]) if category and category.get("slug") else None,
        category_name=str(category["name"]) if category and category.get("name") else None,
        thumbnail=(str(row["thumbnail"]) if row.get("thumbnail") else None),
    )


def parse_detail_images(payload: dict[str, Any]) -> list[DetailImage]:
    raw = payload.get("images") or []
    out: list[DetailImage] = []
    for idx, img in enumerate(raw):
        if not isinstance(img, dict):
            continue
        url = img.get("url") or img.get("image_url")
        if not url:
            continue
        out.append(
            DetailImage(
                image_id=int(img["id"]) if img.get("id") is not None else None,
                url=str(url),
                is_primary=bool(img.get("is_primary")),
                display_order=int(img["display_order"])
                if img.get("display_order") is not None
                else idx,
            )
        )
    # Reproduce presenter ordering: (not is_primary, display_order, id)
    out.sort(key=lambda i: (not i.is_primary, i.display_order, i.image_id or 0))
    return out


async def fetch_all_products(
    transport: RateLimitedTransport,
    *,
    api_base: str = DEFAULT_API_BASE,
    page_size: int = 1000,
    cache: dict[str, Any] | None = None,
) -> tuple[list[ProductListItem], int]:
    """Paginate public list until unique IDs match meta.total_count."""
    if page_size < 1 or page_size > 1000:
        raise BaselineError("api", "page_size must be 1..1000")
    base = api_base.rstrip("/")
    cache = cache if cache is not None else {}
    items: list[ProductListItem] = []
    seen: set[int] = set()
    skip = 0
    total_count: int | None = None

    while True:
        url = f"{base}{PRODUCT_LIST_PATH}?skip={skip}&limit={page_size}"
        if url in cache:
            payload = cache[url]
        else:
            transport.counters.product_list_requests += 1
            payload = await transport.get_json(url, kind="api")
            cache[url] = payload
        if not isinstance(payload, dict) or "data" not in payload or "meta" not in payload:
            raise BaselineError("api", "list response missing data/meta")
        meta = payload["meta"]
        total_count = int(meta["total_count"])
        page = payload["data"] or []
        if not isinstance(page, list):
            raise BaselineError("api", "list data must be an array")
        for row in page:
            item = parse_list_item(row)
            if item.product_id in seen:
                raise BaselineError(
                    "api",
                    f"duplicate product_id {item.product_id} across pages at skip={skip}",
                )
            seen.add(item.product_id)
            items.append(item)
        skip += len(page)
        if skip >= total_count or not page:
            break
        if not meta.get("has_next", skip < total_count):
            if skip < total_count:
                raise BaselineError(
                    "api",
                    f"pagination stopped early: got {skip} of {total_count}",
                )
            break

    if total_count is None:
        raise BaselineError("api", "total_count unresolved")
    if len(seen) != total_count:
        raise BaselineError(
            "api",
            f"unique_product_ids_seen={len(seen)} != total_count={total_count}",
        )
    return items, total_count


async def fetch_product_detail(
    transport: RateLimitedTransport,
    product_id: int,
    *,
    api_base: str = DEFAULT_API_BASE,
    cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = api_base.rstrip("/")
    url = f"{base}{PRODUCT_DETAIL_PATH.format(product_id=product_id)}"
    cache = cache if cache is not None else {}
    if url in cache:
        return cache[url]
    transport.counters.product_detail_requests += 1
    payload = await transport.get_json(url, kind="api")
    if not isinstance(payload, dict):
        raise BaselineError("api", f"detail for {product_id} not an object")
    cache[url] = payload
    return payload


def detail_url(api_base: str, product_id: int) -> str:
    return f"{api_base.rstrip('/')}{PRODUCT_DETAIL_PATH.format(product_id=product_id)}"


def list_url(api_base: str, skip: int, limit: int) -> str:
    return f"{api_base.rstrip('/')}{PRODUCT_LIST_PATH}?skip={skip}&limit={limit}"


def slug_detail_url(api_base: str, slug: str) -> str:
    return f"{api_base.rstrip('/')}/api/v1/products/slug/{quote(slug, safe='')}"


def empty_counters() -> RunCounters:
    return RunCounters()
