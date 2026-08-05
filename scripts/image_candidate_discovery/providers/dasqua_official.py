"""Dasqua official candidate discovery (IMG-02B-02)."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit


def to_ascii_url(url: str) -> str:
    """Percent-encode non-ASCII path/query so urllib Request accepts the URL."""
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc.encode("idna").decode("ascii") if parts.netloc else parts.netloc,
            quote(unquote(parts.path), safe="/%:@"),
            quote(unquote(parts.query), safe="=&%:@,+"),
            parts.fragment,
        )
    )
from .. import LANE_SPECS, CandidateDiscoveryError
from ..output import stable_candidate_id
from ..transport import DiscoveryError, HostThrottledFetcher, host_allowed

SITE = "https://www.dasquatools.com"
SITEMAPS = [
    f"{SITE}/product_sitemap.xml",
    f"{SITE}/product_2_sitemap.xml",
    f"{SITE}/product_3_sitemap.xml",
]
PAGE_ALLOWED = frozenset({"www.dasquatools.com", "dasquatools.com"})
# Official image assets are on GlobalSo CDNs linked from dasquatools.com pages.
IMAGE_ALLOWED = PAGE_ALLOWED | frozenset(
    {"cdn.globalso.com", *[f"ecdn{i}.globalso.com" for i in range(1, 16)]}
)
ALLOWED = IMAGE_ALLOWED  # fetcher may retrieve both pages and (later) images

CODE_RE = re.compile(r"\b(\d{3,5}-\d{3,5})(?:-[A-Za-z0-9]+|[A-Za-z])?\b")
TITLE_DASQUA_RE = re.compile(
    r"Dasqua\s+(\d{3,5}-\d{3,5})(?:-[A-Za-z0-9]+|[A-Za-z])?\b",
    re.IGNORECASE,
)
ITEM_NUMBER_RE = re.compile(
    r"(?:Item\s*Number|Item\s*No\.?|Order\s*No\.?|Art\.?\s*No\.?|Product\s*No\.?)\s*[:：]\s*"
    r"(\d{3,5}-\d{3,5})(?:-[A-Za-z0-9]+|[A-Za-z])?\b",
    re.IGNORECASE,
)
OG_IMAGE_RE = re.compile(
    r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']|'
    r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
    re.IGNORECASE,
)
IMAGE_PRODUCT_RE = re.compile(
    r"https://[^\"'\s]+image_product[^\"'\s]+\.(?:png|jpg|jpeg|webp)",
    re.IGNORECASE,
)


def normalize_dasqua_code(raw: str) -> str:
    text = (raw or "").strip()
    m = re.match(r"^(\d{3,5}-\d{3,5})", text)
    return m.group(1) if m else text


def extract_primary_code(title: str, url: str, html: str = "") -> str | None:
    """Prefer title/URL identity; only use HTML item labels when they corroborate."""
    path = unquote(urlparse(url).path or "")
    title_text = title or ""

    m = TITLE_DASQUA_RE.search(title_text)
    if m:
        return normalize_dasqua_code(m.group(1))

    m2 = re.search(r"dasqua-(\d{3,5}-\d{3,5})", path, re.IGNORECASE)
    if m2:
        return normalize_dasqua_code(m2.group(1))

    title_codes = [normalize_dasqua_code(c) for c in CODE_RE.findall(title_text)]
    title_codes = list(dict.fromkeys(title_codes))
    if len(title_codes) == 1:
        return title_codes[0]

    path_codes = [normalize_dasqua_code(c) for c in CODE_RE.findall(path)]
    path_codes = list(dict.fromkeys(path_codes))
    if len(path_codes) == 1:
        return path_codes[0]

    labeled = [normalize_dasqua_code(c) for c in ITEM_NUMBER_RE.findall(html or "")]
    labeled = list(dict.fromkeys(labeled))
    if labeled:
        path_l = path.casefold()
        title_l = title_text.casefold()
        for code in labeled:
            if code.casefold() in path_l or code in title_text or code.casefold() in title_l:
                return code
        if len(labeled) == 1:
            return labeled[0]
    return None


def extract_image(html: str) -> str | None:
    m = OG_IMAGE_RE.search(html or "")
    if m:
        og = (m.group(1) or m.group(2) or "").strip()
        if og and host_allowed(og, IMAGE_ALLOWED) and "image_product" in og:
            return og
        if og and host_allowed(og, IMAGE_ALLOWED):
            return og
    m2 = IMAGE_PRODUCT_RE.search(html or "")
    if m2 and host_allowed(m2.group(0), IMAGE_ALLOWED):
        return m2.group(0)
    return None


def _parse_sitemap(xml_text: str) -> list[str]:
    urls: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise CandidateDiscoveryError("dasqua", f"sitemap parse error: {exc}") from exc
    for loc in root.iter():
        if loc.tag.endswith("loc") and loc.text:
            url = loc.text.strip()
            if host_allowed(url, PAGE_ALLOWED):
                urls.append(url)
    return urls


def discover_dasqua_candidates(
    work_items: list[dict[str, str]],
    *,
    fetcher: HostThrottledFetcher,
    concurrency: int = 3,
    limit: int | None = None,
) -> dict[str, Any]:
    spec = LANE_SPECS["dasqua"]
    if limit is not None:
        work_items = work_items[:limit]

    # Load sitemap product URLs
    page_urls: list[str] = []
    seen_u: set[str] = set()
    for sm in SITEMAPS:
        try:
            status, body, _ctype, _final = fetcher.get(sm, fail_code="sitemap_fetch_failed")
            if status != 200:
                continue
            xml_text = body.decode("utf-8", errors="replace")
        except DiscoveryError:
            continue
        for url in _parse_sitemap(xml_text):
            if url not in seen_u:
                seen_u.add(url)
                page_urls.append(url)
    page_urls.sort()

    needed_codes = {normalize_dasqua_code((i.get("sku") or "").strip()) for i in work_items}
    # Prefer sitemap URLs that already embed a needed item code.
    preferred: list[str] = []
    rest: list[str] = []
    for url in page_urls:
        path = unquote(urlparse(url).path or "").casefold()
        if any(code.casefold() in path for code in needed_codes if code):
            preferred.append(url)
        else:
            rest.append(url)
    ordered_urls = preferred + rest

    # Crawl product pages (stop early once every requested code is observed).
    extracts: list[dict[str, str]] = []
    found_codes: set[str] = set()

    def one(url: str) -> dict[str, str] | None:
        try:
            status, body, _ctype, final = fetcher.get(
                to_ascii_url(url), fail_code="page_fetch_failed"
            )
            if status != 200:
                return None
            html = body.decode("utf-8", errors="replace")
        except (DiscoveryError, UnicodeEncodeError, UnicodeError):
            return None
        title_m = re.search(r"<title>([^<]+)", html, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else ""
        code = extract_primary_code(title, url, html)
        image = extract_image(html)
        if not code or not image:
            return None
        if not host_allowed(image, IMAGE_ALLOWED):
            return None
        if "dasqua" not in html.casefold() and "dasqua" not in title.casefold():
            return None
        return {
            "code": code,
            "detail_url": final or url,
            "image_url": image,
            "title": title,
        }

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        # Submit in waves so we can stop once needed codes are covered.
        batch_size = max(concurrency * 8, 24)
        idx = 0
        while idx < len(ordered_urls):
            if needed_codes and needed_codes.issubset(found_codes):
                break
            batch = ordered_urls[idx : idx + batch_size]
            idx += batch_size
            print(
                json.dumps(
                    {
                        "phase": "progress",
                        "lane": "dasqua",
                        "urls_done": min(idx, len(ordered_urls)),
                        "urls_total": len(ordered_urls),
                        "codes_found": len(found_codes),
                        "codes_needed": len(needed_codes),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            futs = [pool.submit(one, u) for u in batch]
            for fut in as_completed(futs):
                row = fut.result()
                if row:
                    extracts.append(row)
                    found_codes.add(row["code"])

    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in extracts:
        by_code[row["code"]].append(row)

    accepted_map: dict[str, dict[str, str]] = {}
    ambiguous_codes: set[str] = set()
    for code, group in by_code.items():
        imgs = {g["image_url"] for g in group}
        if len(imgs) != 1:
            # majority vote
            counts: dict[str, int] = defaultdict(int)
            for g in group:
                counts[g["image_url"]] += 1
            top = max(counts.values())
            winners = [k for k, v in counts.items() if v == top]
            if len(winners) != 1 or top < 1:
                ambiguous_codes.add(code)
                continue
            pick = next(g for g in group if g["image_url"] == winners[0])
        else:
            pick = group[0]
        # require Dasqua manufacturer evidence already checked
        accepted_map[code] = pick

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []

    for item in work_items:
        sku = (item.get("sku") or "").strip()
        code = normalize_dasqua_code(sku)
        product_id = (item.get("product_id") or "").strip()
        if code in ambiguous_codes:
            rejected.append(
                {
                    "lane_id": spec["lane_id"],
                    "product_id": product_id,
                    "sku": sku,
                    "product_name": item.get("product_name") or "",
                    "reason_code": "ambiguous_official_code",
                    "reason_detail": f"multiple conflicting images for code {code}",
                    "notes": "",
                }
            )
            continue
        hit = accepted_map.get(code)
        if hit is None:
            rejected.append(
                {
                    "lane_id": spec["lane_id"],
                    "product_id": product_id,
                    "sku": sku,
                    "product_name": item.get("product_name") or "",
                    "reason_code": "official_page_not_found",
                    "reason_detail": f"no unambiguous official page for code {code}",
                    "notes": "",
                }
            )
            continue
        cand = {
            "schema_version": "1",
            "task_id": "IMG-02B",
            "lane_id": spec["lane_id"],
            "product_id": product_id,
            "product_key": item.get("product_key") or f"product_id:{product_id}",
            "sku": sku,
            "product_name": item.get("product_name") or "",
            "brand_key": "dasqua",
            "work_type": item.get("work_type") or "",
            "work_reasons": item.get("work_reasons") or "",
            "priority": item.get("priority") or "",
            "source_adapter": spec["adapter"],
            "source_class": spec["source_class"],
            "source_detail_url": hit["detail_url"],
            "source_image_url": hit["image_url"],
            "source_image_index": "0",
            "candidate_discovery_method": "official_sitemap_item_code",
            "candidate_match_basis": "exact_item_code",
            "manufacturer_evidence": "page_title_or_body_dasqua",
            "sku_evidence": f"item_code:{code}",
            "confidence": "very_high",
            "rights_status": "review_required",
            "apply_status": "not_started",
            "discovery_status": "candidate_ready",
            "notes": "",
            "detail_url": hit["detail_url"],
            "image_url": hit["image_url"],
            "brand": "Dasqua",
        }
        cand["_candidate_id"] = stable_candidate_id(
            [spec["lane_id"], product_id, sku, hit["detail_url"], hit["image_url"]]
        )
        candidates.append(cand)

    return {
        "candidates": candidates,
        "rejected": rejected,
        "manual": manual,
        "stats": {
            "requested": len(work_items),
            "official_candidate_pages": len(extracts),
            "sitemap_urls": len(page_urls),
            "unique_codes_indexed": len(by_code),
            "ambiguous_codes": len(ambiguous_codes),
            "accepted_candidates": len(candidates),
            "rejected": len(rejected),
            "manual_review": len(manual),
        },
    }
