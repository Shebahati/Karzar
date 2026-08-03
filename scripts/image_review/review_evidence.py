"""Validate completed IMG-02A-02 human-review evidence against Pilot manifests."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .contracts import PILOT_BATCH_ID, REVIEW_SCHEMA_VERSION, ReviewError


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate_human_review_bundle(
    review_dir: Path,
    *,
    pilot_dir: Path,
) -> dict[str, Any]:
    """Validate identity contract and return aggregate counters."""
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
    if state.get("batch_id") != PILOT_BATCH_ID:
        raise ReviewError("review", "review-state batch_id mismatch")

    pilot_assets = {r["asset_id"]: r for r in _read_csv(pilot_dir / "asset-manifest.csv")}
    pilot_asgs = {
        r["assignment_id"]: r for r in _read_csv(pilot_dir / "assignment-manifest.csv")
    }

    if len(assets) != 100 or len(assignments) != 465:
        raise ReviewError(
            "review",
            f"unexpected row counts assets={len(assets)} assignments={len(assignments)}",
        )

    asset_ids = [r["asset_id"] for r in assets]
    asg_ids = [r["assignment_id"] for r in assignments]
    if len(set(asset_ids)) != 100 or len(set(asg_ids)) != 465:
        raise ReviewError("review", "duplicate review IDs")
    if set(asset_ids) != set(pilot_assets):
        raise ReviewError("review", "asset review IDs do not exactly cover Pilot assets")
    if set(asg_ids) != set(pilot_asgs):
        raise ReviewError("review", "assignment review IDs do not exactly cover Pilot")
    if set(state.get("assets", {})) != set(pilot_assets):
        raise ReviewError("review", "review-state assets do not cover Pilot")
    if set(state.get("assignments", {})) != set(pilot_asgs):
        raise ReviewError("review", "review-state assignments do not cover Pilot")

    state_blob = json.dumps(state, ensure_ascii=False)
    if "UNREVIEWED" in state_blob:
        raise ReviewError("review", "review-state contains UNREVIEWED")
    for row in assets + assignments:
        if any(v == "UNREVIEWED" for v in row.values()):
            raise ReviewError("review", "CSV contains UNREVIEWED")
        if str(row.get("batch_id")) != PILOT_BATCH_ID:
            raise ReviewError("review", "CSV batch_id mismatch")
        if str(row.get("review_schema_version")) != str(REVIEW_SCHEMA_VERSION):
            raise ReviewError("review", "CSV schema version mismatch")

    for row in assets:
        if row.get("rights_status") != "review_required":
            raise ReviewError("review", f"rights_status must stay review_required: {row['asset_id']}")
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
        pilot = pilot_asgs[row["assignment_id"]]
        if row["asset_id"] != pilot["asset_id"]:
            raise ReviewError("review", "assignment asset_id drift")
        if str(row["image_id"]) != str(pilot["image_id"]):
            raise ReviewError("review", "assignment image_id drift")
        if str(row["product_id"]) != str(pilot["product_id"]):
            raise ReviewError("review", "assignment product_id drift")
        s = state["assignments"][row["assignment_id"]]
        for key in ("suitability_status", "assignment_decision", "assignment_notes"):
            if s.get(key) != row.get(key):
                raise ReviewError(
                    "review", f"state/CSV mismatch assignment {row['assignment_id']} {key}"
                )

    aggregates = {
        "assets_reviewed": 100,
        "assignments_reviewed": 465,
        "watermark": dict(Counter(r["watermark_status"] for r in assets)),
        "asset_decisions": dict(Counter(r["asset_decision"] for r in assets)),
        "assignment_suitability": dict(
            Counter(r["suitability_status"] for r in assignments)
        ),
        "assignment_decisions": dict(
            Counter(r["assignment_decision"] for r in assignments)
        ),
    }
    return aggregates
