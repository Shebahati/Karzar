"""Sitemap / sitemap-index adapter."""

from __future__ import annotations

import re
from typing import Any

from ..extract import extract_product_images, extract_title
from ..identity import exact_sku_in_text, normalize_sku
from .base import IndexedHit, ProbeResult, SourceAdapter
from .probe import probe_url
from .spec import SourceSpec

_LOC_RE = re.compile(r"<loc>\s*([^<]+)\s*</loc>", re.I)


class SitemapAdapter(SourceAdapter):
    adapter_type = "sitemap"

    def __init__(self, spec: SourceSpec) -> None:
        super().__init__(spec.source_id, spec.domain, spec.lane, spec.country, spec.base_url)
        self.sitemap_url = spec.sitemap_url or f"{self.base_url}/sitemap.xml"
        self._locs: list[str] = []

    def probe_source(self, fetcher: Any) -> ProbeResult:
        self.probe_attempted = True
        self.probe = probe_url(self.source_id, self.sitemap_url, attempts=2)
        if not self.probe.reachable:
            self.degraded = True
            self.last_error = self.probe.failure_class
        return self.probe

    def _fetch_locs(self, fetcher: Any, url: str, depth: int = 0) -> list[str]:
        if depth > 2:
            return []
        try:
            status, body, _ctype, _final = fetcher.get(url, fail_code="sitemap_fetch")
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            return []
        if status != 200:
            self.last_error = f"http_{status}"
            return []
        text = body.decode("utf-8", errors="replace")
        locs = [m.group(1).strip() for m in _LOC_RE.finditer(text)]
        out: list[str] = []
        child_sitemaps = [u for u in locs if "sitemap" in u.lower() and u.endswith(".xml")]
        productish = [u for u in locs if u not in child_sitemaps]
        out.extend(productish)
        for child in child_sitemaps[:20]:
            out.extend(self._fetch_locs(fetcher, child, depth + 1))
        return out

    def build_index(self, fetcher: Any, sample_skus: list[str] | None = None) -> int:
        self.executed = True
        self._locs = self._fetch_locs(fetcher, self.sitemap_url)
        samples = [normalize_sku(s) for s in (sample_skus or []) if s][:200]
        # Index URLs that contain sample SKU tokens; also keep all product-like paths keyed by token in path
        for loc in self._locs:
            path = loc.lower()
            tokens = re.findall(r"[a-z0-9][a-z0-9\-_/]{2,}", path)
            for tok in tokens:
                key = normalize_sku(tok)
                if not key:
                    continue
                if samples and key not in samples and not any(key in s or s in key for s in samples):
                    # still index path tokens for bulk; prefer sample hits
                    pass
                if key not in self._index:
                    self._index[key] = IndexedHit(sku=tok, title="", page_url=loc, image_urls=[])
        return len(self._index)

    def lookup(self, sku: str) -> IndexedHit | None:  # type: ignore[override]
        if not self.bulk_enabled:
            return None
        hit = self._index.get(normalize_sku(sku))
        return hit

    def enrich_hit(self, fetcher: Any, hit: IndexedHit, sku: str) -> IndexedHit:
        """Fetch PDP and extract images when index only has URL."""
        if hit.image_urls:
            return hit
        try:
            status, body, _ctype, final = fetcher.get(hit.page_url, fail_code="pdp_fetch")
        except Exception:
            return hit
        if status != 200:
            return hit
        html = body.decode("utf-8", errors="replace")
        title = extract_title(html)
        urls, _ev, has_pdp = extract_product_images(html, final or hit.page_url, sku=sku)
        if not has_pdp or not exact_sku_in_text(sku, title + "\n" + html[:5000]):
            return hit
        hit.title = title
        hit.image_urls = urls[:5]
        return hit
