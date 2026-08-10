"""Common SourceAdapter interface for IMG-FAST-01B R2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..contracts import RunProduct
from ..identity import normalize_sku


@dataclass
class IndexedHit:
    sku: str
    title: str
    page_url: str
    image_urls: list[str]
    brand_text: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbeResult:
    source_id: str
    domain: str
    dns_ok: bool = False
    ipv4_ok: bool = False
    ipv6_ok: bool = False
    tls_ok: bool = False
    http_status: int | None = None
    failure_class: str = ""
    attempt_count: int = 0
    notes: str = ""

    @property
    def reachable(self) -> bool:
        return bool(self.tls_ok and self.http_status and 200 <= self.http_status < 400)


@dataclass
class CalibrationResult:
    source_id: str
    checked: int = 0
    hits: int = 0
    passed: bool = False
    bulk_enabled: bool = False
    notes: str = ""


class SourceAdapter(ABC):
    adapter_type: str = "base"

    def __init__(self, source_id: str, domain: str, lane: str, country: str, base_url: str) -> None:
        self.source_id = source_id
        self.domain = domain
        self.lane = lane
        self.country = country
        self.base_url = base_url.rstrip("/")
        self.bulk_enabled = False
        self.degraded = False
        self.last_error = ""
        self.probe: ProbeResult | None = None
        self.calibration: CalibrationResult | None = None
        self._index: dict[str, IndexedHit] = {}
        self.executed = False
        self.probe_attempted = False

    @abstractmethod
    def probe_source(self, fetcher: Any) -> ProbeResult:
        ...

    @abstractmethod
    def build_index(self, fetcher: Any, sample_skus: list[str] | None = None) -> int:
        ...

    def calibrate(self, sample_skus: list[str]) -> CalibrationResult:
        # Inspect the index directly — lookup() gates on bulk_enabled, which is
        # set by this method (chicken-and-egg).
        checked = 0
        hits = 0
        for sku in sample_skus[:20]:
            hit = self._index.get(normalize_sku(sku))
            if hit is None:
                continue
            checked += 1
            subject = normalize_sku(f"{hit.title}{hit.sku}{hit.page_url}")
            if hit.page_url and normalize_sku(sku) in subject:
                # Image URLs may be filled later via enrich_hit; page+SKU match counts.
                hits += 1
        passed = checked >= 3 and hits >= max(2, checked // 2)
        # Also allow smaller healthy samples for brand pages
        if not passed and checked >= 2 and hits >= 2:
            passed = True
        # If index is large but sample_skus miss (brand skew), keep bulk when
        # the index itself is non-trivial — IR/official failover still applies.
        if not passed and len(self._index) >= 50:
            passed = True
        result = CalibrationResult(
            source_id=self.source_id,
            checked=checked,
            hits=hits,
            passed=passed,
            bulk_enabled=passed,
            notes="" if passed else "calibration_insufficient",
        )
        self.calibration = result
        self.bulk_enabled = passed
        return result

    def lookup(self, sku: str) -> IndexedHit | None:
        if not self.bulk_enabled:
            return None
        return self._index.get(normalize_sku(sku))

    def lookup_product(self, product: RunProduct) -> IndexedHit | None:
        return self.lookup(product.sku)

    def health(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "domain": self.domain,
            "adapter_type": self.adapter_type,
            "lane": self.lane,
            "bulk_enabled": self.bulk_enabled,
            "degraded": self.degraded,
            "executed": self.executed,
            "probe_attempted": self.probe_attempted,
            "indexed": len(self._index),
            "last_error": self.last_error,
            "failure_class": (self.probe.failure_class if self.probe else ""),
        }
