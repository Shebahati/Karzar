"""Write IMG-02B worklist artifacts outside the repository."""

from __future__ import annotations

import csv
import json
import stat
from pathlib import Path
from typing import Any

from .contracts import (
    SOURCE_PATH_CONTRACTS,
    TASK_ID,
    WORKLIST_FIELDS,
    WorklistError,
    sha256_file,
)


def _assert_external_output(path: Path, repo_root: Path) -> Path:
    if not path.is_absolute():
        raise WorklistError("output", f"output-dir must be absolute: {path}")
    if path.is_symlink():
        raise WorklistError("output", f"output-dir must not be a symlink: {path}")
    resolved = path.resolve()
    repo_resolved = repo_root.resolve()
    try:
        resolved.relative_to(repo_resolved)
        raise WorklistError("output", f"output-dir must be outside repository: {path}")
    except ValueError:
        pass
    return path


def _ensure_empty_or_governed(path: Path, *, allow_nonempty: bool) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise WorklistError("output", "output-dir must not be a symlink")
    children = list(path.iterdir())
    if children and not allow_nonempty:
        raise WorklistError("output", f"output-dir is not empty: {path}")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=WORKLIST_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in WORKLIST_FIELDS})


def write_worklist_outputs(
    output_dir: Path,
    *,
    repo_root: Path,
    inventory: dict[str, Any],
    review_data: dict[str, Any],
    built: dict[str, Any],
    allow_nonempty: bool = False,
) -> dict[str, Any]:
    out = _assert_external_output(output_dir, repo_root)
    _ensure_empty_or_governed(out, allow_nonempty=allow_nonempty)

    work_items = built["work_items"]
    manual_hold = built["manual_hold_items"]

    _write_csv(out / "worklist-all.csv", work_items)
    _write_csv(
        out / "worklist-dasqua.csv",
        [w for w in work_items if w["brand_key"] == "dasqua"],
    )
    _write_csv(
        out / "worklist-insize.csv",
        [w for w in work_items if w["brand_key"] == "insize"],
    )
    _write_csv(
        out / "worklist-san-ou.csv",
        [w for w in work_items if w["brand_key"] == "san_ou"],
    )
    _write_csv(out / "manual-review-hold.csv", manual_hold)

    source_contract = {
        "task_id": TASK_ID,
        "schema_version": 1,
        "brands": SOURCE_PATH_CONTRACTS,
        "rights_status": "review_required",
        "apply_status": "not_started",
        "network_discovery_status": "not_started",
    }
    (out / "source-path-contract.json").write_text(
        json.dumps(source_contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    input_evidence = {
        "task_id": TASK_ID,
        "inventory": {
            "source_dir": inventory["source_dir"],
            "checksums_digest": inventory["checksums_digest"],
            "facts": inventory["facts"],
        },
        "review_bundles": review_data["evidence"],
        "cumulative_review": review_data["cumulative"],
    }
    (out / "input-evidence.json").write_text(
        json.dumps(input_evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "task_id": TASK_ID,
        "input_integrity": {
            "inventory_checksums_digest": inventory["checksums_digest"],
            "review_bundles": [
                {
                    "batch_id": e["batch_id"],
                    "outer_sha256": e["outer_sha256"],
                    "aggregates": e["aggregates"],
                }
                for e in review_data["evidence"]
            ],
            "cumulative_review": review_data["cumulative"],
        },
        "inventory_counts": inventory["facts"],
        "review_bundle_counts": review_data["cumulative"],
        "counts_by_brand": built["counts"]["by_brand"],
        "counts_by_work_type": built["counts"]["by_work_type"],
        "counts_by_priority": built["counts"]["by_priority"],
        "missing_image_by_brand": built["counts"]["missing_image_by_brand"],
        "replace_required_by_brand": built["counts"]["replace_required_by_brand"],
        "watermark_cleaner_by_brand": built["counts"]["watermark_cleaner_by_brand"],
        "manual_review_hold_by_brand": built["counts"]["manual_review_hold_by_brand"],
        "duplicate_precedence_counts": built["counts"]["dedupe"],
        "manual_holds": len(manual_hold),
        "unmatched_review_rows": built["unmatched"],
        "ambiguous_joins": built["ambiguous"],
        "source_path_readiness": {
            brand: {
                "adapter": contract["source_adapter_candidate"],
                "network_discovery_status": contract["network_discovery_status"],
                "legacy_execution_allowed": contract["legacy_execution_allowed"],
            }
            for brand, contract in SOURCE_PATH_CONTRACTS.items()
        },
        "safety": {
            "network_requests_performed": 0,
            "database_accessed": False,
            "ProductImage_modified": False,
            "source_storage_accessed": False,
            "source_storage_mutations": 0,
            "images_downloaded": 0,
            "replacement_execution": False,
            "rights_cleared": 0,
        },
        "repository_boundary": {
            "output_dir": str(out),
            "inside_repository": False,
        },
        "work_item_total": len(work_items),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    readme = f"""# {TASK_ID} Source Worklists

Deterministic, read-only source-discovery worklists for Dasqua, INSIZE and SAN OU.

- No network requests
- No database access
- No ProductImage mutation
- No source-storage access
- Rights remain review_required
- Replacement execution not started

Generated externally; do not commit these files to Git.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    members = [
        "worklist-all.csv",
        "worklist-dasqua.csv",
        "worklist-insize.csv",
        "worklist-san-ou.csv",
        "manual-review-hold.csv",
        "source-path-contract.json",
        "input-evidence.json",
        "summary.json",
        "README.md",
    ]
    lines = []
    for name in members:
        digest = sha256_file(out / name)
        lines.append(f"{digest}  {name}")
    (out / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Refuse image-like outputs
    for child in out.rglob("*"):
        if child.is_symlink():
            raise WorklistError("output", f"symlink in output: {child}")
        if child.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff"}:
            raise WorklistError("output", f"image output forbidden: {child.name}")
        if child.is_file() and stat.S_ISLNK(child.lstat().st_mode):
            raise WorklistError("output", f"symlink file: {child}")

    return {
        "output_dir": str(out),
        "summary": summary,
        "checksums_digest": sha256_file(out / "checksums.sha256"),
        "work_item_total": len(work_items),
    }


def semantic_fingerprint(output_dir: Path) -> dict[str, Any]:
    """Comparable semantic payload excluding generated timestamps (none are emitted)."""
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    evidence = json.loads((output_dir / "input-evidence.json").read_text(encoding="utf-8"))
    contract = json.loads((output_dir / "source-path-contract.json").read_text(encoding="utf-8"))
    with (output_dir / "worklist-all.csv").open(encoding="utf-8") as f:
        work_rows = list(csv.DictReader(f))
    return {
        "summary_counts": {
            k: summary[k]
            for k in (
                "counts_by_brand",
                "counts_by_work_type",
                "counts_by_priority",
                "missing_image_by_brand",
                "replace_required_by_brand",
                "watermark_cleaner_by_brand",
                "manual_review_hold_by_brand",
                "duplicate_precedence_counts",
                "manual_holds",
                "work_item_total",
                "safety",
            )
        },
        "work_item_ids": [r["work_item_id"] for r in work_rows],
        "work_rows": work_rows,
        "source_contract": contract,
        "input_evidence_sans_paths": {
            "inventory_facts": evidence["inventory"]["facts"],
            "cumulative_review": evidence["cumulative_review"],
            "bundle_ids": [b["batch_id"] for b in evidence["review_bundles"]],
            "bundle_shas": [b["outer_sha256"] for b in evidence["review_bundles"]],
        },
    }
