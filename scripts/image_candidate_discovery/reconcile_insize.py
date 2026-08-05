"""INSIZE first/second-run drift and materialization reconciliation (external)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import CandidateDiscoveryError
from .output import assert_external_output, ensure_absent_or_empty, write_csv
from .worklists import sha256_file

STABLE_CANDIDATE_FIELDS = [
    "schema_version",
    "task_id",
    "lane_id",
    "product_id",
    "product_key",
    "sku",
    "product_name",
    "brand_key",
    "work_type",
    "work_reasons",
    "priority",
    "source_adapter",
    "source_class",
    "source_detail_url",
    "source_image_url",
    "source_image_index",
    "candidate_discovery_method",
    "candidate_match_basis",
    "manufacturer_evidence",
    "sku_evidence",
    "confidence",
    "rights_status",
    "apply_status",
    "discovery_status",
    "eligible_for_automatic_discovery",
    "notes",
]

DRIFT_REVIEW_FIELDS = [
    "product_id",
    "product_key",
    "sku",
    "product_name",
    "work_type",
    "work_reasons",
    "priority",
    "lane_id",
    "drift_type",
    "first_detail_url",
    "second_detail_url",
    "first_image_url",
    "second_image_url",
    "materialized",
    "local_asset_path",
    "asset_sha256",
    "review_status",
    "discovery_status",
    "eligible_for_automatic_discovery",
    "rights_status",
    "apply_status",
    "reason_code",
    "reason_detail",
    "notes",
]


def _load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _key(row: dict[str, str]) -> str:
    return (row.get("product_id") or "").strip() or (row.get("sku") or "").strip()


def _index_by_product(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        pid = (row.get("product_id") or "").strip()
        if not pid:
            raise CandidateDiscoveryError("reconcile", "missing product_id in row")
        if pid in out:
            raise CandidateDiscoveryError(
                "reconcile", f"duplicate product_id in source CSV: {pid}"
            )
        out[pid] = row
    return out


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
    if len(by1) != len(first):
        raise CandidateDiscoveryError("reconcile", "duplicate or missing keys in first run")
    if len(by2) != len(second):
        raise CandidateDiscoveryError("reconcile", "duplicate or missing keys in second run")
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
        by_sha: dict[str, list[str]] = {}
        for r in accepted:
            digest = (r.get("sha256") or "").strip()
            if digest:
                by_sha.setdefault(digest, []).append(r.get("sku") or "")
        family_groups = {k: v for k, v in by_sha.items() if len(v) > 1}
        materialization = {
            "discovered_candidates": len(first),
            "raw_materialized_rows": len(accepted),
            "materialized_rows": len(accepted),
            "non_materialized_rows": len(rejected),
            "non_materialized_reason_distribution": dict(reason_dist),
            "unique_assets": unique_assets,
            "family_or_duplicate_asset_groups": {
                k: v for k, v in sorted(family_groups.items())
            },
            "family_group_count": len(family_groups),
            "accepted_rows": accepted,
            "rejected_rows": rejected,
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
        "stable_product_ids": stable_intersection,
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
            "changed_or_removed": (
                "discovery_status=source_drift_review; "
                "eligible_for_automatic_discovery=false; "
                "normal_accepted_coverage=false"
            ),
        },
        "coverage": {
            "candidate_discovery_coverage_pct": round(
                100.0 * len(stable_intersection) / requested, 2
            )
            if requested
            else 0.0,
            # Raw/pre-quarantine figure kept for historical comparison only.
            "validated_materialization_coverage_pct": round(
                100.0
                * int(materialization.get("raw_materialized_rows") or 0)
                / requested,
                2,
            )
            if requested
            else 0.0,
            # Alias kept for readers; prefer stable_* after apply_insize_reconciliation.
            "raw_pre_quarantine_materialization_coverage_pct": round(
                100.0
                * int(materialization.get("raw_materialized_rows") or 0)
                / requested,
                2,
            )
            if requested
            else 0.0,
        },
        "materialization": {
            k: v
            for k, v in materialization.items()
            if k not in {"accepted_rows", "rejected_rows"}
        },
        "_materialization_rows": materialization,
        "_by_first": by1,
        "_by_second": by2,
    }
    return report


def write_insize_reconcile_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in report.items() if not k.startswith("_")}
    output_path.write_text(
        json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _drift_type(
    product_id: str,
    removed: set[str],
    detail_ids: set[str],
    image_ids: set[str],
) -> str:
    parts: list[str] = []
    if product_id in removed:
        parts.append("removed_in_second_run")
    if product_id in detail_ids:
        parts.append("detail_url_changed")
    if product_id in image_ids:
        parts.append("image_url_changed")
    return "|".join(parts) if parts else "source_drift"


def apply_insize_reconciliation(
    *,
    first_run_dir: Path,
    second_run_dir: Path,
    materialization_dir: Path,
    output_dir: Path,
    repo_root: Path,
    requested: int = 263,
) -> dict[str, Any]:
    """Write governed effective INSIZE outputs after applying drift quarantine."""
    out = assert_external_output(output_dir, repo_root)
    ensure_absent_or_empty(out)

    report = reconcile_insize_candidate_runs(
        first_run_dir=first_run_dir,
        second_run_dir=second_run_dir,
        materialization_dir=materialization_dir,
        requested=requested,
    )
    by1: dict[str, dict[str, str]] = report["_by_first"]
    by2: dict[str, dict[str, str]] = report["_by_second"]
    mat_bundle = report["_materialization_rows"]
    accepted_rows: list[dict[str, str]] = list(mat_bundle.get("accepted_rows") or [])
    rejected_rows: list[dict[str, str]] = list(mat_bundle.get("rejected_rows") or [])

    drift_ids = set(report["source_drift_rows"])
    stable_ids = set(report["stable_product_ids"])
    first_ids = set(by1)

    if drift_ids | stable_ids != first_ids:
        raise CandidateDiscoveryError(
            "reconcile",
            "incomplete partition: stable∪drift must equal first-run product IDs",
        )
    if drift_ids & stable_ids:
        raise CandidateDiscoveryError(
            "reconcile", "stable and drift product ID sets must be disjoint"
        )
    if len(stable_ids) + len(drift_ids) != len(first_ids):
        raise CandidateDiscoveryError(
            "reconcile",
            f"partition size mismatch: {len(stable_ids)}+{len(drift_ids)}!={len(first_ids)}",
        )
    if len(first_ids) != int(report["first_run_candidates"]):
        raise CandidateDiscoveryError(
            "reconcile", "report first_run_candidates disagrees with source CSV"
        )

    # Index materialization by product_id (fail closed on duplicates / missing id).
    acc_by_pid = _index_by_product(accepted_rows)
    rej_by_pid = _index_by_product(rejected_rows)
    for pid in acc_by_pid:
        if pid not in first_ids:
            raise CandidateDiscoveryError(
                "reconcile",
                f"manifest row product_id={pid} absent from first-run candidates",
            )
    for pid in rej_by_pid:
        if pid not in first_ids:
            raise CandidateDiscoveryError(
                "reconcile",
                f"rejected row product_id={pid} absent from first-run candidates",
            )
    for pid in drift_ids:
        if pid not in first_ids:
            raise CandidateDiscoveryError("reconcile", f"unknown drift product: {pid}")

    detail_ids = {c["product_id"] for c in report["detail_url_changes"]}
    image_ids = {c["product_id"] for c in report["image_url_changes"]}
    removed = set(report["removed_candidates"])

    stable_candidates: list[dict[str, Any]] = []
    for pid in sorted(stable_ids, key=lambda x: int(x)):
        row = dict(by1[pid])
        if (row.get("discovery_status") or "") == "source_drift_review":
            raise CandidateDiscoveryError(
                "reconcile", f"stable candidate {pid} marked source_drift_review"
            )
        row["discovery_status"] = row.get("discovery_status") or "candidate_ready"
        row["eligible_for_automatic_discovery"] = "true"
        row["notes"] = (row.get("notes") or "").strip()
        if row["notes"]:
            row["notes"] += "; "
        row["notes"] += "r2_stable_intersection"
        stable_candidates.append(row)

    drift_rows: list[dict[str, Any]] = []
    for pid in sorted(drift_ids, key=lambda x: int(x)):
        first = by1[pid]
        second = by2.get(pid)
        mat = acc_by_pid.get(pid)
        rej = rej_by_pid.get(pid)
        materialized = mat is not None
        drift_rows.append(
            {
                "product_id": pid,
                "product_key": first.get("product_key") or f"product_id:{pid}",
                "sku": first.get("sku") or "",
                "product_name": first.get("product_name") or "",
                "work_type": first.get("work_type") or "",
                "work_reasons": first.get("work_reasons") or "",
                "priority": first.get("priority") or "",
                "lane_id": first.get("lane_id") or "IMG-02B-03",
                "drift_type": _drift_type(pid, removed, detail_ids, image_ids),
                "first_detail_url": first.get("source_detail_url") or "",
                "second_detail_url": (second.get("source_detail_url") if second else "")
                or "",
                "first_image_url": first.get("source_image_url") or "",
                "second_image_url": (second.get("source_image_url") if second else "")
                or "",
                "materialized": "true" if materialized else "false",
                "local_asset_path": (mat.get("local_asset_path") if mat else "") or "",
                "asset_sha256": (mat.get("sha256") if mat else "") or "",
                "review_status": "source_drift_review",
                "discovery_status": "source_drift_review",
                "eligible_for_automatic_discovery": "false",
                "rights_status": "review_required",
                "apply_status": "not_started",
                "reason_code": "source_drift_review",
                "reason_detail": (
                    "first/second candidate run disagree; "
                    "excluded from normal accepted coverage"
                ),
                "notes": (
                    f"drift_type={_drift_type(pid, removed, detail_ids, image_ids)};"
                    f"materialized={'true' if materialized else 'false'};"
                    f"reject={(rej.get('reason_code') if rej else '')}"
                ),
            }
        )
        # Quarantine: must not remain candidate_ready / normal accepted.
        if (first.get("discovery_status") or "candidate_ready") == "candidate_ready":
            pass  # expected historically; effective output is drift review

    stable_materialized = [
        dict(acc_by_pid[pid])
        for pid in sorted(stable_ids, key=lambda x: int(x))
        if pid in acc_by_pid
    ]
    for row in stable_materialized:
        row["review_status"] = row.get("review_status") or "stable_review"
        row["notes"] = ((row.get("notes") or "") + "; r2_stable_materialized").strip("; ")

    drift_materialized_ids = {pid for pid in drift_ids if pid in acc_by_pid}
    if any(pid in {r.get("product_id") for r in stable_materialized} for pid in drift_materialized_ids):
        raise CandidateDiscoveryError(
            "reconcile", "materialized row present in both stable and drift outputs"
        )

    stable_rejected = [
        dict(rej_by_pid[pid])
        for pid in sorted(stable_ids, key=lambda x: int(x))
        if pid in rej_by_pid
    ]
    drift_rejected_ids = {pid for pid in drift_ids if pid in rej_by_pid}

    # Partition proofs against first-run size.
    n_stable_mat = len(stable_materialized)
    n_drift_mat = len(drift_materialized_ids)
    n_stable_non = len(stable_rejected)
    n_drift_non = len(drift_rejected_ids)
    # Drift rows may be neither in acc nor rej only if missing — fail closed.
    for pid in drift_ids:
        if pid not in acc_by_pid and pid not in rej_by_pid:
            raise CandidateDiscoveryError(
                "reconcile",
                f"drift product {pid} missing from both manifest and rejected",
            )
    for pid in stable_ids:
        if pid not in acc_by_pid and pid not in rej_by_pid:
            raise CandidateDiscoveryError(
                "reconcile",
                f"stable product {pid} missing from both manifest and rejected",
            )

    if n_stable_mat + n_drift_mat + n_stable_non + n_drift_non != len(first_ids):
        raise CandidateDiscoveryError(
            "reconcile",
            "materialization partition incomplete: "
            f"{n_stable_mat}+{n_drift_mat}+{n_stable_non}+{n_drift_non}!={len(first_ids)}",
        )
    if n_stable_mat + n_drift_mat != len(accepted_rows):
        raise CandidateDiscoveryError(
            "reconcile",
            f"raw materialized {len(accepted_rows)} != stable {n_stable_mat} + drift {n_drift_mat}",
        )
    if n_stable_non + n_drift_non != len(rejected_rows):
        raise CandidateDiscoveryError(
            "reconcile",
            f"raw rejected {len(rejected_rows)} != stable {n_stable_non} + drift {n_drift_non}",
        )

    write_csv(out / "stable-candidates.csv", stable_candidates, STABLE_CANDIDATE_FIELDS)
    write_csv(out / "source-drift-review.csv", drift_rows, DRIFT_REVIEW_FIELDS)
    write_csv(
        out / "stable-materialized-manifest.csv",
        stable_materialized,
        sorted({k for row in stable_materialized for k in row} or ["product_id"]),
    )
    write_csv(
        out / "stable-materialization-rejected.csv",
        stable_rejected,
        sorted({k for row in stable_rejected for k in row} or ["product_id"]),
    )

    stable_asset_hashes = sorted(
        {r.get("sha256") for r in stable_materialized if r.get("sha256")}
    )
    drift_asset_hashes = sorted(
        {r.get("asset_sha256") for r in drift_rows if r.get("asset_sha256")}
    )
    packaged_unique = sorted(
        {*(stable_asset_hashes), *(drift_asset_hashes)}
    )

    first_summary_path = first_run_dir / "summary.json"
    timing: dict[str, Any] = {
        "timing_status": "legacy_unreliable",
        "timing_used_for_governance": False,
    }
    if first_summary_path.is_file():
        first_summary = json.loads(first_summary_path.read_text(encoding="utf-8"))
        timing["historical_started_at"] = first_summary.get("started_at")
        timing["historical_finished_at"] = first_summary.get("finished_at")
        timing["historical_elapsed_seconds"] = first_summary.get("elapsed_seconds")

    summary = {
        "schema_version": 1,
        "task_id": "IMG-02B",
        "lane_id": "IMG-02B-03",
        "brand_key": "insize",
        "first_run_candidates": len(first_ids),
        "second_run_candidates": int(report["second_run_candidates"]),
        "stable_candidates": len(stable_candidates),
        "source_drift_rows": len(drift_rows),
        "raw_materialized_rows": len(accepted_rows),
        "stable_materialized_rows": n_stable_mat,
        "materialized_source_drift_rows": n_drift_mat,
        "stable_non_materialized_rows": n_stable_non,
        "non_materialized_source_drift_rows": n_drift_non,
        "coverage": {
            "stable_candidate_discovery_coverage_pct": round(
                100.0 * len(stable_candidates) / requested, 2
            ),
            "stable_validated_materialization_coverage_pct": round(
                100.0 * n_stable_mat / requested, 2
            ),
            "raw_pre_quarantine_materialization_coverage_pct": round(
                100.0 * len(accepted_rows) / requested, 2
            ),
            "requested": requested,
        },
        "assets": {
            "packaged_unique_assets": len(packaged_unique),
            "stable_accepted_asset_hashes": len(stable_asset_hashes),
            "drift_evidence_asset_hashes": len(drift_asset_hashes),
            "stable_accepted_asset_sha256": stable_asset_hashes,
            "drift_evidence_asset_sha256": drift_asset_hashes,
        },
        "policy": report["policy"],
        "timing": timing,
        "rights_status": "review_required",
        "apply_status": "not_started",
        "partition_proofs": {
            "candidates": f"{len(stable_candidates)}+{len(drift_rows)}={len(first_ids)}",
            "materialization": (
                f"{n_stable_mat}+{n_drift_mat}+{n_stable_non}+{n_drift_non}={len(first_ids)}"
            ),
        },
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_insize_reconcile_report(report, out / "reconcile-report.json")

    members = [
        "stable-candidates.csv",
        "source-drift-review.csv",
        "stable-materialized-manifest.csv",
        "stable-materialization-rejected.csv",
        "summary.json",
        "reconcile-report.json",
    ]
    lines = [f"{sha256_file(out / name)}  {name}" for name in members]
    (out / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "output_dir": str(out),
        "checksums_digest": sha256_file(out / "checksums.sha256"),
        "summary": summary,
        "stable_candidates": len(stable_candidates),
        "source_drift_rows": len(drift_rows),
        "stable_materialized_rows": n_stable_mat,
        "materialized_source_drift_rows": n_drift_mat,
    }
