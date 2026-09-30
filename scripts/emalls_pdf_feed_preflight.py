#!/usr/bin/env python3
"""Read-only Emalls PDF feed preflight (Contract B).

Does not call live Emalls. Does not require a token. Never mutates catalog.

Examples:

  python scripts/emalls_pdf_feed_preflight.py \\
    --base-url http://127.0.0.1:8000/api/v1 \\
    --item-per-page 50 --pages 0

  python scripts/emalls_pdf_feed_preflight.py --method post --json-output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

PLACEHOLDER_HINTS = (
    "placeholder",
    "woocommerce-placeholder",
    "no-image",
    "karzar-editorial",
    "/images/placeholders/",
)
PRIVATE_HOST_HINTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1", ".local", "staging", "catalog-staging")
PRODUCT_KEYS = {
    "title",
    "id",
    "price",
    "old_price",
    "category",
    "image",
    "color",
    "guarantee",
    "is_available",
    "url",
}
ROOT_KEYS = {
    "success",
    "products",
    "total_items",
    "pages_count",
    "item_per_page",
    "page_num",
}


def _request(url: str, *, method: str, timeout: float) -> dict[str, Any]:
    req = Request(
        url,
        data=b"" if method.upper() == "POST" else None,
        headers={"Accept": "application/json"},
        method=method.upper(),
    )
    with urlopen(req, timeout=timeout) as response:  # noqa: S310 — operator tool
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("response is not a JSON object")
    return data


def _url_bad(url: str) -> list[str]:
    problems: list[str] = []
    if not url:
        return ["empty"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        problems.append("not_public_https")
    host = (parsed.hostname or "").lower()
    if any(h in host or host == h.lstrip(".") for h in PRIVATE_HOST_HINTS):
        problems.append("private_or_staging_host")
    return problems


def analyze_feed(pages: list[dict[str, Any]]) -> dict[str, Any]:
    all_products: list[dict[str, Any]] = []
    root_issues: list[str] = []
    for page_payload in pages:
        missing_root = ROOT_KEYS - set(page_payload.keys())
        if missing_root:
            root_issues.append(f"missing_root:{sorted(missing_root)}")
        if page_payload.get("success") is not True:
            root_issues.append("success_not_true")
        products = page_payload.get("products")
        if not isinstance(products, list):
            root_issues.append("products_not_list")
            continue
        all_products.extend(products)

    ids = [str(p.get("id")) for p in all_products]
    dupes = sorted(k for k, c in Counter(ids).items() if c > 1 and k != "None")

    missing_title = missing_category = missing_image = missing_url = 0
    price_type_errors = fractional_price_errors = 0
    old_price_equal = old_price_lower = 0
    placeholder_image = non_https = bad_url = 0
    available_true = available_false = 0
    field_surface_leaks = 0
    is_available_type_errors = 0

    for product in all_products:
        extra = set(product.keys()) - PRODUCT_KEYS
        if extra or "stock_quantity" in product:
            field_surface_leaks += 1
        title = str(product.get("title") or "").strip()
        if not title:
            missing_title += 1
        if not str(product.get("category") or "").strip():
            missing_category += 1
        image = str(product.get("image") or "").strip()
        if not image:
            missing_image += 1
        else:
            if any(h in image.lower() for h in PLACEHOLDER_HINTS):
                placeholder_image += 1
            if _url_bad(image):
                non_https += 1
        url = str(product.get("url") or "").strip()
        if not url:
            missing_url += 1
        else:
            if _url_bad(url) or "/product/" not in url:
                bad_url += 1
            if "/api/" in url or "admin." in url:
                bad_url += 1
        price = product.get("price")
        if not isinstance(price, int) or isinstance(price, bool):
            price_type_errors += 1
        old_price = product.get("old_price")
        if old_price is not None:
            if not isinstance(old_price, int) or isinstance(old_price, bool):
                price_type_errors += 1
            elif isinstance(price, int) and not isinstance(price, bool):
                if old_price == price:
                    old_price_equal += 1
                if old_price < price:
                    old_price_lower += 1
        avail = product.get("is_available")
        if avail is True:
            available_true += 1
        elif avail is False:
            available_false += 1
        else:
            is_available_type_errors += 1
        pid = product.get("id")
        if not isinstance(pid, str) or not pid.strip():
            field_surface_leaks += 1

    first = pages[0] if pages else {}
    return {
        "root_issues": root_issues,
        "fetched": len(all_products),
        "total_items_reported": first.get("total_items"),
        "pages_count_reported": first.get("pages_count"),
        "duplicate_ids": dupes,
        "missing_title": missing_title,
        "missing_category": missing_category,
        "missing_image": missing_image,
        "missing_url": missing_url,
        "price_type_errors": price_type_errors,
        "fractional_price_errors": fractional_price_errors,
        "old_price_equal_current": old_price_equal,
        "old_price_lower_than_current": old_price_lower,
        "placeholder_image": placeholder_image,
        "non_https_or_private_image": non_https,
        "bad_product_url": bad_url,
        "available_true": available_true,
        "available_false": available_false,
        "is_available_type_errors": is_available_type_errors,
        "field_surface_leaks": field_surface_leaks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Emalls PDF feed preflight")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("KARZAR_API_BASE", "http://127.0.0.1:8000/api/v1"),
    )
    parser.add_argument("--item-per-page", type=int, default=50)
    parser.add_argument("--pages", type=int, default=0, help="0 = all pages")
    parser.add_argument("--method", choices=("get", "post"), default="get")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json-output", action="store_true")
    args = parser.parse_args(argv)

    if args.item_per_page < 1 or args.item_per_page > 100:
        print("ERROR: --item-per-page must be 1..100", file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/")
    path = f"{base}/integrations/emalls/feed"
    pages_data: list[dict[str, Any]] = []
    page = 1
    pages_count = None
    while True:
        if args.pages and page > args.pages:
            break
        query = urlencode({"page": page, "item_per_page": args.item_per_page})
        url = f"{path}?{query}"
        try:
            payload = _request(url, method=args.method, timeout=args.timeout)
        except HTTPError as exc:
            print(f"ERROR: HTTP {exc.code}: {exc.read()[:400]!r}", file=sys.stderr)
            return 1
        except URLError as exc:
            print(f"ERROR: cannot reach {url}: {exc}", file=sys.stderr)
            return 1
        pages_data.append(payload)
        if pages_count is None:
            pages_count = payload.get("pages_count")
        products = payload.get("products") or []
        if not products:
            break
        if pages_count is not None and page >= int(pages_count):
            break
        page += 1

    analysis = analyze_feed(pages_data)
    report = {
        "endpoint": path,
        "method": args.method.upper(),
        "item_per_page": args.item_per_page,
        "pages_fetched": len(pages_data),
        **analysis,
    }
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("EMALLS PDF FEED PREFLIGHT (read-only)")
        for key, value in report.items():
            print(f"  {key}: {value}")

    problems = (
        bool(report["root_issues"])
        or bool(report["duplicate_ids"])
        or report["missing_title"]
        or report["missing_category"]
        or report["missing_image"]
        or report["missing_url"]
        or report["price_type_errors"]
        or report["placeholder_image"]
        or report["non_https_or_private_image"]
        or report["bad_product_url"]
        or report["is_available_type_errors"]
        or report["field_surface_leaks"]
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
