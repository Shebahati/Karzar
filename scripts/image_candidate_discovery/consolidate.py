"""Consolidate IMG-02B per-lane discovery outputs (external only)."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import TASK_ID
from .output import assert_external_output, ensure_absent_or_empty, write_csv
from .worklists import sha256_file

MANUAL_FIELDS = [
    "lane_id",
    "product_id",
    "product_key",
    "sku",
    "product_name",
    "work_type",
    "work_reasons",
    "priority",
    "reason_code",
    "reason_detail",
    "source_detail_url",
    "discovery_status",
    "eligible_for_automatic_discovery",
    "notes",
]


def _normalize_manual_row(row: dict[str, str]) -> dict[str, str]:
    product_id = (row.get("product_id") or "").strip()
    out = {k: (row.get(k) or "") for k in MANUAL_FIELDS}
    if not out["product_key"] and product_id:
        out["product_key"] = f"product_id:{product_id}"
    if not out["discovery_status"]:
        out["discovery_status"] = "manual_review"
    out["eligible_for_automatic_discovery"] = "false"
    return out


def _drift_to_manual(row: dict[str, str]) -> dict[str, str]:
    return _normalize_manual_row(
        {
            "lane_id": row.get("lane_id") or "IMG-02B-03",
            "product_id": row.get("product_id") or "",
            "product_key": row.get("product_key") or "",
            "sku": row.get("sku") or "",
            "product_name": row.get("product_name") or "",
            "work_type": row.get("work_type") or "",
            "work_reasons": row.get("work_reasons") or "",
            "priority": row.get("priority") or "",
            "reason_code": row.get("reason_code") or "source_drift_review",
            "reason_detail": row.get("reason_detail") or "",
            "source_detail_url": row.get("first_detail_url")
            or row.get("source_detail_url")
            or "",
            "discovery_status": "source_drift_review",
            "eligible_for_automatic_discovery": "false",
            "notes": row.get("notes") or "",
        }
    )


def consolidate_lane_outputs(
    *,
    lane_dirs: dict[str, Path],
    download_dirs: dict[str, Path] | None,
    output_dir: Path,
    repo_root: Path,
    accepted_manifest_by_brand: dict[str, Path] | None = None,
    drift_review_csvs: list[Path] | None = None,
) -> dict[str, Any]:
    out = assert_external_output(output_dir, repo_root)
    ensure_absent_or_empty(out)

    all_accepted: list[dict[str, str]] = []
    all_rejected: list[dict[str, str]] = []
    all_manual: list[dict[str, str]] = []
    all_drift: list[dict[str, str]] = []
    coverage_brand: list[dict[str, str]] = []
    coverage_work_type: list[dict[str, str]] = []
    lane_summaries: dict[str, Any] = {}

    sha_to_brands: dict[str, set[str]] = defaultdict(set)
    sha_to_skus: dict[str, set[str]] = defaultdict(set)
    accepted_overrides = accepted_manifest_by_brand or {}

    for brand, lane_dir in sorted(lane_dirs.items()):
        summary = json.loads((lane_dir / "summary.json").read_text(encoding="utf-8"))
        lane_summaries[brand] = summary
        with (lane_dir / "candidate-input.csv").open(encoding="utf-8") as f:
            cands = list(csv.DictReader(f))
        with (lane_dir / "rejected-candidates.csv").open(encoding="utf-8") as f:
            rejs = list(csv.DictReader(f))
        with (lane_dir / "manual-review.csv").open(encoding="utf-8") as f:
            mans = list(csv.DictReader(f))
        all_rejected.extend(rejs)
        for man in mans:
            all_manual.append(_normalize_manual_row(man))

        accepted_count = 0
        unique_assets = 0
        mans_rows: list[dict[str, str]] = []
        override = accepted_overrides.get(brand)
        if override is not None and override.is_file():
            with override.open(encoding="utf-8") as f:
                mans_rows = list(csv.DictReader(f))
        elif (
            download_dirs
            and brand in download_dirs
            and (download_dirs[brand] / "manifests" / "manifest.csv").is_file()
        ):
            with (download_dirs[brand] / "manifests" / "manifest.csv").open(
                encoding="utf-8"
            ) as f:
                mans_rows = list(csv.DictReader(f))

        if mans_rows:
            for row in mans_rows:
                all_accepted.append(row)
                accepted_count += 1
                digest = (row.get("sha256") or "").strip()
                if digest:
                    sha_to_brands[digest].add(brand)
                    sha_to_skus[digest].add(row.get("sku") or "")
            unique_assets = len({r.get("sha256") for r in mans_rows if r.get("sha256")})
        else:
            # Candidate-only stage: treat ready candidates as pre-download accepted queue
            for row in cands:
                if (row.get("discovery_status") or "") == "source_drift_review":
                    continue
                all_accepted.append(
                    {
                        "brand": brand,
                        "sku": row.get("sku") or "",
                        "product_id": row.get("product_id") or "",
                        "source_detail_url": row.get("source_detail_url") or "",
                        "source_image_url": row.get("source_image_url") or "",
                        "rights_status": row.get("rights_status") or "review_required",
                        "lane_id": row.get("lane_id") or "",
                        "work_type": row.get("work_type") or "",
                        "sha256": "",
                    }
                )
            accepted_count = len(
                [
                    r
                    for r in cands
                    if (r.get("discovery_status") or "") != "source_drift_review"
                ]
            )

        requested = int(summary.get("requested") or 0)
        coverage_brand.append(
            {
                "brand_key": brand,
                "requested": str(requested),
                "candidates": str(len(cands)),
                "accepted_or_queued": str(accepted_count),
                "rejected": str(len(rejs)),
                "manual_review": str(len(mans)),
                "unique_downloaded_assets": str(unique_assets),
                "coverage_pct": (
                    f"{(100.0 * accepted_count / requested):.2f}" if requested else "0.00"
                ),
            }
        )
        wt = Counter(r.get("work_type") or "" for r in cands)
        for work_type, count in sorted(wt.items()):
            coverage_work_type.append(
                {
                    "brand_key": brand,
                    "work_type": work_type,
                    "candidate_count": str(count),
                }
            )

    for path in drift_review_csvs or []:
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                all_drift.append(dict(row))
                all_manual.append(_drift_to_manual(row))

    # Fail closed: accepted must not contain drift product IDs when drift provided.
    drift_pids = {(r.get("product_id") or "").strip() for r in all_drift}
    drift_pids.discard("")
    if drift_pids:
        for row in all_accepted:
            pid = (row.get("product_id") or "").strip()
            if pid in drift_pids:
                raise ValueError(
                    f"accepted manifest contains drift product_id={pid}"
                )

    for row in all_manual:
        if (row.get("eligible_for_automatic_discovery") or "").casefold() != "false":
            row["eligible_for_automatic_discovery"] = "false"

    ordinary_manual = [
        r
        for r in all_manual
        if (r.get("discovery_status") or "") != "source_drift_review"
        and (r.get("reason_code") or "") != "source_drift_review"
    ]
    combined_governed = len(all_manual)

    cross: list[dict[str, str]] = []
    for digest, brands in sorted(sha_to_brands.items()):
        if len(brands) > 1:
            cross.append(
                {
                    "sha256": digest,
                    "brands": "|".join(sorted(brands)),
                    "skus": "|".join(sorted(s for s in sha_to_skus[digest] if s)),
                }
            )

    write_csv(
        out / "all-accepted-manifest.csv",
        all_accepted,
        sorted({k for row in all_accepted for k in row.keys()}) or ["sku"],
    )
    write_csv(
        out / "all-rejected-candidates.csv",
        all_rejected,
        [
            "lane_id",
            "product_id",
            "sku",
            "product_name",
            "reason_code",
            "reason_detail",
            "notes",
        ],
    )
    write_csv(out / "all-manual-review.csv", all_manual, MANUAL_FIELDS)
    if all_drift:
        write_csv(
            out / "all-source-drift-review.csv",
            all_drift,
            sorted({k for row in all_drift for k in row.keys()}) or ["product_id"],
        )
    write_csv(
        out / "cross-brand-duplicate-report.csv",
        cross,
        ["sha256", "brands", "skus"],
    )
    write_csv(
        out / "coverage-by-brand.csv",
        coverage_brand,
        [
            "brand_key",
            "requested",
            "candidates",
            "accepted_or_queued",
            "rejected",
            "manual_review",
            "unique_downloaded_assets",
            "coverage_pct",
        ],
    )
    write_csv(
        out / "coverage-by-work-type.csv",
        coverage_work_type,
        ["brand_key", "work_type", "candidate_count"],
    )

    summary = {
        "task_id": TASK_ID,
        "lanes": lane_summaries,
        "totals": {
            "stable_accepted_or_materialized": len(all_accepted),
            "accepted_or_queued": len(all_accepted),
            "rejected": len(all_rejected),
            "ordinary_manual_review": len(ordinary_manual),
            "source_drift_review": len(all_drift),
            "combined_governed_review": combined_governed,
            "manual_review": combined_governed,
            "cross_brand_duplicate_assets": len(cross),
        },
        "coverage_by_brand": coverage_brand,
        "rights_status": "review_required",
        "apply_status": "not_started",
        "safety": {
            "database_accessed": False,
            "ProductImage_modified": False,
            "application_storage_mutations": 0,
            "replacement_execution": False,
            "rights_cleared": 0,
        },
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "README.md").write_text(
        "# IMG-02B Parallel Discovery Consolidation\n\n"
        "External candidate discovery outputs for Dasqua, INSIZE and SAN OU.\n"
        "Stable accepted manifest excludes source-drift quarantine rows.\n"
        "rights_status=review_required; apply_status=not_started.\n"
        "Do not commit raw assets or manifests to Git.\n",
        encoding="utf-8",
    )
    members = [
        "all-accepted-manifest.csv",
        "all-rejected-candidates.csv",
        "all-manual-review.csv",
        "cross-brand-duplicate-report.csv",
        "coverage-by-brand.csv",
        "coverage-by-work-type.csv",
        "summary.json",
        "README.md",
    ]
    if all_drift:
        members.insert(3, "all-source-drift-review.csv")
    lines = [f"{sha256_file(out / m)}  {m}" for m in members]
    (out / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "output_dir": str(out),
        "checksums_digest": sha256_file(out / "checksums.sha256"),
        "summary": summary,
    }
