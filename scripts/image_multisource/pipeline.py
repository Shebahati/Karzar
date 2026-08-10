"""Batch-001 orchestration for eligibility, registry snapshot, and calibration."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from . import BATCH_ID, NODE_ID, TASK_ID
from .calibrate import CalibrationResult, calibrate_source, summarize_calibrations
from .eligibility import build_eligibility_report, write_eligibility_report
from .output import (
    assert_external_output,
    ensure_absent_or_empty,
    write_checksums,
    write_csv,
    write_json,
)
from .registry import (
    builtin_known_host_registry,
    load_registry,
    sort_sources,
    write_registry_snapshot,
)

RELATION_FIELDS = [
    "schema_version",
    "task_id",
    "node_id",
    "batch_id",
    "product_id",
    "product_key",
    "sku",
    "brand_key",
    "work_type",
    "priority",
    "source_id",
    "source_class",
    "source_detail_url",
    "source_image_url",
    "match_basis",
    "discovery_status",
    "eligible_for_automatic_acceptance",
    "rights_status",
    "apply_status",
    "notes",
]


def run_foundation_and_calibration(
    *,
    worklist_csv: Path,
    r2_seed: Path,
    output_dir: Path,
    repo_root: Path,
    registry_path: Path | None = None,
    calibration_limit: int = 20,
    probes: dict[str, Any] | None = None,
    robots_txt_by_source: dict[str, str] | None = None,
) -> dict[str, Any]:
    out = assert_external_output(output_dir, repo_root)
    ensure_absent_or_empty(out)
    (out / "source-calibrations").mkdir()
    (out / "assets").mkdir()
    (out / "evidence").mkdir()

    sources = (
        load_registry(registry_path)
        if registry_path is not None
        else builtin_known_host_registry()
    )
    write_registry_snapshot(sources, out / "source-registry-snapshot.json")

    eligibility = build_eligibility_report(worklist_csv=worklist_csv, r2_seed=r2_seed)
    write_eligibility_report(eligibility, out / "eligibility-report.json")

    # Empty governed queues for calibration checkpoint (bulk discovery not started).
    empty_fields = RELATION_FIELDS
    for name in (
        "candidate-relations.csv",
        "stable-candidates.csv",
        "retailer-review.csv",
        "manual-review.csv",
        "rejected.csv",
    ):
        write_csv(out / name, [], empty_fields)

    write_csv(
        out / "asset-manifest.csv",
        [],
        [
            "asset_id",
            "sha256",
            "perceptual_hash",
            "source_image_url",
            "width",
            "height",
            "format",
            "byte_size",
            "quality_status",
            "watermark_status",
            "local_asset_path",
        ],
    )
    write_csv(out / "duplicate-groups.csv", [], ["group_key", "member_count", "asset_ids"])
    write_csv(
        out / "coverage-by-brand.csv",
        [
            {
                "brand_key": k,
                "remaining_eligible": str(v),
                "stable_candidates": "0",
                "retailer_review": "0",
            }
            for k, v in sorted(eligibility["remaining_eligible_by_brand"].items())
        ],
        ["brand_key", "remaining_eligible", "stable_candidates", "retailer_review"],
    )
    write_csv(
        out / "coverage-by-source-class.csv",
        [{"source_class": c, "enabled_sources": "0", "candidate_relations": "0"} for c in ("S1", "S2", "S3", "S4", "S5")],
        ["source_class", "enabled_sources", "candidate_relations"],
    )
    write_csv(
        out / "coverage-by-work-type.csv",
        [
            {"work_type": k, "remaining_eligible": str(v)}
            for k, v in sorted(eligibility["remaining_eligible_by_work_type"].items())
        ],
        ["work_type", "remaining_eligible"],
    )

    calib_results: list[CalibrationResult] = []
    probe_map = dict(probes or {})
    robots_map = dict(robots_txt_by_source or {})
    for source in sort_sources(sources):
        if source.authorization_status == "unknown":
            result = calibrate_source(
                source=source,
                eligibility_report=eligibility,
                worklist_csv=worklist_csv,
                output_dir=out / "source-calibrations",
                limit=min(calibration_limit, 1),
                probe=lambda _s, _r: {
                    "product_id": "",
                    "sku": "",
                    "status": "skipped",
                    "page_identity_ok": False,
                    "exact_sku_ok": False,
                    "redirect_ok": True,
                    "generic_category": False,
                    "parser_drift": False,
                    "asset_host_ok": False,
                    "notes": "unknown authorization — not probed",
                },
            )
            result.enabled_after_calibration = False
            result.disable_reason = "unknown_authorization"
            write_json(
                out / "source-calibrations" / f"{source.source_id}.json", result.to_dict()
            )
            calib_results.append(result)
            continue

        probe = probe_map.get(source.source_id)
        result = calibrate_source(
            source=source,
            eligibility_report=eligibility,
            worklist_csv=worklist_csv,
            output_dir=out / "source-calibrations",
            limit=calibration_limit,
            robots_txt=robots_map.get(source.source_id),
            probe=probe,
        )
        calib_results.append(result)

    calib_summary = summarize_calibrations(calib_results)

    # Update coverage-by-source-class with enabled counts
    enabled_by_class = Counter(
        r.source_class for r in calib_results if r.enabled_after_calibration
    )
    write_csv(
        out / "coverage-by-source-class.csv",
        [
            {
                "source_class": c,
                "enabled_sources": str(enabled_by_class.get(c, 0)),
                "candidate_relations": "0",
            }
            for c in ("S1", "S2", "S3", "S4", "S5")
        ],
        ["source_class", "enabled_sources", "candidate_relations"],
    )

    summary = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "batch_id": BATCH_ID,
        "phase": "calibration_checkpoint",
        "progress_suggested": 20,
        "eligibility_totals": eligibility["totals"],
        "calibration": calib_summary,
        "candidate_relations": 0,
        "unique_image_candidates": 0,
        "stable_candidates": 0,
        "retailer_review_candidates": 0,
        "manual_review_candidates": 0,
        "rejected_candidates": 0,
        "rights_status": "review_required",
        "apply_status": "not_started",
        "safety": {
            "database_accessed": False,
            "ProductImage_modified": False,
            "application_storage_mutations": 0,
            "images_applied": 0,
            "replacement_execution": False,
            "rights_cleared": 0,
            "raw_generated_output_tracked_in_git": 0,
        },
        "limits": {
            "per_host_concurrency": 2,
            "global_concurrency": 8,
            "delay_per_host_seconds": 0.8,
            "transient_retries": 2,
        },
        "seed": {
            "img02b_r2_stable_relations": eligibility["totals"]["already_sourced"],
            "img02b_r2_source_drift": eligibility["totals"]["source_drift"],
            "do_not_redownload_seed_assets_unnecessarily": True,
        },
    }
    write_json(out / "summary.json", summary)
    (out / "README.md").write_text(
        "# IMG-02C-01 Multisource Batch 001\n\n"
        "Calibration checkpoint only. Bulk discovery not started.\n"
        "rights_status=review_required; apply_status=not_started.\n"
        "Do not commit raw assets or manifests to Git.\n",
        encoding="utf-8",
    )

    members = [
        "source-registry-snapshot.json",
        "eligibility-report.json",
        "candidate-relations.csv",
        "stable-candidates.csv",
        "retailer-review.csv",
        "manual-review.csv",
        "rejected.csv",
        "asset-manifest.csv",
        "duplicate-groups.csv",
        "coverage-by-brand.csv",
        "coverage-by-source-class.csv",
        "coverage-by-work-type.csv",
        "summary.json",
        "README.md",
    ]
    # Include calibration JSON files in checksums for determinism of listed members only.
    checksums_digest = write_checksums(out, members)
    return {
        "output_dir": str(out),
        "checksums_digest": checksums_digest,
        "summary": summary,
        "eligibility": eligibility,
        "sources": [s.to_dict() for s in sources],
        "calibration": calib_summary,
    }


def enabled_source_ids(calib_summary: dict[str, Any]) -> set[str]:
    return {
        str(r["source_id"])
        for r in calib_summary.get("calibration_results") or []
        if r.get("enabled_after_calibration")
    }
