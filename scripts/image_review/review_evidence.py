"""Validate completed IMG-02A-02 human-review evidence against batch manifests."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .contracts import REVIEW_SCHEMA_VERSION, ReviewError

_UNREVIEWED_TOKENS = ("UNREVIEWED", "unreviewed")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate_human_review_bundle(
    review_dir: Path,
    *,
    batch_dir: Path | None = None,
    pilot_dir: Path | None = None,
    expected_asset_count: int | None = None,
    expected_assignment_count: int | None = None,
    expected_batch_id: str | None = None,
) -> dict[str, Any]:
    """
    Validate identity contract and return aggregate counters.

    ``pilot_dir`` remains accepted as an alias of ``batch_dir`` for Pilot 001 callers.
    """
    package_dir = batch_dir or pilot_dir
    if package_dir is None:
        raise ReviewError("review", "batch_dir (or pilot_dir) is required")

    asset_path = review_dir / "asset-review.csv"
    asg_path = review_dir / "assignment-review.csv"
    state_path = review_dir / "review-state.json"
    for p in (asset_path, asg_path, state_path):
        if not p.is_file():
            raise ReviewError("review", f"missing review file: {p.name}")

    assets = _read_csv(asset_path)
    assignments = _read_csv(asg_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))

    if state.get("review_schema_version") != REVIEW_SCHEMA_VERSION:
        raise ReviewError("review", "review-state schema version mismatch")

    package_assets = {r["asset_id"]: r for r in _read_csv(package_dir / "asset-manifest.csv")}
    package_asgs = {
        r["assignment_id"]: r for r in _read_csv(package_dir / "assignment-manifest.csv")
    }

    asset_count = expected_asset_count if expected_asset_count is not None else len(package_assets)
    asg_count = (
        expected_assignment_count
        if expected_assignment_count is not None
        else len(package_asgs)
    )
    if asset_count != len(package_assets) or asg_count != len(package_asgs):
        raise ReviewError(
            "review",
            "expected counts do not match package manifests "
            f"(assets {asset_count}/{len(package_assets)}, "
            f"assignments {asg_count}/{len(package_asgs)})",
        )

    batch_id = expected_batch_id or str(
        state.get("batch_id")
        or (assets[0].get("batch_id") if assets else "")
        or ""
    )
    if not batch_id:
        raise ReviewError("review", "batch_id missing from review evidence")
    if state.get("batch_id") != batch_id:
        raise ReviewError("review", "review-state batch_id mismatch")

    if len(assets) != asset_count or len(assignments) != asg_count:
        raise ReviewError(
            "review",
            f"unexpected row counts assets={len(assets)} assignments={len(assignments)}",
        )

    asset_ids = [r["asset_id"] for r in assets]
    asg_ids = [r["assignment_id"] for r in assignments]
    if len(set(asset_ids)) != asset_count or len(set(asg_ids)) != asg_count:
        raise ReviewError("review", "duplicate review IDs")
    if set(asset_ids) != set(package_assets):
        raise ReviewError("review", "asset review IDs do not exactly cover batch assets")
    if set(asg_ids) != set(package_asgs):
        raise ReviewError("review", "assignment review IDs do not exactly cover batch")
    if set(state.get("assets", {})) != set(package_assets):
        raise ReviewError("review", "review-state assets do not cover batch")
    if set(state.get("assignments", {})) != set(package_asgs):
        raise ReviewError("review", "review-state assignments do not cover batch")

    state_blob = json.dumps(state, ensure_ascii=False)
    for token in _UNREVIEWED_TOKENS:
        if token in state_blob:
            raise ReviewError("review", f"review-state contains {token}")
    for row in assets + assignments:
        for value in row.values():
            if value in _UNREVIEWED_TOKENS:
                raise ReviewError("review", f"CSV contains {value}")
        if str(row.get("batch_id")) != batch_id:
            raise ReviewError("review", "CSV batch_id mismatch")
        if str(row.get("review_schema_version")) != str(REVIEW_SCHEMA_VERSION):
            raise ReviewError("review", "CSV schema version mismatch")

    for row in assets:
        if row.get("rights_status") != "review_required":
            raise ReviewError(
                "review", f"rights_status must stay review_required: {row['asset_id']}"
            )
        if row.get("rights_status") == "cleared_by_owner":
            raise ReviewError("review", "cleared_by_owner is forbidden")
        s = state["assets"][row["asset_id"]]
        for key in (
            "watermark_status",
            "quality_status",
            "background_status",
            "crop_status",
            "asset_decision",
            "rights_status",
            "asset_notes",
        ):
            if s.get(key) != row.get(key):
                raise ReviewError("review", f"state/CSV mismatch asset {row['asset_id']} {key}")

    for row in assignments:
        package = package_asgs[row["assignment_id"]]
        if row["asset_id"] != package["asset_id"]:
            raise ReviewError("review", "assignment asset_id drift")
        if str(row["image_id"]) != str(package["image_id"]):
            raise ReviewError("review", "assignment image_id drift")
        if str(row["product_id"]) != str(package["product_id"]):
            raise ReviewError("review", "assignment product_id drift")
        s = state["assignments"][row["assignment_id"]]
        for key in ("suitability_status", "assignment_decision", "assignment_notes"):
            if s.get(key) != row.get(key):
                raise ReviewError(
                    "review", f"state/CSV mismatch assignment {row['assignment_id']} {key}"
                )

    aggregates = {
        "batch_id": batch_id,
        "assets_reviewed": asset_count,
        "assignments_reviewed": asg_count,
        "watermark": dict(Counter(r["watermark_status"] for r in assets)),
        "asset_decisions": dict(Counter(r["asset_decision"] for r in assets)),
        "assignment_suitability": dict(
            Counter(r["suitability_status"] for r in assignments)
        ),
        "assignment_decisions": dict(
            Counter(r["assignment_decision"] for r in assignments)
        ),
        "replace_required_assignments": sum(
            1 for r in assignments if r.get("assignment_decision") == "REPLACE_REQUIRED"
        ),
        "manual_review_assignments": sum(
            1 for r in assignments if r.get("assignment_decision") == "MANUAL_REVIEW"
        ),
    }
    return aggregates
