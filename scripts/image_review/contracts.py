"""Contracts and constants for IMG-02A-02 human-review batches."""

from __future__ import annotations

from typing import Any

TASK_ID = "IMG-02A-02"
PILOT_BATCH_ID = "IMG-02A-02-PILOT-001"
REVIEW_SCHEMA_VERSION = 1
AUTHORITATIVE_CHECKSUMS_DIGEST = (
    "4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d"
)

REQUIRED_SOURCE_FILES = (
    "inventory.csv",
    "inventory.json",
    "summary.json",
    "run-metadata.json",
    "duplicate-exact-sha.csv",
    "checksums.sha256",
)

EXPECTED_SOURCE_SUMMARY: dict[str, Any] = {
    "total_products": 5918,
    "total_product_images": 1194,
    "valid_local_image_rows": 1193,
    "external_remote_rows": 1,
    "missing_local_file_rows": 0,
    "decode_failed_rows": 0,
    "unique_local_asset_sha256s": 614,
    "exact_duplicate_sha_groups": 188,
    "cross_product_duplicate_sha_groups": 188,
    "cross_brand_duplicate_sha_groups": 0,
}

PILOT_UNIQUE_ASSETS = 100
PILOT_SHARED_COUNT = 50
PILOT_SINGLETON_COUNT = 50

PREVIEW_MAX_EDGE = 1600
THUMB_MAX_EDGE = 420
PREVIEW_JPEG_QUALITY = 90

WATERMARK_STATUS_VALUES = (
    "unreviewed",
    "none_visible",
    "manufacturer_brand",
    "distributor_or_retailer",
    "marketplace_or_third_party",
    "unknown_text_or_logo",
    "ambiguous",
)
QUALITY_STATUS_VALUES = ("unreviewed", "good", "acceptable", "weak", "poor", "unusable")
BACKGROUND_STATUS_VALUES = (
    "unreviewed",
    "clean_white",
    "clean_neutral",
    "acceptable_context",
    "busy",
    "problematic_transparency",
    "unknown",
)
CROP_STATUS_VALUES = (
    "unreviewed",
    "good",
    "too_tight",
    "excessive_whitespace",
    "clipped",
    "wrong_orientation",
    "unknown",
)
ASSET_DECISION_VALUES = (
    "UNREVIEWED",
    "KEEP",
    "KEEP_AS_SECONDARY",
    "PREFER_REPLACEMENT",
    "REPLACE_REQUIRED",
    "MANUAL_REVIEW",
    "BROKEN_OR_UNAVAILABLE",
)
RIGHTS_STATUS_VALUES = (
    "review_required",
    "unknown",
    "official_source_candidate",
    "authorized_distributor_candidate",
    "cleared_by_owner",
)
SUITABILITY_STATUS_VALUES = (
    "unreviewed",
    "exact_or_likely_exact",
    "family_shared_plausible",
    "likely_mismatch",
    "insufficient_context",
)
ASSIGNMENT_DECISION_VALUES = ASSET_DECISION_VALUES

ASSET_MANIFEST_FIELDS = (
    "asset_id",
    "sha256",
    "source_relative_path",
    "byte_size",
    "mime_type",
    "detected_format",
    "width",
    "height",
    "reference_count",
    "product_count",
    "brand_count",
    "image_ids",
    "product_ids",
    "brands",
    "is_exact_duplicate_group",
    "is_cross_product_shared",
    "is_cross_brand_shared",
    "selection_segment",
    "selection_rank",
    "preview_filename",
    "thumb_filename",
    "watermark_prescreen",
    "watermark_review_required",
    "min_dimension",
    "max_dimension",
    "megapixels",
    "aspect_ratio",
    "alpha_present",
    "border_lightness_mean",
    "border_uniformity_score",
    "sharpness_score",
    "low_resolution_candidate",
    "extreme_aspect_candidate",
    "transparent_background_candidate",
    "busy_or_nonuniform_border_candidate",
)

ASSIGNMENT_MANIFEST_FIELDS = (
    "assignment_id",
    "asset_id",
    "image_id",
    "product_id",
    "sku",
    "product_slug",
    "product_name",
    "brand_id",
    "brand_name",
    "category_id",
    "category_name",
    "is_primary",
    "display_order",
    "image_url",
)

ASSET_REVIEW_TEMPLATE_FIELDS = (
    "review_schema_version",
    "batch_id",
    "asset_id",
    "watermark_status",
    "quality_status",
    "background_status",
    "crop_status",
    "asset_decision",
    "rights_status",
    "asset_notes",
)

ASSIGNMENT_REVIEW_TEMPLATE_FIELDS = (
    "review_schema_version",
    "batch_id",
    "assignment_id",
    "asset_id",
    "image_id",
    "product_id",
    "suitability_status",
    "assignment_decision",
    "assignment_notes",
)


class ReviewError(Exception):
    """Fail-closed operator error for IMG-02A-02."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")
