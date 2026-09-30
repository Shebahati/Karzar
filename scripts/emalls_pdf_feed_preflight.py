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
import math
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
PRIVATE_HOST_HINTS = (
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    ".local",
    "staging",
    "catalog-staging",
)
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
ROOT_KEYS = frozenset(
    {
        "success",
        "products",
        "total_items",
        "pages_count",
        "item_per_page",
        "page_num",
    }
)


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


def _is_strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def analyze_feed(
    pages: list[dict[str, Any]],
    *,
    requested_item_per_page: int,
    scan_complete: bool,
) -> dict[str, Any]:
    """Validate root contract, pagination arithmetic, and product surface.

    ``scan_complete`` is True only for a full feed scan (``--pages 0`` that
    fetched through ``pages_count``). Partial scans do not require
    ``fetched == total_items``.
    """
    issues: list[str] = []
    all_products: list[dict[str, Any]] = []

    if not pages:
        issues.append("no_pages_fetched")
        return {
            "issues": issues,
            "root_issues": issues,
            "scan_complete": scan_complete,
            "fetched": 0,
            "total_items_reported": None,
            "pages_count_reported": None,
            "duplicate_ids": [],
            "missing_title": 0,
            "missing_category": 0,
            "missing_image": 0,
            "missing_url": 0,
            "price_type_errors": 0,
            "fractional_price_errors": None,
            "fractional_price_note": (
                "API-only preflight cannot observe fractional original_price "
                "omitted as null; use a DB-level audit for that anomaly."
            ),
            "old_price_equal_current": 0,
            "old_price_lower_than_current": 0,
            "placeholder_image": 0,
            "non_https_or_private_image": 0,
            "bad_product_url": 0,
            "available_true": 0,
            "available_false": 0,
            "is_available_type_errors": 0,
            "field_surface_leaks": 0,
            "ok": False,
        }

    first = pages[0]
    expected_total = first.get("total_items")
    expected_pages = first.get("pages_count")

    for index, page_payload in enumerate(pages):
        page_num_expected = index + 1
        missing_root = ROOT_KEYS - set(page_payload.keys())
        if missing_root:
            issues.append(f"missing_root:{sorted(missing_root)}")
        unexpected_root = set(page_payload.keys()) - ROOT_KEYS
        if unexpected_root:
            issues.append(f"unexpected_root:{sorted(unexpected_root)}")

        success = page_payload.get("success")
        if success is not True:
            issues.append(f"page_{page_num_expected}:success_not_true")
        if not isinstance(success, bool):
            issues.append(f"page_{page_num_expected}:success_not_bool")

        for field in ("total_items", "pages_count", "item_per_page", "page_num"):
            value = page_payload.get(field)
            if not _is_strict_int(value):
                issues.append(f"page_{page_num_expected}:{field}_not_int")

        products = page_payload.get("products")
        if not isinstance(products, list):
            issues.append(f"page_{page_num_expected}:products_not_list")
            products = []

        page_num = page_payload.get("page_num")
        if _is_strict_int(page_num) and page_num != page_num_expected:
            issues.append(
                f"page_{page_num_expected}:wrong_page_num:{page_num}"
            )

        item_per_page = page_payload.get("item_per_page")
        if _is_strict_int(item_per_page) and item_per_page != requested_item_per_page:
            issues.append(
                f"page_{page_num_expected}:wrong_item_per_page:{item_per_page}"
            )

        if page_payload.get("total_items") != expected_total:
            issues.append(f"page_{page_num_expected}:total_items_changed")
        if page_payload.get("pages_count") != expected_pages:
            issues.append(f"page_{page_num_expected}:pages_count_changed")

        all_products.extend(products)

    if _is_strict_int(expected_total) and _is_strict_int(expected_pages):
        if expected_total == 0:
            if expected_pages != 0:
                issues.append("pages_count_nonzero_when_total_zero")
        else:
            expected_calc = math.ceil(expected_total / requested_item_per_page)
            if expected_pages != expected_calc:
                issues.append(
                    f"pages_count_mismatch:reported={expected_pages}"
                    f":expected={expected_calc}"
                )

        if scan_complete and _is_strict_int(expected_pages):
            if expected_total > 0 and len(pages) < expected_pages:
                issues.append(
                    f"incomplete_scan:fetched_pages={len(pages)}"
                    f":pages_count={expected_pages}"
                )
            # Premature empty + fullness checks across declared pages.
            fetched_so_far = 0
            for index, page_payload in enumerate(pages):
                page_num = index + 1
                products = page_payload.get("products")
                if not isinstance(products, list):
                    continue
                count = len(products)
                if (
                    expected_pages > 0
                    and page_num <= expected_pages
                    and expected_total > fetched_so_far
                    and count == 0
                ):
                    issues.append(f"premature_empty_page:{page_num}")
                if expected_pages > 0 and page_num < expected_pages:
                    if count != requested_item_per_page:
                        issues.append(
                            f"page_{page_num}:not_full:"
                            f"got={count}:expected={requested_item_per_page}"
                        )
                if expected_pages > 0 and page_num == expected_pages:
                    remainder = expected_total % requested_item_per_page
                    expected_last = (
                        requested_item_per_page if remainder == 0 else remainder
                    )
                    if expected_total > 0 and count != expected_last:
                        issues.append(
                            f"final_page_size_mismatch:got={count}"
                            f":expected={expected_last}"
                        )
                fetched_so_far += count

            if len(all_products) != expected_total:
                issues.append(
                    f"fetched_ne_total_items:fetched={len(all_products)}"
                    f":total_items={expected_total}"
                )

    ids = [str(p.get("id")) for p in all_products]
    dupes = sorted(k for k, c in Counter(ids).items() if c > 1 and k != "None")
    if dupes:
        issues.append(f"duplicate_ids:{dupes}")

    missing_title = missing_category = missing_image = missing_url = 0
    price_type_errors = 0
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
        if not _is_strict_int(price):
            price_type_errors += 1
        old_price = product.get("old_price")
        if old_price is not None:
            if not _is_strict_int(old_price):
                price_type_errors += 1
            elif _is_strict_int(price):
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

    product_issues = (
        missing_title
        or missing_category
        or missing_image
        or missing_url
        or price_type_errors
        or placeholder_image
        or non_https
        or bad_url
        or is_available_type_errors
        or field_surface_leaks
    )
    if product_issues:
        issues.append("product_field_failures")

    return {
        "issues": issues,
        "root_issues": [i for i in issues if i.startswith(("missing_root", "unexpected_root", "page_", "success", "pages_count", "fetched", "incomplete", "premature", "final_page"))],
        "scan_complete": scan_complete,
        "fetched": len(all_products),
        "total_items_reported": expected_total,
        "pages_count_reported": expected_pages,
        "duplicate_ids": dupes,
        "missing_title": missing_title,
        "missing_category": missing_category,
        "missing_image": missing_image,
        "missing_url": missing_url,
        "price_type_errors": price_type_errors,
        "fractional_price_errors": None,
        "fractional_price_note": (
            "API-only preflight cannot observe fractional original_price "
            "omitted as null; use a DB-level audit for that anomaly."
        ),
        "old_price_equal_current": old_price_equal,
        "old_price_lower_than_current": old_price_lower,
        "placeholder_image": placeholder_image,
        "non_https_or_private_image": non_https,
        "bad_product_url": bad_url,
        "available_true": available_true,
        "available_false": available_false,
        "is_available_type_errors": is_available_type_errors,
        "field_surface_leaks": field_surface_leaks,
        "ok": not issues,
    }


def fetch_feed_pages(
    *,
    base_url: str,
    item_per_page: int,
    pages_limit: int,
    method: str,
    timeout: float,
) -> tuple[list[dict[str, Any]], bool]:
    """Fetch pages. Returns (pages, scan_complete).

    ``pages_limit == 0`` means fetch the full feed through ``pages_count``.
    """
    base = base_url.rstrip("/")
    path = f"{base}/integrations/emalls/feed"
    pages_data: list[dict[str, Any]] = []
    page = 1
    pages_count: int | None = None
    partial = pages_limit > 0

    while True:
        if partial and page > pages_limit:
            break
        query = urlencode({"page": page, "item_per_page": item_per_page})
        url = f"{path}?{query}"
        payload = _request(url, method=method, timeout=timeout)
        pages_data.append(payload)
        if pages_count is None:
            raw_pages = payload.get("pages_count")
            pages_count = int(raw_pages) if _is_strict_int(raw_pages) else 0

        if partial:
            if page >= pages_limit:
                break
        else:
            if pages_count == 0:
                break
            if page >= pages_count:
                break
            # Do not treat empty products as success mid-scan; keep fetching
            # through pages_count so analyze_feed can flag premature empties.
        page += 1

    if partial:
        scan_complete = False
    else:
        reported = pages_data[0].get("pages_count") if pages_data else 0
        reported_i = int(reported) if _is_strict_int(reported) else 0
        if reported_i == 0:
            scan_complete = True
        else:
            scan_complete = len(pages_data) >= reported_i
    return pages_data, scan_complete


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

    try:
        pages_data, scan_complete = fetch_feed_pages(
            base_url=args.base_url,
            item_per_page=args.item_per_page,
            pages_limit=args.pages,
            method=args.method,
            timeout=args.timeout,
        )
    except HTTPError as exc:
        print(f"ERROR: HTTP {exc.code}: {exc.read()[:400]!r}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"ERROR: cannot reach feed: {exc}", file=sys.stderr)
        return 1

    analysis = analyze_feed(
        pages_data,
        requested_item_per_page=args.item_per_page,
        scan_complete=scan_complete,
    )
    report = {
        "endpoint": f"{args.base_url.rstrip('/')}/integrations/emalls/feed",
        "method": args.method.upper(),
        "item_per_page": args.item_per_page,
        "pages_fetched": len(pages_data),
        "scan_complete": scan_complete,
        "full_feed": bool(scan_complete),
        **{k: v for k, v in analysis.items() if k != "scan_complete"},
    }
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("EMALLS PDF FEED PREFLIGHT (read-only)")
        for key, value in report.items():
            print(f"  {key}: {value}")

    return 0 if analysis["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
