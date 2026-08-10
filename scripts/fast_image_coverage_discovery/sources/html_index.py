"""Generic HTML brand/index + PDP adapter (abzarmarket priority)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from ..extract import extract_product_images, extract_title
from ..identity import exact_sku_in_text, normalize_sku
from .base import IndexedHit, ProbeResult, SourceAdapter
from .probe import probe_url
from .spec import SourceSpec

_HREF_RE = re.compile(r'href=["\']([^"\']*?/product/[^"\']+)["\']', re.I)


def brand_slug(brand_key: str) -> str:
    raw = brand_key.split("|")[0].strip()
    raw = re.sub(r"[^A-Za-z0-9]+", "-", raw).strip("-").lower()
    # map known Persian-hyphen keys
    aliases = {
        "astpower": "ast-power",
        "ast-power": "ast-power",
        "dasqua": "dasqua",
        "tiger-tec": "tiger-tec",
        "chumpower": "chumpower",
        "asimeto": "asimeto",
        "insize": "insize",
        "san-ou": "san-ou",
        "mitutoyo": "mitutoyo",
        "yowax": "yowax",
        "et": "et",
        "terma": "terma",
        "groz": "groz",
        "mighty-seven": "mighty-seven",
    }
    return aliases.get(raw, raw)


_brand_slug = brand_slug  # back-compat for internal callers


class HtmlIndexAdapter(SourceAdapter):
    adapter_type = "html_index"

    def __init__(self, spec: SourceSpec) -> None:
        super().__init__(spec.source_id, spec.domain, spec.lane, spec.country, spec.base_url)
        self.brand_path_template = spec.brand_path_template or f"{self.base_url}/brand/{{brand}}"

    def probe_source(self, fetcher: Any) -> ProbeResult:
        self.probe_attempted = True
        self.probe = probe_url(self.source_id, self.base_url, attempts=2)
        if not self.probe.reachable:
            self.degraded = True
            self.last_error = self.probe.failure_class
        return self.probe

    def build_index(self, fetcher: Any, sample_skus: list[str] | None = None) -> int:
        self.executed = True
        # Prefer brands requested by the run; fall back to a short known list.
        brands = [
            "dasqua",
            "insize",
            "ast-power",
            "chumpower",
            "asimeto",
            "tiger-tec",
            "yowax",
            "san-ou",
            "mitutoyo",
            "terma",
            "groz",
            "et",
            "mighty-seven",
        ]
        # sample_skus unused for brand list; optional brand hints via attribute
        hint_brands = getattr(self, "_brand_hints", None)
        if hint_brands:
            brands = list(dict.fromkeys([*hint_brands, *brands]))[:20]
        for brand in brands:
            url = self.brand_path_template.format(brand=brand)
            try:
                status, body, _ctype, final = fetcher.get(url, fail_code="brand_page")
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                continue
            if status != 200:
                continue
            html = body.decode("utf-8", errors="replace")
            for m in _HREF_RE.finditer(html):
                href = urljoin(final or url, m.group(1))
                # Extract possible model tokens from slug
                slug = href.rstrip("/").split("/")[-1]
                tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_/]{2,}", slug)
                # Also extract dashed model codes like 1041-2215
                tokens.extend(re.findall(r"\d{2,5}-\d{2,5}[A-Za-z]?", slug))
                tokens.extend(re.findall(r"[A-Z]{1,6}\d{2,5}[A-Z0-9\-]*", slug, re.I))
                for tok in tokens:
                    key = normalize_sku(tok)
                    if key and key not in self._index:
                        self._index[key] = IndexedHit(
                            sku=tok,
                            title=slug.replace("-", " "),
                            page_url=href,
                            image_urls=[],
                            brand_text=brand,
                        )
        return len(self._index)

    def enrich_hit(self, fetcher: Any, hit: IndexedHit, sku: str) -> IndexedHit:
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
        if not exact_sku_in_text(sku, f"{title}\n{html[:8000]}\n{hit.page_url}"):
            return hit
        urls, _ev, _pdp = extract_product_images(html, final or hit.page_url, sku=sku)
        hit.title = title or hit.title
        hit.image_urls = urls[:5]
        return hit

    def search_sku_on_site(self, fetcher: Any, product_sku: str, brand_key: str) -> IndexedHit | None:
        """Fallback: try brand page + slug contains SKU."""
        brand = _brand_slug(brand_key) if brand_key else ""
        candidates = []
        if brand:
            candidates.append(self.brand_path_template.format(brand=brand))
        # Direct product slug guess patterns used by abzarmarket
        slug_sku = product_sku.lower().replace(" ", "-")
        if brand:
            candidates.append(f"{self.base_url}/product/{brand}-{slug_sku}")
            candidates.append(f"{self.base_url}/product/{brand}-{slug_sku}-a")
        for url in candidates:
            try:
                status, body, _ctype, final = fetcher.get(url, fail_code="search_fetch")
            except Exception:
                continue
            if status != 200:
                continue
            html = body.decode("utf-8", errors="replace")
            title = extract_title(html)
            subject = f"{title}\n{html[:8000]}\n{final}"
            if not exact_sku_in_text(product_sku, subject):
                # brand listing page — scan product links
                for m in _HREF_RE.finditer(html):
                    href = urljoin(final or url, m.group(1))
                    if normalize_sku(product_sku) in normalize_sku(href):
                        hit = IndexedHit(sku=product_sku, title="", page_url=href, image_urls=[], brand_text=brand)
                        return self.enrich_hit(fetcher, hit, product_sku)
                continue
            urls, _ev, has_pdp = extract_product_images(html, final or url, sku=product_sku)
            if has_pdp and urls:
                return IndexedHit(
                    sku=product_sku,
                    title=title,
                    page_url=final or url,
                    image_urls=urls[:5],
                    brand_text=brand,
                )
        return None
