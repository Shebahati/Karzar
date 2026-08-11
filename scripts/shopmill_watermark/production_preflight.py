"""Read-only production preflight for ShopMill watermark cleanup.

Validates every affected serving path under a resolved PRODUCTS_STORAGE_ROOT.
Never writes under the uploads tree. Never applies repairs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

TASK_ID = "IMG-SHOPMILL-WATERMARK-CLEANUP"
EXPECTED_TARGET_PATHS = 410
EXPECTED_UNIQUE_ASSETS = 163

CLASSIFICATIONS = (
    "EXACT_MATCH",
    "SOURCE_CHANGED",
    "MISSING_SOURCE",
    "INVALID_PATH",
    "DUPLICATE_PATH",
    "OTHER_ERROR",
)

CSV_FIELDS = [
    "product_id",
    "product_slug",
    "sku",
    "brand_name",
    "serving_relative_path",
    "resolved_absolute_path",
    "production_sha256",
    "expected_source_sha256",
    "repaired_sha256",
    "file_size",
    "classification",
    "notes",
    "image_id",
    "image_url_original",
]


@dataclass
class TargetRow:
    product_id: str
    product_slug: str
    sku: str
    brand_name: str
    serving_relative_path: str
    expected_source_sha256: str
    repaired_sha256: str
    image_id: str
    image_url_original: str
    repaired_local_path: str


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_relative_path(raw: str) -> str | None:
    """Return a safe relative POSIX path, or None if invalid."""
    value = (raw or "").strip().replace("\\", "/")
    if not value:
        return None
    if value.startswith("/") or value.startswith("~"):
        return None
    if "://" in value:
        return None
    parts: list[str] = []
    for part in value.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            return None
        if "\x00" in part:
            return None
        parts.append(part)
    if not parts:
        return None
    return "/".join(parts)


def resolve_under_root(storage_root: Path, rel: str) -> Path | None:
    """Resolve rel strictly under storage_root; reject escapes."""
    try:
        root = storage_root.resolve()
    except OSError:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def assert_report_dir_safe(report_dir: Path, storage_root: Path) -> Path:
    """Refuse report dirs that nest inside the live uploads root."""
    report = report_dir.resolve()
    root = storage_root.resolve()
    try:
        report.relative_to(root)
        raise SystemExit(
            f"refusing report-dir inside PRODUCTS_STORAGE_ROOT: {report} under {root}"
        )
    except ValueError:
        pass
    # Also refuse if report equals root
    if report == root:
        raise SystemExit("refusing report-dir equal to PRODUCTS_STORAGE_ROOT")
    report.mkdir(parents=True, exist_ok=True)
    return report


def load_targets(manifest: Path) -> list[TargetRow]:
    rows: list[TargetRow] = []
    with manifest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {(k or "").lstrip("\ufeff"): (v or "") for k, v in raw.items() if k is not None}
            # Full remediation manifest uses remediation_ok; slim target CSV omits it.
            if "remediation_ok" in row and str(row.get("remediation_ok")).lower() not in {
                "1",
                "true",
                "t",
                "yes",
            }:
                continue
            rel = (
                str(row.get("mapped_local_relative_path") or "").strip()
                or str(row.get("serving_relative_path") or "").strip()
            )
            rows.append(
                TargetRow(
                    product_id=str(row.get("product_id") or "").strip(),
                    product_slug=str(row.get("product_slug") or "").strip(),
                    sku=str(row.get("sku") or "").strip(),
                    brand_name=str(row.get("brand_name") or "").strip(),
                    serving_relative_path=rel,
                    expected_source_sha256=str(
                        row.get("sha256_original")
                        or row.get("expected_source_sha256")
                        or ""
                    ).strip(),
                    repaired_sha256=str(
                        row.get("sha256_final") or row.get("repaired_sha256") or ""
                    ).strip(),
                    image_id=str(row.get("image_id") or "").strip(),
                    image_url_original=str(row.get("image_url_original") or "").strip(),
                    repaired_local_path=str(row.get("output_path") or "").strip(),
                )
            )
    return rows


def classify_target(
    *,
    storage_root: Path,
    target: TargetRow,
    seen_rels: dict[str, str],
) -> dict[str, str]:
    rel_raw = target.serving_relative_path
    rel = normalize_relative_path(rel_raw)
    base = {
        "product_id": target.product_id,
        "product_slug": target.product_slug,
        "sku": target.sku,
        "brand_name": target.brand_name,
        "serving_relative_path": rel or rel_raw,
        "resolved_absolute_path": "",
        "production_sha256": "",
        "expected_source_sha256": target.expected_source_sha256,
        "repaired_sha256": target.repaired_sha256,
        "file_size": "",
        "classification": "OTHER_ERROR",
        "notes": "",
        "image_id": target.image_id,
        "image_url_original": target.image_url_original,
    }

    if rel is None:
        base["classification"] = "INVALID_PATH"
        base["notes"] = "absolute_or_traversal_or_empty"
        return base

    prior = seen_rels.get(rel)
    if prior is not None and prior != target.expected_source_sha256:
        base["classification"] = "DUPLICATE_PATH"
        base["notes"] = f"conflicting_expected_hash prior={prior}"
        return base
    if prior is not None and prior == target.expected_source_sha256:
        # Same path + same expected hash appearing twice in assignments is unexpected
        # for this corpus (410 unique paths). Still flag as duplicate path occurrence.
        base["classification"] = "DUPLICATE_PATH"
        base["notes"] = "relative_path_repeated_in_manifest"
        return base
    seen_rels[rel] = target.expected_source_sha256

    resolved = resolve_under_root(storage_root, rel)
    if resolved is None:
        base["classification"] = "INVALID_PATH"
        base["notes"] = "path_escapes_storage_root"
        return base
    base["resolved_absolute_path"] = str(resolved)

    try:
        st = resolved.lstat()
    except FileNotFoundError:
        base["classification"] = "MISSING_SOURCE"
        base["notes"] = "file_not_found"
        return base
    except OSError as exc:
        base["classification"] = "OTHER_ERROR"
        base["notes"] = f"lstat_failed:{exc}"
        return base

    if stat.S_ISLNK(st.st_mode):
        base["classification"] = "OTHER_ERROR"
        base["notes"] = "symlink_rejected"
        return base
    if not stat.S_ISREG(st.st_mode):
        base["classification"] = "OTHER_ERROR"
        base["notes"] = "not_regular_file"
        return base

    base["file_size"] = str(st.st_size)
    try:
        production_sha = sha256_file(resolved)
    except OSError as exc:
        base["classification"] = "OTHER_ERROR"
        base["notes"] = f"hash_failed:{exc}"
        return base
    base["production_sha256"] = production_sha

    expected = target.expected_source_sha256
    repaired = target.repaired_sha256
    if expected and production_sha == expected:
        base["classification"] = "EXACT_MATCH"
        base["notes"] = "production_matches_expected_source_sha256"
        return base
    if repaired and production_sha == repaired:
        # Already equals repaired bytes — still not an apply; classify as SOURCE_CHANGED
        # relative to "expected original", with explicit note.
        base["classification"] = "SOURCE_CHANGED"
        base["notes"] = (
            "production_equals_repaired_sha_not_expected_source;"
            "regenerate_not_required_if_intentional_prior_apply"
        )
        return base
    if expected and production_sha != expected:
        base["classification"] = "SOURCE_CHANGED"
        base["notes"] = (
            "production_differs_from_expected_source;"
            "do_not_apply_existing_repair;"
            "requires_method_c_from_production_bytes"
        )
        return base

    base["classification"] = "OTHER_ERROR"
    base["notes"] = "missing_expected_source_sha_for_comparison"
    return base


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def build_summary(
    *,
    storage_root: Path,
    results: list[dict[str, str]],
    targets: list[TargetRow],
    expected_target_paths: int,
    expected_unique_assets: int,
) -> dict:
    counts = Counter(r["classification"] for r in results)
    unique_expected = {t.expected_source_sha256 for t in targets if t.expected_source_sha256}
    by_asset: dict[str, list[str]] = defaultdict(list)
    for row in results:
        sha = row.get("expected_source_sha256") or ""
        if sha:
            by_asset[sha].append(row["classification"])

    asset_rollup = []
    for sha, classes in sorted(by_asset.items()):
        c = Counter(classes)
        order = [
            "OTHER_ERROR",
            "INVALID_PATH",
            "DUPLICATE_PATH",
            "MISSING_SOURCE",
            "SOURCE_CHANGED",
            "EXACT_MATCH",
        ]
        worst = next((k for k in order if c.get(k)), "OTHER_ERROR")
        asset_rollup.append(
            {
                "expected_source_sha256": sha,
                "assignment_count": len(classes),
                "classification_counts": dict(c),
                "rollup_classification": worst,
            }
        )

    accounted = len(results)
    summary = {
        "task_id": TASK_ID,
        "mode": "read_only_preflight",
        "observed_at_utc": _utc_now(),
        "products_storage_root": str(storage_root.resolve()),
        "TARGET_PATHS_EXPECTED": expected_target_paths,
        "TARGET_PATHS_ACCOUNTED_FOR": accounted,
        "UNIQUE_ASSETS_EXPECTED": expected_unique_assets,
        "UNIQUE_ASSETS_IN_MANIFEST": len(unique_expected),
        "EXACT_MATCH": counts.get("EXACT_MATCH", 0),
        "SOURCE_CHANGED": counts.get("SOURCE_CHANGED", 0),
        "MISSING_SOURCE": counts.get("MISSING_SOURCE", 0),
        "INVALID_PATH": counts.get("INVALID_PATH", 0),
        "DUPLICATE_PATH": counts.get("DUPLICATE_PATH", 0),
        "OTHER_ERROR": counts.get("OTHER_ERROR", 0),
        "classification_counts": {k: counts.get(k, 0) for k in CLASSIFICATIONS},
        "reconciliation_ok": (
            accounted == expected_target_paths
            and sum(counts.get(k, 0) for k in CLASSIFICATIONS) == accounted
        ),
        "mutations": {
            "uploads_modified": False,
            "files_written_under_storage_root": False,
            "apply_executed": False,
            "backup_executed": False,
        },
        "unique_asset_rollup": asset_rollup,
    }
    return summary


def render_human_summary(summary: dict) -> str:
    lines = [
        f"# {TASK_ID} — production preflight (READ-ONLY)",
        "",
        f"observed_at_utc: {summary['observed_at_utc']}",
        f"PRODUCTS_STORAGE_ROOT: {summary['products_storage_root']}",
        "",
        f"TARGET_PATHS_EXPECTED={summary['TARGET_PATHS_EXPECTED']}",
        f"TARGET_PATHS_ACCOUNTED_FOR={summary['TARGET_PATHS_ACCOUNTED_FOR']}",
        f"UNIQUE_ASSETS_EXPECTED={summary['UNIQUE_ASSETS_EXPECTED']}",
        f"UNIQUE_ASSETS_IN_MANIFEST={summary['UNIQUE_ASSETS_IN_MANIFEST']}",
        f"EXACT_MATCH={summary['EXACT_MATCH']}",
        f"SOURCE_CHANGED={summary['SOURCE_CHANGED']}",
        f"MISSING_SOURCE={summary['MISSING_SOURCE']}",
        f"INVALID_PATH={summary['INVALID_PATH']}",
        f"DUPLICATE_PATH={summary['DUPLICATE_PATH']}",
        f"OTHER_ERROR={summary['OTHER_ERROR']}",
        f"reconciliation_ok={summary['reconciliation_ok']}",
        "",
        "mutations.uploads_modified=false",
        "mutations.apply_executed=false",
        "",
        "NOTE: SOURCE_CHANGED means production bytes differ from the hash used to",
        "build the staged repair. Do NOT apply that repair; regenerate Method C",
        "from the exact production bytes in a later authorized phase.",
        "",
    ]
    return "\n".join(lines)


def run_preflight(
    *,
    manifest: Path,
    storage_root: Path,
    report_dir: Path,
    expected_target_paths: int = EXPECTED_TARGET_PATHS,
    expected_unique_assets: int = EXPECTED_UNIQUE_ASSETS,
) -> int:
    if not storage_root.is_dir():
        print(f"PRODUCTS_STORAGE_ROOT missing or not a directory: {storage_root}", file=sys.stderr)
        return 2
    report_dir = assert_report_dir_safe(report_dir, storage_root)
    targets = load_targets(manifest)
    if len(targets) != expected_target_paths:
        print(
            f"warning: manifest target count {len(targets)} != expected {expected_target_paths}",
            file=sys.stderr,
        )

    seen_rels: dict[str, str] = {}
    results: list[dict[str, str]] = []
    for target in targets:
        results.append(classify_target(storage_root=storage_root, target=target, seen_rels=seen_rels))

    summary = build_summary(
        storage_root=storage_root,
        results=results,
        targets=targets,
        expected_target_paths=expected_target_paths,
        expected_unique_assets=expected_unique_assets,
    )
    csv_path = report_dir / "preflight-per-path.csv"
    json_path = report_dir / "preflight-report.json"
    txt_path = report_dir / "preflight-summary.txt"
    write_csv(csv_path, results)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    txt_path.write_text(render_human_summary(summary), encoding="utf-8")

    print(render_human_summary(summary))
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    print(f"summary={txt_path}")
    return 0 if summary["reconciliation_ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "READ-ONLY ShopMill production preflight. "
            "Hashes every target path under PRODUCTS_STORAGE_ROOT; "
            "writes reports only to --report-dir (never under uploads)."
        )
    )
    p.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Target/remediation CSV with mapped_local_relative_path + sha columns",
    )
    p.add_argument(
        "--products-storage-root",
        type=Path,
        required=True,
        help="Absolute host path to .../uploads/products (resolved live volume mount)",
    )
    p.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="Directory for JSON/CSV/summary output (must NOT be under uploads)",
    )
    p.add_argument(
        "--expected-target-paths",
        type=int,
        default=EXPECTED_TARGET_PATHS,
        help=f"Expected assignment/path count (default {EXPECTED_TARGET_PATHS})",
    )
    p.add_argument(
        "--expected-unique-assets",
        type=int,
        default=EXPECTED_UNIQUE_ASSETS,
        help=f"Expected unique source hashes (default {EXPECTED_UNIQUE_ASSETS})",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_preflight(
        manifest=args.manifest,
        storage_root=args.products_storage_root,
        report_dir=args.report_dir,
        expected_target_paths=args.expected_target_paths,
        expected_unique_assets=args.expected_unique_assets,
    )


if __name__ == "__main__":
    raise SystemExit(main())
