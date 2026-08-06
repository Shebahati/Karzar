"""Offline IMG-02C-01 R2 remediation from immutable R1 Artifact (no live network)."""

from __future__ import annotations

import csv
import json
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import BATCH_ID, NODE_ID, TASK_ID, MultisourceError
from .image_identity import classify_filename_identity
from .output import (
    assert_external_output,
    ensure_absent_or_empty,
    verify_checksums,
    write_csv,
    write_full_checksums,
    write_json,
)
from .quality import inspect_image_bytes, sha256_bytes
from .registry import builtin_r1_registry, sort_sources

R1_FALSE_STABLE_PIDS = frozenset({"3837", "3920", "4119"})
R1_BRAND_CONFLICT_PIDS = frozenset(
    {"1061", "1116", "1159", "1606", "1612", "1714", "1717", "1718", "1721"}
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
    "reason_code",
    "notes",
    "asset_id",
    "evidence_kind",
]

MAT_FIELDS = [
    "product_id",
    "product_key",
    "sku",
    "brand_key",
    "source_id",
    "source_detail_url",
    "source_image_url",
    "discovery_status",
    "reason_code",
    "reason_detail",
    "http_status",
    "final_url",
]

ASSET_FIELDS = [
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
]

MAP_FIELDS = [
    "product_id",
    "sku",
    "brand_key",
    "source_id",
    "discovery_status",
    "asset_id",
    "sha256",
    "source_image_url",
]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_asset_bytes(r1_root: Path, local_path: str) -> bytes | None:
    if not local_path:
        return None
    p = Path(local_path)
    # Prefer path relative to R1 assets by filename
    name = p.name
    cand = r1_root / "assets" / name
    if cand.is_file():
        return cand.read_bytes()
    if p.is_file():
        return p.read_bytes()
    return None


def _contact_sheet(paths: list[Path], dest: Path, *, cols: int = 4, thumb: int = 160) -> None:
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise MultisourceError("r2", f"Pillow unavailable for contact sheets: {exc}") from exc
    if not paths:
        # empty placeholder
        Image.new("RGB", (thumb, thumb), (240, 240, 240)).save(dest, format="JPEG", quality=80)
        return
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb, rows * thumb), (250, 250, 250))
    for i, path in enumerate(paths[: cols * rows]):
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((thumb, thumb))
                x = (i % cols) * thumb
                y = (i // cols) * thumb
                sheet.paste(im, (x, y))
        except Exception:
            continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, format="JPEG", quality=85)


def run_r2_remediation(
    *,
    r1_root: Path,
    output_dir: Path,
    repo_root: Path,
    r1_zip: Path | None = None,
) -> dict[str, Any]:
    if not r1_root.is_dir():
        raise MultisourceError("r2", f"R1 root missing: {r1_root}")
    if r1_zip is not None and r1_zip.is_file():
        # Verify immutability marker only — do not modify R1 zip.
        _ = sha256_bytes(r1_zip.read_bytes())

    out = assert_external_output(output_dir, repo_root)
    ensure_absent_or_empty(out)
    for sub in (
        "assets",
        "evidence",
        "source-calibrations",
        "bulk-health-reports",
        "contact-sheets",
        "contact-sheets/by-status",
        "contact-sheets/by-source",
        "contact-sheets/by-brand",
        "contact-sheets/by-duplicate-group",
    ):
        (out / sub).mkdir(parents=True, exist_ok=True)

    raw_relations = _load_csv(r1_root / "candidate-relations.csv")
    r1_assets = _load_csv(r1_root / "asset-manifest.csv")
    r1_summary = json.loads((r1_root / "summary.json").read_text(encoding="utf-8"))
    eligibility = json.loads((r1_root / "eligibility-report.json").read_text(encoding="utf-8"))

    # Index R1 assets by source_image_url and by sha
    assets_by_url: dict[str, dict[str, str]] = {}
    for a in r1_assets:
        url = a.get("source_image_url") or ""
        if url and url not in assets_by_url:
            assets_by_url[url] = a

    # Copy calibrations for evidence continuity
    calib_src = r1_root / "source-calibrations"
    calib_enabled: set[str] = set()
    if calib_src.is_dir():
        for path in calib_src.glob("*.json"):
            shutil.copy2(path, out / "source-calibrations" / path.name)
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("enabled_after_calibration"):
                calib_enabled.add(str(data.get("source_id") or path.stem))

    # Preserve research / auth / eligibility
    for name in (
        "source-research-ledger.csv",
        "authorization-evidence.csv",
        "eligibility-report.json",
    ):
        src = r1_root / name
        if src.is_file():
            shutil.copy2(src, out / name)

    # Evidence: R1 immutability pointer
    if r1_zip and r1_zip.is_file():
        (out / "evidence" / "R1-IMMUTABLE.txt").write_text(
            f"path={r1_zip}\nsha256={sha256_bytes(r1_zip.read_bytes())}\n"
            f"raw_discovered_relations={len(raw_relations)}\n"
            "status=validation_failed_immutable_evidence\n",
            encoding="utf-8",
        )

    # --- classify each raw relation ---
    materialization_failed: list[dict[str, str]] = []
    identity_conflicts: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    working: list[dict[str, str]] = []

    sha_store: dict[str, dict[str, Any]] = {}  # sha -> asset meta + bytes path
    copies_removed = 0
    raw_downloaded_files = 0
    relation_asset_map: list[dict[str, str]] = []

    def ensure_unique_asset(
        *,
        data: bytes,
        source_image_url: str,
        preferred_name: str,
    ) -> dict[str, str] | None:
        nonlocal copies_removed, raw_downloaded_files
        raw_downloaded_files += 1
        meta = inspect_image_bytes(data)
        if meta.get("quality_status") != "ok":
            return None
        sha = str(meta["sha256"])
        if sha in sha_store:
            copies_removed += 1
            existing = sha_store[sha]
            return {
                "asset_id": existing["asset_id"],
                "sha256": sha,
                "perceptual_hash": existing["perceptual_hash"],
                "source_image_url": source_image_url,
                "width": existing["width"],
                "height": existing["height"],
                "format": existing["format"],
                "byte_size": existing["byte_size"],
                "quality_status": "ok",
                "watermark_status": existing["watermark_status"],
                "local_asset_path": existing["local_asset_path"],
            }
        asset_id = sha[:16]
        fname = f"{asset_id}.jpg"
        rel_path = f"assets/{fname}"
        abs_path = out / rel_path
        abs_path.write_bytes(data)
        row = {
            "asset_id": asset_id,
            "sha256": sha,
            "perceptual_hash": str(meta.get("perceptual_hash") or ""),
            "source_image_url": source_image_url,
            "width": str(meta.get("width") or ""),
            "height": str(meta.get("height") or ""),
            "format": str(meta.get("format") or ""),
            "byte_size": str(meta.get("byte_size") or ""),
            "quality_status": "ok",
            "watermark_status": str(meta.get("watermark_status") or "review_required"),
            "local_asset_path": rel_path,
        }
        sha_store[sha] = row
        _ = preferred_name
        return row

    for rel in raw_relations:
        row = dict(rel)
        row.setdefault("reason_code", "")
        row.setdefault("asset_id", "")
        row.setdefault("evidence_kind", "")
        pid = row.get("product_id") or ""
        sku = row.get("sku") or ""
        brand = row.get("brand_key") or ""
        source_id = row.get("source_id") or ""
        image_url = row.get("source_image_url") or ""
        image_path = unquote(urlparse(image_url).path or "").casefold()
        looks_like_image = image_path.endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ) or ("/uploads/" in image_path) or ("image-generator" in image_path)

        # PDF semantics: whole page is never automatic product image
        if source_id == "insize_eu261_pdf" or row.get("notes") in {
            "single_sku_catalog_page",
            "multi_sku_catalog_page",
        }:
            row["discovery_status"] = "manual_review"
            row["eligible_for_automatic_acceptance"] = "false"
            row["match_basis"] = "catalog_page_evidence"
            row["evidence_kind"] = "catalog_page_evidence"
            row["reason_code"] = "catalog_page_requires_product_crop"
            row["notes"] = "catalog_page_requires_product_crop"
            if pid in R1_FALSE_STABLE_PIDS:
                row["notes"] = "catalog_page_requires_product_crop|demoted_r1_false_stable"

        # Forced brand-conflict quarantine list (retail image rows)
        forced_conflict = pid in R1_BRAND_CONFLICT_PIDS
        if looks_like_image:
            fname_signal = classify_filename_identity(
                expected_brand=brand,
                expected_sku=sku,
                source_image_url=image_url,
            )
        else:
            fname_signal = {
                "signal": "ok",
                "reason_code": "",
                "detail": "",
                "filename": "",
            }
        if forced_conflict or fname_signal.get("reason_code") == "conflicting_image_brand":
            row["discovery_status"] = "image_identity_conflict"
            row["eligible_for_automatic_acceptance"] = "false"
            row["reason_code"] = "conflicting_image_brand"
            row["notes"] = fname_signal.get("detail") or "conflicting_image_brand"
            identity_conflicts.append(row)
            # still try to keep asset for review evidence if materialized
            asset_meta = assets_by_url.get(image_url)
            data = _read_asset_bytes(r1_root, (asset_meta or {}).get("local_asset_path") or "")
            if data:
                stored = ensure_unique_asset(
                    data=data, source_image_url=image_url, preferred_name=pid
                )
                if stored:
                    row["asset_id"] = stored["asset_id"]
                    relation_asset_map.append(
                        {
                            "product_id": pid,
                            "sku": sku,
                            "brand_key": brand,
                            "source_id": source_id,
                            "discovery_status": row["discovery_status"],
                            "asset_id": stored["asset_id"],
                            "sha256": stored["sha256"],
                            "source_image_url": image_url,
                        }
                    )
            continue

        if fname_signal.get("signal") == "sku_filename_conflict":
            # Quarantine separately (not automatic false match)
            row["discovery_status"] = "image_identity_conflict"
            row["eligible_for_automatic_acceptance"] = "false"
            row["reason_code"] = fname_signal.get("reason_code") or "conflicting_image_sku"
            row["notes"] = fname_signal.get("detail") or "sku_filename_conflict"
            identity_conflicts.append(row)
            asset_meta = assets_by_url.get(image_url)
            data = _read_asset_bytes(r1_root, (asset_meta or {}).get("local_asset_path") or "")
            if data:
                stored = ensure_unique_asset(
                    data=data, source_image_url=image_url, preferred_name=pid
                )
                if stored:
                    row["asset_id"] = stored["asset_id"]
                    relation_asset_map.append(
                        {
                            "product_id": pid,
                            "sku": sku,
                            "brand_key": brand,
                            "source_id": source_id,
                            "discovery_status": row["discovery_status"],
                            "asset_id": stored["asset_id"],
                            "sha256": stored["sha256"],
                            "source_image_url": image_url,
                        }
                    )
            continue

        # Materialization gate
        asset_meta = assets_by_url.get(image_url)
        data = None
        if asset_meta:
            data = _read_asset_bytes(r1_root, asset_meta.get("local_asset_path") or "")
        # PDF page renders may use catalog URL as source_image_url — recover via local file name patterns
        if data is None and source_id == "insize_eu261_pdf":
            # find any r1 asset for this product id
            for a in r1_assets:
                if f"__{pid}__" in (a.get("local_asset_path") or ""):
                    data = _read_asset_bytes(r1_root, a.get("local_asset_path") or "")
                    if data:
                        image_url = a.get("source_image_url") or image_url
                        break
            if data is None:
                # page render may live under cache-refs; product-linked recovery above is preferred
                pass

        if data is None:
            fail = {
                "product_id": pid,
                "product_key": row.get("product_key") or "",
                "sku": sku,
                "brand_key": brand,
                "source_id": source_id,
                "source_detail_url": row.get("source_detail_url") or "",
                "source_image_url": image_url,
                "discovery_status": "materialization_failed",
                "reason_code": "assetless_relation",
                "reason_detail": "source_image_url has no corresponding materialized asset",
                "http_status": "",
                "final_url": image_url,
            }
            materialization_failed.append(fail)
            continue

        stored = ensure_unique_asset(
            data=data, source_image_url=image_url, preferred_name=pid
        )
        if stored is None:
            materialization_failed.append(
                {
                    "product_id": pid,
                    "product_key": row.get("product_key") or "",
                    "sku": sku,
                    "brand_key": brand,
                    "source_id": source_id,
                    "source_detail_url": row.get("source_detail_url") or "",
                    "source_image_url": image_url,
                    "discovery_status": "materialization_failed",
                    "reason_code": "quality_reject",
                    "reason_detail": "image bytes failed quality gate",
                    "http_status": "",
                    "final_url": image_url,
                }
            )
            continue

        row["asset_id"] = stored["asset_id"]
        row["source_image_url"] = image_url
        if row.get("discovery_status") == "candidate_ready":
            # should already be demoted for PDF; belt-and-suspenders
            row["discovery_status"] = "manual_review"
            row["eligible_for_automatic_acceptance"] = "false"
            row["reason_code"] = row.get("reason_code") or "catalog_page_requires_product_crop"
        if row.get("discovery_status") == "rejected":
            rejected.append(row)
        else:
            working.append(row)
        relation_asset_map.append(
            {
                "product_id": pid,
                "sku": sku,
                "brand_key": brand,
                "source_id": source_id,
                "discovery_status": row["discovery_status"],
                "asset_id": stored["asset_id"],
                "sha256": stored["sha256"],
                "source_image_url": image_url,
            }
        )

    # Split queues (identity conflicts already separated)
    stable = [r for r in working if r.get("discovery_status") == "candidate_ready"]
    retailer = [r for r in working if r.get("discovery_status") == "retailer_review"]
    manual = [r for r in working if r.get("discovery_status") == "manual_review"]
    other_rej = [r for r in working if r.get("discovery_status") == "rejected"]
    rejected.extend(other_rej)

    # Guarantee demotion of the three false stables into manual if somehow present
    assert all(r.get("product_id") not in R1_FALSE_STABLE_PIDS for r in stable)
    for pid in R1_FALSE_STABLE_PIDS:
        if not any(r.get("product_id") == pid for r in manual):
            # may be in identity or mat-failed; if in working under other status, move
            for r in list(working):
                if r.get("product_id") == pid and r.get("discovery_status") != "manual_review":
                    r["discovery_status"] = "manual_review"
                    r["eligible_for_automatic_acceptance"] = "false"
                    r["reason_code"] = "catalog_page_requires_product_crop"
                    manual.append(r)

    all_candidates = stable + retailer + manual + identity_conflicts
    # Rebuild working lists after demotion sweep
    stable = [r for r in all_candidates if r.get("discovery_status") == "candidate_ready"]
    retailer = [r for r in all_candidates if r.get("discovery_status") == "retailer_review"]
    manual = [r for r in all_candidates if r.get("discovery_status") == "manual_review"]
    identity_conflicts = [
        r for r in all_candidates if r.get("discovery_status") == "image_identity_conflict"
    ]

    asset_rows = sorted(sha_store.values(), key=lambda a: a["sha256"])
    write_csv(out / "asset-manifest.csv", asset_rows, ASSET_FIELDS)
    write_csv(out / "relation-asset-map.csv", relation_asset_map, MAP_FIELDS)

    # Duplicate groups after unique-asset storage:
    # - exact: multiple relations pointing at same sha256
    # - url: multiple relations sharing normalized source URL (via map)
    # - phash: unique assets sharing identical perceptual hash
    sha_to_assets: dict[str, list[str]] = defaultdict(list)
    for m in relation_asset_map:
        sha_to_assets[m["sha256"]].append(m.get("asset_id") or "")
    exact_dup_groups = []
    for sha, members in sorted(sha_to_assets.items()):
        uniq = sorted({m for m in members if m})
        # count relations sharing sha
        rel_count = len(members)
        if rel_count >= 2:
            exact_dup_groups.append(
                {
                    "group_key": f"sha256:{sha}",
                    "member_count": str(rel_count),
                    "asset_ids": "|".join(uniq),
                }
            )
    url_groups: dict[str, list[str]] = defaultdict(list)
    for m in relation_asset_map:
        url_groups[m.get("source_image_url") or ""].append(m.get("asset_id") or "")
    url_dup_groups = []
    for url, members in sorted(url_groups.items()):
        if not url or len(members) < 2:
            continue
        url_dup_groups.append(
            {
                "group_key": f"url:{url}",
                "member_count": str(len(members)),
                "asset_ids": "|".join(sorted({m for m in members if m})),
            }
        )
    phash_groups: dict[str, list[str]] = defaultdict(list)
    for a in asset_rows:
        if a.get("perceptual_hash"):
            phash_groups[a["perceptual_hash"]].append(a["asset_id"])
    phash_dup_groups = [
        {
            "group_key": f"phash:{ph}",
            "member_count": str(len(members)),
            "asset_ids": "|".join(sorted(members)),
        }
        for ph, members in sorted(phash_groups.items())
        if len(members) >= 2
    ]
    dup_groups = exact_dup_groups + url_dup_groups + phash_dup_groups
    write_csv(
        out / "duplicate-groups.csv",
        dup_groups,
        ["group_key", "member_count", "asset_ids"],
    )

    write_csv(out / "candidate-relations.csv", all_candidates, RELATION_FIELDS)
    write_csv(out / "stable-candidates.csv", stable, RELATION_FIELDS)
    write_csv(out / "retailer-review.csv", retailer, RELATION_FIELDS)
    write_csv(out / "manual-review.csv", manual, RELATION_FIELDS)
    write_csv(out / "image-identity-conflicts.csv", identity_conflicts, RELATION_FIELDS)
    write_csv(out / "materialization-rejected.csv", materialization_failed, MAT_FIELDS)
    write_csv(out / "rejected.csv", rejected, RELATION_FIELDS)

    # Coverage
    rem_brand = eligibility.get("remaining_eligible_by_brand") or {}
    brand_cov: dict[str, Counter] = defaultdict(Counter)
    for r in all_candidates:
        brand_cov[r.get("brand_key") or ""][r.get("discovery_status") or ""] += 1
    write_csv(
        out / "coverage-by-brand.csv",
        [
            {
                "brand_key": b,
                "remaining_eligible": str(rem_brand.get(b, 0)),
                "stable_candidates": str(brand_cov[b].get("candidate_ready", 0)),
                "retailer_review": str(brand_cov[b].get("retailer_review", 0)),
                "manual_review": str(brand_cov[b].get("manual_review", 0)),
                "image_identity_conflicts": str(
                    brand_cov[b].get("image_identity_conflict", 0)
                ),
            }
            for b in sorted(set(rem_brand) | set(brand_cov))
        ],
        [
            "brand_key",
            "remaining_eligible",
            "stable_candidates",
            "retailer_review",
            "manual_review",
            "image_identity_conflicts",
        ],
    )
    by_source = Counter(r.get("source_id") for r in all_candidates)
    write_csv(
        out / "coverage-by-source.csv",
        [{"source_id": k, "candidate_relations": str(v)} for k, v in sorted(by_source.items())],
        ["source_id", "candidate_relations"],
    )

    # Bulk health + effective registry
    sources = sort_sources(builtin_r1_registry())
    declarations = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "sources": [s.to_dict() for s in sources],
    }
    write_json(out / "source-registry-declarations.json", declarations)

    health_by_source: dict[str, dict[str, Any]] = {}
    for sid in sorted({r.get("source_id") or "" for r in raw_relations} | calib_enabled):
        src_raw = [r for r in raw_relations if r.get("source_id") == sid]
        src_conf = [r for r in identity_conflicts if r.get("source_id") == sid]
        src_mat = [r for r in materialization_failed if r.get("source_id") == sid]
        brand_conflicts = sum(
            1 for r in src_conf if r.get("reason_code") == "conflicting_image_brand"
        )
        sku_fn = sum(
            1
            for r in src_conf
            if r.get("reason_code") in {"conflicting_image_sku", "sku_filename_mismatch"}
        )
        health = {
            "source_id": sid,
            "brand_conflict_count": brand_conflicts,
            "sku_filename_conflict_count": sku_fn,
            "assetless_relation_count": len(src_mat),
            "image_identity_unproven_count": sum(
                1
                for r in src_raw
                if classify_filename_identity(
                    expected_brand=r.get("brand_key") or "",
                    expected_sku=r.get("sku") or "",
                    source_image_url=r.get("source_image_url") or "",
                ).get("signal")
                == "unproven"
            ),
            "download_failure_rate": round(len(src_mat) / max(len(src_raw), 1), 4),
            "parser_drift_rate": 0.0,
            "raw_relations": len(src_raw),
        }
        # Degrade when systematic brand conflicts
        degraded = brand_conflicts >= 3 or (
            brand_conflicts >= 1 and brand_conflicts / max(len(src_raw), 1) >= 0.05
        )
        health["bulk_degraded"] = degraded
        health["effective_status"] = "bulk_degraded" if degraded else (
            "effective_after_bulk" if sid in calib_enabled else "disabled"
        )
        health_by_source[sid] = health
        write_json(out / "bulk-health-reports" / f"{sid}.json", health)

    effective_sources = []
    for s in sources:
        sid = s.source_id
        enabled_cal = sid in calib_enabled
        health = health_by_source.get(sid) or {
            "bulk_degraded": False,
            "effective_status": "disabled",
        }
        if enabled_cal and not health.get("bulk_degraded"):
            eff = "effective_after_bulk"
            eff_enabled = True
        elif enabled_cal and health.get("bulk_degraded"):
            eff = "bulk_degraded"
            eff_enabled = False
        else:
            eff = "disabled"
            eff_enabled = False
        effective_sources.append(
            {
                **s.to_dict(),
                "declared_enabled": s.enabled,
                "enabled_after_calibration": enabled_cal,
                "effective_after_bulk": eff_enabled,
                "effective_status": eff,
                "decision_reason": (
                    "calibration_passed"
                    if eff == "effective_after_bulk"
                    else (
                        "bulk_brand_conflict_degraded"
                        if eff == "bulk_degraded"
                        else "not_enabled_or_disabled"
                    )
                ),
                "calibration_report": f"source-calibrations/{sid}.json",
                "bulk_health_report": f"bulk-health-reports/{sid}.json",
            }
        )

    write_json(
        out / "source-registry-effective.json",
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "batch_id": BATCH_ID,
            "sources": effective_sources,
            "effective_source_ids": [
                s["source_id"] for s in effective_sources if s.get("effective_after_bulk")
            ],
            "calibration_enabled_source_ids": sorted(calib_enabled),
            "degraded_source_ids": [
                s["source_id"] for s in effective_sources if s.get("effective_status") == "bulk_degraded"
            ],
        },
    )

    enabled_by_class = Counter(
        s["source_class"]
        for s in effective_sources
        if s.get("effective_after_bulk")
    )
    by_class = Counter(r.get("source_class") for r in all_candidates)
    write_csv(
        out / "coverage-by-source-class.csv",
        [
            {
                "source_class": c,
                "enabled_sources": str(enabled_by_class.get(c, 0)),
                "candidate_relations": str(by_class.get(c, 0)),
            }
            for c in ("S1", "S2", "S3", "S4", "S5")
        ],
        ["source_class", "enabled_sources", "candidate_relations"],
    )

    # Contact sheets
    asset_by_id = {a["asset_id"]: out / a["local_asset_path"] for a in asset_rows}

    def sheet_for(rows: list[dict[str, str]], dest: Path) -> None:
        paths = []
        for r in rows:
            aid = r.get("asset_id") or ""
            p = asset_by_id.get(aid)
            if p and p.is_file():
                paths.append(p)
        _contact_sheet(paths[:24], dest)

    sheet_for(stable, out / "contact-sheets/by-status/stable.jpg")
    sheet_for(retailer, out / "contact-sheets/by-status/retailer-review.jpg")
    sheet_for(manual, out / "contact-sheets/by-status/manual-review.jpg")
    sheet_for(
        identity_conflicts,
        out / "contact-sheets/by-status/image-identity-conflict.jpg",
    )
    for sid, _cnt in by_source.items():
        sheet_for(
            [r for r in all_candidates if r.get("source_id") == sid],
            out / "contact-sheets/by-source" / f"{sid}.jpg",
        )
    for brand in sorted({r.get("brand_key") or "unknown" for r in all_candidates}):
        sheet_for(
            [r for r in all_candidates if (r.get("brand_key") or "unknown") == brand],
            out / "contact-sheets/by-brand" / f"{brand or 'unknown'}.jpg",
        )
    for i, g in enumerate(exact_dup_groups[:20]):
        ids = (g.get("asset_ids") or "").split("|")
        paths = [asset_by_id[a] for a in ids if a in asset_by_id]
        _contact_sheet(paths, out / "contact-sheets/by-duplicate-group" / f"sha-{i:02d}.jpg")

    effective_ids = [
        s["source_id"] for s in effective_sources if s.get("effective_after_bulk")
    ]
    degraded_ids = [
        s["source_id"] for s in effective_sources if s.get("effective_status") == "bulk_degraded"
    ]

    summary = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "node_id": "IMG-02C-01-R2-PDF-RETAIL-ARTIFACT-INTEGRITY",
        "batch_id": "IMG-02C-01-R2",
        "phase": "r2_semantic_correction",
        "progress_suggested": 60,
        "r1_immutable": {
            "path": str(r1_zip) if r1_zip else str(r1_root),
            "raw_discovered_relations": len(raw_relations),
            "validation_status": "failed_immutable_evidence",
        },
        "eligibility_totals": eligibility.get("totals"),
        "raw_discovered_relations": len(raw_relations),
        "materialized_relations": len(all_candidates),
        "materialization_failed_relations": len(materialization_failed),
        "unique_materialized_assets": len(asset_rows),
        "stable_candidates": len(stable),
        "retailer_review_candidates": len(retailer),
        "manual_review_candidates": len(manual),
        "image_identity_conflicts": len(identity_conflicts),
        "rejected_candidates": len(rejected),
        "dedupe": {
            "raw_downloaded_files": raw_downloaded_files,
            "unique_physical_sha_assets": len(asset_rows),
            "exact_duplicate_groups": len(exact_dup_groups),
            "exact_duplicate_copies_removed": copies_removed,
            "perceptual_duplicate_groups": len(phash_dup_groups),
        },
        "sources": {
            "declared": len(sources),
            "calibration_enabled": sorted(calib_enabled),
            "effective_after_bulk": effective_ids,
            "degraded": degraded_ids,
        },
        "enabled_sources": effective_ids,
        "enabled_source_classes": sorted(
            {s["source_class"] for s in effective_sources if s.get("effective_after_bulk")}
        ),
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
            "live_network_used": False,
        },
        "r1_summary_preserved_facts": {
            "products_attempted": r1_summary.get("products_attempted"),
            "candidate_relations": r1_summary.get("candidate_relations"),
            "unique_image_candidates": r1_summary.get("unique_image_candidates"),
        },
    }
    write_json(out / "summary.json", summary)
    (out / "README.md").write_text(
        "# IMG-02C-01-R2\n\n"
        "Semantic correction of R1 Artifact (immutable).\n"
        "PDF whole-page renders are catalog_page_evidence only.\n"
        "Retail brand/SKU filename conflicts quarantined.\n"
        "One physical file per SHA-256; portable relative asset paths.\n"
        "rights_status=review_required; apply_status=not_started.\n",
        encoding="utf-8",
    )

    checksum_info = write_full_checksums(out)
    verify = verify_checksums(out)
    if verify["checksum_failures"] or verify["checksum_uncovered_files"]:
        raise MultisourceError(
            "r2",
            f"checksum integrity failed: {verify}",
        )
    summary["checksum"] = {
        "entries": verify["checksum_entries"],
        "failures": verify["checksum_failures"],
        "uncovered_files": verify["checksum_uncovered_files"],
        "regular_file_count": verify["regular_file_count"],
    }
    write_json(out / "summary.json", summary)
    # rewrite checksums after summary update
    checksum_info = write_full_checksums(out)
    verify = verify_checksums(out)

    return {
        "output_dir": str(out),
        "summary": summary,
        "checksum": verify,
        "checksums_digest": checksum_info["checksums_digest"],
    }


def package_review_zip(output_dir: Path, zip_path: Path) -> str:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{output_dir.name}/{path.relative_to(output_dir).as_posix()}")
    return sha256_bytes(zip_path.read_bytes())
