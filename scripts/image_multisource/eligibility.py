"""Deterministic eligibility universe for IMG-02C batch-001."""

from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from . import MultisourceError


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _pids_from_rows(rows: list[dict[str, str]], field: str = "product_id") -> set[str]:
    out: set[str] = set()
    for row in rows:
        pid = (row.get(field) or "").strip()
        if pid:
            out.add(pid)
    return out


def load_r2_seed_exclusions(r2_zip_or_dir: Path) -> dict[str, set[str]]:
    """Load IMG-02B-R2 exclusions: stable accepted, source-drift, manual/ineligible."""
    stable: set[str] = set()
    drift: set[str] = set()
    manual: set[str] = set()

    def ingest_from_root(root: Path) -> None:
        accepted = root / "consolidated" / "all-accepted-manifest.csv"
        drift_path = root / "consolidated" / "all-source-drift-review.csv"
        manual_path = root / "consolidated" / "all-manual-review.csv"
        if accepted.is_file():
            stable.update(_pids_from_rows(_load_csv_rows(accepted)))
        if drift_path.is_file():
            drift.update(_pids_from_rows(_load_csv_rows(drift_path)))
        if manual_path.is_file():
            for row in _load_csv_rows(manual_path):
                pid = (row.get("product_id") or "").strip()
                if not pid:
                    continue
                eligible = (
                    row.get("eligible_for_automatic_discovery") or ""
                ).strip().casefold()
                status = (row.get("discovery_status") or "").strip().casefold()
                if eligible == "false" or status in {"manual_review", "source_drift_review"}:
                    manual.add(pid)

    if r2_zip_or_dir.is_dir():
        ingest_from_root(r2_zip_or_dir)
    elif r2_zip_or_dir.is_file() and r2_zip_or_dir.suffix.casefold() == ".zip":
        with zipfile.ZipFile(r2_zip_or_dir) as zf:
            # Prefer consolidated members under IMG-02B-R2/
            members = {
                "accepted": None,
                "drift": None,
                "manual": None,
            }
            for name in zf.namelist():
                norm = name.replace("\\", "/")
                if norm.endswith("consolidated/all-accepted-manifest.csv"):
                    members["accepted"] = norm
                elif norm.endswith("consolidated/all-source-drift-review.csv"):
                    members["drift"] = norm
                elif norm.endswith("consolidated/all-manual-review.csv"):
                    members["manual"] = norm
            if not members["accepted"] or not members["drift"] or not members["manual"]:
                raise MultisourceError(
                    "eligibility",
                    "IMG-02B-R2 zip missing consolidated accepted/drift/manual CSVs",
                )
            import io

            for key, member in members.items():
                assert member is not None
                text = zf.read(member).decode("utf-8-sig")
                rows = list(csv.DictReader(io.StringIO(text)))
                pids = _pids_from_rows(rows)
                if key == "accepted":
                    stable |= pids
                elif key == "drift":
                    drift |= pids
                else:
                    for row in rows:
                        pid = (row.get("product_id") or "").strip()
                        if not pid:
                            continue
                        eligible = (
                            row.get("eligible_for_automatic_discovery") or ""
                        ).strip().casefold()
                        status = (row.get("discovery_status") or "").strip().casefold()
                        if (
                            eligible == "false"
                            or status in {"manual_review", "source_drift_review"}
                        ):
                            manual.add(pid)
    else:
        raise MultisourceError("eligibility", f"invalid R2 seed path: {r2_zip_or_dir}")

    return {
        "stable_sourced": stable,
        "source_drift": drift,
        "manual_or_ineligible": manual,
    }


def build_eligibility_report(
    *,
    worklist_csv: Path,
    r2_seed: Path,
) -> dict[str, Any]:
    if not worklist_csv.is_file():
        raise MultisourceError("eligibility", f"worklist missing: {worklist_csv}")
    rows = _load_csv_rows(worklist_csv)
    if not rows:
        raise MultisourceError("eligibility", "worklist is empty")

    exclusions = load_r2_seed_exclusions(r2_seed)
    stable = set(exclusions["stable_sourced"])
    drift = set(exclusions["source_drift"])
    manual_seed = set(exclusions["manual_or_ineligible"])

    hold_pids: set[str] = set()
    ineligible_auto: set[str] = set()
    by_pid: dict[str, dict[str, str]] = {}
    for row in rows:
        pid = (row.get("product_id") or "").strip()
        if not pid:
            raise MultisourceError("eligibility", "worklist row missing product_id")
        if pid in by_pid:
            raise MultisourceError("eligibility", f"duplicate product_id in worklist: {pid}")
        by_pid[pid] = row
        if (row.get("work_type") or "").strip() == "manual_review_hold":
            hold_pids.add(pid)
        if (row.get("eligible_for_automatic_discovery") or "").strip().casefold() != "true":
            ineligible_auto.add(pid)

    # Manual/ineligible union: original hold + worklist ineligible + R2 governed manual/drift
    manual_ineligible = set(hold_pids) | set(ineligible_auto) | set(manual_seed) | set(drift)

    # Already sourced = stable accepted relations from R2
    already_sourced = set(stable)

    remaining: list[dict[str, str]] = []
    for pid, row in sorted(by_pid.items(), key=lambda kv: int(kv[0])):
        if pid in already_sourced:
            continue
        if pid in drift:
            continue
        if pid in manual_ineligible:
            continue
        remaining.append(row)

    brand_counts = Counter((r.get("brand_key") or "") for r in remaining)
    work_type_counts = Counter((r.get("work_type") or "") for r in remaining)
    priority_counts = Counter((r.get("priority") or "") for r in remaining)

    report = {
        "schema_version": 1,
        "task_id": "IMG-02C",
        "node_id": "IMG-02C-01-MULTISOURCE-BATCH-001",
        "inputs": {
            "worklist_csv": str(worklist_csv),
            "r2_seed": str(r2_seed),
        },
        "totals": {
            "total_governed_work_items": len(by_pid),
            "already_sourced": len(already_sourced),
            "source_drift": len(drift),
            "manual_or_ineligible": len(manual_ineligible),
            "remaining_eligible": len(remaining),
        },
        "exclusion_sets": {
            "already_sourced_product_ids": sorted(already_sourced, key=lambda x: int(x)),
            "source_drift_product_ids": sorted(drift, key=lambda x: int(x)),
            "manual_or_ineligible_product_ids": sorted(
                manual_ineligible, key=lambda x: int(x)
            ),
        },
        "remaining_eligible_by_brand": dict(sorted(brand_counts.items())),
        "remaining_eligible_by_work_type": dict(sorted(work_type_counts.items())),
        "remaining_eligible_by_priority": dict(sorted(priority_counts.items())),
        "policy": {
            "exclude_original_manual_hold": True,
            "exclude_stable_sourced_relations": True,
            "exclude_source_drift_from_automatic_acceptance": True,
            "exclude_ineligible_for_automatic_discovery": True,
            "do_not_hardcode_remaining_total": True,
        },
        "remaining_eligible_product_ids": [
            (r.get("product_id") or "").strip() for r in remaining
        ],
    }
    # Fail closed: remaining must not intersect exclusions.
    rem_ids = set(report["remaining_eligible_product_ids"])
    if rem_ids & already_sourced:
        raise MultisourceError("eligibility", "remaining intersects already_sourced")
    if rem_ids & drift:
        raise MultisourceError("eligibility", "remaining intersects source_drift")
    if rem_ids & hold_pids:
        raise MultisourceError("eligibility", "remaining intersects manual_hold")
    return report


def write_eligibility_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def select_calibration_sample(
    report: dict[str, Any],
    worklist_csv: Path,
    *,
    brand_key: str,
    limit: int = 20,
) -> list[dict[str, str]]:
    if limit < 1 or limit > 20:
        raise MultisourceError("eligibility", "calibration limit must be 1..20")
    eligible_ids = set(report["remaining_eligible_product_ids"])
    rows = _load_csv_rows(worklist_csv)
    sample = [
        r
        for r in rows
        if (r.get("product_id") or "").strip() in eligible_ids
        and (r.get("brand_key") or "").strip() == brand_key
    ]
    sample.sort(
        key=lambda r: (
            (r.get("priority") or ""),
            (r.get("sku") or "").casefold(),
            int(r.get("product_id") or 0),
        )
    )
    return sample[:limit]
