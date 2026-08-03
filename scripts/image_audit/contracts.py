"""Contracts, constants, and reason codes for IMG-02A-01 inventory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TASK_ID = "IMG-02A-01"
PUBLIC_PATH_MARKER = "/static/uploads/products/"
DEFAULT_STORAGE_REL = ("data", "uploads", "products")

PRIOR_REFERENCE_SNAPSHOT = {
    "total_products": 5917,
    "products_with_image_rows": 1193,
    "captured_from": "earlier catalog export",
}

URL_KINDS = frozenset(
    {
        "internal_static_absolute",
        "internal_static_relative",
        "external_http",
        "external_https",
        "unsupported_scheme",
        "malformed_url",
        "empty_url",
    }
)

STORAGE_ENTRY_STATUSES = frozenset(
    {
        "regular_image",
        "regular_non_image",
        "decode_failed",
        "symlink_rejected",
        "non_regular_rejected",
        "path_rejected",
    }
)

COVERAGE_STATUSES = frozenset(
    {
        "valid_local_primary",
        "valid_local_non_primary_only",
        "remote_unverified_primary",
        "remote_unverified_non_primary_only",
        "mixed_local_and_remote",
        "image_rows_but_none_usable",
        "no_image_rows",
        "deleted_product",
    }
)

# Pillow decompression-bomb ceiling (pixels). Align with cautious operator policy.
MAX_IMAGE_PIXELS = 89_478_485  # ~Pillow default

MAX_HASH_STREAM_CHUNK = 1024 * 1024
MAX_SIGNATURE_READ = 64 * 1024


class AuditError(Exception):
    """Operator-facing audit failure (fail-closed)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass
class ProductRow:
    product_id: int
    sku: str
    slug: str
    name: str
    category_id: int | None
    brand_id: int | None
    is_active: bool
    is_available: bool
    deleted_at: Any
    brand_name: str | None
    category_name: str | None


@dataclass
class ImageRow:
    image_id: int
    product_id: int
    image_url: str
    is_primary: bool
    display_order: int


@dataclass
class UrlClassification:
    url_kind: str
    sanitized_url: str
    url_host: str | None
    url_path: str | None
    query_present: bool
    mapped_relative_path: str | None = None
    reason_codes: list[str] = field(default_factory=list)


@dataclass
class FileMeta:
    local_exists: bool | None
    local_relative_path: str | None
    local_entry_status: str | None
    byte_size: int | None
    sha256: str | None
    detected_format: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    decode_status: str | None


@dataclass
class StorageEntry:
    relative_path: str
    status: str
    byte_size: int | None = None
    sha256: str | None = None
    detected_format: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    decode_status: str | None = None
    reason_codes: list[str] = field(default_factory=list)
