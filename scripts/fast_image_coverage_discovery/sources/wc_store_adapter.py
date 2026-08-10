"""WooCommerce Store API source adapter."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from ..identity import normalize_sku
from .base import IndexedHit, ProbeResult, SourceAdapter
from .probe import probe_url
from .spec import SourceSpec


class WooCommerceAdapter(SourceAdapter):
    adapter_type = "wc_store"

    def __init__(self, spec: SourceSpec) -> None:
        super().__init__(spec.source_id, spec.domain, spec.lane, spec.country, spec.base_url)
        self.api = (spec.wc_store_api or "").rstrip("/")

    def probe_source(self, fetcher: Any) -> ProbeResult:
        self.probe_attempted = True
        url = f"{self.api}?per_page=1&page=1" if self.api else self.base_url
        self.probe = probe_url(self.source_id, url, attempts=2)
        if not self.probe.reachable:
            self.degraded = True
            self.last_error = self.probe.failure_class
        return self.probe

    def build_index(self, fetcher: Any, sample_skus: list[str] | None = None) -> int:
        if not self.api:
            self.last_error = "no_wc_store_api"
            return 0
        self.executed = True
        terms = [""]
        # Prefer brand-ish search tokens from sample SKUs' product names unavailable — use empty crawl
        for term in terms:
            page = 1
            while page <= 30:
                url = (
                    f"{self.api}?search={quote(term)}&per_page=100&page={page}"
                    if term
                    else f"{self.api}?per_page=100&page={page}"
                )
                try:
                    status, body, _ctype, _final = fetcher.get(url, fail_code="wc_fetch")
                except Exception as exc:  # noqa: BLE001
                    self.last_error = str(exc)
                    break
                if status != 200:
                    self.last_error = f"http_{status}"
                    break
                try:
                    payload = json.loads(body.decode("utf-8", errors="replace"))
                except Exception as exc:  # noqa: BLE001
                    self.last_error = f"parser_failure:{exc}"
                    break
                if not isinstance(payload, list) or not payload:
                    break
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    sku = str(item.get("sku") or "").strip()
                    title = str(item.get("name") or "")
                    permalink = str(item.get("permalink") or item.get("link") or "")
                    imgs: list[str] = []
                    for img in item.get("images") or []:
                        if isinstance(img, dict) and img.get("src"):
                            imgs.append(str(img["src"]))
                    keys = set()
                    if sku:
                        keys.add(normalize_sku(sku))
                    for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_/]{2,}", title):
                        keys.add(normalize_sku(tok))
                    hit = IndexedHit(sku=sku, title=title, page_url=permalink, image_urls=imgs)
                    for k in keys:
                        if k and k not in self._index:
                            self._index[k] = hit
                if len(payload) < 100:
                    break
                page += 1
        return len(self._index)
