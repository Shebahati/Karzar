"""WooCommerce Store API source indexer and bulk SKU matcher."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from scripts.image_discovery.transport import HostThrottledFetcher

from ..extract import parse_wc_product_images
from ..identity import exact_sku_in_text, normalize_sku
from .registry import SourceSpec

PER_PAGE = 100
MAX_CALIBRATION = 20


@dataclass
class IndexedProduct:
    sku: str
    title: str
    permalink: str
    image_urls: list[str]
    raw: dict[str, Any] = field(repr=False, default_factory=dict)


@dataclass
class SourceIndex:
    source_id: str
    domain: str
    by_sku: dict[str, IndexedProduct] = field(default_factory=dict)
    calibration_checked: int = 0
    calibration_passed: bool = False
    bulk_enabled: bool = False
    last_error: str = ""


def _fetch_json(fetcher: HostThrottledFetcher, url: str) -> Any:
    status, body, _ctype, _final = fetcher.get(url, fail_code="wc_api_fetch_failed")
    if status != 200:
        raise RuntimeError(f"HTTP {status} for {url}")
    return json.loads(body.decode("utf-8", errors="replace"))


def _extract_sku_from_wc(item: dict[str, Any]) -> str:
    for key in ("sku", "id"):
        val = item.get(key)
        if val:
            return str(val).strip()
    return ""


def build_wc_index(
    spec: SourceSpec,
    fetcher: HostThrottledFetcher,
    *,
    search_terms: list[str] | None = None,
    max_pages: int = 200,
) -> SourceIndex:
    index = SourceIndex(source_id=spec.source_id, domain=spec.domain)
    if not spec.wc_store_api:
        index.last_error = "no_wc_store_api"
        return index
    api = spec.wc_store_api.rstrip("/")
    terms = search_terms or [""]
    for term in terms:
        page = 1
        while page <= max_pages:
            if term:
                url = f"{api}?search={quote(term)}&per_page={PER_PAGE}&page={page}"
            else:
                url = f"{api}?per_page={PER_PAGE}&page={page}"
            try:
                payload = _fetch_json(fetcher, url)
            except Exception as exc:  # noqa: BLE001
                index.last_error = str(exc)
                break
            if not isinstance(payload, list) or not payload:
                break
            for item in payload:
                if not isinstance(item, dict):
                    continue
                sku = _extract_sku_from_wc(item)
                title = str(item.get("name") or "")
                permalink = str(item.get("permalink") or item.get("link") or "")
                imgs = parse_wc_product_images(item)
                keys = set()
                if sku:
                    keys.add(normalize_sku(sku))
                for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_/]{2,}", title):
                    keys.add(normalize_sku(tok))
                rec = IndexedProduct(sku=sku, title=title, permalink=permalink, image_urls=imgs, raw=item)
                for k in keys:
                    if k and k not in index.by_sku:
                        index.by_sku[k] = rec
            if len(payload) < PER_PAGE:
                break
            page += 1
    return index


def calibrate_index(index: SourceIndex, sample_skus: list[str]) -> bool:
    checked = 0
    hits = 0
    for sku in sample_skus[:MAX_CALIBRATION]:
        norm = normalize_sku(sku)
        rec = index.by_sku.get(norm)
        if not rec:
            continue
        checked += 1
        if rec.image_urls and rec.permalink and exact_sku_in_text(sku, rec.title):
            hits += 1
    index.calibration_checked = checked
    index.calibration_passed = checked >= 3 and hits >= max(2, checked // 2)
    index.bulk_enabled = index.calibration_passed
    return index.bulk_enabled


def lookup_sku(index: SourceIndex, sku: str) -> IndexedProduct | None:
    if not index.bulk_enabled:
        return None
    return index.by_sku.get(normalize_sku(sku))
