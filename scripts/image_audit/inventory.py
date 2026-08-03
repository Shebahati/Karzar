"""Orchestrate canonical ProductImage inventory (IMG-02A-01)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .contracts import (
    PRIOR_REFERENCE_SNAPSHOT,
    TASK_ID,
    ImageRow,
    ProductRow,
    StorageEntry,
)
from .database import ReadOnlyDbContext, fetch_product_images, fetch_products
from .output import publish_inventory_outputs, write_csv, write_json
from .storage import (
    classify_image_url,
    file_meta_for_mapped_path,
    scan_storage_tree,
)

INVENTORY_FIELDS = [
    "observed_at_utc",
    "image_id",
    "product_id",
    "sku",
    "product_slug",
    "product_name",
    "product_deleted",
    "product_is_active",
    "product_is_available",
    "brand_id",
    "brand_name",
    "category_id",
    "category_name",
    "image_url",
    "url_kind",
    "url_host",
    "url_path",
    "query_present",
    "is_primary",
    "display_order",
    "product_image_count",
    "product_primary_image_count",
    "mapped_local_relative_path",
    "local_exists",
    "local_entry_status",
    "byte_size",
    "sha256",
    "detected_format",
    "mime_type",
    "width",
    "height",
    "decode_status",
    "exact_sha_group",
    "audit_status",
    "reason_codes",
]

COVERAGE_FIELDS = [
    "product_id",
    "sku",
    "name",
    "brand",
    "category",
    "deleted",
    "is_active",
    "is_available",
    "total_image_rows",
    "primary_image_rows",
    "valid_local_images",
    "remote_unverified_images",
    "invalid_image_rows",
    "missing_local_images",
    "has_any_image_row",
    "has_any_usable_or_remote_image",
    "coverage_status",
]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dup_key_for_image(img: ImageRow, *, storage_root: Path) -> str:
    cls = classify_image_url(img.image_url, storage_root=storage_root)
    if cls.url_kind in {"external_http", "external_https"}:
        parts = urlsplit((img.image_url or "").strip())
        scheme = (parts.scheme or "").lower()
        host = (parts.hostname or "").lower()
        port = parts.port
        port_str = "" if port is None else str(port)
        path = parts.path or ""
        return f"ext:{scheme}|{host}|{port_str}|{path}"
    if cls.mapped_relative_path:
        return f"int:{cls.mapped_relative_path}"
    return f"other:{(img.image_url or '').strip().lower()}"


def _is_valid_local_image(row: dict[str, Any]) -> bool:
    return (
        row.get("local_exists") is True
        and row.get("local_entry_status") == "regular_image"
        and row.get("decode_status") == "ok"
        and bool(row.get("sha256"))
    )


def _is_remote(row: dict[str, Any]) -> bool:
    return row.get("audit_status") == "remote_unverified"


def _audit_status_for_row(
    *,
    cls,
    meta,
    storage_scan: bool,
    reason_codes: list[str],
) -> str:
    if not storage_scan and cls.url_kind.startswith("internal") and cls.mapped_relative_path:
        reason_codes.append("storage_scan_skipped")
        reason_codes.append("local_unverified")
        return "local_unverified"
    if cls.url_kind in {"external_http", "external_https"}:
        return "remote_unverified"
    if cls.url_kind in {"empty_url", "malformed_url", "unsupported_scheme"}:
        return "invalid_url"
    if cls.mapped_relative_path is None and cls.url_kind.startswith("internal"):
        return "unsafe_or_unmapped_path"
    if meta.local_entry_status == "symlink_rejected":
        reason_codes.append("symlink_rejected")
        return "symlink_target"
    if meta.local_entry_status == "non_regular_rejected":
        reason_codes.append("non_regular_rejected")
        return "non_regular_local_target"
    if meta.local_entry_status == "decode_failed":
        reason_codes.append("decode_failed")
        return "decode_failed"
    if meta.local_entry_status == "regular_non_image":
        reason_codes.append("regular_non_image")
        return "non_image_local_file"
    if meta.local_entry_status == "path_rejected":
        reason_codes.append("path_rejected")
        return "unsafe_or_unmapped_path"
    if meta.local_exists is False:
        reason_codes.append("missing_local_file")
        return "missing_local_file"
    return "ok"


async def run_inventory(
    *,
    db: ReadOnlyDbContext,
    storage_root: Path,
    output_dir: Path,
    include_deleted_products: bool = True,
    storage_scan: bool = True,
    repository_root: Path,
) -> dict[str, Any]:
    started = _utc_now()
    observed = started

    products = await fetch_products(db.session, include_deleted=include_deleted_products)
    all_products = await fetch_products(db.session, include_deleted=True)
    all_product_ids = {p.product_id for p in all_products}
    images = await fetch_product_images(db.session)
    product_by_id = {p.product_id: p for p in products}

    images_by_product: dict[int, list[ImageRow]] = defaultdict(list)
    for img in images:
        if img.product_id in all_product_ids:
            images_by_product[img.product_id].append(img)

    storage_entries: list[StorageEntry] = []
    storage_index: dict[str, StorageEntry] = {}
    if storage_scan:
        storage_entries = scan_storage_tree(storage_root)
        storage_index = {e.relative_path: e for e in storage_entries}

    inventory_rows: list[dict[str, Any]] = []
    for img in images:
        if img.product_id in all_product_ids and img.product_id not in product_by_id:
            continue
        product = product_by_id.get(img.product_id)
        cls = classify_image_url(img.image_url, storage_root=storage_root)
        reason_codes = list(cls.reason_codes)

        if cls.url_kind in {"external_http", "external_https"}:
            meta = file_meta_for_mapped_path(
                storage_root,
                None,
                storage_index=None,
                allow_filesystem_fallback=False,
            )
            audit_status = "remote_unverified"
        elif not storage_scan:
            meta = file_meta_for_mapped_path(
                storage_root,
                cls.mapped_relative_path,
                storage_index=None,
                allow_filesystem_fallback=False,
            )
            audit_status = _audit_status_for_row(
                cls=cls,
                meta=meta,
                storage_scan=storage_scan,
                reason_codes=reason_codes,
            )
        else:
            meta = file_meta_for_mapped_path(
                storage_root,
                cls.mapped_relative_path,
                storage_index=storage_index,
            )
            audit_status = _audit_status_for_row(
                cls=cls,
                meta=meta,
                storage_scan=storage_scan,
                reason_codes=reason_codes,
            )

        siblings = images_by_product.get(img.product_id, [])
        primary_count = sum(1 for s in siblings if s.is_primary)

        inventory_rows.append(
            {
                "observed_at_utc": observed,
                "image_id": img.image_id,
                "product_id": img.product_id,
                "sku": product.sku if product else "",
                "product_slug": product.slug if product else "",
                "product_name": product.name if product else "",
                "product_deleted": bool(product.deleted_at) if product else None,
                "product_is_active": product.is_active if product else None,
                "product_is_available": product.is_available if product else None,
                "brand_id": product.brand_id if product else None,
                "brand_name": product.brand_name if product else None,
                "category_id": product.category_id if product else None,
                "category_name": product.category_name if product else None,
                "image_url": cls.sanitized_url,
                "url_kind": cls.url_kind,
                "url_host": cls.url_host,
                "url_path": cls.url_path,
                "query_present": cls.query_present,
                "is_primary": img.is_primary,
                "display_order": img.display_order,
                "product_image_count": len(siblings),
                "product_primary_image_count": primary_count,
                "mapped_local_relative_path": cls.mapped_relative_path,
                "local_exists": meta.local_exists,
                "local_entry_status": meta.local_entry_status,
                "byte_size": meta.byte_size,
                "sha256": meta.sha256,
                "detected_format": meta.detected_format,
                "mime_type": meta.mime_type,
                "width": meta.width,
                "height": meta.height,
                "decode_status": meta.decode_status,
                "exact_sha_group": "",
                "audit_status": audit_status,
                "reason_codes": reason_codes,
                "_raw_url_for_dup": img.image_url,
                "_brand_id": product.brand_id if product else None,
            }
        )

    sha_to_image_ids: dict[str, list[int]] = defaultdict(list)
    sha_to_paths: dict[str, set[str]] = defaultdict(set)
    sha_to_products: dict[str, set[int]] = defaultdict(set)
    sha_to_brands: dict[str, set[int | None]] = defaultdict(set)
    for row in inventory_rows:
        if _is_valid_local_image(row) and row["sha256"]:
            sha = row["sha256"]
            sha_to_image_ids[sha].append(int(row["image_id"]))
            if row.get("mapped_local_relative_path"):
                sha_to_paths[sha].add(str(row["mapped_local_relative_path"]))
            sha_to_products[sha].add(int(row["product_id"]))
            sha_to_brands[sha].add(row.get("_brand_id"))

    for e in storage_entries:
        if e.status == "regular_image" and e.sha256:
            sha_to_paths[e.sha256].add(e.relative_path)

    group_id_by_sha: dict[str, str] = {}
    for i, sha in enumerate(sorted(sha_to_paths.keys()), start=1):
        group_id_by_sha[sha] = f"sha-group-{i:05d}"

    for row in inventory_rows:
        sha = row.get("sha256")
        if sha and sha in group_id_by_sha and _is_valid_local_image(row):
            row["exact_sha_group"] = group_id_by_sha[sha]

    duplicate_rows: list[dict[str, Any]] = []
    exact_dup_groups = 0
    cross_product_groups = 0
    cross_brand_groups = 0
    for sha in sorted(sha_to_paths.keys()):
        paths = sorted(sha_to_paths[sha])
        product_ids_for_sha = sorted(x for x in sha_to_products.get(sha, set()))
        brands = sorted(x for x in sha_to_brands.get(sha, set()) if x is not None)
        image_ids = sorted(sha_to_image_ids.get(sha, []))
        multi_path = len(paths) > 1
        multi_ref = len(image_ids) > 1
        if not (multi_path or multi_ref):
            continue
        exact_dup_groups += 1
        if len(product_ids_for_sha) > 1:
            cross_product_groups += 1
        if len(set(brands)) > 1:
            cross_brand_groups += 1
        duplicate_rows.append(
            {
                "exact_sha_group": group_id_by_sha[sha],
                "sha256": sha,
                "physical_path_count": len(paths),
                "physical_paths": "|".join(paths),
                "product_image_row_count": len(image_ids),
                "image_ids": "|".join(str(i) for i in image_ids),
                "product_ids": "|".join(str(p) for p in product_ids_for_sha),
                "brand_ids": "|".join(str(b) for b in brands),
                "same_path_multi_reference": len(paths) == 1 and multi_ref,
                "duplicate_physical_files": multi_path,
                "cross_product": len(product_ids_for_sha) > 1,
                "cross_brand": len(set(brands)) > 1,
                "review_status": "pending_human_review",
            }
        )

    coverage_rows: list[dict[str, Any]] = []
    inv_by_product: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in inventory_rows:
        inv_by_product[int(row["product_id"])].append(row)

    for product in products:
        rows = inv_by_product.get(product.product_id, [])
        deleted = bool(product.deleted_at)
        valid_local = sum(1 for r in rows if _is_valid_local_image(r))
        remote = sum(1 for r in rows if _is_remote(r))
        missing = sum(1 for r in rows if r.get("audit_status") == "missing_local_file")
        invalid = sum(
            1
            for r in rows
            if r.get("audit_status")
            in {
                "invalid_url",
                "unsafe_or_unmapped_path",
                "decode_failed",
                "non_image_local_file",
                "symlink_target",
                "non_regular_local_target",
            }
        )
        primary_rows = sum(1 for r in rows if r.get("is_primary"))
        coverage_status = _coverage_status(
            deleted=deleted,
            rows=rows,
            valid_local=valid_local,
            remote=remote,
        )
        coverage_rows.append(
            {
                "product_id": product.product_id,
                "sku": product.sku,
                "name": product.name,
                "brand": product.brand_name or "",
                "category": product.category_name or "",
                "deleted": deleted,
                "is_active": product.is_active,
                "is_available": product.is_available,
                "total_image_rows": len(rows),
                "primary_image_rows": primary_rows,
                "valid_local_images": valid_local,
                "remote_unverified_images": remote,
                "invalid_image_rows": invalid,
                "missing_local_images": missing,
                "has_any_image_row": len(rows) > 0,
                "has_any_usable_or_remote_image": (valid_local + remote) > 0,
                "coverage_status": coverage_status,
            }
        )

    coverage_rows.sort(key=lambda r: int(r["product_id"]))

    anomaly_rows = _detect_anomalies(
        products,
        images,
        inventory_rows,
        product_by_id,
        all_product_ids=all_product_ids,
        storage_root=storage_root,
    )

    referenced_paths = {
        str(r["mapped_local_relative_path"])
        for r in inventory_rows
        if r.get("mapped_local_relative_path")
        and r.get("local_exists") is True
    }
    unreferenced: list[dict[str, Any]] = []
    rejected_storage: list[dict[str, Any]] = []
    for e in storage_entries:
        if e.status in {"symlink_rejected", "non_regular_rejected", "path_rejected"}:
            rejected_storage.append(
                {
                    "relative_path": e.relative_path,
                    "status": e.status,
                    "reason_codes": "|".join(e.reason_codes),
                    "review_status": "pending_human_review",
                }
            )
            continue
        if e.status in {"regular_image", "regular_non_image", "decode_failed"}:
            if e.relative_path not in referenced_paths:
                unreferenced.append(
                    {
                        "relative_path": e.relative_path,
                        "byte_size": e.byte_size,
                        "sha256": e.sha256,
                        "format": e.detected_format,
                        "mime_type": e.mime_type,
                        "width": e.width,
                        "height": e.height,
                        "decode_status": e.decode_status,
                        "reference_count": 0,
                        "review_status": "pending_human_review",
                    }
                )

    broken = [
        r
        for r in inventory_rows
        if r["audit_status"]
        in {
            "missing_local_file",
            "invalid_url",
            "unsafe_or_unmapped_path",
            "decode_failed",
            "non_image_local_file",
            "symlink_target",
            "non_regular_local_target",
        }
    ]
    remote_rows = [r for r in inventory_rows if r["audit_status"] == "remote_unverified"]
    without_valid = [
        c
        for c in coverage_rows
        if not c["deleted"] and c["valid_local_images"] == 0
    ]
    multi_image = [c for c in coverage_rows if c["total_image_rows"] > 1]

    public_inventory = []
    for row in inventory_rows:
        pub = {k: row.get(k) for k in INVENTORY_FIELDS}
        public_inventory.append(pub)
    public_inventory.sort(key=lambda r: (int(r["product_id"]), int(r["image_id"])))

    completed = _utc_now()
    non_deleted = [p for p in products if not p.deleted_at]
    active = [p for p in non_deleted if p.is_active]
    available = [p for p in non_deleted if p.is_available]
    selected_product_ids = {p.product_id for p in products}
    products_with_images = {
        int(r["product_id"])
        for r in inventory_rows
        if int(r["product_id"]) in selected_product_ids
    }
    products_without_primary = sum(
        1 for c in coverage_rows if c["total_image_rows"] > 0 and c["primary_image_rows"] == 0
    )
    products_with_multi_primary = sum(1 for c in coverage_rows if c["primary_image_rows"] > 1)

    summary = {
        "task_id": TASK_ID,
        "started_at_utc": started,
        "completed_at_utc": completed,
        "database_read_only": db.dialect == "postgresql" and db.transaction_read_only == "on",
        "database_name": db.database_name,
        "storage_root": str(storage_root),
        "storage_scan_completed": storage_scan,
        "storage_scan_skipped": not storage_scan,
        "total_products": len(products),
        "non_deleted_products": len(non_deleted),
        "active_products": len(active),
        "available_products": len(available),
        "total_product_images": len(inventory_rows),
        "products_with_image_rows": len(products_with_images),
        "products_without_image_rows": len(products) - len(products_with_images),
        "products_with_multiple_images": len(multi_image),
        "products_without_primary": products_without_primary,
        "products_with_multiple_primary": products_with_multi_primary,
        "internal_static_rows": sum(
            1 for r in public_inventory if str(r["url_kind"]).startswith("internal_static")
        ),
        "external_remote_rows": len(remote_rows),
        "invalid_url_rows": sum(1 for r in public_inventory if r["audit_status"] == "invalid_url"),
        "valid_local_image_rows": sum(1 for r in public_inventory if _is_valid_local_image(r)),
        "missing_local_file_rows": sum(
            1 for r in public_inventory if r["audit_status"] == "missing_local_file"
        ),
        "local_unverified_rows": sum(
            1 for r in public_inventory if r["audit_status"] == "local_unverified"
        ),
        "decode_failed_rows": sum(1 for r in public_inventory if r["audit_status"] == "decode_failed"),
        "unique_local_asset_sha256s": len(sha_to_paths),
        "exact_duplicate_sha_groups": exact_dup_groups,
        "cross_product_duplicate_sha_groups": cross_product_groups,
        "cross_brand_duplicate_sha_groups": cross_brand_groups,
        "storage_regular_files": sum(
            1
            for e in storage_entries
            if e.status in {"regular_image", "regular_non_image", "decode_failed"}
        ),
        "unreferenced_storage_files": len(unreferenced),
        "rejected_storage_entries": len(rejected_storage),
        "repository_modified_by_run": False,
        "database_modified": False,
        "storage_modified": False,
        "storage_mutations": 0,
        "network_requests_performed": 0,
        "prior_reference_snapshot": PRIOR_REFERENCE_SNAPSHOT,
        "current_delta": {
            "total_products": len(products) - int(PRIOR_REFERENCE_SNAPSHOT["total_products"]),
            "products_with_image_rows": len(products_with_images)
            - int(PRIOR_REFERENCE_SNAPSHOT["products_with_image_rows"]),
        },
    }

    run_metadata = {
        "task_id": TASK_ID,
        "started_at_utc": started,
        "completed_at_utc": completed,
        "dialect": db.dialect,
        "database_name": db.database_name,
        "database_user": db.database_user,
        "transaction_read_only": db.transaction_read_only,
        "storage_root": str(storage_root),
        "output_dir": str(output_dir),
        "include_deleted_products": include_deleted_products,
        "storage_scan": storage_scan,
        "storage_scan_skipped": not storage_scan,
        "repository_root": str(repository_root),
        "network_requests_performed": 0,
        "database_modified": False,
        "storage_modified": False,
        "storage_mutations": 0,
    }

    checksum_names = [
        "inventory.csv",
        "inventory.json",
        "product-coverage.csv",
        "product-coverage.json",
        "summary.json",
        "run-metadata.json",
        "broken-or-unavailable.csv",
        "remote-unverified.csv",
        "database-anomalies.csv",
        "duplicate-exact-sha.csv",
        "products-without-valid-image.csv",
        "products-with-multiple-images.csv",
        "unreferenced-storage-assets.csv",
        "rejected-storage-entries.csv",
    ]

    def _write_all(staging: Path) -> None:
        write_csv(staging / "inventory.csv", INVENTORY_FIELDS, public_inventory)
        write_json(staging / "inventory.json", public_inventory)
        write_csv(staging / "product-coverage.csv", COVERAGE_FIELDS, coverage_rows)
        write_json(staging / "product-coverage.json", coverage_rows)
        write_json(staging / "summary.json", summary)
        write_json(staging / "run-metadata.json", run_metadata)
        write_csv(
            staging / "broken-or-unavailable.csv",
            INVENTORY_FIELDS,
            [{k: r.get(k) for k in INVENTORY_FIELDS} for r in broken],
        )
        write_csv(
            staging / "remote-unverified.csv",
            INVENTORY_FIELDS,
            [{k: r.get(k) for k in INVENTORY_FIELDS} for r in remote_rows],
        )
        anom_fields = ["anomaly_type", "product_id", "image_id", "detail"]
        write_csv(staging / "database-anomalies.csv", anom_fields, anomaly_rows)
        dup_fields = [
            "exact_sha_group",
            "sha256",
            "physical_path_count",
            "physical_paths",
            "product_image_row_count",
            "image_ids",
            "product_ids",
            "brand_ids",
            "same_path_multi_reference",
            "duplicate_physical_files",
            "cross_product",
            "cross_brand",
            "review_status",
        ]
        write_csv(staging / "duplicate-exact-sha.csv", dup_fields, duplicate_rows)
        write_csv(staging / "products-without-valid-image.csv", COVERAGE_FIELDS, without_valid)
        write_csv(staging / "products-with-multiple-images.csv", COVERAGE_FIELDS, multi_image)
        unref_fields = [
            "relative_path",
            "byte_size",
            "sha256",
            "format",
            "mime_type",
            "width",
            "height",
            "decode_status",
            "reference_count",
            "review_status",
        ]
        write_csv(staging / "unreferenced-storage-assets.csv", unref_fields, unreferenced)
        rej_fields = ["relative_path", "status", "reason_codes", "review_status"]
        write_csv(staging / "rejected-storage-entries.csv", rej_fields, rejected_storage)

    publish_inventory_outputs(
        output_dir,
        writers=[_write_all],
        checksum_names=checksum_names,
    )
    return summary


def _coverage_status(
    *,
    deleted: bool,
    rows: list[dict[str, Any]],
    valid_local: int,
    remote: int,
) -> str:
    if deleted:
        return "deleted_product"
    if not rows:
        return "no_image_rows"
    primary_valid = any(r.get("is_primary") and _is_valid_local_image(r) for r in rows)
    primary_remote = any(r.get("is_primary") and _is_remote(r) for r in rows)
    if valid_local and remote:
        return "mixed_local_and_remote"
    if valid_local:
        return "valid_local_primary" if primary_valid else "valid_local_non_primary_only"
    if remote:
        return "remote_unverified_primary" if primary_remote else "remote_unverified_non_primary_only"
    return "image_rows_but_none_usable"


def _detect_anomalies(
    products: list[ProductRow],
    images: list[ImageRow],
    inventory_rows: list[dict[str, Any]],
    product_by_id: dict[int, ProductRow],
    *,
    all_product_ids: set[int],
    storage_root: Path,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    inventory_image_ids = {int(r["image_id"]) for r in inventory_rows}
    for img in images:
        if img.image_id not in inventory_image_ids:
            continue
        if img.product_id not in all_product_ids:
            out.append(
                {
                    "anomaly_type": "product_image_missing_product",
                    "product_id": img.product_id,
                    "image_id": img.image_id,
                    "detail": "ProductImage references missing Product",
                }
            )
        if img.display_order < 0:
            out.append(
                {
                    "anomaly_type": "negative_display_order",
                    "product_id": img.product_id,
                    "image_id": img.image_id,
                    "detail": f"display_order={img.display_order}",
                }
            )
        if not (img.image_url or "").strip():
            out.append(
                {
                    "anomaly_type": "empty_image_url",
                    "product_id": img.product_id,
                    "image_id": img.image_id,
                    "detail": "empty image_url",
                }
            )

    by_product: dict[int, list[ImageRow]] = defaultdict(list)
    for img in images:
        if img.image_id in inventory_image_ids:
            by_product[img.product_id].append(img)
    for pid, imgs in by_product.items():
        primaries = [i for i in imgs if i.is_primary]
        if len(primaries) > 1:
            out.append(
                {
                    "anomaly_type": "multiple_primary_images",
                    "product_id": pid,
                    "image_id": primaries[0].image_id,
                    "detail": f"primary_count={len(primaries)}",
                }
            )
        if imgs and not primaries:
            out.append(
                {
                    "anomaly_type": "images_with_no_primary",
                    "product_id": pid,
                    "image_id": imgs[0].image_id,
                    "detail": f"image_count={len(imgs)}",
                }
            )

    seen: dict[tuple[int, str], int] = {}
    for img in images:
        if img.image_id not in inventory_image_ids:
            continue
        key = (img.product_id, _dup_key_for_image(img, storage_root=storage_root))
        if key in seen:
            out.append(
                {
                    "anomaly_type": "duplicate_product_normalized_url",
                    "product_id": img.product_id,
                    "image_id": img.image_id,
                    "detail": f"duplicate_of_image_id={seen[key]}",
                }
            )
        else:
            seen[key] = img.image_id

    for row in inventory_rows:
        if row.get("url_kind") == "unsupported_scheme":
            out.append(
                {
                    "anomaly_type": "unsupported_url_scheme",
                    "product_id": row["product_id"],
                    "image_id": row["image_id"],
                    "detail": row.get("url_kind"),
                }
            )
        if row.get("audit_status") == "unsafe_or_unmapped_path" and str(
            row.get("url_kind", "")
        ).startswith("internal"):
            out.append(
                {
                    "anomaly_type": "local_static_outside_storage",
                    "product_id": row["product_id"],
                    "image_id": row["image_id"],
                    "detail": "|".join(row.get("reason_codes") or []),
                }
            )

    for p in products:
        if p.deleted_at and by_product.get(p.product_id):
            out.append(
                {
                    "anomaly_type": "deleted_product_retaining_images",
                    "product_id": p.product_id,
                    "image_id": by_product[p.product_id][0].image_id,
                    "detail": f"image_count={len(by_product[p.product_id])}",
                }
            )

    out.sort(key=lambda r: (str(r["anomaly_type"]), int(r["product_id"]), int(r["image_id"])))
    return out
