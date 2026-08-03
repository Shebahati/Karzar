"""Versioned review label schemas and templates."""

from __future__ import annotations

from typing import Any

from .contracts import (
    ASSET_DECISION_VALUES,
    ASSET_REVIEW_TEMPLATE_FIELDS,
    ASSIGNMENT_DECISION_VALUES,
    ASSIGNMENT_REVIEW_TEMPLATE_FIELDS,
    BACKGROUND_STATUS_VALUES,
    CROP_STATUS_VALUES,
    QUALITY_STATUS_VALUES,
    REVIEW_SCHEMA_VERSION,
    RIGHTS_STATUS_VALUES,
    SUITABILITY_STATUS_VALUES,
    WATERMARK_STATUS_VALUES,
)


def review_schema_document(batch_id: str) -> dict[str, Any]:
    return {
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "batch_id_default": batch_id,
        "asset_level": {
            "watermark_status": list(WATERMARK_STATUS_VALUES),
            "quality_status": list(QUALITY_STATUS_VALUES),
            "background_status": list(BACKGROUND_STATUS_VALUES),
            "crop_status": list(CROP_STATUS_VALUES),
            "asset_decision": list(ASSET_DECISION_VALUES),
            "rights_status": list(RIGHTS_STATUS_VALUES),
            "defaults": {
                "watermark_status": "unreviewed",
                "quality_status": "unreviewed",
                "background_status": "unreviewed",
                "crop_status": "unreviewed",
                "asset_decision": "UNREVIEWED",
                "rights_status": "review_required",
                "asset_notes": "",
            },
            "never_auto_set": ["cleared_by_owner"],
        },
        "assignment_level": {
            "suitability_status": list(SUITABILITY_STATUS_VALUES),
            "assignment_decision": list(ASSIGNMENT_DECISION_VALUES),
            "defaults": {
                "suitability_status": "unreviewed",
                "assignment_decision": "UNREVIEWED",
                "assignment_notes": "",
            },
        },
        "notes": {
            "watermark_vs_rights": (
                "Visible manufacturer logos are not automatic rights clearance. "
                "rights_status remains independent of watermark_status."
            ),
            "prescreen": "Technical pre-screen flags are advisory only; humans decide.",
        },
    }


def asset_review_template_rows(batch_id: str, asset_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset_id in asset_ids:
        rows.append(
            {
                "review_schema_version": REVIEW_SCHEMA_VERSION,
                "batch_id": batch_id,
                "asset_id": asset_id,
                "watermark_status": "unreviewed",
                "quality_status": "unreviewed",
                "background_status": "unreviewed",
                "crop_status": "unreviewed",
                "asset_decision": "UNREVIEWED",
                "rights_status": "review_required",
                "asset_notes": "",
            }
        )
    return rows


def assignment_review_template_rows(
    batch_id: str, assignments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a in assignments:
        rows.append(
            {
                "review_schema_version": REVIEW_SCHEMA_VERSION,
                "batch_id": batch_id,
                "assignment_id": a["assignment_id"],
                "asset_id": a["asset_id"],
                "image_id": a["image_id"],
                "product_id": a["product_id"],
                "suitability_status": "unreviewed",
                "assignment_decision": "UNREVIEWED",
                "assignment_notes": "",
            }
        )
    return rows


ASSET_TEMPLATE_FIELDS = ASSET_REVIEW_TEMPLATE_FIELDS
ASSIGNMENT_TEMPLATE_FIELDS = ASSIGNMENT_REVIEW_TEMPLATE_FIELDS
