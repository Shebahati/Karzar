"""Bounded SAN OU official site-shape calibration (IMG-02B-04 R1)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from .transport import DiscoveryError, HostThrottledFetcher, host_allowed

ALLOWED = frozenset({"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"})

SHAPE_SEED_URLS = (
    "https://en.sanouchuck.com/robots.txt",
    "https://www.sanouchuck.com/robots.txt",
    "https://en.sanouchuck.com/sitemap.xml",
    "https://www.sanouchuck.com/sitemap.xml",
    "https://en.sanouchuck.com/",
    "https://www.sanouchuck.com/",
    "https://en.sanouchuck.com/download.aspx",
    "https://www.sanouchuck.com/download.aspx",
    "https://en.sanouchuck.com/product.aspx",
    "https://en.sanouchuck.com/product-n.aspx",
)


def _classify_page(url: str, status: int, ctype: str, title: str, html: str) -> str:
    path = (urlparse(url).path or "").casefold()
    low = (html or "").casefold()
    if status != 200:
        return "http_error"
    if "robots.txt" in path:
        return "robots"
    if "sitemap" in path:
        return "sitemap"
    if "download" in path:
        return "download_catalog_index"
    if "productshow.aspx" in path:
        return "product_detail_candidate"
    if path in {"/", "/index.aspx", "/index.html"}:
        return "homepage"
    if "product" in path:
        return "product_index_or_search"
    if "san ou" in low or "sanou" in low:
        return "brand_content"
    return "unknown"


def _product_link_patterns(html: str, base: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html or "", re.I)
    out: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        abs_url = urljoin(base, href)
        if not host_allowed(abs_url, ALLOWED):
            continue
        path = (urlparse(abs_url).path or "").casefold()
        if "productshow.aspx" in path or re.search(r"product.*\.aspx", path):
            if abs_url not in seen:
                seen.add(abs_url)
                out.append(abs_url)
    return out[:20]


def calibrate_sanou_site_shape(
    *,
    fetcher: HostThrottledFetcher,
    model_samples: list[dict[str, str]] | None = None,
    max_model_samples: int = 25,
) -> dict[str, Any]:
    """Probe robots/sitemaps/home/index + up to 25 model-bearing rows."""
    rows: list[dict[str, Any]] = []

    def probe(url: str) -> dict[str, Any]:
        try:
            status, body, ctype, final = fetcher.get(url, fail_code="shape_fetch_failed")
            html = body.decode("utf-8", errors="replace")
        except DiscoveryError as exc:
            return {
                "requested_url": url,
                "http_status": None,
                "final_url": "",
                "content_type": "",
                "page_title": "",
                "detected_page_type": "source_unavailable",
                "product_link_pattern": [],
                "model_evidence_location": "",
                "image_pattern": "",
                "parser_result": str(exc),
            }
        title_m = re.search(r"<title>([^<]+)", html, re.I)
        title = title_m.group(1).strip() if title_m else ""
        final_url = final or url
        page_type = _classify_page(final_url, status, ctype, title, html)
        links = _product_link_patterns(html, final_url)
        img = ""
        m = re.search(
            r"(?:src|data-src)=[\"']([^\"']+/images/product/[^\"']+\.(?:jpg|jpeg|png|webp))",
            html,
            re.I,
        )
        if m:
            img = urljoin(final_url, m.group(1))
        return {
            "requested_url": url,
            "http_status": status,
            "final_url": final_url,
            "content_type": ctype,
            "page_title": title[:200],
            "detected_page_type": page_type,
            "product_link_pattern": links[:10],
            "model_evidence_location": "",
            "image_pattern": img,
            "parser_result": "ok" if status == 200 else f"http_{status}",
        }

    for url in SHAPE_SEED_URLS:
        rows.append(probe(url))

    proven_detail = any(r.get("detected_page_type") == "product_detail_candidate" for r in rows)
    samples = (model_samples or [])[:max_model_samples]
    for item in samples:
        model = (item.get("model") or item.get("sku") or "").strip()
        # Prefer productshow listing pages discovered in seed probes.
        seed_links = []
        for r in rows:
            seed_links.extend(r.get("product_link_pattern") or [])
        target = next((u for u in seed_links if "productshow" in u.casefold()), None)
        if target is None:
            # Do not re-run guessed search matrix for all samples — one shape miss is enough.
            rows.append(
                {
                    "requested_url": f"model_sample:{model}",
                    "http_status": None,
                    "final_url": "",
                    "content_type": "",
                    "page_title": item.get("product_name") or "",
                    "detected_page_type": (
                        "source_unavailable" if not proven_detail else "model_not_published"
                    ),
                    "product_link_pattern": [],
                    "model_evidence_location": "",
                    "image_pattern": "",
                    "parser_result": (
                        "no_proven_productshow_shape; skipping guessed search matrix"
                    ),
                    "product_id": item.get("product_id") or "",
                    "sku": item.get("sku") or "",
                    "model": model,
                }
            )
            continue
        row = probe(target)
        row["product_id"] = item.get("product_id") or ""
        row["sku"] = item.get("sku") or ""
        row["model"] = model
        text = (row.get("page_title") or "") + " " + (row.get("parser_result") or "")
        if model and model.casefold() in text.casefold():
            row["model_evidence_location"] = "title_or_body"
        rows.append(row)

    # Recompute after model samples — productshow probes may prove detail shape.
    proven_detail = any(
        r.get("detected_page_type") == "product_detail_candidate" for r in rows
    )
    model_on_detail = any(
        (r.get("detected_page_type") == "product_detail_candidate")
        and (r.get("model_evidence_location") or "")
        for r in rows
    )
    outcome = "source_unavailable"
    if proven_detail and model_on_detail:
        outcome = "official_detail_candidate"
    elif proven_detail:
        # Detail URL shape exists but sample models were not evidenced on those pages.
        outcome = "parser_drift"
    elif any(r.get("detected_page_type") == "download_catalog_index" for r in rows):
        outcome = "official_catalog_only"

    return {
        "calibration_rows": rows,
        "governed_outcome": outcome,
        "proven_product_detail_shape": proven_detail,
        "seed_url_count": len(SHAPE_SEED_URLS),
        "model_sample_count": len(samples),
        "note": (
            "Do not run all 215 model-bearing products until a real official "
            "product shape is proven or the site is classified unavailable."
        ),
    }
