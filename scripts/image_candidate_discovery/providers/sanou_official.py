"""SAN OU official candidate discovery (IMG-02B-04)."""

from __future__ import annotations

import html as html_lib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from .. import LANE_SPECS
from ..output import stable_candidate_id
from ..transport import DiscoveryError, HostThrottledFetcher, host_allowed

ALLOWED = frozenset({"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"})

# Model tokens seen on SAN OU worklist names: K12-160, J2116H/M/C, HKJ2510, Q250, 3HB-215, …
MODEL_TOKEN_RE = re.compile(
    r"(?:"
    r"\b(?P<kseries>K(?:1[12]|72|\d{2}))-?-?(?P<ksize>\d{2,4})(?:MM)?\b"
    r"|\b(?P<hkj>HKJ\d{3,5})\b"
    r"|\b(?P<jdrill>J\d{3,5}[A-Z]?)\b"
    r"|\b(?P<scroll>SCROLL)-?-?(?P<scrollsize>\d{2,4})\b"
    r"|\b(?P<pinion>PINION)-(?P<pinionsize>\d{2,4})\b"
    r"|\b(?P<morse>MS\d-(?:B\d{1,2}|JT\d))\b"
    r"|\b(?P<cyl>C\d{2}-\d{1,2})\b"
    r"|\b(?P<qchuck>Q\d{2,3})\b"
    r"|\b(?P<hyd>3HB?)-?-?(?P<hydsize>\d{2,3}[A-Z]?\d?)\b"
    r"|\b(?P<sb>SB-\d{2,4})\b"
    r"|(?<![A-Za-z0-9])(?P<mt>MT[1-6])(?![A-Za-z0-9])"
    r"|\b(?P<arbor>B(?:12|16|18|22))\b"
    r"|\b(?P<dead>D11[3-5])\b"
    r")",
    re.IGNORECASE,
)

SEARCH_TEMPLATES = (
    # Prefer English official host first; Chinese host as fallback.
    "https://en.sanouchuck.com/product.aspx?keyword={q}",
    "https://en.sanouchuck.com/search.aspx?key={q}",
    "https://www.sanouchuck.com/product.aspx?keyword={q}",
    "https://www.sanouchuck.com/search.aspx?key={q}",
)

HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
IMG_SRC_RE = re.compile(
    r'(?:src|data-src|data-original)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?)["\']',
    re.IGNORECASE,
)
OG_IMAGE_RE = re.compile(
    r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']|'
    r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
    re.IGNORECASE,
)

SKIP_PATH_PARTS = (
    "login",
    "register",
    "cart",
    "download.aspx",
    "javascript:",
    "mailto:",
    "#",
    "index.aspx",
    "about.aspx",
    "service.aspx",
    "product-package.aspx",
    "contact",
)

# Listing placeholders / chrome — never accept as product image.
_BAD_IMAGE_MARKERS = (
    "logo",
    "icon",
    "banner",
    "sprite",
    "blank",
    "/pl1.",
    "/pl2.",
    "/pl3.",
    "/images/banner",
)


def extract_model_tokens(text: str) -> list[str]:
    """Extract ordered unique model tokens from a product name / SKU blob."""
    found: list[str] = []
    seen: set[str] = set()
    for m in MODEL_TOKEN_RE.finditer(text or ""):
        if m.group("kseries") and m.group("ksize"):
            tok = f"{m.group('kseries').upper()}-{m.group('ksize')}"
        elif m.group("hkj"):
            tok = m.group("hkj").upper()
        elif m.group("jdrill"):
            tok = m.group("jdrill").upper()
        elif m.group("scroll") and m.group("scrollsize"):
            tok = f"SCROLL-{m.group('scrollsize')}"
        elif m.group("pinion") and m.group("pinionsize"):
            tok = f"PINION-{m.group('pinionsize')}"
        elif m.group("morse"):
            tok = m.group("morse").upper()
        elif m.group("cyl"):
            tok = m.group("cyl").upper()
        elif m.group("qchuck"):
            tok = m.group("qchuck").upper()
        elif m.group("hyd") and m.group("hydsize"):
            tok = f"{m.group('hyd').upper()}-{m.group('hydsize').upper()}"
        elif m.group("sb"):
            tok = m.group("sb").upper()
        elif m.group("mt"):
            tok = m.group("mt").upper()
        elif m.group("dead"):
            tok = m.group("dead").upper()
        elif m.group("arbor"):
            tok = m.group("arbor").upper()
        else:
            continue
        if len(tok) < 3 or tok.startswith("SO-"):
            continue
        if tok not in seen:
            seen.add(tok)
            found.append(tok)
    return found


def _clean_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", html_lib.unescape(text))


def _token_present(text: str, token: str) -> bool:
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(token)}(?:MM)?(?![A-Za-z0-9])",
            text or "",
            re.IGNORECASE,
        )
    )


def _abs_url(base: str, href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith(("javascript:", "mailto:", "data:")):
        return None
    abs_url = urljoin(base, href)
    if not host_allowed(abs_url, ALLOWED):
        return None
    path = (urlparse(abs_url).path or "").casefold()
    if any(part in path or part in abs_url.casefold() for part in SKIP_PATH_PARTS):
        return None
    return abs_url


def extract_product_links(html: str, base_url: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for href in HREF_RE.findall(html or ""):
        abs_url = _abs_url(base_url, href)
        if not abs_url:
            continue
        parsed = urlparse(abs_url)
        path = (parsed.path or "").casefold()
        query = (parsed.query or "").casefold()
        # Official catalog detail pages look like productshow.aspx?id=278.
        is_show = path.endswith("productshow.aspx") and "id=" in query
        is_named_detail = any(
            tip in path
            for tip in ("prodetail", "productdetail", "product-detail", "goodsdetail")
        )
        if not (is_show or is_named_detail):
            continue
        if abs_url not in seen:
            seen.add(abs_url)
            out.append(abs_url)
    return out[:8]


def extract_official_image(html: str, base_url: str) -> str | None:
    candidates: list[str] = []
    m = OG_IMAGE_RE.search(html or "")
    if m:
        og = (m.group(1) or m.group(2) or "").strip()
        abs_og = _abs_url(base_url, og)
        if abs_og:
            candidates.append(abs_og)
    for src in IMG_SRC_RE.findall(html or ""):
        abs_img = _abs_url(base_url, src)
        if abs_img:
            candidates.append(abs_img)

    def _usable(url: str) -> bool:
        low = url.casefold()
        return not any(bad in low for bad in _BAD_IMAGE_MARKERS)

    usable = [u for u in candidates if _usable(u)]
    if not usable:
        return None
    # Prefer timestamped catalog assets under /images/product/<digits>…
    for url in usable:
        if re.search(r"/images/product/\d", url, re.IGNORECASE):
            return url
    return usable[0]

def manufacturer_present(html: str) -> bool:
    text = _clean_text(html)
    return bool(
        re.search(r"\bsan\s*ou\b|\bsanou\b|\bsano\b", text, re.IGNORECASE)
        or re.search(r"sanouchuck", html or "", re.IGNORECASE)
    )


def _search_urls_for_model(model: str) -> list[str]:
    q = quote(model)
    return [tpl.format(q=q) for tpl in SEARCH_TEMPLATES]


def _resolve_one(
    item: dict[str, str],
    *,
    fetcher: HostThrottledFetcher,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Return (candidate, rejected, manual) — at most one non-None."""
    spec = LANE_SPECS["san_ou"]
    sku = (item.get("sku") or "").strip()
    product_id = (item.get("product_id") or "").strip()
    product_name = item.get("product_name") or ""
    models = extract_model_tokens(f"{sku} {product_name}")

    def reject(code: str, detail: str) -> tuple[None, dict[str, Any], None]:
        return (
            None,
            {
                "lane_id": spec["lane_id"],
                "product_id": product_id,
                "sku": sku,
                "product_name": product_name,
                "reason_code": code,
                "reason_detail": detail,
                "notes": "",
            },
            None,
        )

    def manual_row(code: str, detail: str, detail_url: str = "") -> tuple[None, None, dict[str, Any]]:
        return (
            None,
            None,
            {
                "lane_id": spec["lane_id"],
                "product_id": product_id,
                "sku": sku,
                "product_name": product_name,
                "product_key": item.get("product_key") or f"product_id:{product_id}",
                "work_type": item.get("work_type") or "",
                "work_reasons": item.get("work_reasons") or "",
                "priority": item.get("priority") or "",
                "reason_code": code,
                "reason_detail": detail,
                "source_detail_url": detail_url,
                "discovery_status": "manual_review",
                "eligible_for_automatic_discovery": "false",
                "notes": f"models:{','.join(models)}",
            },
        )

    if not models:
        return manual_row(
            "model_token_not_found",
            "no extractable SAN OU model token in name/sku; "
            "eligible_for_automatic_discovery=false",
        )

    page_hits: list[dict[str, str]] = []
    catalog_only: list[dict[str, str]] = []
    fetch_errors = 0
    successful_searches = 0

    for model in models:
        for search_url in _search_urls_for_model(model):
            try:
                status, body, _ctype, final = fetcher.get(
                    search_url, fail_code="search_fetch_failed"
                )
                if status != 200:
                    fetch_errors += 1
                    continue
                html = body.decode("utf-8", errors="replace")
                successful_searches += 1
            except DiscoveryError:
                fetch_errors += 1
                continue

            base = final or search_url
            page_text = _clean_text(html)
            model_on_page = _token_present(page_text, model) or _token_present(html, model)
            if not model_on_page:
                # Search miss — do not crawl unrelated productshow nav links.
                continue

            # Search shells often show shared placeholders — require a detail hit
            # unless the search response itself is already a product detail URL.
            is_detail_shell = bool(
                re.search(
                    r"prodetail|productdetail|product-detail|productshow\.aspx",
                    (final or search_url).casefold(),
                )
            ) and ("id=" in (final or search_url).casefold())
            image = extract_official_image(html, base) if is_detail_shell else None
            if manufacturer_present(html) and image and host_allowed(image, ALLOWED):
                page_hits.append(
                    {
                        "model": model,
                        "detail_url": base,
                        "image_url": image,
                    }
                )
                break

            for link in extract_product_links(html, base):
                try:
                    st2, body2, _ct2, final2 = fetcher.get(
                        link, fail_code="detail_fetch_failed"
                    )
                    if st2 != 200:
                        continue
                    detail_html = body2.decode("utf-8", errors="replace")
                except DiscoveryError:
                    continue
                detail_base = final2 or link
                detail_text = _clean_text(detail_html)
                if not _token_present(detail_text, model) and not _token_present(
                    detail_html, model
                ):
                    continue
                if not manufacturer_present(detail_html):
                    continue
                img = extract_official_image(detail_html, detail_base)
                if img and host_allowed(img, ALLOWED):
                    page_hits.append(
                        {
                            "model": model,
                            "detail_url": detail_base,
                            "image_url": img,
                        }
                    )
                    break
                catalog_only.append(
                    {
                        "model": model,
                        "detail_url": detail_base,
                    }
                )
            if page_hits:
                break
            # English search returned the model token but no usable detail image —
            # keep catalog_only evidence and skip the Chinese duplicate matrix.
            if search_url.startswith("https://en.sanouchuck.com/"):
                break
        if page_hits:
            break

    if page_hits:
        # Prefer unambiguous single image; else first deterministic by URL.
        by_image = {h["image_url"]: h for h in page_hits}
        if len(by_image) > 1:
            # Conflicting images for same work item → reject
            return reject(
                "ambiguous_official_model",
                f"multiple official images for models {models}",
            )
        hit = sorted(page_hits, key=lambda h: (h["detail_url"], h["image_url"]))[0]
        cand = {
            "schema_version": "1",
            "task_id": "IMG-02B",
            "lane_id": spec["lane_id"],
            "product_id": product_id,
            "product_key": item.get("product_key") or f"product_id:{product_id}",
            "sku": sku,
            "product_name": product_name,
            "brand_key": "san_ou",
            "work_type": item.get("work_type") or "",
            "work_reasons": item.get("work_reasons") or "",
            "priority": item.get("priority") or "",
            "source_adapter": spec["adapter"],
            "source_class": spec["source_class"],
            "source_detail_url": hit["detail_url"],
            "source_image_url": hit["image_url"],
            "source_image_index": "0",
            "candidate_discovery_method": "official_model_search",
            "candidate_match_basis": "exact_model_token",
            "manufacturer_evidence": "page_sanou_manufacturer",
            "sku_evidence": f"model:{hit['model']}",
            "confidence": "very_high",
            "rights_status": "review_required",
            "apply_status": "not_started",
            "discovery_status": "candidate_ready",
            "notes": "",
            "detail_url": hit["detail_url"],
            "image_url": hit["image_url"],
            "brand": "SAN OU",
        }
        cand["_candidate_id"] = stable_candidate_id(
            [spec["lane_id"], product_id, sku, hit["detail_url"], hit["image_url"]]
        )
        return cand, None, None

    if catalog_only:
        hit = sorted(catalog_only, key=lambda h: h["detail_url"])[0]
        return manual_row(
            "official_catalog_only",
            f"model {hit['model']} found on official page without stable image URL",
            hit["detail_url"],
        )

    if successful_searches == 0 and fetch_errors:
        return reject(
            "source_unavailable",
            "could not fetch SAN OU official search/product pages "
            "(not product-level official_page_not_found)",
        )
    if successful_searches > 0 and not page_hits and not catalog_only:
        # HTML returned but no product-detail/catalog shape — site/parser mismatch,
        # not a product-level "page not found".
        return reject(
            "parser_drift",
            "official search/index responses returned without a parseable product "
            "detail or catalog shape (not product-level official_page_not_found)",
        )
    return reject(
        "official_page_not_found",
        f"no unambiguous official page for models {models}",
    )


def discover_sanou_candidates(
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

    def one(
        item: dict[str, str],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        return _resolve_one(item, fetcher=fetcher)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futs = {pool.submit(one, item): item for item in work_items}
        done = 0
        for fut in as_completed(futs):
            cand, rej, man = fut.result()
            done += 1
            if done == 1 or done % 25 == 0 or done == len(work_items):
                print(
                    json.dumps(
                        {
                            "phase": "progress",
                            "lane": "san_ou",
                            "done": done,
                            "total": len(work_items),
                            "accepted": len(candidates) + (1 if cand is not None else 0),
                            "manual": len(manual) + (1 if man is not None else 0),
                            "rejected": len(rejected) + (1 if rej is not None else 0),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            if cand is not None:
                candidates.append(cand)
            elif man is not None:
                manual.append(man)
            elif rej is not None:
                rejected.append(rej)

    candidates.sort(
        key=lambda r: ((r.get("sku") or "").casefold(), int(r.get("product_id") or 0))
    )
    rejected.sort(
        key=lambda r: ((r.get("sku") or "").casefold(), int(r.get("product_id") or 0))
    )
    manual.sort(
        key=lambda r: ((r.get("sku") or "").casefold(), int(r.get("product_id") or 0))
    )

    return {
        "candidates": candidates,
        "rejected": rejected,
        "manual": manual,
        "stats": {
            "requested": len(work_items),
            "discovered_candidates": len(candidates),
            "validated_candidate_rows": len(candidates),
            "accepted_candidates": len(candidates),
            "rejected": len(rejected),
            "manual_review": len(manual),
            "model_token_not_found": sum(
                1 for m in manual if m.get("reason_code") == "model_token_not_found"
            ),
            "official_catalog_only": sum(
                1 for m in manual if m.get("reason_code") == "official_catalog_only"
            ),
            "source_unavailable": sum(
                1 for r in rejected if r.get("reason_code") == "source_unavailable"
            ),
            "parser_drift": sum(
                1 for r in rejected if r.get("reason_code") == "parser_drift"
            ),
        },
    }
