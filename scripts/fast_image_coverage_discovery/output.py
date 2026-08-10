"""External artifact packaging for IMG-FAST-01B."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import ACCEPTED_SEED_ARTIFACT_SHA256, ACCEPTED_USABLE_PRIMARY, TASK_ID
from .contracts import (
    ATTEMPT_FIELDS,
    GREEN_FIELDS,
    RED_FIELDS,
    YELLOW_FIELDS,
    DiscoveryRunState,
    DriftRow,
    RunProduct,
)
from .orchestrator import summarize_run


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_baseline_drift(path: Path, rows: list[DriftRow]) -> None:
    _write_csv(
        path,
        ["product_id", "sku", "brand_key", "drift_status", "notes"],
        [row.__dict__ for row in rows],
    )


def write_run_universe(path: Path, products: list[RunProduct]) -> None:
    _write_csv(
        path,
        ["product_id", "sku", "brand_key", "category_slug", "product_name", "origin", "brand_sort_key"],
        [p.__dict__ for p in products],
    )


def collect_rows(state: DiscoveryRunState) -> dict[str, list[dict[str, Any]]]:
    greens: list[dict[str, Any]] = []
    yellows: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    reds: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []

    for ps in state.products.values():
        if ps.final_status == "green_exact":
            for a in ps.attempts:
                if a.discovery_status == "green_exact":
                    greens.append(a.as_green_row())
                    if a.asset:
                        relations.append(
                            {
                                "product_id": a.product_id,
                                "asset_sha256": a.asset.sha256,
                                "asset_relative_path": a.asset.relative_path,
                                "source_page_url": a.source_page_url,
                                "source_image_url": a.source_image_url,
                            }
                        )
                    break
        elif ps.final_status == "yellow_review" and ps.best_yellow:
            yellows.append(ps.best_yellow.as_yellow_row())
        else:
            unresolved.append({"product_id": ps.product_id, "final_status": "unresolved"})
        for a in ps.attempts:
            attempts.append(a.as_attempt_row())
            if a.discovery_status == "red_rejected":
                reds.append(a.as_red_row())

    return {
        "green-exact.csv": greens,
        "yellow-review.csv": yellows,
        "unresolved.csv": unresolved,
        "red-rejected.csv": reds,
        "all-attempts.csv": attempts,
        "relation-asset-map.csv": relations,
    }


def coverage_by_brand(state: DiscoveryRunState, universe: list[RunProduct]) -> list[dict[str, Any]]:
    uni = Counter(p.brand_sort_key for p in universe)
    green = Counter()
    yellow = Counter()
    unresolved = Counter()
    for p in universe:
        ps = state.products.get(p.product_id)
        if not ps:
            unresolved[p.brand_sort_key] += 1
            continue
        if ps.final_status == "green_exact":
            green[p.brand_sort_key] += 1
        elif ps.final_status == "yellow_review":
            yellow[p.brand_sort_key] += 1
        else:
            unresolved[p.brand_sort_key] += 1
    rows = []
    for brand, count in uni.most_common():
        rows.append(
            {
                "brand_key": brand,
                "universe": count,
                "green_exact": green.get(brand, 0),
                "yellow_review": yellow.get(brand, 0),
                "unresolved": unresolved.get(brand, 0),
            }
        )
    return rows


def duplicate_groups(relations: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    by_sha: dict[str, list[int]] = defaultdict(list)
    by_url: dict[str, list[int]] = defaultdict(list)
    for r in relations:
        by_sha[r["asset_sha256"]].append(int(r["product_id"]))
        by_url[r["source_image_url"]].append(int(r["product_id"]))
    sha_rows = [
        {"asset_sha256": k, "product_ids": ";".join(map(str, v)), "count": len(v)}
        for k, v in by_sha.items()
        if len(v) > 1
    ]
    url_rows = [
        {"source_image_url": k, "product_ids": ";".join(map(str, v)), "count": len(v)}
        for k, v in by_url.items()
        if len(v) > 1
    ]
    return sha_rows, url_rows


def write_yellow_review_html(path: Path, yellow_rows: list[dict[str, Any]], package_dir: Path) -> None:
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>IMG-FAST-01B Yellow Review</title>",
        "<style>body{font-family:sans-serif} .card{border:1px solid #ccc;margin:8px;padding:8px}",
        "img{max-width:240px;max-height:240px}</style></head><body>",
        f"<h1>{TASK_ID} Yellow Review</h1>",
    ]
    for row in yellow_rows:
        img = row.get("asset_relative_path") or ""
        src = img if not img else img
        parts.append("<div class='card'>")
        parts.append(f"<div><b>{row.get('product_id')}</b> SKU {row.get('sku')} — {row.get('reason_code')}</div>")
        if src:
            parts.append(f"<img src='{src}' alt='candidate'>")
        parts.append(f"<div>{row.get('recommended_action','')}</div></div>")
    parts.append("</body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_checksums(package_dir: Path) -> tuple[list[str], list[str], list[str]]:
    entries: list[str] = []
    failures: list[str] = []
    for fp in sorted(package_dir.rglob("*")):
        if fp.is_file() and fp.name != "checksums.sha256":
            rel = fp.relative_to(package_dir).as_posix()
            entries.append(f"{_sha256_file(fp)}  {rel}")
    (package_dir / "checksums.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")
    return entries, failures, []


def build_summary_json(
    state: DiscoveryRunState,
    *,
    seed_zip: Path,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "completed_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "accepted_seed_artifact_sha256": ACCEPTED_SEED_ARTIFACT_SHA256,
        "accepted_seed_zip": str(seed_zip),
        "api_base": state.api_base,
        "baseline_seed_total": state.baseline_seed_total,
        "active_seed_missing": state.active_seed_missing,
        "resolved_since_baseline": state.resolved_since_baseline,
        "removed_since_baseline": state.removed_since_baseline,
        "new_missing_since_baseline": state.new_missing_since_baseline,
        "run_discovery_universe_total": state.run_discovery_universe_total,
        "usable_primary_baseline": ACCEPTED_USABLE_PRIMARY,
        "projected_usable_primary_after_green_apply": ACCEPTED_USABLE_PRIMARY + int(metrics.get("green_exact", 0)),
        "database_modified": False,
        "ProductImage_modified": False,
        "application_storage_mutations": 0,
        "production_API_write_requests": 0,
        "images_applied": 0,
        "deploy_performed": False,
        **metrics,
    }


def write_package(
    package_dir: Path,
    *,
    state: DiscoveryRunState,
    drift_rows: list[DriftRow],
    run_universe: list[RunProduct],
    seed_zip: Path,
) -> dict[str, Any]:
    package_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_rows(state)
    write_baseline_drift(package_dir / "baseline-to-run-drift.csv", drift_rows)
    write_run_universe(package_dir / "run-universe.csv", run_universe)
    for name, data in rows.items():
        if name == "green-exact.csv":
            _write_csv(package_dir / name, GREEN_FIELDS, data)
        elif name == "yellow-review.csv":
            _write_csv(package_dir / name, YELLOW_FIELDS, data)
        elif name == "red-rejected.csv":
            _write_csv(package_dir / name, RED_FIELDS, data)
        elif name == "all-attempts.csv":
            _write_csv(package_dir / name, ATTEMPT_FIELDS, data)
        else:
            _write_csv(package_dir / name, list(data[0].keys()) if data else ["product_id"], data)

    brand_rows = coverage_by_brand(state, run_universe)
    _write_csv(
        package_dir / "coverage-by-brand.csv",
        ["brand_key", "universe", "green_exact", "yellow_review", "unresolved"],
        brand_rows,
    )
    sha_dups, url_dups = duplicate_groups(rows["relation-asset-map.csv"])
    _write_csv(package_dir / "duplicate-groups-sha.csv", ["asset_sha256", "product_ids", "count"], sha_dups)
    _write_csv(package_dir / "duplicate-groups-url.csv", ["source_image_url", "product_ids", "count"], url_dups)
    _write_csv(package_dir / "duplicate-groups-phash.csv", ["asset_sha256", "note"], [])

    assets = []
    for sha, rel in state.sha_assets.items():
        assets.append({"asset_sha256": sha, "asset_relative_path": rel})
    _write_csv(package_dir / "asset-manifest.csv", ["asset_sha256", "asset_relative_path"], assets)

    write_yellow_review_html(package_dir / "yellow-review.html", rows["yellow-review.csv"], package_dir)

    metrics = summarize_run(state)
    summary = build_summary_json(state, seed_zip=seed_zip, metrics=metrics)
    (package_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = package_dir / "README.md"
    readme.write_text(
        f"# {TASK_ID} external discovery artifact\n\n"
        "Discovery + download + classification only. No DB/ProductImage mutations.\n",
        encoding="utf-8",
    )
    entries, failures, uncovered = write_checksums(package_dir)
    return {"summary": summary, "checksum_entries": len(entries), "checksum_failures": failures}


def zip_package(package_dir: Path, zip_path: Path) -> str:
    if zip_path.is_file():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in sorted(package_dir.rglob("*")):
            if fp.is_file():
                zf.write(fp, arcname=fp.relative_to(package_dir).as_posix())
    return _sha256_file(zip_path)
