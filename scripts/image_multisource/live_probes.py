"""Optional live calibration probes for known hosts (stdlib urllib only)."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .matching import host_allowed, host_of
from .registry import SourceDeclaration
from .robots import classify_robots_text

USER_AGENT = "KarzarImageMultisource/0.1 (+calibration; local-ops)"


def _fetch(url: str, *, timeout: float = 20.0) -> tuple[int, str, bytes]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — host allowlisted by caller
        final = resp.geturl()
        data = resp.read(2_000_000)
        return int(getattr(resp, "status", 200) or 200), final, data


def fetch_robots_for_source(source: SourceDeclaration, *, delay: float = 0.8) -> str:
    host = source.allowed_page_hosts[0]
    url = f"https://{host}/robots.txt"
    time.sleep(delay)
    try:
        _status, _final, data = _fetch(url)
        return data.decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError):
        return "User-agent: *\nDisallow:\n"


def probe_insize_tosag(source: SourceDeclaration, row: dict[str, str], *, delay: float = 0.8) -> dict[str, Any]:
    sku = (row.get("sku") or "").strip()
    pid = (row.get("product_id") or "").strip()
    search = f"https://www.tosag.ch/search?q={quote(sku)}"
    time.sleep(delay)
    try:
        status, final, data = _fetch(search)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "product_id": pid,
            "sku": sku,
            "status": "fetch_error",
            "page_identity_ok": False,
            "exact_sku_ok": False,
            "redirect_ok": host_allowed(search, source.allowed_page_hosts),
            "generic_category": False,
            "parser_drift": False,
            "asset_host_ok": False,
            "notes": f"error:{type(exc).__name__}",
        }
    text = data.decode("utf-8", errors="replace")
    redirect_ok = host_allowed(final, source.allowed_page_hosts)
    sku_ok = sku.casefold() in text.casefold()
    # Very light structure check: search page should mention product-ish anchors.
    structure_ok = ("product" in text.casefold()) or ("artikel" in text.casefold()) or sku_ok
    return {
        "product_id": pid,
        "sku": sku,
        "status": "probed",
        "http_status": status,
        "final_url": final,
        "page_identity_ok": structure_ok and redirect_ok,
        "exact_sku_ok": sku_ok and redirect_ok,
        "redirect_ok": redirect_ok,
        "generic_category": False,
        "parser_drift": (not structure_ok) and redirect_ok,
        "asset_host_ok": False,
        "notes": f"search_probe;final_host={host_of(final)}",
    }


def probe_official_homepage(
    source: SourceDeclaration, row: dict[str, str], *, delay: float = 0.8
) -> dict[str, Any]:
    """Conservative probe: homepage + sku token search only (no invented PDP URLs)."""
    sku = (row.get("sku") or "").strip()
    pid = (row.get("product_id") or "").strip()
    host = source.allowed_page_hosts[0]
    url = f"https://{host}/"
    time.sleep(delay)
    try:
        status, final, data = _fetch(url)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "product_id": pid,
            "sku": sku,
            "status": "fetch_error",
            "page_identity_ok": False,
            "exact_sku_ok": False,
            "redirect_ok": False,
            "generic_category": False,
            "parser_drift": True,
            "asset_host_ok": False,
            "notes": f"error:{type(exc).__name__}",
        }
    text = data.decode("utf-8", errors="replace")
    redirect_ok = host_allowed(final, source.allowed_page_hosts)
    # Homepage cannot confirm exact SKU — mark exact_sku_ok false (fail closed).
    has_nav = bool(re.search(r"<html|<!doctype", text, flags=re.I))
    return {
        "product_id": pid,
        "sku": sku,
        "status": "probed_homepage_only",
        "http_status": status,
        "final_url": final,
        "page_identity_ok": has_nav and redirect_ok,
        "exact_sku_ok": False,
        "redirect_ok": redirect_ok,
        "generic_category": False,
        "parser_drift": not has_nav,
        "asset_host_ok": False,
        "notes": "no governed PDP mapping in calibration; exact SKU not confirmed on homepage",
    }


def build_live_probe_map(sources: list[SourceDeclaration], *, delay: float = 0.8) -> dict[str, Any]:
    robots_cache: dict[str, str] = {}
    probes: dict[str, Any] = {}

    def wrap(source: SourceDeclaration, fn):
        def _inner(src: SourceDeclaration, row: dict[str, str]) -> dict[str, Any]:
            return fn(src, row, delay=delay)

        return _inner

    for source in sources:
        if source.authorization_status == "unknown":
            continue
        if source.source_id not in robots_cache:
            robots_cache[source.source_id] = fetch_robots_for_source(source, delay=delay)
        if source.source_id == "insize_tosag":
            probes[source.source_id] = wrap(source, probe_insize_tosag)
        else:
            probes[source.source_id] = wrap(source, probe_official_homepage)
    probes["_robots_txt"] = robots_cache
    return probes


def robots_status_for(source_id: str, robots_cache: dict[str, str], source: SourceDeclaration) -> dict[str, str]:
    text = robots_cache.get(source_id, "User-agent: *\nDisallow:\n")
    host = source.allowed_page_hosts[0]
    return classify_robots_text(
        text,
        user_agent=USER_AGENT,
        url=f"https://{host}/",
    )
