"""Source registry factory (IMG-FAST-01B R2)."""

from __future__ import annotations

from .base import SourceAdapter
from .html_index import HtmlIndexAdapter
from .prior_artifact import PriorArtifactAdapter
from .sitemap import SitemapAdapter
from .spec import (  # noqa: F401 — re-export
    DEFAULT_SOURCES,
    IRANIAN_DOMAINS,
    SourceSpec,
    allowed_page_hosts,
    is_iranian_domain,
    sources_for_lane,
)
from .wc_store_adapter import WooCommerceAdapter


def build_adapter(spec: SourceSpec) -> SourceAdapter | None:
    if spec.adapter_type == "wc_store":
        return WooCommerceAdapter(spec)
    if spec.adapter_type == "sitemap":
        return SitemapAdapter(spec)
    if spec.adapter_type == "html_index":
        return HtmlIndexAdapter(spec)
    if spec.adapter_type == "prior_artifact":
        return PriorArtifactAdapter(spec)
    if spec.adapter_type == "configured_but_unsupported_adapter":
        return None
    return None
