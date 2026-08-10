"""Shared contracts for IMG-FAST-01A."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from . import STATES


class BaselineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class ProductListItem:
    product_id: int
    sku: str
    slug: str | None
    name: str
    brand_key: str | None
    brand_id: int | None
    category_id: int | None
    category_slug: str | None
    category_name: str | None
    thumbnail: str | None


@dataclass(frozen=True)
class DetailImage:
    image_id: int | None
    url: str
    is_primary: bool
    display_order: int


@dataclass
class AssetValidation:
    url: str
    normalized_url: str
    http_status: int | None = None
    final_url: str | None = None
    content_type: str | None = None
    byte_size: int | None = None
    decode_ok: bool = False
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    error: str | None = None
    is_known_placeholder: bool = False
    attempts: int = 0
    transient_exhausted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductClassification:
    product_id: int
    sku: str
    slug: str | None
    name: str
    brand_key: str | None
    brand_id: int | None
    category_id: int | None
    category_slug: str | None
    category_name: str | None
    image_state: str
    primary_image_present: bool
    primary_image_reference: str | None
    primary_decode_ok: bool | None
    primary_width: int | None
    primary_height: int | None
    primary_sha256: str | None
    primary_http_status: int | None
    placeholder_flag: bool
    broken_flag: bool
    fast_coverage_needed: bool
    priority_tier: str = "unassigned"
    priority_basis: str = "none"
    reason_code: str = ""
    notes: str = ""
    detail_fetched: bool = False
    images_count: int = 0
    reusable_image_id: int | None = None
    reusable_image_url: str | None = None
    reusable_is_primary: bool | None = None
    reusable_display_order: int | None = None
    reusable_decode_ok: bool | None = None
    reusable_width: int | None = None
    reusable_height: int | None = None
    reusable_sha256: str | None = None
    reusable_selection_reason: str | None = None
    suggested_discovery_lane: str | None = None

    def __post_init__(self) -> None:
        if self.image_state not in STATES:
            raise BaselineError("state", f"invalid image_state {self.image_state!r}")


@dataclass
class RunCounters:
    product_list_requests: int = 0
    product_detail_requests: int = 0
    asset_validation_requests: int = 0
    count_429: int = 0
    count_5xx_exhausted: int = 0
    other_exhausted_network_failures: int = 0
    api_write_requests: int = 0
    external_discovery_requests: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class ScanResult:
    classifications: list[ProductClassification] = field(default_factory=list)
    asset_validations: list[AssetValidation] = field(default_factory=list)
    counters: RunCounters = field(default_factory=RunCounters)
    catalog_total: int = 0
    unique_product_ids: list[int] = field(default_factory=list)
    authority_notes: dict[str, Any] = field(default_factory=dict)
