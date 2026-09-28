#!/usr/bin/env python3
"""Read-only Emalls adapter preflight.

Calls the local/staging Emalls extraction endpoint, paginates, and reports
integrity issues. Never mutates catalog data. Never commits tokens.

Examples:

  # Prefer form encoding for external-compatibility checks (official plugin style):
  python scripts/emalls_preflight.py \\
    --base-url http://127.0.0.1:8000/api/v1 \\
    --token "$EMALLS_TEST_TOKEN" \\
    --request-format form \\
    --limit 100 --pages 0

  python scripts/emalls_preflight.py ... --request-format json --json-output
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
    "no_image",
    "noimage",
    "default-image",
    "karzar-editorial",
    "/images/placeholders/",
)

PRIVATE_HOST_HINTS = (
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    ".local",
    "staging.",
    "catalog-staging",
)

SKU_SPEC_KEY = "شناسه کالا"


def _post(
    url: str,
    payload: dict[str, Any],
    *,
    request_format: str,
    timeout: float,
) -> dict[str, Any]:
    if request_format == "json":
        body = json.dumps(payload).encode("utf-8")
        content_type = "application/json"
    elif request_format == "form":
        body = urlencode(
            {key: "" if value is None else str(value) for key, value in payload.items()}
        ).encode("utf-8")
        content_type = "application/x-www-form-urlencoded"
    else:
        raise ValueError(f"unsupported request format: {request_format}")

    request = Request(
        url,
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 — operator tool
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("Emalls response is not a JSON object")
    return data


def _is_placeholder(url: str) -> bool:
    lowered = url.lower()
    return any(token in lowered for token in PLACEHOLDER_HINTS)


def _url_problems(url: str, *, expect_https: bool = True) -> list[str]:
    problems: list[str] = []
    if not url:
        problems.append("empty")
        return problems
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        problems.append("non_absolute")
        return problems
    if expect_https and parsed.scheme != "https":
        problems.append("non_https")
    host = (parsed.hostname or "").lower()
    if any(hint in host or host.endswith(hint) or host == hint.lstrip(".") for hint in PRIVATE_HOST_HINTS):
        problems.append("private_or_staging_host")
    return problems


def analyze_products(
    products: list[dict[str, Any]],
    *,
    expected_skus: dict[int, str] | None = None,
    expected_page_origin: str | None = None,
) -> dict[str, Any]:
    """Analyze Emalls product rows. Pure helper for CLI and tests."""
    page_uniques: list[Any] = []
    missing_page_url = 0
    missing_image = 0
    placeholder_image = 0
    invalid_price = 0
    missing_title = 0
    malformed_specs = 0
    non_https_public = 0
    non_absolute_image = 0
    private_host_image = 0
    page_url_host_mismatch = 0
    sku_spec_missing = 0
    sku_spec_mismatch = 0
    samples: list[dict[str, Any]] = []

    expected_origin = (expected_page_origin or "").rstrip("/")

    for product in products:
        page_unique = product.get("page_unique")
        page_uniques.append(page_unique)
        title = str(product.get("title") or "").strip()
        if not title:
            missing_title += 1

        page_url = str(product.get("page_url") or "").strip()
        if not page_url:
            missing_page_url += 1
        else:
            for problem in _url_problems(page_url):
                if problem == "non_https":
                    non_https_public += 1
                if problem in {"private_or_staging_host", "non_absolute"}:
                    page_url_host_mismatch += 1
            if expected_origin and not page_url.startswith(f"{expected_origin}/product/"):
                page_url_host_mismatch += 1

        image_link = str(product.get("image_link") or "").strip()
        if not image_link:
            missing_image += 1
        else:
            if _is_placeholder(image_link):
                placeholder_image += 1
            for problem in _url_problems(image_link):
                if problem == "non_absolute":
                    non_absolute_image += 1
                if problem == "non_https":
                    non_https_public += 1
                if problem == "private_or_staging_host":
                    private_host_image += 1

        current_price = product.get("current_price")
        if current_price is None:
            invalid_price += 1
        elif not isinstance(current_price, str):
            invalid_price += 1
        elif current_price != "" and not current_price.replace(".", "", 1).isdigit():
            invalid_price += 1

        spec = product.get("spec")
        sku_in_spec: str | None = None
        if spec is None:
            malformed_specs += 1
        elif not isinstance(spec, list):
            malformed_specs += 1
        elif len(spec) > 1:
            malformed_specs += 1
        elif len(spec) == 1 and not isinstance(spec[0], dict):
            malformed_specs += 1
        elif isinstance(spec, list) and spec and isinstance(spec[0], dict):
            sku_in_spec = str(spec[0].get(SKU_SPEC_KEY) or "").strip() or None
            if not sku_in_spec:
                sku_spec_missing += 1
            elif expected_skus is not None and isinstance(page_unique, int):
                expected = (expected_skus.get(page_unique) or "").strip()
                if expected and sku_in_spec != expected:
                    sku_spec_mismatch += 1
        else:
            sku_spec_missing += 1

        if len(samples) < 5:
            samples.append(
                {
                    "page_unique": page_unique,
                    "title": product.get("title"),
                    "current_price": product.get("current_price"),
                    "availability": product.get("availability"),
                    "page_url": product.get("page_url"),
                    "image_link": product.get("image_link"),
                    "sku_spec": sku_in_spec,
                }
            )

    counts = Counter(page_uniques)
    duplicates = sorted(key for key, count in counts.items() if count > 1 and key is not None)

    return {
        "fetched": len(products),
        "unique_page_unique": len(set(page_uniques)),
        "duplicate_page_unique": duplicates,
        "missing_page_url": missing_page_url,
        "missing_image": missing_image,
        "placeholder_image": placeholder_image,
        "invalid_price": invalid_price,
        "missing_title": missing_title,
        "malformed_specs": malformed_specs,
        "non_https_public_urls": non_https_public,
        "non_absolute_image": non_absolute_image,
        "private_host_image": private_host_image,
        "page_url_host_mismatch": page_url_host_mismatch,
        "sku_spec_missing": sku_spec_missing,
        "sku_spec_mismatch": sku_spec_mismatch,
        "samples": samples,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Emalls adapter preflight")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("KARZAR_API_BASE", "http://127.0.0.1:8000/api/v1"),
        help="API v1 base URL (Category A local default)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("EMALLS_TEST_TOKEN", ""),
        help="Emalls test token (or set EMALLS_TEST_TOKEN). Never commit real tokens.",
    )
    parser.add_argument(
        "--request-format",
        choices=("form", "json"),
        default="form",
        help="POST encoding (default form = external Emalls compatibility)",
    )
    parser.add_argument("--limit", type=int, default=100, help="Page size (1-100)")
    parser.add_argument(
        "--pages",
        type=int,
        default=0,
        help="Max pages to fetch (0 = all pages until empty/beyond max_pages)",
    )
    parser.add_argument(
        "--expected-page-origin",
        default=os.environ.get("EMALLS_PUBLIC_SITE_ORIGIN", ""),
        help=(
            "Expected HTTPS origin for page_url checks "
            "(set EMALLS_PUBLIC_SITE_ORIGIN or pass explicitly; no production default)"
        ),
    )
    parser.add_argument(
        "--expected-sku-map",
        default="",
        help="Optional JSON object mapping page_unique→sku for sku_spec_mismatch checks",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json-output", action="store_true")
    args = parser.parse_args(argv)

    token = (args.token or "").strip()
    if not token:
        print("ERROR: provide --token or EMALLS_TEST_TOKEN", file=sys.stderr)
        return 2
    if args.limit < 1 or args.limit > 100:
        print("ERROR: --limit must be 1..100", file=sys.stderr)
        return 2

    expected_skus: dict[int, str] | None = None
    if args.expected_sku_map.strip():
        loaded = json.loads(args.expected_sku_map)
        if not isinstance(loaded, dict):
            print("ERROR: --expected-sku-map must be a JSON object", file=sys.stderr)
            return 2
        expected_skus = {int(key): str(value) for key, value in loaded.items()}

    base = args.base_url.rstrip("/")
    url = f"{base}/integrations/emalls/products"
    all_products: list[dict[str, Any]] = []
    count = None
    max_pages = None
    page = 1

    while True:
        if args.pages and page > args.pages:
            break
        try:
            payload = _post(
                url,
                {"token": token, "page": page, "limit": args.limit, "variation": "false"},
                request_format=args.request_format,
                timeout=args.timeout,
            )
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"ERROR: HTTP {exc.code} from Emalls endpoint: {body[:500]}", file=sys.stderr)
            return 1
        except URLError as exc:
            print(f"ERROR: cannot reach {url}: {exc}", file=sys.stderr)
            return 1

        if count is None:
            count = payload.get("count")
            max_pages = payload.get("max_pages")
        products = payload.get("products") or []
        if not isinstance(products, list):
            print("ERROR: products is not a list", file=sys.stderr)
            return 1
        all_products.extend(products)
        if not products:
            break
        if max_pages is not None and page >= int(max_pages):
            break
        page += 1

    analysis = analyze_products(
        all_products,
        expected_skus=expected_skus,
        expected_page_origin=args.expected_page_origin,
    )
    report = {
        "endpoint": url,
        "request_format": args.request_format,
        "eligible_count": count,
        "max_pages": max_pages,
        "pages_fetched": page if all_products or page == 1 else page - 1,
        "limit": args.limit,
        **analysis,
    }

    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("EMALLS PREFLIGHT (read-only)")
        print(f"  endpoint:              {report['endpoint']}")
        print(f"  request_format:        {report['request_format']}")
        print(f"  eligible_count:        {report['eligible_count']}")
        print(f"  max_pages:             {report['max_pages']}")
        print(f"  pages_fetched:         {report['pages_fetched']}")
        print(f"  fetched_rows:          {report['fetched']}")
        print(f"  duplicate_page_unique: {report['duplicate_page_unique'] or 'none'}")
        print(f"  missing_page_url:      {report['missing_page_url']}")
        print(f"  missing_image:         {report['missing_image']}")
        print(f"  placeholder_image:     {report['placeholder_image']}")
        print(f"  non_absolute_image:    {report['non_absolute_image']}")
        print(f"  private_host_image:    {report['private_host_image']}")
        print(f"  invalid_price:         {report['invalid_price']}")
        print(f"  missing_title:         {report['missing_title']}")
        print(f"  malformed_specs:       {report['malformed_specs']}")
        print(f"  sku_spec_missing:      {report['sku_spec_missing']}")
        print(f"  sku_spec_mismatch:     {report['sku_spec_mismatch']}")
        print(f"  non_https_public_urls: {report['non_https_public_urls']}")
        print(f"  page_url_host_mismatch:{report['page_url_host_mismatch']}")
        print("  samples:")
        for sample in report["samples"]:
            print(f"    - {sample}")

    problems = (
        bool(report["duplicate_page_unique"])
        or report["missing_page_url"]
        or report["missing_image"]
        or report["placeholder_image"]
        or report["non_absolute_image"]
        or report["private_host_image"]
        or report["invalid_price"]
        or report["missing_title"]
        or report["malformed_specs"]
        or report["sku_spec_missing"]
        or report["sku_spec_mismatch"]
        or report["page_url_host_mismatch"]
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
