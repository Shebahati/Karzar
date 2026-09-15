"""Dataclasses for the read-only zcc.ir catalog pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


@dataclass
class DiscoveryUrl:
    url: str
    kind: str
    lastmod: str | None = None
    sitemap_image_urls: list[str] = field(default_factory=list)
    evidence_method: str = "sitemap"


@dataclass
class FetchResult:
    url: str
    ok: bool
    status: int | None = None
    body: str = ""
    error: str | None = None
    from_cache: bool = False
    elapsed_ms: int | None = None
    content_type: str = ""


@dataclass
class SourceProduct:
    source_site: str
    source_url: str
    canonical_url: str | None
    source_product_id: str | None
    source_slug: str | None
    source_internal_sku: str | None
    brand: str | None
    brand_normalized: str | None
    brand_evidence: str | None
    sku: str | None
    manufacturer_code: str | None
    model: str | None
    part_number: str | None
    name_fa: str | None
    name_original: str | None
    category_path: list[str]
    source_category: str | None
    source_subcategory: str | None
    source_category_url: str | None
    short_description: str | None
    description: str | None
    price_raw: str | None
    price_currency: str | None
    price_normalized: str | None
    price_status: str | None
    availability_raw: str | None
    availability_normalized: str | None
    main_image_url: str | None
    gallery_image_urls: list[str]
    technical_specs: dict[str, str]
    attributes: dict[str, str]
    weight: str | None
    dimensions: str | None
    source_last_modified: str | None
    crawl_timestamp: str | None
    evidence_method: str
    parse_confidence: str
    parse_flags: list[str]
    jsonld_brand: str | None
    image_source: str | None
    gallery_count: int
    commerce_authority: str
    parser_version: str
    product_type: str | None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: _jsonable(v) for k, v in data.items()}


@dataclass
class BrandRow:
    brand_source_name: str
    normalized_brand: str | None
    karzar_brand_match: str | None
    karzar_brand_id: str | None
    confidence: str
    status: str
    product_count: int
    evidence: str = ""


@dataclass
class CategoryMapRow:
    source_category_path: str
    source_category_name: str
    source_product_count: int
    karzar_category_id: str | None
    karzar_category_path: str | None
    mapping_status: str
    mapping_confidence: str
    mapping_reason: str


@dataclass
class ReconcileRow:
    source_url: str
    brand_normalized: str | None
    manufacturer_code: str | None
    source_internal_sku: str | None
    name_fa: str | None
    status: str
    match_method: str | None
    karzar_id: str | None
    karzar_sku: str | None
    karzar_name: str | None
    karzar_brand: str | None
    source_price_toman: str | None
    karzar_price_toman: str | None
    source_availability: str | None
    karzar_availability: str | None
    review_reason: str | None
    commerce_authority: str
    parse_flags: str = ""


@dataclass
class QualityIssue:
    kind: str
    key: str
    count: int
    examples: list[str]
    message: str
