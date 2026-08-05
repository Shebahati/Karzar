"""Output writers for candidate discovery lanes (external only)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from . import CANDIDATE_FIELDS, CandidateDiscoveryError
from .worklists import sha256_file


def assert_external_output(path: Path, repo_root: Path) -> Path:
    if not path.is_absolute():
        raise CandidateDiscoveryError("output", f"output-dir must be absolute: {path}")
    if path.is_symlink():
        raise CandidateDiscoveryError("output", f"output-dir must not be a symlink: {path}")
    try:
        path.resolve().relative_to(repo_root.resolve())
        raise CandidateDiscoveryError("output", f"output-dir must be outside repository: {path}")
    except ValueError:
        pass
    return path


def ensure_absent_or_empty(path: Path) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise CandidateDiscoveryError("output", f"invalid output path: {path}")
        if list(path.iterdir()):
            raise CandidateDiscoveryError("output", f"output-dir is not empty: {path}")
        return
    path.mkdir(parents=True, exist_ok=False)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_lane_outputs(
    output_dir: Path,
    *,
    repo_root: Path,
    lane_id: str,
    brand_key: str,
    candidates: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    manual: list[dict[str, Any]],
    summary: dict[str, Any],
    run_state: dict[str, Any],
) -> dict[str, Any]:
    out = assert_external_output(output_dir, repo_root)
    ensure_absent_or_empty(out)
    (out / "evidence").mkdir()
    (out / "logs").mkdir()
    (out / "assets").mkdir()

    write_csv(out / "candidate-input.csv", candidates, CANDIDATE_FIELDS)
    write_csv(
        out / "rejected-candidates.csv",
        rejected,
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
    write_csv(
        out / "manual-review.csv",
        manual,
        [
            "lane_id",
            "product_id",
            "sku",
            "product_name",
            "reason_code",
            "reason_detail",
            "source_detail_url",
            "notes",
        ],
    )
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "run-state.json").write_text(
        json.dumps(run_state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    members = [
        "candidate-input.csv",
        "rejected-candidates.csv",
        "manual-review.csv",
        "summary.json",
        "run-state.json",
    ]
    lines = [f"{sha256_file(out / name)}  {name}" for name in members]
    (out / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "output_dir": str(out),
        "lane_id": lane_id,
        "brand_key": brand_key,
        "candidate_count": len(candidates),
        "rejected_count": len(rejected),
        "manual_count": len(manual),
        "checksums_digest": sha256_file(out / "checksums.sha256"),
    }


def stable_candidate_id(parts: list[str]) -> str:
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
