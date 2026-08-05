"""INSIZE / TOSAG candidate discovery (IMG-02B-03)."""

from __future__ import annotations

import html as html_lib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote

from .. import LANE_SPECS
from ..output import stable_candidate_id
from ..transport import DiscoveryError, HostThrottledFetcher, host_allowed

TOSAG_BASE = "https://www.tosag.ch"
ALLOWED = frozenset({"www.tosag.ch", "tosag.ch"})

SKIP_LINK_PARTS = (
    "homepage",
    "Register",
    "Forgot-password",
    "Impressum",
    "Privacy",
    "rss.xml",
    "templates/",
    "plugins/",
)

PRODUCTBOX_ANCHOR_RE = re.compile(
    r'class="productbox-title[^"]*"[^>]*>\s*<a href="(https://www\.tosag\.ch/[^"?#]+)"',
    re.IGNORECASE | re.DOTALL,
)
LG_IMAGE_RE = re.compile(
    r"https://www\.tosag\.ch/media/image/product/\d+/lg/[^\"'\s>]+\.jpg",
    re.IGNORECASE,
)
MD_IMAGE_RE = re.compile(
    r"https://www\.tosag\.ch/media/image/product/\d+/md/[^\"'\s>]+\.jpg",
    re.IGNORECASE,
)


def clean_html_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", html_lib.unescape(text))


def sku_token_present(text: str, sku: str) -> bool:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(sku)}(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    return bool(pattern.search(text or ""))


def sku_search_variants(sku: str) -> list[str]:
    """High-precision search variants; confirmation still requires catalog SKU exactly."""
    variants: list[str] = []
    for candidate in (sku, sku.upper(), sku.lower()):
        if candidate and candidate not in variants:
            variants.append(candidate)
    parts = sku.split("-")
    if len(parts) == 2 and all(parts):
        reversed_sku = f"{parts[1]}-{parts[0]}"
        if reversed_sku not in variants:
            variants.append(reversed_sku)
    return variants


def extract_search_product_links(html: str) -> list[str]:
    links: list[str] = []
    for block in re.split(r'id="result-wrapper_buy_form_', html or "")[1:]:
        if "Insize" not in block and "INSIZE" not in block:
            continue
        match = PRODUCTBOX_ANCHOR_RE.search(block)
        if match:
            links.append(match.group(1))
    if not links:
        for match in PRODUCTBOX_ANCHOR_RE.finditer(html or ""):
            links.append(match.group(1))
    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        if any(part in link for part in SKIP_LINK_PARTS):
            continue
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped[:8]


def extract_primary_image(html: str) -> str | None:
    images = LG_IMAGE_RE.findall(html or "")
    if not images:
        images = MD_IMAGE_RE.findall(html or "")
    if not images:
        return None
    unique = sorted(set(images), key=lambda url: ("~2" in url, url))
    return unique[0]


def is_insize_detail_page(html: str) -> bool:
    if re.search(r"Manufacturers:\s*</[^>]+>\s*Insize", html or "", re.IGNORECASE):
        return True
    if re.search(r"Manufacturers:.*?Insize", clean_html_text(html or ""), re.IGNORECASE):
        return True
    if re.search(r'itemprop="brand"[^>]*>.*?Insize', html or "", re.IGNORECASE | re.DOTALL):
        return True
    return bool(re.search(r"\bINSIZE\b", html or "") and "Measuring" in (html or ""))


def sku_confirmed_on_detail(html: str, sku: str) -> bool:
    escaped = re.escape(sku)
    patterns = [
        rf">\s*{escaped}\s*-",
        rf"(?:^|[\s\-/>])\s*{escaped}\s*-",
        rf"SKU:\s*{escaped}\b",
        rf'data-sku-\d+="{escaped}"',
        rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])",
    ]
    if any(re.search(pattern, html or "", re.IGNORECASE) for pattern in patterns):
        return True
    text = clean_html_text(html or "")
    return bool(re.search(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", text, re.IGNORECASE))


def _search_page_has_product_markup(html: str) -> bool:
    low = (html or "").casefold()
    return "productbox" in low or "result-wrapper_buy_form_" in low or "media/image/product" in low


def _detail_has_product_media_markup(html: str) -> bool:
    low = (html or "").casefold()
    return "media/image/product" in low or "product-image" in low or 'property="og:image"' in low


def _resolve_one(
    item: dict[str, str],
    *,
    fetcher: HostThrottledFetcher,
    parser_drift: list[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (candidate, rejected). Exactly one is non-None."""
    spec = LANE_SPECS["insize"]
    sku = (item.get("sku") or "").strip()
    product_id = (item.get("product_id") or "").strip()
    product_name = item.get("product_name") or ""

    def reject(code: str, detail: str) -> tuple[None, dict[str, Any]]:
        return None, {
            "lane_id": spec["lane_id"],
            "product_id": product_id,
            "sku": sku,
            "product_name": product_name,
            "reason_code": code,
            "reason_detail": detail,
            "notes": "",
        }

    candidates: list[str] = []
    seen_links: set[str] = set()
    search_failed = 0
    search_ok = 0
    for query in sku_search_variants(sku):
        search_url = f"{TOSAG_BASE}/?suche={quote(query)}&lang=eng"
        try:
            status, body, _ctype, _final = fetcher.get(
                search_url, fail_code="search_fetch_failed"
            )
            if status != 200:
                search_failed += 1
                continue
            search_html = body.decode("utf-8", errors="replace")
            search_ok += 1
        except DiscoveryError:
            search_failed += 1
            continue

        links = extract_search_product_links(search_html)
        if not links and _search_page_has_product_markup(search_html):
            if "productbox-title" not in search_html.casefold():
                parser_drift.append(f"search_markup:{sku}")
        for link in links:
            if not host_allowed(link, ALLOWED):
                continue
            if link not in seen_links:
                seen_links.add(link)
                candidates.append(link)
        if candidates:
            break

    if not candidates:
        if search_failed and not search_ok:
            return reject("fetch_search_failed", "TOSAG search page could not be fetched")
        return reject("no_product_candidates", "no TOSAG product links for SKU search")

    last_issue = "sku_not_on_detail_page"
    for detail_url in candidates:
        try:
            status, body, _ctype, final = fetcher.get(
                f"{detail_url}?lang=eng", fail_code="detail_fetch_failed"
            )
            if status != 200:
                last_issue = "fetch_detail_failed"
                continue
            detail_html = body.decode("utf-8", errors="replace")
        except DiscoveryError:
            last_issue = "fetch_detail_failed"
            continue

        if not is_insize_detail_page(detail_html):
            last_issue = "not_insize_manufacturer"
            continue
        if not sku_confirmed_on_detail(detail_html, sku):
            last_issue = "sku_not_on_detail_page"
            continue
        image_url = extract_primary_image(detail_html)
        if not image_url:
            if _detail_has_product_media_markup(detail_html):
                parser_drift.append(f"detail_image:{sku}")
            last_issue = "no_product_image"
            continue
        if not host_allowed(image_url, ALLOWED):
            last_issue = "image_host_rejected"
            continue

        final_detail = final or detail_url
        cand = {
            "schema_version": "1",
            "task_id": "IMG-02B",
            "lane_id": spec["lane_id"],
            "product_id": product_id,
            "product_key": item.get("product_key") or f"product_id:{product_id}",
            "sku": sku,
            "product_name": product_name,
            "brand_key": "insize",
            "work_type": item.get("work_type") or "",
            "work_reasons": item.get("work_reasons") or "",
            "priority": item.get("priority") or "",
            "source_adapter": spec["adapter"],
            "source_class": spec["source_class"],
            "source_detail_url": final_detail,
            "source_image_url": image_url,
            "source_image_index": "0",
            "candidate_discovery_method": "tosag_sku_search",
            "candidate_match_basis": "exact_sku",
            "manufacturer_evidence": "tosag_insize_manufacturer",
            "sku_evidence": f"detail_sku:{sku}",
            "confidence": "very_high",
            "rights_status": "review_required",
            "apply_status": "not_started",
            "discovery_status": "candidate_ready",
            "notes": "",
            "detail_url": final_detail,
            "image_url": image_url,
            "brand": "INSIZE",
        }
        cand["_candidate_id"] = stable_candidate_id(
            [spec["lane_id"], product_id, sku, final_detail, image_url]
        )
        return cand, None

    return reject(last_issue, last_issue.replace("_", " "))


def discover_insize_candidates(
    work_items: list[dict[str, str]],
    *,
    fetcher: HostThrottledFetcher,
    concurrency: int = 3,
    limit: int | None = None,
) -> dict[str, Any]:
    if limit is not None:
        work_items = work_items[:limit]

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    parser_drift: list[str] = []
    drift_lock_notes: list[str] = []

    def one(item: dict[str, str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
        local_drift: list[str] = []
        cand, rej = _resolve_one(item, fetcher=fetcher, parser_drift=local_drift)
        return cand, rej, local_drift

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futs = {pool.submit(one, item): item for item in work_items}
        for fut in as_completed(futs):
            cand, rej, local_drift = fut.result()
            drift_lock_notes.extend(local_drift)
            if cand is not None:
                candidates.append(cand)
            elif rej is not None:
                rejected.append(rej)

    parser_drift.extend(drift_lock_notes)
    candidates.sort(
        key=lambda r: ((r.get("sku") or "").casefold(), int(r.get("product_id") or 0))
    )
    rejected.sort(
        key=lambda r: ((r.get("sku") or "").casefold(), int(r.get("product_id") or 0))
    )

    return {
        "candidates": candidates,
        "rejected": rejected,
        "manual": manual,
        "stats": {
            "requested": len(work_items),
            "accepted_candidates": len(candidates),
            "rejected": len(rejected),
            "manual_review": len(manual),
            "parser_drift": len(parser_drift),
            "parser_drift_samples": parser_drift[:20],
        },
    }
