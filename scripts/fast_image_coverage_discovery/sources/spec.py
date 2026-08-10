"""SourceSpec definitions (no adapter imports — avoids cycles)."""

from __future__ import annotations

from dataclasses import dataclass

IRANIAN_DOMAINS = frozenset(
    {
        "shopmilltools.com",
        "www.shopmilltools.com",
        "azarsanat.net",
        "www.azarsanat.net",
        "abzarmarket.com",
        "www.abzarmarket.com",
        "abzarham.com",
        "www.abzarham.com",
        "abzarsara.com",
        "www.abzarsara.com",
    }
)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    domain: str
    lane: str
    country: str
    source_class: str
    adapter_type: str
    base_url: str
    wc_store_api: str | None = None
    sitemap_url: str | None = None
    brand_path_template: str | None = None
    enabled: bool = True
    notes: str = ""


DEFAULT_SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        source_id="shopmill_wc",
        domain="shopmilltools.com",
        lane="IR-1",
        country="IR",
        source_class="iranian_retailer",
        adapter_type="wc_store",
        base_url="https://shopmilltools.com",
        wc_store_api="https://shopmilltools.com/wp-json/wc/store/v1/products",
    ),
    SourceSpec(
        source_id="azarsanat_wc",
        domain="azarsanat.net",
        lane="IR-1",
        country="IR",
        source_class="iranian_retailer",
        adapter_type="wc_store",
        base_url="https://azarsanat.net",
        wc_store_api="https://azarsanat.net/wp-json/wc/store/v1/products",
    ),
    SourceSpec(
        source_id="abzarmarket_html",
        domain="abzarmarket.com",
        lane="IR-1",
        country="IR",
        source_class="iranian_retailer",
        adapter_type="html_index",
        base_url="https://abzarmarket.com",
        brand_path_template="https://abzarmarket.com/brand/{brand}",
        notes="priority Iranian PDP/brand catalog",
    ),
    SourceSpec(
        source_id="abzarham_sitemap",
        domain="abzarham.com",
        lane="IR-2",
        country="IR",
        source_class="iranian_retailer",
        adapter_type="sitemap",
        base_url="https://abzarham.com",
        sitemap_url="https://abzarham.com/pa_brand-sitemap.xml",
    ),
    SourceSpec(
        source_id="dasqua_official",
        domain="www.dasqua.com",
        lane="OFFICIAL",
        country="CN",
        source_class="official_manufacturer",
        adapter_type="sitemap",
        base_url="https://www.dasqua.com",
        sitemap_url="https://www.dasqua.com/sitemap.xml",
    ),
    SourceSpec(
        source_id="insize_tosag",
        domain="www.insize.com",
        lane="OFFICIAL",
        country="CN",
        source_class="official_manufacturer",
        adapter_type="configured_but_unsupported_adapter",
        base_url="https://www.insize.com",
        notes="topology probe required; not counted as investigated until adapter implemented",
    ),
    SourceSpec(
        source_id="sanou_official",
        domain="www.sanou.com",
        lane="OFFICIAL",
        country="CN",
        source_class="official_manufacturer",
        adapter_type="configured_but_unsupported_adapter",
        base_url="https://www.sanou.com",
        notes="probe topology before adapter selection",
    ),
    SourceSpec(
        source_id="prior_artifact_reuse",
        domain="local.prior-artifact",
        lane="REUSE",
        country="XX",
        source_class="prior_artifact",
        adapter_type="prior_artifact",
        base_url="file:///prior",
    ),
)


def is_iranian_domain(domain: str) -> bool:
    d = domain.lower().strip(".")
    return d in IRANIAN_DOMAINS or d.endswith(".ir")


def sources_for_lane(lane: str) -> list[SourceSpec]:
    return [s for s in DEFAULT_SOURCES if s.lane == lane and s.enabled]


def allowed_page_hosts() -> frozenset[str]:
    hosts: set[str] = set()
    for spec in DEFAULT_SOURCES:
        if spec.adapter_type == "prior_artifact":
            continue
        d = spec.domain.lower()
        hosts.add(d)
        if d.startswith("www."):
            hosts.add(d[4:])
        else:
            hosts.add("www." + d)
    return frozenset(hosts)
