"""INSIZE first/second-run drift and materialization reconciliation (external)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _key(row: dict[str, str]) -> str:
    return (row.get("product_id") or "").strip() or (row.get("sku") or "").strip()


def reconcile_insize_candidate_runs(
    *,
    first_run_dir: Path,
    second_run_dir: Path,
    materialization_dir: Path | None = None,
    requested: int = 263,
) -> dict[str, Any]:
    """Compare two candidate CSVs by product_id; optionally reconcile materialization."""
    first = _load_candidates(first_run_dir / "candidate-input.csv")
    second = _load_candidates(second_run_dir / "candidate-input.csv")
    by1 = {_key(r): r for r in first if _key(r)}
    by2 = {_key(r): r for r in second if _key(r)}
    keys1, keys2 = set(by1), set(by2)
    stable = sorted(keys1 & keys2)
    removed = sorted(keys1 - keys2)
    added = sorted(keys2 - keys1)

    detail_changes: list[dict[str, str]] = []
    image_changes: list[dict[str, str]] = []
    for k in stable:
        a, b = by1[k], by2[k]
        if (a.get("source_detail_url") or "") != (b.get("source_detail_url") or ""):
            detail_changes.append(
                {
                    "product_id": k,
                    "sku": a.get("sku") or "",
                    "before": a.get("source_detail_url") or "",
                    "after": b.get("source_detail_url") or "",
                }
            )
        if (a.get("source_image_url") or "") != (b.get("source_image_url") or ""):
            image_changes.append(
                {
                    "product_id": k,
                    "sku": a.get("sku") or "",
                    "before": a.get("source_image_url") or "",
                    "after": b.get("source_image_url") or "",
                }
            )

    sku_1120 = {
        "first": next((r for r in first if (r.get("sku") or "") == "1120-500"), None),
        "second": next((r for r in second if (r.get("sku") or "") == "1120-500"), None),
    }

    changed_or_removed = sorted(
        set(removed)
        | {c["product_id"] for c in detail_changes}
        | {c["product_id"] for c in image_changes}
    )
    stable_intersection = [
        k
        for k in stable
        if k not in {c["product_id"] for c in detail_changes}
        and k not in {c["product_id"] for c in image_changes}
    ]

    materialization: dict[str, Any] = {}
    if materialization_dir is not None:
        rejected_path = materialization_dir / "manifests" / "rejected.csv"
        manifest_path = materialization_dir / "manifests" / "manifest.csv"
        rejected = (
            list(csv.DictReader(rejected_path.open(encoding="utf-8")))
            if rejected_path.is_file()
            else []
        )
        accepted = (
            list(csv.DictReader(manifest_path.open(encoding="utf-8")))
            if manifest_path.is_file()
            else []
        )
        reason_dist = Counter(r.get("reason_code") or "" for r in rejected)
        unique_assets = len({r.get("sha256") for r in accepted if r.get("sha256")})
        # Family/duplicate relationships among accepted rows
        by_sha: dict[str, list[str]] = {}
        for r in accepted:
            digest = (r.get("sha256") or "").strip()
            if digest:
                by_sha.setdefault(digest, []).append(r.get("sku") or "")
        family_groups = {k: v for k, v in by_sha.items() if len(v) > 1}
        materialization = {
            "discovered_candidates": len(first),
            "materialized_rows": len(accepted),
            "non_materialized_rows": len(rejected),
            "non_materialized_reason_distribution": dict(reason_dist),
            "unique_assets": unique_assets,
            "family_or_duplicate_asset_groups": {
                k: v for k, v in sorted(family_groups.items())
            },
            "family_group_count": len(family_groups),
        }

    report = {
        "first_run_candidates": len(first),
        "second_run_candidates": len(second),
        "stable_intersection": len(stable_intersection),
        "unchanged_candidates": len(stable_intersection),
        "removed_candidates": removed,
        "added_candidates": added,
        "detail_url_changes": detail_changes,
        "image_url_changes": image_changes,
        "source_drift_rows": changed_or_removed,
        "source_drift_count": len(changed_or_removed),
        "sku_1120_500": {
            "first": (
                {
                    "sku": sku_1120["first"].get("sku"),
                    "detail": sku_1120["first"].get("source_detail_url"),
                    "image": sku_1120["first"].get("source_image_url"),
                }
                if sku_1120["first"]
                else None
            ),
            "second": (
                {
                    "sku": sku_1120["second"].get("sku"),
                    "detail": sku_1120["second"].get("source_detail_url"),
                    "image": sku_1120["second"].get("source_image_url"),
                }
                if sku_1120["second"]
                else None
            ),
        },
        "policy": {
            "stable_intersection": "eligible_for_normal_review",
            "changed_or_removed": "discovery_status=source_drift_review; automatic_acceptance=false",
        },
        "coverage": {
            "candidate_discovery_coverage_pct": round(
                100.0 * len(stable_intersection) / requested, 2
            )
            if requested
            else 0.0,
            "validated_materialization_coverage_pct": round(
                100.0
                * int(materialization.get("materialized_rows") or 0)
                / requested,
                2,
            )
            if requested
            else 0.0,
        },
        "materialization": materialization,
    }
    return report


def write_insize_reconcile_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
