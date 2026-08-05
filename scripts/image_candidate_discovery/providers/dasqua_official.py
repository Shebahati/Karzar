"""Dasqua official candidate discovery (IMG-02B-02).

Identity model (R1):
- governed_sku: worklist SKU trimmed only (suffix preserved)
- official_item_code_exact: extracted exact item/model code (suffix preserved)
- optional_family_code: first numeric pair only — secondary evidence, never auto-identity
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit

from .. import LANE_SPECS, CandidateDiscoveryError
from ..output import stable_candidate_id
from ..transport import DiscoveryError, HostThrottledFetcher, host_allowed, host_of


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


SITE = "https://www.dasquatools.com"
SITEMAPS = [
    f"{SITE}/product_sitemap.xml",
    f"{SITE}/product_2_sitemap.xml",
    f"{SITE}/product_3_sitemap.xml",
]

PAGE_ALLOWED = frozenset({"www.dasquatools.com", "dasquatools.com"})
# Observed GlobalSo asset hosts from live Dasqua product pages (R1 evidence).
# Do not pre-authorize ecdn1–ecdn15 without observation.
OBSERVED_ASSET_HOSTS = frozenset({"cdn.globalso.com", "ecdn6.globalso.com"})
IMAGE_ALLOWED = PAGE_ALLOWED | OBSERVED_ASSET_HOSTS

# Full exact item code including optional alphanumeric suffix (e.g. 4111-8105A).
EXACT_CODE_RE = re.compile(
    r"\b(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)\b"
)
TITLE_DASQUA_RE = re.compile(
    r"Dasqua\s+(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)\b",
    re.IGNORECASE,
)
ITEM_NUMBER_RE = re.compile(
    r"(?:Item\s*Number|Item\s*No\.?|Order\s*No\.?|Art\.?\s*No\.?|Product\s*No\.?)\s*[:：]\s*"
    r"(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)\b",
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


def governed_sku(raw: str) -> str:
    """Worklist SKU trimmed only — byte-for-byte equal after strip."""
    return (raw or "").strip()


def family_code(exact_or_sku: str) -> str:
    """Secondary family key (first numeric pair). Never auto-identity."""
    text = (exact_or_sku or "").strip()
    m = re.match(r"^(\d{3,5}-\d{3,5})", text)
    return m.group(1) if m else text


def normalize_dasqua_code(raw: str) -> str:
    """Deprecated alias: returns family_code only. Prefer governed_sku / exact extract."""
    return family_code(raw)


def extract_exact_item_code(title: str, url: str, html: str = "") -> str | None:
    """Extract exact official item code with suffix preserved."""
    path = unquote(urlparse(url).path or "")
    title_text = title or ""

    m = TITLE_DASQUA_RE.search(title_text)
    if m:
        return m.group(1)

    m2 = re.search(r"dasqua-(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)", path, re.IGNORECASE)
    if m2:
        return m2.group(1)

    title_codes = list(dict.fromkeys(EXACT_CODE_RE.findall(title_text)))
    if len(title_codes) == 1:
        return title_codes[0]

    path_codes = list(dict.fromkeys(EXACT_CODE_RE.findall(path)))
    if len(path_codes) == 1:
        return path_codes[0]

    labeled = list(dict.fromkeys(ITEM_NUMBER_RE.findall(html or "")))
    if labeled:
        path_l = path.casefold()
        title_l = title_text.casefold()
        for code in labeled:
            if code.casefold() in path_l or code.casefold() in title_l:
                return code
        if len(labeled) == 1:
            return labeled[0]
    return None


def extract_primary_code(title: str, url: str, html: str = "") -> str | None:
    """Backward-compatible name — returns exact item code (suffix preserved)."""
    return extract_exact_item_code(title, url, html)


def allow_dasqua_image_url(image_url: str, *, parent_detail_url: str) -> bool:
    """CDN/asset URLs require a validated Dasqua page parent — never stand alone."""
    if not host_allowed(parent_detail_url, PAGE_ALLOWED):
        return False
    if host_of(parent_detail_url) not in PAGE_ALLOWED:
        return False
    return host_allowed(image_url, IMAGE_ALLOWED)


def extract_image(html: str, *, parent_detail_url: str = "") -> str | None:
    parent = parent_detail_url or f"{SITE}/"
    m = OG_IMAGE_RE.search(html or "")
    if m:
        og = (m.group(1) or m.group(2) or "").strip()
        if og and allow_dasqua_image_url(og, parent_detail_url=parent) and "image_product" in og:
            return og
        if og and allow_dasqua_image_url(og, parent_detail_url=parent):
            return og
    m2 = IMAGE_PRODUCT_RE.search(html or "")
    if m2 and allow_dasqua_image_url(m2.group(0), parent_detail_url=parent):
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


def _norm_code(code: str) -> str:
    """Case-fold exact item codes so path/title suffix case does not false-ambiguate."""
    return (code or "").strip().casefold()


def _page_is_family_ambiguous(html: str, exact_code: str, title: str = "", url: str = "") -> bool:
    """True when primary product evidence shows multiple distinct exact item codes.

    Related-product sidebars often list other Dasqua codes. Prefer title + labeled
    Item Number. If neither yields codes, fall back to whole-page codes (fail closed).
    """
    primary: set[str] = set()
    m = TITLE_DASQUA_RE.search(title or "")
    if m:
        primary.add(_norm_code(m.group(1)))
    labeled = list(dict.fromkeys(ITEM_NUMBER_RE.findall(html or "")))
    primary.update(_norm_code(c) for c in labeled)
    path = unquote(urlparse(url or "").path or "")
    path_codes = list(dict.fromkeys(EXACT_CODE_RE.findall(path)))
    if len(path_codes) == 1:
        primary.add(_norm_code(path_codes[0]))
    if primary:
        return len(primary) > 1
    # No primary labeled/title evidence — fail closed on multiple body codes.
    return len({_norm_code(c) for c in EXACT_CODE_RE.findall(html or "")}) > 1


def _validate_with_adapter(sku: str, html: str, detail_url: str) -> tuple[bool, str, str]:
    """Shared SourceAdapter subject validation — discovery must match materialization."""
    from image_discovery.sources.dasqua_official import DasquaOfficialAdapter

    ev = DasquaOfficialAdapter().validate_page(
        sku=sku, page_html=html, detail_url=detail_url
    )
    if ev.manufacturer_confirmed and ev.sku_confirmed:
        return True, "", ""
    return (
        False,
        ev.reason_code or "adapter_rejected",
        ev.reason_detail or "",
    )


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

    needed_exact = {governed_sku(i.get("sku") or "") for i in work_items}
    needed_exact.discard("")
    needed_family = {family_code(s) for s in needed_exact}

    preferred: list[str] = []
    rest: list[str] = []
    for url in page_urls:
        path = unquote(urlparse(url).path or "").casefold()
        if any(s.casefold() in path for s in needed_exact) or any(
            f.casefold() in path for f in needed_family
        ):
            preferred.append(url)
        else:
            rest.append(url)
    # Bounded runs (--limit): crawl preferred URL matches only, plus a small
    # rest buffer. Full-lane runs still scan the complete sitemap order.
    if limit is not None:
        buffer = max(limit * 8, 48)
        ordered_urls = preferred + rest[:buffer]
    else:
        ordered_urls = preferred + rest

    extracts: list[dict[str, Any]] = []
    found_exact: set[str] = set()

    def one(url: str) -> dict[str, Any] | None:
        try:
            status, body, _ctype, final = fetcher.get(
                to_ascii_url(url), fail_code="page_fetch_failed"
            )
            if status != 200:
                return None
            # Fail closed: page final host must remain Dasqua (no GlobalSo redirect).
            if not host_allowed(final or url, PAGE_ALLOWED):
                return None
            html = body.decode("utf-8", errors="replace")
        except (DiscoveryError, UnicodeEncodeError, UnicodeError):
            return None
        title_m = re.search(r"<title>([^<]+)", html, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else ""
        exact = extract_exact_item_code(title, url, html)
        detail = final or url
        image = extract_image(html, parent_detail_url=detail)
        if not exact or not image:
            return None
        if "dasqua" not in html.casefold() and "dasqua" not in title.casefold():
            return None
        if _page_is_family_ambiguous(html, exact, title=title, url=url):
            return {
                "exact_code": exact,
                "family_code": family_code(exact),
                "detail_url": detail,
                "image_url": image,
                "title": title,
                "html": html,
                "family_ambiguous": True,
            }
        return {
            "exact_code": exact,
            "family_code": family_code(exact),
            "detail_url": detail,
            "image_url": image,
            "title": title,
            "html": html,
            "family_ambiguous": False,
        }

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        batch_size = max(concurrency * 8, 24)
        idx = 0
        while idx < len(ordered_urls):
            if needed_exact and needed_exact.issubset(found_exact):
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
                        "codes_found": len(found_exact),
                        "codes_needed": len(needed_exact),
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
                    # Count resolved either as unambiguous hit or as ambiguous family —
                    # otherwise family sidebars stall the crawl with codes_found=0 forever.
                    found_exact.add(row["exact_code"])

    by_exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in extracts:
        by_exact[row["exact_code"]].append(row)

    # No majority voting: multiple pages/images for one exact code → ambiguous.
    unambiguous: dict[str, dict[str, Any]] = {}
    ambiguous_exact: set[str] = set()
    for code, group in by_exact.items():
        if any(g.get("family_ambiguous") for g in group):
            ambiguous_exact.add(code)
            continue
        details = {g["detail_url"] for g in group}
        imgs = {g["image_url"] for g in group}
        if len(details) != 1 or len(imgs) != 1:
            ambiguous_exact.add(code)
            continue
        unambiguous[code] = group[0]

    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    exact_suffix_collisions = 0
    ambiguous_families = 0

    # Detect governed SKUs that share a family base but differ by suffix.
    by_family_sku: dict[str, list[str]] = defaultdict(list)
    for item in work_items:
        sku = governed_sku(item.get("sku") or "")
        if sku:
            by_family_sku[family_code(sku)].append(sku)
    for _fam, skus in by_family_sku.items():
        if len(set(skus)) > 1:
            exact_suffix_collisions += len(set(skus))

    for item in work_items:
        sku = governed_sku(item.get("sku") or "")
        product_id = (item.get("product_id") or "").strip()
        product_name = item.get("product_name") or ""

        # Exact match only — family code never establishes automatic identity.
        hit = unambiguous.get(sku)
        if hit is None:
            # Try case-insensitive exact key
            hit = next(
                (unambiguous[k] for k in unambiguous if k.casefold() == sku.casefold()),
                None,
            )

        if sku in ambiguous_exact or (
            hit is None and any(k.casefold() == sku.casefold() for k in ambiguous_exact)
        ):
            ambiguous_families += 1
            manual.append(
                {
                    "lane_id": spec["lane_id"],
                    "product_id": product_id,
                    "sku": sku,
                    "product_name": product_name,
                    "reason_code": "ambiguous_official_product",
                    "reason_detail": (
                        "multiple detail pages, images, or family-only evidence "
                        f"for exact item code related to {sku}"
                    ),
                    "source_detail_url": "",
                    "notes": f"family_code:{family_code(sku)}",
                }
            )
            continue

        if hit is None:
            rejected.append(
                {
                    "lane_id": spec["lane_id"],
                    "product_id": product_id,
                    "sku": sku,
                    "product_name": product_name,
                    "reason_code": "official_page_not_found",
                    "reason_detail": (
                        f"no unambiguous official page for governed_sku={sku} "
                        f"(family={family_code(sku)} is not automatic identity)"
                    ),
                    "notes": "",
                }
            )
            continue

        ok, reason_code, reason_detail = _validate_with_adapter(
            sku, hit["html"], hit["detail_url"]
        )
        if not ok:
            rejected.append(
                {
                    "lane_id": spec["lane_id"],
                    "product_id": product_id,
                    "sku": sku,
                    "product_name": product_name,
                    "reason_code": reason_code or "adapter_rejected",
                    "reason_detail": reason_detail
                    or "SourceAdapter rejected page that discovery would have accepted",
                    "notes": "candidate_adapter_consistency",
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
            "product_name": product_name,
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
            "sku_evidence": f"exact_item_code:{hit['exact_code']};family:{hit['family_code']}",
            "confidence": "very_high",
            "rights_status": "review_required",
            "apply_status": "not_started",
            "discovery_status": "candidate_ready",
            "notes": f"governed_sku={sku};official_item_code_exact={hit['exact_code']}",
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
            "discovered_candidates": len(candidates),
            "validated_candidate_rows": len(candidates),
            "official_candidate_pages": len(extracts),
            "sitemap_urls": len(page_urls),
            "unique_exact_codes_indexed": len(by_exact),
            "ambiguous_official_product": len(ambiguous_exact),
            "exact_suffix_collisions": exact_suffix_collisions,
            "ambiguous_families": ambiguous_families,
            "rejected": len(rejected),
            "manual_review": len(manual),
            "observed_asset_hosts": sorted(OBSERVED_ASSET_HOSTS),
        },
    }
