"""Contracts for IMG-FAST-01B one-image discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DiscoveryStatus = Literal["green_exact", "yellow_review", "red_rejected", "unresolved"]
OwnerUsagePolicy = Literal["iranian_source_allowed", "non_iranian_not_precleared"]
DriftStatus = Literal[
    "active_seed_missing",
    "resolved_since_baseline",
    "removed_since_baseline",
    "new_missing_since_baseline",
]

GREEN_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "product_name",
    "category",
    "source_domain",
    "source_country",
    "source_class",
    "source_page_url",
    "source_image_url",
    "match_type",
    "brand_evidence",
    "sku_model_evidence",
    "page_identity_evidence",
    "gallery_identity_evidence",
    "asset_sha256",
    "asset_relative_path",
    "width",
    "height",
    "format",
    "owner_usage_policy",
    "discovery_status",
    "temporary_primary_eligible",
    "discovery_timestamp",
]

YELLOW_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "product_name",
    "category",
    "source_domain",
    "source_page_url",
    "source_image_url",
    "reason_code",
    "missing_evidence",
    "best_known_evidence",
    "asset_sha256",
    "asset_relative_path",
    "width",
    "height",
    "recommended_action",
    "discovery_timestamp",
]

RED_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "source_domain",
    "source_page_url",
    "source_image_url",
    "reason_code",
    "reason_detail",
    "attempt_timestamp",
]

ATTEMPT_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "source_id",
    "source_domain",
    "lane",
    "source_page_url",
    "source_image_url",
    "outcome",
    "reason_code",
    "reason_detail",
    "attempt_timestamp",
]


class DiscoveryError(Exception):
    """Fatal discovery configuration or integrity error."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass
class SeedProduct:
    product_id: int
    sku: str
    brand_key: str
    category_id: int | None
    category_slug: str
    product_name: str
    current_state: str
    suggested_discovery_lane: str
    notes: str = ""


@dataclass
class RunProduct:
    product_id: int
    sku: str
    brand_key: str
    category_slug: str
    product_name: str
    origin: str  # active_seed_missing | new_missing_since_baseline
    brand_sort_key: str = ""


@dataclass
class DriftRow:
    product_id: int
    sku: str
    brand_key: str
    drift_status: DriftStatus
    notes: str = ""


@dataclass
class MaterializedAsset:
    sha256: str
    relative_path: str
    width: int
    height: int
    format: str
    byte_size: int
    mime_type: str
    source_url: str
    phash: str = ""


@dataclass
class DiscoveryCandidate:
    product_id: int
    sku: str
    brand_key: str
    product_name: str
    category: str
    source_id: str
    source_domain: str
    source_country: str
    source_class: str
    lane: str
    source_page_url: str
    source_image_url: str
    match_type: str
    brand_evidence: str
    sku_model_evidence: str
    page_identity_evidence: str
    gallery_identity_evidence: str
    owner_usage_policy: OwnerUsagePolicy
    discovery_status: DiscoveryStatus
    temporary_primary_eligible: bool
    asset: MaterializedAsset | None = None
    reason_code: str = ""
    missing_evidence: str = ""
    best_known_evidence: str = ""
    recommended_action: str = ""
    discovery_timestamp: str = ""
    stop_search: bool = False

    def as_green_row(self) -> dict[str, Any]:
        if self.discovery_status != "green_exact" or self.asset is None:
            raise ValueError("green row requires materialized asset")
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "brand_key": self.brand_key,
            "product_name": self.product_name,
            "category": self.category,
            "source_domain": self.source_domain,
            "source_country": self.source_country,
            "source_class": self.source_class,
            "source_page_url": self.source_page_url,
            "source_image_url": self.source_image_url,
            "match_type": self.match_type,
            "brand_evidence": self.brand_evidence,
            "sku_model_evidence": self.sku_model_evidence,
            "page_identity_evidence": self.page_identity_evidence,
            "gallery_identity_evidence": self.gallery_identity_evidence,
            "asset_sha256": self.asset.sha256,
            "asset_relative_path": self.asset.relative_path,
            "width": self.asset.width,
            "height": self.asset.height,
            "format": self.asset.format,
            "owner_usage_policy": self.owner_usage_policy,
            "discovery_status": self.discovery_status,
            "temporary_primary_eligible": self.temporary_primary_eligible,
            "discovery_timestamp": self.discovery_timestamp,
        }

    def as_yellow_row(self) -> dict[str, Any]:
        asset = self.asset
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "brand_key": self.brand_key,
            "product_name": self.product_name,
            "category": self.category,
            "source_domain": self.source_domain,
            "source_page_url": self.source_page_url,
            "source_image_url": self.source_image_url,
            "reason_code": self.reason_code,
            "missing_evidence": self.missing_evidence,
            "best_known_evidence": self.best_known_evidence,
            "asset_sha256": asset.sha256 if asset else "",
            "asset_relative_path": asset.relative_path if asset else "",
            "width": asset.width if asset else "",
            "height": asset.height if asset else "",
            "recommended_action": self.recommended_action,
            "discovery_timestamp": self.discovery_timestamp,
        }

    def as_red_row(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "brand_key": self.brand_key,
            "source_domain": self.source_domain,
            "source_page_url": self.source_page_url,
            "source_image_url": self.source_image_url,
            "reason_code": self.reason_code,
            "reason_detail": self.missing_evidence or self.best_known_evidence,
            "attempt_timestamp": self.discovery_timestamp,
        }

    def as_attempt_row(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "brand_key": self.brand_key,
            "source_id": self.source_id,
            "source_domain": self.source_domain,
            "lane": self.lane,
            "source_page_url": self.source_page_url,
            "source_image_url": self.source_image_url,
            "outcome": self.discovery_status,
            "reason_code": self.reason_code,
            "reason_detail": self.missing_evidence or self.best_known_evidence,
            "attempt_timestamp": self.discovery_timestamp,
        }


@dataclass
class ProductTerminalState:
    product_id: int
    final_status: Literal["green_exact", "yellow_review", "unresolved"]
    stop_search: bool = False
    best_yellow: DiscoveryCandidate | None = None
    green: DiscoveryCandidate | None = None
    attempts: list[DiscoveryCandidate] = field(default_factory=list)


@dataclass
class SourceHealth:
    source_id: str
    domain: str
    lane: str
    status: str
    calibration_passed: bool
    bulk_enabled: bool
    products_matched: int = 0
    greens: int = 0
    last_error: str = ""


@dataclass
class DiscoveryRunState:
    api_base: str
    package_dir: str
    seed_manifest_sha256: str
    baseline_seed_total: int = 4708
    active_seed_missing: int = 0
    resolved_since_baseline: int = 0
    removed_since_baseline: int = 0
    new_missing_since_baseline: int = 0
    run_discovery_universe_total: int = 0
    products: dict[int, ProductTerminalState] = field(default_factory=dict)
    source_health: dict[str, SourceHealth] = field(default_factory=dict)
    url_cache: dict[str, str] = field(default_factory=dict)
    sha_assets: dict[str, str] = field(default_factory=dict)

    def to_checkpoint(self) -> dict[str, Any]:
        def _cand(c: DiscoveryCandidate | None) -> dict[str, Any] | None:
            if c is None:
                return None
            asset = None
            if c.asset is not None:
                asset = {
                    "sha256": c.asset.sha256,
                    "relative_path": c.asset.relative_path,
                    "width": c.asset.width,
                    "height": c.asset.height,
                    "format": c.asset.format,
                    "byte_size": c.asset.byte_size,
                    "mime_type": c.asset.mime_type,
                    "source_url": c.asset.source_url,
                }
            return {
                "product_id": c.product_id,
                "sku": c.sku,
                "brand_key": c.brand_key,
                "product_name": c.product_name,
                "category": c.category,
                "source_id": c.source_id,
                "source_domain": c.source_domain,
                "source_country": c.source_country,
                "source_class": c.source_class,
                "lane": c.lane,
                "source_page_url": c.source_page_url,
                "source_image_url": c.source_image_url,
                "match_type": c.match_type,
                "brand_evidence": c.brand_evidence,
                "sku_model_evidence": c.sku_model_evidence,
                "page_identity_evidence": c.page_identity_evidence,
                "gallery_identity_evidence": c.gallery_identity_evidence,
                "owner_usage_policy": c.owner_usage_policy,
                "discovery_status": c.discovery_status,
                "temporary_primary_eligible": c.temporary_primary_eligible,
                "reason_code": c.reason_code,
                "missing_evidence": c.missing_evidence,
                "best_known_evidence": c.best_known_evidence,
                "recommended_action": c.recommended_action,
                "discovery_timestamp": c.discovery_timestamp,
                "stop_search": c.stop_search,
                "asset": asset,
            }

        return {
            "api_base": self.api_base,
            "package_dir": self.package_dir,
            "seed_manifest_sha256": self.seed_manifest_sha256,
            "baseline_seed_total": self.baseline_seed_total,
            "active_seed_missing": self.active_seed_missing,
            "resolved_since_baseline": self.resolved_since_baseline,
            "removed_since_baseline": self.removed_since_baseline,
            "new_missing_since_baseline": self.new_missing_since_baseline,
            "run_discovery_universe_total": self.run_discovery_universe_total,
            "terminals": {
                str(pid): {
                    "final_status": ps.final_status,
                    "stop_search": ps.stop_search,
                    "green": _cand(ps.green),
                    "best_yellow": _cand(ps.best_yellow),
                    "attempts": [_cand(a) for a in ps.attempts if a is not None],
                }
                for pid, ps in self.products.items()
            },
            "url_cache": self.url_cache,
            "sha_assets": self.sha_assets,
        }
