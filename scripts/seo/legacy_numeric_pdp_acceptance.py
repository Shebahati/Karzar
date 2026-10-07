#!/usr/bin/env python3
"""Post-deploy read-only acceptance for legacy numeric PDP HTTP 301 contract (Wave 2B-1)."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable

MAX_REDIRECT_HOPS = 10
USER_AGENT = "Karzar-Legacy-PDP-Acceptance/1.0"


@dataclass
class ApiProduct:
    status: int
    slug: str | None


@dataclass
class RedirectProbe:
    status: int
    location: str
    hops: list[str] = field(default_factory=list)
    final_url: str = ""
    final_status: int = 0
    canonical: str = ""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def fetch_api_product(api_base: str, product_id: str, timeout: float = 30.0) -> ApiProduct:
    url = f"{api_base.rstrip('/')}/products/{product_id}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            slug = (data.get("slug") or "").strip() or None
            return ApiProduct(status=resp.status, slug=slug)
    except urllib.error.HTTPError as exc:
        return ApiProduct(status=exc.code, slug=None)
    except Exception:
        return ApiProduct(status=0, slug=None)


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
    m = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
        html,
        re.I,
    )
    return m.group(1).strip() if m else ""


def absolute_url(base: str, location: str) -> str:
    if not location:
        return ""
    if urllib.parse.urlparse(location).netloc:
        return location
    return urllib.parse.urljoin(base if base.endswith("/") else base + "/", location.lstrip("/"))


def follow_redirect_chain(start_url: str, timeout: float) -> RedirectProbe:
    probe = RedirectProbe(status=0, location="", hops=[start_url])
    current = start_url
    for _ in range(MAX_REDIRECT_HOPS):
        req = urllib.request.Request(current, method="GET", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                probe.final_url = resp.url
                probe.final_status = resp.status
                html = resp.read().decode("utf-8", errors="replace")
                probe.canonical = extract_canonical(html)
                return probe
        except urllib.error.HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308):
                probe.final_status = exc.code
                return probe
            loc = absolute_url(current, exc.headers.get("Location", ""))
            if not loc:
                probe.final_status = exc.code
                return probe
            if loc in probe.hops:
                probe.final_status = exc.code
                probe.location = loc
                return probe
            probe.hops.append(loc)
            current = loc
    probe.final_status = 0
    return probe


def probe_numeric_redirect(site: str, product_id: str, timeout: float = 30.0) -> RedirectProbe:
    start = f"{site.rstrip('/')}/product/{product_id}"
    req = urllib.request.Request(start, method="GET", headers={"User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(NoRedirectHandler())
    probe = RedirectProbe(status=0, location="", hops=[start])
    try:
        with opener.open(req, timeout=timeout) as resp:
            probe.status = resp.status
            probe.final_url = resp.url
            probe.final_status = resp.status
            html = resp.read().decode("utf-8", errors="replace")
            probe.canonical = extract_canonical(html)
            return probe
    except urllib.error.HTTPError as exc:
        probe.status = exc.code
        probe.location = exc.headers.get("Location", "")
        if exc.code in (301, 302, 303, 307, 308):
            first_target = absolute_url(start, probe.location)
            tail = follow_redirect_chain(first_target, timeout=timeout)
            probe.hops = [start] + tail.hops
            probe.final_url = tail.final_url
            probe.final_status = tail.final_status
            probe.canonical = tail.canonical
        return probe
    except Exception:
        probe.status = 0
        return probe


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
    if normalize_url(loc) != normalize_url(expected):
        errors.append("BAD_LOCATION")
    if len(probe.hops) != len(set(probe.hops)):
        errors.append("REDIRECT_LOOP")
    if len(probe.hops) > MAX_REDIRECT_HOPS:
        errors.append("BAD_REDIRECT_CHAIN")
    if probe.final_status != 200:
        errors.append("BAD_FINAL_STATUS")
    if normalize_url(probe.canonical) != normalize_url(expected):
        errors.append("BAD_FINAL_CANONICAL")
    return errors


def run_acceptance(
    rows: Iterable[dict[str, str]],
    site: str,
    api_base: str,
    id_column: str = "numeric_id",
) -> dict[str, int]:
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
    }
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
        if bucket != "REQUIRED_301":
            continue
        probe = probe_numeric_redirect(site, pid)
        errs = verify_required_301(site, pid, api.slug or "", probe)
        if not errs:
            counts["HTTP_301_OK"] += 1
        for e in errs:
            counts[e] = counts.get(e, 0) + 1
    return counts


def hard_pass(counts: dict[str, int]) -> bool:
    required = counts.get("REQUIRED_301", 0)
    return (
        counts.get("HTTP_301_OK", 0) == required
        and counts.get("BAD_STATUS", 0) == 0
        and counts.get("BAD_LOCATION", 0) == 0
        and counts.get("REDIRECT_LOOP", 0) == 0
        and counts.get("BAD_FINAL_STATUS", 0) == 0
        and counts.get("BAD_FINAL_CANONICAL", 0) == 0
        and counts.get("BAD_REDIRECT_CHAIN", 0) == 0
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
    counts = run_acceptance(rows, args.site, args.api_base)
    print(json.dumps(counts, indent=2))
    return 0 if hard_pass(counts) else 1


if __name__ == "__main__":
    sys.exit(main())
