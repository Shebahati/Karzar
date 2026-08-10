"""Source registry and lane definitions."""

from __future__ import annotations

from dataclasses import dataclass

IRANIAN_TLD = frozenset({".ir"})
IRANIAN_DOMAINS = frozenset(
    {
        "shopmilltools.com",
        "www.shopmilltools.com",
        "azarsanat.net",
        "www.azarsanat.net",
        "abzarsara.com",
        "www.abzarsara.com",
        "persiantools.com",
        "www.persiantools.com",
    }
)


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    domain: str
    lane: str
    country: str
    source_class: str
    base_url: str
    wc_store_api: str | None = None
    sitemap_url: str | None = None
    enabled: bool = True


DEFAULT_SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        source_id="shopmill_wc",
        domain="shopmilltools.com",
        lane="IR-1",
        country="IR",
        source_class="iranian_retailer_wc",
        base_url="https://shopmilltools.com",
        wc_store_api="https://shopmilltools.com/wp-json/wc/store/v1/products",
    ),
    SourceSpec(
        source_id="azarsanat_wc",
        domain="azarsanat.net",
        lane="IR-1",
        country="IR",
        source_class="iranian_retailer_wc",
        base_url="https://azarsanat.net",
        wc_store_api="https://azarsanat.net/wp-json/wc/store/v1/products",
    ),
    SourceSpec(
        source_id="dasqua_official",
        domain="www.dasqua.com",
        lane="OFFICIAL",
        country="CN",
        source_class="official_manufacturer",
        base_url="https://www.dasqua.com",
        sitemap_url="https://www.dasqua.com/sitemap.xml",
    ),
    SourceSpec(
        source_id="insize_tosag",
        domain="www.insize.com",
        lane="OFFICIAL",
        country="CN",
        source_class="official_manufacturer",
        base_url="https://www.insize.com",
    ),
    SourceSpec(
        source_id="sanou_official",
        domain="www.sanou.com",
        lane="OFFICIAL",
        country="CN",
        source_class="official_manufacturer",
        base_url="https://www.sanou.com",
    ),
)


def is_iranian_domain(domain: str) -> bool:
    d = domain.lower().strip(".")
    if d in IRANIAN_DOMAINS or d.endswith(".ir"):
        return True
    return any(d.endswith(tld) for tld in IRANIAN_TLD)


def sources_for_lane(lane: str) -> list[SourceSpec]:
    return [s for s in DEFAULT_SOURCES if s.lane == lane and s.enabled]
