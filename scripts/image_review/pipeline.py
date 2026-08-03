"""Orchestrate offline human-review package generation (Pilot + sequential batches)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scripts.image_audit.contracts import AuditError

from .contracts import (
    ASSET_MANIFEST_FIELDS,
    ASSIGNMENT_MANIFEST_FIELDS,
    AUTHORITATIVE_CHECKSUMS_DIGEST,
    EXPECTED_SOURCE_SUMMARY,
    PILOT_BATCH_ID,
    PILOT_SHARED_COUNT,
    PILOT_SINGLETON_COUNT,
    REVIEW_SCHEMA_VERSION,
    TASK_ID,
    ReviewError,
)
from .html_review import assert_html_offline_contract, build_review_html
from .output import (
    create_pilot_zip,
    prepare_review_output_dir,
    publish_review_outputs,
    write_csv,
    write_json,
)
from .previews import generate_derivatives
from .prior_batches import load_prior_batch_exclusions
from .review_schema import (
    ASSET_TEMPLATE_FIELDS,
    ASSIGNMENT_TEMPLATE_FIELDS,
    asset_review_template_rows,
    assignment_review_template_rows,
    review_schema_document,
)
from .selection import assignments_for_assets, group_assets, select_review_batch_assets
from .source_inventory import assert_storage_root, load_verified_source

REVIEW_GUIDE_FA = """# راهنمای بازبینی انسانی تصاویر موجود (IMG-02A-02)

## دو سطح بازبینی

1. **سطح دارایی (Asset):** درباره خود فایل تصویر تصمیم می‌گیرید — کیفیت، پس‌زمینه، کراپ، واترمارک قابل‌رؤیت، اولویت جایگزینی، و وضعیت حقوق.
2. **سطح انتساب (Assignment):** دربارهٔ استفادهٔ همان تصویر برای یک محصول مشخص تصمیم می‌گیرید — آیا تصویر همان SKU را نشان می‌دهد، تصویر خانوادگی/مشترک است، یا نامتناسب به نظر می‌رسد.

یک تصویر ممکن است از نظر بصری خوب باشد ولی برای یکی از محصولات متصل مناسب نباشد. این دو تصمیم را ادغام نکنید.

## واترمارک

- واترمارک خرده‌فروش/توزیع‌کننده/مارکت‌پلیس را جدا از لوگوی سازنده ثبت کنید.
- **لوگوی سازنده به‌خودی‌خود مشکل حقوق نیست** و به‌معنای مجوز قطعی هم نیست.
- وضعیت حقوق (`rights_status`) از وضعیت واترمارک جدا است و پیش‌فرض آن `review_required` است.
- این بسته هیچ حکم حقوقی صادر نمی‌کند و مجوز قانونی ادعا نمی‌کند.

## کیفیت فنی

- وضوح پایین، تاری، کراپ نامناسب و پس‌زمینه شلوغ را با برچسب‌های کیفیت/پس‌زمینه/کراپ ثبت کنید.
- پرچم‌های پیش‌غربال فنی فقط هشدار هستند، نه رأی نهایی.

## تناسب محصول

- `exact_or_likely_exact`: تصویر همان محصول/SKU را نشان می‌دهد.
- `family_shared_plausible`: تصویر خانواده/سری است و برای این محصول قابل‌قبول به نظر می‌رسد.
- `likely_mismatch`: به نظر می‌رسد به محصول دیگری تعلق دارد.
- `insufficient_context`: برای قضاوت به اطلاعات بیشتر نیاز است.

## معنی تصمیم‌ها

- `KEEP` / `KEEP_AS_SECONDARY` / `PREFER_REPLACEMENT` / `REPLACE_REQUIRED` / `MANUAL_REVIEW` / `BROKEN_OR_UNAVAILABLE`
- این بازبینی هیچ فایلی را حذف یا جایگزین نمی‌کند و پایگاه‌داده/`ProductImage` را تغییر نمی‌دهد.

## خروجی

ویرایش‌های موقت فقط در مرورگر (localStorage) می‌مانند. CSV/JSON را صادر کنید. هیچ داده‌ای به شبکه ارسال نمی‌شود.
"""


def _wrap_audit(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
    try:
        return fn(*args, **kwargs)
    except AuditError as e:
        raise ReviewError(e.code, str(e).split(": ", 1)[-1]) from e


def build_review_batch_package(
    source_dir: Path,
    storage_root: Path,
    output_dir: Path,
    repository_root: Path,
    *,
    task_id: str = TASK_ID,
    batch_id: str = PILOT_BATCH_ID,
    expected_checksums_digest: str = AUTHORITATIVE_CHECKSUMS_DIGEST,
    expected_summary: dict[str, Any] | None = None,
    shared_count: int = PILOT_SHARED_COUNT,
    singleton_count: int = PILOT_SINGLETON_COUNT,
    prior_batch_dirs: Sequence[Path] | None = None,
    zip_path: Path | None = None,
    network_guard: Any | None = None,
) -> dict[str, Any]:
    """Build a deterministic offline review package. On failure, output_dir is left empty."""
    if network_guard is not None:
        network_guard()

    summary_expect = EXPECTED_SOURCE_SUMMARY if expected_summary is None else expected_summary
    prior_dirs = list(prior_batch_dirs or [])
    try:
        _wrap_audit(
            prepare_review_output_dir,
            output_dir,
            repository_root=repository_root,
            storage_root=storage_root,
        )
        _wrap_audit(assert_storage_root, storage_root)
        mapping, source_summary, rows = load_verified_source(
            source_dir,
            expected_checksums_digest=expected_checksums_digest,
            expected_summary=summary_expect,
        )
        assets, remote_deferred = group_assets(rows)
        known_ids = {str(a["sha256"]).lower() for a in assets}

        prior_evidence = load_prior_batch_exclusions(
            prior_dirs,
            repository_root=repository_root,
            storage_root=storage_root,
            output_dir=output_dir,
            known_source_asset_ids=known_ids,
        )
        excluded_ids = prior_evidence["excluded_asset_ids"]

        selected, selection_meta = select_review_batch_assets(
            assets,
            excluded_asset_ids=excluded_ids,
            shared_count=shared_count,
            singleton_count=singleton_count,
            total=shared_count + singleton_count,
        )
        overlap = sorted(set(selection_meta["selected_asset_ids"]) & set(excluded_ids))
        if overlap:
            raise ReviewError("selection", f"prior-batch overlap detected: {overlap[0]}")
        selection_meta["prior_overlap_count"] = 0
        selection_meta["prior_batch_ids"] = list(prior_evidence["prior_batch_ids"])
        selection_meta["prior_batch_count"] = prior_evidence["prior_batch_count"]

        assignments = assignments_for_assets(selected)
        for asset in selected:
            expected_ids = sorted(int(i) for i in asset["image_ids"])
            got = sorted(
                a["image_id"] for a in assignments if a["asset_id"] == asset["sha256"]
            )
            if got != expected_ids:
                raise ReviewError(
                    "selection",
                    f"missing assignments for asset {asset['sha256']}: {got} != {expected_ids}",
                )

        schema = review_schema_document()
        derivative_records: list[dict[str, Any]] = []
        manifest_assets: list[dict[str, Any]] = []

        def writer(staging: Path) -> None:
            nonlocal derivative_records, manifest_assets
            preview_dir = staging / "previews"
            thumb_dir = staging / "thumbs"
            preview_dir.mkdir(parents=True, exist_ok=True)
            thumb_dir.mkdir(parents=True, exist_ok=True)
            derivative_records = []
            manifest_assets = []
            for asset in selected:
                rel = str(asset["source_relative_path"] or "")
                if not rel:
                    raise ReviewError("storage", f"missing source path for {asset['sha256']}")
                deriv = generate_derivatives(
                    storage_root,
                    relative_path=rel,
                    expected_sha256=str(asset["sha256"]),
                    preview_dir=preview_dir,
                    thumb_dir=thumb_dir,
                )
                derivative_records.append(deriv)
                row = {k: asset.get(k) for k in ASSET_MANIFEST_FIELDS if k in asset}
                row.update(deriv["prescreen"])
                row["preview_filename"] = deriv["preview_filename"]
                row["thumb_filename"] = deriv["thumb_filename"]
                row["width"] = deriv["width"]
                row["height"] = deriv["height"]
                row["selection_segment"] = asset["selection_segment"]
                row["selection_rank"] = asset["selection_rank"]
                row["image_ids"] = asset["image_ids"]
                row["product_ids"] = asset["product_ids"]
                row["brands"] = asset["brands"]
                manifest_assets.append(row)

            write_json(
                staging / "batch-metadata.json",
                {
                    "task_id": task_id,
                    "batch_id": batch_id,
                    "review_schema_version": REVIEW_SCHEMA_VERSION,
                    "source_unique_assets": selection_meta["source_unique_assets"],
                    "prior_batch_ids": selection_meta["prior_batch_ids"],
                    "prior_batch_count": selection_meta["prior_batch_count"],
                    "excluded_prior_asset_count": selection_meta["excluded_prior_asset_count"],
                    "eligible_assets_before_selection": selection_meta[
                        "eligible_assets_before_selection"
                    ],
                    "selected_unique_assets": len(manifest_assets),
                    "shared_assets_selected": selection_meta["shared_selected"],
                    "singleton_assets_selected": selection_meta["singleton_selected"],
                    "assignment_rows": len(assignments),
                    "remaining_unique_assets_after_selection": selection_meta[
                        "remaining_unique_assets_after_selection"
                    ],
                    "fallback_used": selection_meta["fallback_used"],
                    "selection": selection_meta,
                },
            )
            write_json(
                staging / "source-evidence.json",
                {
                    "source_dir_name": source_dir.name,
                    "checksums_sha256_digest": expected_checksums_digest,
                    "verified_manifest_files": sorted(mapping.keys()),
                    "source_summary": {
                        k: source_summary.get(k) for k in summary_expect.keys()
                    },
                },
            )
            write_json(
                staging / "prior-batch-evidence.json",
                {
                    "prior_batch_ids": prior_evidence["prior_batch_ids"],
                    "prior_batch_count": prior_evidence["prior_batch_count"],
                    "excluded_prior_asset_count": prior_evidence["excluded_prior_asset_count"],
                    "prior_batches": [
                        {
                            "batch_id": r["batch_id"],
                            "task_id": r.get("task_id"),
                            "selected_unique_assets": r["selected_unique_assets"],
                            "batch_dir": r["batch_dir"],
                            # Asset IDs intentionally omitted from Git-facing aggregates;
                            # present only in the external package for operator audit.
                            "asset_id_count": len(r["asset_ids"]),
                        }
                        for r in prior_evidence["prior_batches"]
                    ],
                },
            )
            write_csv(staging / "asset-manifest.csv", ASSET_MANIFEST_FIELDS, manifest_assets)
            write_json(staging / "asset-manifest.json", manifest_assets)
            write_csv(staging / "assignment-manifest.csv", ASSIGNMENT_MANIFEST_FIELDS, assignments)
            write_json(staging / "assignment-manifest.json", assignments)
            asset_templates = asset_review_template_rows(
                batch_id, [a["asset_id"] for a in manifest_assets]
            )
            asg_templates = assignment_review_template_rows(batch_id, assignments)
            write_csv(staging / "asset-review-template.csv", ASSET_TEMPLATE_FIELDS, asset_templates)
            write_csv(
                staging / "assignment-review-template.csv",
                ASSIGNMENT_TEMPLATE_FIELDS,
                asg_templates,
            )
            write_json(staging / "review-schema.json", schema)
            (staging / "review-guide-fa.md").write_text(REVIEW_GUIDE_FA, encoding="utf-8")
            html = build_review_html(
                batch_id=batch_id,
                assets=manifest_assets,
                assignments=assignments,
                schema=schema,
            )
            assert_html_offline_contract(html)
            (staging / "review.html").write_text(html, encoding="utf-8")
            write_csv(
                staging / "remote-deferred.csv",
                ("image_id", "product_id", "sku", "image_url", "reason"),
                remote_deferred,
            )
            brands = sorted(
                {b for a in manifest_assets for b in (a.get("brands") or []) if b}
            )
            summary = {
                "task_id": task_id,
                "batch_id": batch_id,
                "review_schema_version": REVIEW_SCHEMA_VERSION,
                "source_unique_assets": selection_meta["source_unique_assets"],
                "prior_batch_ids": selection_meta["prior_batch_ids"],
                "prior_batch_count": selection_meta["prior_batch_count"],
                "excluded_prior_asset_count": selection_meta["excluded_prior_asset_count"],
                "eligible_assets_before_selection": selection_meta[
                    "eligible_assets_before_selection"
                ],
                "selected_unique_assets": len(manifest_assets),
                "shared_assets_selected": selection_meta["shared_selected"],
                "singleton_assets_selected": selection_meta["singleton_selected"],
                "assignment_rows": len(assignments),
                "remaining_unique_assets_after_selection": selection_meta[
                    "remaining_unique_assets_after_selection"
                ],
                "brands_represented": brands,
                "brands_represented_count": len(brands),
                "low_resolution_candidates": sum(
                    1 for a in manifest_assets if a.get("low_resolution_candidate")
                ),
                "extreme_aspect_candidates": sum(
                    1 for a in manifest_assets if a.get("extreme_aspect_candidate")
                ),
                "transparent_background_candidates": sum(
                    1 for a in manifest_assets if a.get("transparent_background_candidate")
                ),
                "busy_border_candidates": sum(
                    1
                    for a in manifest_assets
                    if a.get("busy_or_nonuniform_border_candidate")
                ),
                "preview_count": len(list((staging / "previews").iterdir())),
                "thumbnail_count": len(list((staging / "thumbs").iterdir())),
                "remote_deferred_rows": len(remote_deferred),
                "network_requests_performed": 0,
                "database_accessed": False,
                "database_modified": False,
                "source_storage_modified": False,
                "source_storage_mutations": 0,
                "product_images_modified": False,
                "repository_modified_by_batch_run": False,
                "repository_modified_by_pilot_run": False,
                "fallback_used": selection_meta["fallback_used"],
                "selected_asset_ids": [a["asset_id"] for a in manifest_assets],
                "preview_sha256_map": {
                    d["preview_filename"]: d["preview_sha256"] for d in derivative_records
                },
                "thumb_sha256_map": {
                    d["thumb_filename"]: d["thumb_sha256"] for d in derivative_records
                },
            }
            write_json(staging / "summary.json", summary)

        publish_review_outputs(output_dir, writers=[writer])

        result = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
        result["output_dir"] = str(output_dir)
        if zip_path is not None:
            zip_digest = create_pilot_zip(output_dir, zip_path)
            result["batch_zip_path"] = str(zip_path)
            result["batch_zip_sha256"] = zip_digest
            result["pilot_zip_path"] = str(zip_path)
            result["pilot_zip_sha256"] = zip_digest
        return result
    except Exception:
        if output_dir.exists():
            for child in list(output_dir.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
        raise


def build_pilot_package(
    source_dir: Path,
    storage_root: Path,
    output_dir: Path,
    repository_root: Path,
    *,
    batch_id: str = PILOT_BATCH_ID,
    expected_checksums_digest: str = AUTHORITATIVE_CHECKSUMS_DIGEST,
    expected_summary: dict[str, Any] | None = None,
    shared_count: int | None = None,
    singleton_count: int | None = None,
    zip_path: Path | None = None,
    network_guard: Any | None = None,
    task_id: str = TASK_ID,
    prior_batch_dirs: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Backward-compatible entrypoint; defaults preserve Pilot 001 selection."""
    return build_review_batch_package(
        source_dir,
        storage_root,
        output_dir,
        repository_root,
        task_id=task_id,
        batch_id=batch_id,
        expected_checksums_digest=expected_checksums_digest,
        expected_summary=expected_summary,
        shared_count=PILOT_SHARED_COUNT if shared_count is None else shared_count,
        singleton_count=PILOT_SINGLETON_COUNT if singleton_count is None else singleton_count,
        prior_batch_dirs=prior_batch_dirs,
        zip_path=zip_path,
        network_guard=network_guard,
    )


def semantic_compare_summaries(a: dict[str, Any], b: dict[str, Any]) -> None:
    keys = (
        "selected_asset_ids",
        "shared_assets_selected",
        "singleton_assets_selected",
        "assignment_rows",
        "preview_sha256_map",
        "thumb_sha256_map",
        "selected_unique_assets",
        "excluded_prior_asset_count",
        "eligible_assets_before_selection",
        "remaining_unique_assets_after_selection",
        "prior_batch_ids",
    )
    for key in keys:
        if key in a or key in b:
            if a.get(key) != b.get(key):
                raise ReviewError("determinism", f"semantic mismatch on {key}")
