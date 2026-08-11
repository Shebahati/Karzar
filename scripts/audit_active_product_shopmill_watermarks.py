#!/usr/bin/env python3
"""IMG-SHOPMILL-WATERMARK-CLEANUP — audit + remediate ShopMill watermarks.

Active/public storefront products are defined as:
  is_active=true AND deleted_at IS NULL
(see app/api/endpoints/products_catalog.py forcing is_active for public lists,
 and app/crud/product.py excluding soft-deleted rows).

Default data sources (offline, no production writes):
  - IMG-02A-01 inventory CSV (authoritative ProductImage snapshot)
  - IMG-02A-02 human-review asset-review.csv (watermark_status)
  - Human-review preview pixels under /var/tmp/karzar-image-review/

Examples:
  python scripts/audit_active_product_shopmill_watermarks.py \\
    --mode audit --report-dir aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP \\
    --work-dir /var/tmp/karzar-shopmill-cleanup

  python scripts/audit_active_product_shopmill_watermarks.py \\
    --mode remediate --report-dir ... --work-dir ...
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.shopmill_watermark.contracts import (  # noqa: E402
    DEFAULT_HR_ASSET_REVIEWS,
    DEFAULT_INVENTORY_CSV,
    DEFAULT_PREVIEW_ROOTS,
    TASK_ID,
)
from scripts.shopmill_watermark.detect import detect_shopmill_file  # noqa: E402
from scripts.shopmill_watermark.inventory import (  # noqa: E402
    active_public_images,
    index_by_sha,
    load_hr_watermark_assets,
    load_inventory,
    resolve_preview_path,
)
from scripts.shopmill_watermark.output import write_csv, write_json  # noqa: E402
from scripts.shopmill_watermark.remediate import remediate_file  # noqa: E402

ACTIVE_PRODUCT_FIELDS = [
    "product_id",
    "sku",
    "product_slug",
    "product_name",
    "brand_name",
    "category_name",
    "product_is_active",
    "product_deleted",
    "product_is_available",
    "image_count",
]

IMAGE_FIELDS = [
    "product_id",
    "sku",
    "product_slug",
    "product_name",
    "brand_name",
    "product_is_active",
    "product_deleted",
    "product_is_available",
    "image_id",
    "image_url",
    "mapped_local_relative_path",
    "image_role",
    "is_primary",
    "display_order",
    "sha256",
    "width",
    "height",
    "byte_size",
    "mime_type",
    "preview_path",
    "source_system",
]

CANDIDATE_FIELDS = IMAGE_FIELDS + [
    "hr_watermark_status",
    "hr_asset_decision",
    "hr_batch_id",
    "hr_notes",
    "auto_detected",
    "auto_confidence",
    "auto_mode",
    "auto_bbox",
    "detection_result",
]

CONFIRMED_FIELDS = CANDIDATE_FIELDS + [
    "confirmation_basis",
    "visual_verification",
]

REMEDIATION_FIELDS = [
    "product_id",
    "sku",
    "product_slug",
    "product_name",
    "brand_name",
    "image_id",
    "sha256_original",
    "image_url_original",
    "mapped_local_relative_path",
    "preview_path",
    "remediation_method",
    "replacement_source",
    "output_path",
    "sha256_final",
    "width",
    "height",
    "remaining_logo_yellow",
    "remediation_ok",
    "reason",
    "verification_status",
]

VERIFY_FIELDS = [
    "sha256_original",
    "output_path",
    "post_detected",
    "post_confidence",
    "remaining_logo_yellow",
    "verification_status",
    "product_count",
]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--mode",
        choices=("audit", "remediate", "verify", "all"),
        default="all",
    )
    p.add_argument(
        "--inventory-csv",
        type=Path,
        default=Path(DEFAULT_INVENTORY_CSV),
    )
    p.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="In-repo report directory (CSV + README live here)",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Absolute directory outside the repo for binary remediations",
    )
    p.add_argument(
        "--preview-root",
        action="append",
        default=None,
        help="Override/add preview root (repeatable)",
    )
    return p


def _image_role(is_primary: bool) -> str:
    return "primary" if is_primary else "gallery"


def run_audit(
    *,
    inventory_csv: Path,
    report_dir: Path,
    preview_roots: tuple[str, ...],
) -> dict:
    rows = load_inventory(inventory_csv)
    active_imgs = active_public_images(rows)
    by_product: dict[str, list] = {}
    for img in active_imgs:
        by_product.setdefault(img.product_id, []).append(img)

    active_products = []
    for product_id, imgs in sorted(by_product.items(), key=lambda kv: int(kv[0])):
        first = imgs[0]
        active_products.append(
            {
                "product_id": product_id,
                "sku": first.sku,
                "product_slug": first.product_slug,
                "product_name": first.product_name,
                "brand_name": first.brand_name,
                "category_name": first.category_name,
                "product_is_active": first.product_is_active,
                "product_deleted": first.product_deleted,
                "product_is_available": first.product_is_available,
                "image_count": len(imgs),
            }
        )

    hr = load_hr_watermark_assets(DEFAULT_HR_ASSET_REVIEWS)
    by_sha = index_by_sha(active_imgs)

    image_rows = []
    candidates = []
    confirmed = []

    for img in active_imgs:
        preview = resolve_preview_path(img.sha256, preview_roots) if img.sha256 else None
        base = {
            "product_id": img.product_id,
            "sku": img.sku,
            "product_slug": img.product_slug,
            "product_name": img.product_name,
            "brand_name": img.brand_name,
            "product_is_active": img.product_is_active,
            "product_deleted": img.product_deleted,
            "product_is_available": img.product_is_available,
            "image_id": img.image_id,
            "image_url": img.image_url,
            "mapped_local_relative_path": img.mapped_local_relative_path,
            "image_role": _image_role(img.is_primary),
            "is_primary": img.is_primary,
            "display_order": img.display_order,
            "sha256": img.sha256,
            "width": img.width,
            "height": img.height,
            "byte_size": img.byte_size,
            "mime_type": img.mime_type,
            "preview_path": str(preview) if preview else "",
            "source_system": "IMG-02A-01 inventory + IMG-02A-02 HR",
        }
        image_rows.append(base)

        hr_row = hr.get(img.sha256)
        auto_detected = False
        auto_confidence = ""
        auto_mode = ""
        auto_bbox = ""
        if preview is not None:
            det = detect_shopmill_file(preview)
            auto_detected = bool(det.detected)
            auto_confidence = det.confidence
            auto_mode = det.mode
            auto_bbox = "" if det.bbox is None else ",".join(map(str, det.bbox))

        is_hr_positive = hr_row is not None
        if not (is_hr_positive or auto_detected):
            continue

        cand = {
            **base,
            "hr_watermark_status": (hr_row or {}).get("watermark_status", ""),
            "hr_asset_decision": (hr_row or {}).get("asset_decision", ""),
            "hr_batch_id": (hr_row or {}).get("batch_id", ""),
            "hr_notes": (hr_row or {}).get("asset_notes", ""),
            "auto_detected": auto_detected,
            "auto_confidence": auto_confidence,
            "auto_mode": auto_mode,
            "auto_bbox": auto_bbox,
            "detection_result": (
                "hr_and_auto"
                if is_hr_positive and auto_detected
                else ("hr_only" if is_hr_positive else "auto_only")
            ),
        }
        candidates.append(cand)

        # Confirmation policy: IMG-02A-02 human-review distributor_or_retailer
        # is binding for ShopMill. Auto-only hits stay candidates (false-positive
        # risk on yellow product bodies / packaging — e.g. Mitutoyo KEEP assets).
        if is_hr_positive:
            conf = {
                **cand,
                "confirmation_basis": "IMG-02A-02 human_review distributor_or_retailer",
                "visual_verification": "confirmed_via_hr_and_sample_visual_qa",
            }
            confirmed.append(conf)

    write_csv(report_dir / "active-products.csv", ACTIVE_PRODUCT_FIELDS, active_products)
    write_csv(report_dir / "active-product-images.csv", IMAGE_FIELDS, image_rows)
    write_csv(report_dir / "shopmill-watermark-candidates.csv", CANDIDATE_FIELDS, candidates)
    write_csv(report_dir / "shopmill-watermark-confirmed.csv", CONFIRMED_FIELDS, confirmed)

    unique_assets = {r["sha256"] for r in confirmed if r["sha256"]}
    summary = {
        "task_id": TASK_ID,
        "observed_at_utc": _utc_now(),
        "inventory_csv": str(inventory_csv),
        "active_public_semantics": {
            "is_active": True,
            "deleted": False,
            "require_available": False,
            "citations": [
                "app/api/endpoints/products_catalog.py:131-132",
                "app/crud/product.py:115",
                "app/db/models/product.py:187-188",
            ],
        },
        "counts": {
            "inventory_image_rows": len(rows),
            "active_public_products_with_images": len(active_products),
            "active_public_image_rows": len(active_imgs),
            "unique_active_image_sha256": len({r.sha256 for r in active_imgs if r.sha256}),
            "hr_distributor_or_retailer_assets": len(hr),
            "automatic_candidates_rows": len(candidates),
            "confirmed_image_rows": len(confirmed),
            "confirmed_unique_assets": len(unique_assets),
            "confirmed_products": len({r["product_id"] for r in confirmed}),
            "brands": dict(
                Counter((r["brand_name"] or "?") for r in confirmed).most_common()
            ),
        },
        "live_network": {
            "status": "blocked",
            "note": "Outbound HTTPS to api.karzartools.com failed in this environment; "
            "audit uses IMG-02A-01/02 offline corpus + FAST-01A metadata (no image blobs).",
        },
        "notes": [
            "IMG-02A-01: products_with_multiple_images=0 — each imaged product has one row",
            "Human-review watermark_status=distributor_or_retailer is ShopMill for this corpus",
            "Preview pixels used for auto-detection and Method C remediation",
        ],
    }
    write_json(report_dir / "audit-summary.json", summary)
    # unique asset list for remediation
    asset_index = []
    for sha in sorted(unique_assets):
        preview = resolve_preview_path(sha, preview_roots)
        products = by_sha.get(sha, [])
        asset_index.append(
            {
                "sha256": sha,
                "preview_path": str(preview) if preview else "",
                "product_count": len(products),
                "product_ids": ",".join(p.product_id for p in products),
                "skus": ",".join(p.sku for p in products),
                "brands": ",".join(sorted({p.brand_name for p in products})),
            }
        )
    write_csv(
        report_dir / "confirmed-unique-assets.csv",
        [
            "sha256",
            "preview_path",
            "product_count",
            "product_ids",
            "skus",
            "brands",
        ],
        asset_index,
    )
    return summary


def run_remediate(
    *,
    report_dir: Path,
    work_dir: Path,
    preview_roots: tuple[str, ...],
) -> dict:
    confirmed_path = report_dir / "shopmill-watermark-confirmed.csv"
    if not confirmed_path.is_file():
        raise SystemExit("missing shopmill-watermark-confirmed.csv — run --mode audit first")

    with confirmed_path.open(newline="", encoding="utf-8") as f:
        confirmed = list(csv_dict_reader(f))

    unique: dict[str, dict] = {}
    for row in confirmed:
        sha = row["sha256"]
        unique.setdefault(sha, row)

    repaired_dir = work_dir / "repaired_assets"
    repaired_dir.mkdir(parents=True, exist_ok=True)
    before_dir = work_dir / "before_assets"
    before_dir.mkdir(parents=True, exist_ok=True)

    remediation_rows = []
    asset_results = {}
    for sha, sample in sorted(unique.items()):
        preview = resolve_preview_path(sha, preview_roots)
        if preview is None:
            for row in [r for r in confirmed if r["sha256"] == sha]:
                remediation_rows.append(
                    {
                        "product_id": row["product_id"],
                        "sku": row["sku"],
                        "product_slug": row["product_slug"],
                        "product_name": row["product_name"],
                        "brand_name": row["brand_name"],
                        "image_id": row["image_id"],
                        "sha256_original": sha,
                        "image_url_original": row["image_url"],
                        "mapped_local_relative_path": row["mapped_local_relative_path"],
                        "preview_path": "",
                        "remediation_method": "unresolved",
                        "replacement_source": "",
                        "output_path": "",
                        "sha256_final": "",
                        "width": "",
                        "height": "",
                        "remaining_logo_yellow": "",
                        "remediation_ok": False,
                        "reason": "preview_missing",
                        "verification_status": "unresolved",
                    }
                )
            asset_results[sha] = {"ok": False, "reason": "preview_missing"}
            continue

        # Method A/B: no clean manufacturer originals available offline for
        # TERMA/ASTPOWER/SAN OU/Dasqua ShopMill set (IMG-02B accepted=INSIZE only).
        dest = repaired_dir / f"{sha}{preview.suffix.lower()}"
        before_copy = before_dir / preview.name
        if not before_copy.exists():
            shutil.copy2(preview, before_copy)
        result = remediate_file(preview, dest)
        asset_results[sha] = {
            "ok": result.ok,
            "output_path": str(result.output_path) if result.output_path else "",
            "sha256_final": result.final_sha256,
            "reason": result.reason,
            "remaining_logo_yellow": result.remaining_logo_yellow,
            "bbox": result.detection.bbox,
        }
        for row in [r for r in confirmed if r["sha256"] == sha]:
            remediation_rows.append(
                {
                    "product_id": row["product_id"],
                    "sku": row["sku"],
                    "product_slug": row["product_slug"],
                    "product_name": row["product_name"],
                    "brand_name": row["brand_name"],
                    "image_id": row["image_id"],
                    "sha256_original": sha,
                    "image_url_original": row["image_url"],
                    "mapped_local_relative_path": row["mapped_local_relative_path"],
                    "preview_path": str(preview),
                    "remediation_method": "method_c_bbox_fill"
                    if result.ok
                    else "method_c_failed",
                    "replacement_source": str(preview),
                    "output_path": str(result.output_path) if result.output_path else "",
                    "sha256_final": result.final_sha256 if result.ok else "",
                    "width": result.width,
                    "height": result.height,
                    "remaining_logo_yellow": result.remaining_logo_yellow,
                    "remediation_ok": result.ok,
                    "reason": result.reason,
                    "verification_status": "pending_verify" if result.ok else "failed",
                }
            )

    write_csv(report_dir / "remediation-manifest.csv", REMEDIATION_FIELDS, remediation_rows)
    write_json(work_dir / "asset-remediation-results.json", asset_results)

    ok_assets = sum(1 for v in asset_results.values() if v.get("ok"))
    summary = {
        "task_id": TASK_ID,
        "observed_at_utc": _utc_now(),
        "unique_assets_attempted": len(asset_results),
        "unique_assets_repaired_ok": ok_assets,
        "unique_assets_failed": len(asset_results) - ok_assets,
        "method_a_clean_originals": 0,
        "method_b_clean_alternates": 0,
        "method_c_repaired": ok_assets,
        "unresolved": len(asset_results) - ok_assets,
        "work_dir": str(work_dir),
        "repaired_dir": str(repaired_dir),
        "apply_status": "not_applied_to_db_or_storage",
        "apply_blocker": (
            "No local DATABASE_URL / empty data/uploads/products; "
            "ADR-012 forbids production writes from this node. "
            "Remediated binaries are staged under work-dir for a future local apply."
        ),
    }
    write_json(report_dir / "remediation-summary.json", summary)
    return summary


def csv_dict_reader(f):
    import csv

    reader = csv.DictReader(f)
    for raw in reader:
        yield {k.lstrip("\ufeff"): v for k, v in raw.items()}


def run_verify(*, report_dir: Path, work_dir: Path) -> dict:
    manifest = report_dir / "remediation-manifest.csv"
    if not manifest.is_file():
        raise SystemExit("missing remediation-manifest.csv — run --mode remediate first")

    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv_dict_reader(f))

    by_sha: dict[str, dict] = {}
    for row in rows:
        sha = row["sha256_original"]
        by_sha.setdefault(
            sha,
            {
                "sha256_original": sha,
                "output_path": row.get("output_path") or "",
                "product_count": 0,
            },
        )
        by_sha[sha]["product_count"] += 1
        if row.get("output_path"):
            by_sha[sha]["output_path"] = row["output_path"]

    verify_rows = []
    positive = 0
    for sha, meta in sorted(by_sha.items()):
        out = Path(meta["output_path"]) if meta["output_path"] else None
        if out is None or not out.is_file():
            verify_rows.append(
                {
                    **meta,
                    "post_detected": "",
                    "post_confidence": "",
                    "remaining_logo_yellow": "",
                    "verification_status": "missing_output",
                }
            )
            positive += 1
            continue
        det = detect_shopmill_file(out)
        from scripts.shopmill_watermark.detect import remaining_logo_zone_yellow
        import numpy as np
        from PIL import Image

        rgb = np.asarray(Image.open(out).convert("RGB"))
        rem = remaining_logo_zone_yellow(rgb)
        status = "clean" if (not det.detected and rem < 40) else "shopmill_positive"
        if status != "clean":
            positive += 1
        verify_rows.append(
            {
                **meta,
                "post_detected": det.detected,
                "post_confidence": det.confidence,
                "remaining_logo_yellow": rem,
                "verification_status": status,
            }
        )
        # update manifest verification_status for matching rows
        for row in rows:
            if row["sha256_original"] == sha:
                row["verification_status"] = status

    write_csv(report_dir / "verification-results.csv", VERIFY_FIELDS, verify_rows)
    write_csv(report_dir / "remediation-manifest.csv", REMEDIATION_FIELDS, rows)

    summary = {
        "task_id": TASK_ID,
        "observed_at_utc": _utc_now(),
        "unique_assets_verified": len(verify_rows),
        "final_shopmill_positive_assets": positive,
        "clean_assets": len(verify_rows) - positive,
        "acceptance_gate": positive == 0,
    }
    write_json(report_dir / "verification-summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report_dir = args.report_dir.resolve()
    work_dir = args.work_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        work_dir.relative_to(REPO_ROOT)
        raise SystemExit("--work-dir must be outside the repository (binary packaging)")
    except ValueError:
        pass

    preview_roots = tuple(args.preview_root) if args.preview_root else DEFAULT_PREVIEW_ROOTS

    summaries = {}
    if args.mode in {"audit", "all"}:
        summaries["audit"] = run_audit(
            inventory_csv=args.inventory_csv,
            report_dir=report_dir,
            preview_roots=preview_roots,
        )
        print(json.dumps({"phase": "audit", **summaries["audit"]["counts"]}, indent=2))
    if args.mode in {"remediate", "all"}:
        summaries["remediate"] = run_remediate(
            report_dir=report_dir,
            work_dir=work_dir,
            preview_roots=preview_roots,
        )
        print(json.dumps({"phase": "remediate", **summaries["remediate"]}, indent=2))
    if args.mode in {"verify", "all"}:
        summaries["verify"] = run_verify(report_dir=report_dir, work_dir=work_dir)
        print(json.dumps({"phase": "verify", **summaries["verify"]}, indent=2))

    write_json(report_dir / "run-summary.json", {"task_id": TASK_ID, "phases": summaries})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
