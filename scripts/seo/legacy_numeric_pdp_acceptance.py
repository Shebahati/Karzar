#!/usr/bin/env python3
"""Post-deploy read-only acceptance for legacy numeric PDP HTTP 301 contract (Wave 2B-1)."""
from __future__ import annotations

import argparse
import csv
import html.parser
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterable

MAX_REDIRECT_HOPS = 10
USER_AGENT = "Karzar-Legacy-PDP-Acceptance/1.0"
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

FetchFn = Callable[[str, float], tuple[int, dict[str, str], bytes]]


@dataclass
class ApiProduct:
    status: int
    slug: str | None
    error_class: str = ""

CLASSIFICATION_BUCKETS = (
    "HISTORICAL_NOT_FOUND",
    "NO_SLUG",
    "NUMERIC_CANONICAL",
    "REQUIRED_301",
    "OTHER",
)


@dataclass
class RedirectProbe:
    status: int
    location: str
    hops: list[str] = field(default_factory=list)
    final_url: str = ""
    final_status: int = 0
    canonical: str = ""
    redirect_loop: bool = False
    bad_redirect_chain: bool = False
    missing_location: bool = False
    unsupported_redirect: bool = False


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class CanonicalLinkParser(html.parser.HTMLParser):
    """Extract canonical href regardless of rel/href attribute order."""

    def __init__(self) -> None:
        super().__init__()
        self.canonical: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        rel = attr_map.get("rel", "").lower()
        if "canonical" not in rel.split():
            return
        href = attr_map.get("href", "").strip()
        if href:
            self.canonical = href


def default_manual_fetch(url: str, timeout: float) -> tuple[int, dict[str, str], bytes]:
    opener = urllib.request.build_opener(NoRedirectHandler())
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=timeout) as resp:
            headers = {k: v for k, v in resp.headers.items()}
            return resp.status, headers, resp.read()
    except urllib.error.HTTPError as exc:
        headers = {k: v for k, v in exc.headers.items()}
        body = exc.read() if exc.fp is not None else b""
        return exc.code, headers, body
    except Exception:
        return 0, {}, b""


def fetch_api_product(api_base: str, product_id: str, timeout: float = 30.0) -> ApiProduct:
    url = f"{api_base.rstrip('/')}/products/{product_id}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            slug = (data.get("slug") or "").strip() or None
            return ApiProduct(status=resp.status, slug=slug)
    except urllib.error.HTTPError as exc:
        return ApiProduct(status=exc.code, slug=None)
    except Exception as exc:
        return ApiProduct(status=0, slug=None, error_class=exc.__class__.__name__)


def expected_slug_url(site: str, slug: str) -> str:
    segment = urllib.parse.quote(slug, safe="")
    return f"{site.rstrip('/')}/product/{segment}"


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc.lower(), path, "", parsed.query, ""),
    )


def extract_canonical(html: str) -> str:
    parser = CanonicalLinkParser()
    try:
        parser.feed(html)
    except html.parser.HTMLParseError:
        return ""
    return parser.canonical


def header_location(headers: dict[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == "location":
            return value.strip()
    return ""


def absolute_url(base: str, location: str) -> str:
    if not location:
        return ""
    return urllib.parse.urljoin(base, location)


def classification_accounting_ok(counts: dict[str, int]) -> bool:
    total = counts.get("TOTAL_INPUT", 0)
    classified = sum(counts.get(bucket, 0) for bucket in CLASSIFICATION_BUCKETS)
    return classified == total


def walk_redirect_chain(
    start_url: str,
    timeout: float,
    fetch: FetchFn | None = None,
) -> RedirectProbe:
    """Manual redirect traversal; never auto-follows."""
    fetcher = fetch or default_manual_fetch
    probe = RedirectProbe(status=0, location="", hops=[start_url])
    current = start_url
    visited = {normalize_url(start_url)}
    redirect_steps = 0
    first = True

    while True:
        status, headers, body = fetcher(current, timeout)
        if first:
            probe.status = status
            probe.location = header_location(headers)
            first = False

        if status in REDIRECT_STATUSES:
            redirect_steps += 1
            if redirect_steps > MAX_REDIRECT_HOPS:
                probe.bad_redirect_chain = True
                probe.final_url = current
                probe.final_status = status
                return probe

            loc_raw = header_location(headers)
            if not loc_raw:
                probe.missing_location = True
                probe.final_url = current
                probe.final_status = status
                return probe

            next_url = absolute_url(current, loc_raw)
            norm_next = normalize_url(next_url)
            if norm_next in visited:
                probe.redirect_loop = True
                probe.final_url = current
                probe.final_status = status
                return probe

            visited.add(norm_next)
            probe.hops.append(next_url)
            current = next_url
            continue

        if 300 <= status < 400:
            probe.unsupported_redirect = True
            probe.final_url = current
            probe.final_status = status
            return probe

        probe.final_url = current
        probe.final_status = status
        if status == 200 and body:
            probe.canonical = extract_canonical(body.decode("utf-8", errors="replace"))
        return probe


def probe_numeric_redirect(
    site: str,
    product_id: str,
    timeout: float = 30.0,
    fetch: FetchFn | None = None,
) -> RedirectProbe:
    start = f"{site.rstrip('/')}/product/{product_id}"
    return walk_redirect_chain(start, timeout, fetch=fetch)


def classify_api(product_id: str, api: ApiProduct) -> str:
    if api.status == 404:
        return "HISTORICAL_NOT_FOUND"
    if api.status != 200:
        return "OTHER"
    if not api.slug:
        return "NO_SLUG"
    if api.slug == product_id:
        return "NUMERIC_CANONICAL"
    return "REQUIRED_301"


def verify_required_301(site: str, product_id: str, slug: str, probe: RedirectProbe) -> list[str]:
    errors: list[str] = []
    expected = expected_slug_url(site, slug)
    if probe.status != 301:
        errors.append("BAD_STATUS")

    loc = absolute_url(f"{site}/product/{product_id}", probe.location)
    if probe.missing_location or normalize_url(loc) != normalize_url(expected):
        errors.append("BAD_LOCATION")

    if probe.redirect_loop or len({normalize_url(h) for h in probe.hops}) != len(probe.hops):
        errors.append("REDIRECT_LOOP")

    if probe.bad_redirect_chain:
        errors.append("BAD_REDIRECT_CHAIN")

    if probe.unsupported_redirect:
        errors.append("BAD_STATUS")

    if normalize_url(probe.final_url) != normalize_url(expected):
        errors.append("BAD_FINAL_URL")

    if probe.final_status != 200:
        errors.append("BAD_FINAL_STATUS")

    if normalize_url(probe.canonical) != normalize_url(expected):
        errors.append("BAD_FINAL_CANONICAL")

    return errors


@dataclass
class AcceptanceResult:
    counts: dict[str, int]
    other_details: list[dict[str, str | int]]


def run_acceptance(
    rows: Iterable[dict[str, str]],
    site: str,
    api_base: str,
    id_column: str = "numeric_id",
) -> AcceptanceResult:
    counts: dict[str, int] = {
        "TOTAL_INPUT": 0,
        "HISTORICAL_NOT_FOUND": 0,
        "NO_SLUG": 0,
        "NUMERIC_CANONICAL": 0,
        "REQUIRED_301": 0,
        "OTHER": 0,
        "HTTP_301_OK": 0,
        "BAD_STATUS": 0,
        "BAD_LOCATION": 0,
        "REDIRECT_LOOP": 0,
        "BAD_FINAL_STATUS": 0,
        "BAD_FINAL_CANONICAL": 0,
        "BAD_REDIRECT_CHAIN": 0,
        "BAD_FINAL_URL": 0,
        "CLASSIFICATION_ACCOUNTING_ERROR": 0,
    }
    other_details: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for row in rows:
        pid = (row.get(id_column) or row.get("product_identifier") or "").strip()
        if not pid or pid in seen:
            continue
        seen.add(pid)
        counts["TOTAL_INPUT"] += 1
        api = fetch_api_product(api_base, pid)
        bucket = classify_api(pid, api)
        counts[bucket] = counts.get(bucket, 0) + 1
        if bucket == "OTHER":
            err = api.error_class or ("http_error" if api.status else "unknown")
            other_details.append(
                {
                    "product_id": pid,
                    "api_status": api.status,
                    "classification": bucket,
                    "error_class": err,
                }
            )
            continue
        if bucket != "REQUIRED_301":
            continue
        probe = probe_numeric_redirect(site, pid)
        errs = verify_required_301(site, pid, api.slug or "", probe)
        if not errs:
            counts["HTTP_301_OK"] += 1
        for e in errs:
            counts[e] = counts.get(e, 0) + 1
    if not classification_accounting_ok(counts):
        counts["CLASSIFICATION_ACCOUNTING_ERROR"] = 1
    return AcceptanceResult(counts=counts, other_details=other_details)


def hard_pass(counts: dict[str, int]) -> bool:
    required = counts.get("REQUIRED_301", 0)
    return (
        counts.get("OTHER", 0) == 0
        and counts.get("CLASSIFICATION_ACCOUNTING_ERROR", 0) == 0
        and counts.get("HTTP_301_OK", 0) == required
        and counts.get("BAD_STATUS", 0) == 0
        and counts.get("BAD_LOCATION", 0) == 0
        and counts.get("REDIRECT_LOOP", 0) == 0
        and counts.get("BAD_FINAL_STATUS", 0) == 0
        and counts.get("BAD_FINAL_CANONICAL", 0) == 0
        and counts.get("BAD_REDIRECT_CHAIN", 0) == 0
        and counts.get("BAD_FINAL_URL", 0) == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy numeric PDP 301 acceptance gate")
    parser.add_argument("csv_path", help="legacy_96_preflight.csv or cohort CSV")
    parser.add_argument(
        "--site",
        default=os.environ.get("KARZAR_ACCEPTANCE_SITE", "").strip(),
        help="Public storefront origin (or set KARZAR_ACCEPTANCE_SITE)",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("KARZAR_ACCEPTANCE_API_BASE", "").strip(),
        help="Public catalog API base (or set KARZAR_ACCEPTANCE_API_BASE)",
    )
    args = parser.parse_args()
    if not args.site or not args.api_base:
        parser.error("--site and --api-base are required (or set KARZAR_ACCEPTANCE_SITE / KARZAR_ACCEPTANCE_API_BASE)")
    with open(args.csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    result = run_acceptance(rows, args.site, args.api_base)
    for detail in result.other_details:
        print(json.dumps({"other_row": detail}), file=sys.stderr)
    print(json.dumps(result.counts, indent=2))
    return 0 if hard_pass(result.counts) else 1


if __name__ == "__main__":
    sys.exit(main())
