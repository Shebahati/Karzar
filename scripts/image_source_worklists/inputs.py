"""Load authoritative inventory and validated human-review bundles (external only)."""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any

from .contracts import (
    AUTHORITATIVE_CHECKSUMS_DIGEST,
    BUNDLE_SPECS,
    CUMULATIVE_REVIEW,
    EXPECTED_INVENTORY_FACTS,
    WorklistError,
    normalize_brand,
    sha256_file,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _verify_checksums_file(directory: Path) -> int:
    path = directory / "checksums.sha256"
    if not path.is_file() or path.is_symlink():
        raise WorklistError("review", f"missing checksums.sha256 in {directory}")
    items = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise WorklistError("review", f"malformed checksum line: {line!r}")
        expected, name = parts[0], parts[1].lstrip("*").strip()
        if "/" in name or ".." in name or name.startswith("."):
            raise WorklistError("review", f"unsafe checksum member: {name!r}")
        member = directory / name
        if member.is_symlink() or not member.is_file():
            raise WorklistError("review", f"checksum member missing/symlink: {name}")
        actual = sha256_file(member)
        if actual != expected:
            raise WorklistError(
                "review", f"checksum mismatch for {name}: {actual} != {expected}"
            )
        items += 1
    if items == 0:
        raise WorklistError("review", "checksums.sha256 has no entries")
    return items


def extract_review_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Safely extract a human-review ZIP into dest_dir (flat files)."""
    if not zip_path.is_file() or zip_path.is_symlink():
        raise WorklistError("review", f"review ZIP missing: {zip_path}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    for child in list(dest_dir.iterdir()):
        if child.is_file() and not child.is_symlink():
            child.unlink()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            raise WorklistError("review", f"duplicate ZIP members: {zip_path.name}")
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts:
                raise WorklistError("review", f"unsafe ZIP path: {name}")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise WorklistError("review", f"ZIP symlink forbidden: {name}")
            if info.is_dir():
                continue
            target = dest_dir / Path(name).name
            target.write_bytes(zf.read(info.filename))
    return dest_dir


def load_inventory(
    source_dir: Path,
    *,
    expected_checksums_digest: str = AUTHORITATIVE_CHECKSUMS_DIGEST,
) -> dict[str, Any]:
    """Load product-coverage.csv after verifying inventory checksums.sha256."""
    if not source_dir.is_absolute():
        raise WorklistError("inventory", f"source-dir must be absolute: {source_dir}")
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise WorklistError("inventory", f"invalid source-dir: {source_dir}")

    checksums_path = source_dir / "checksums.sha256"
    digest = sha256_file(checksums_path)
    if digest != expected_checksums_digest:
        raise WorklistError(
            "inventory",
            f"checksums.sha256 digest mismatch: {digest} != {expected_checksums_digest}",
        )
    _verify_checksums_file(source_dir)

    coverage_path = source_dir / "product-coverage.csv"
    if not coverage_path.is_file():
        raise WorklistError("inventory", "product-coverage.csv missing")
    products = _read_csv(coverage_path)
    required = {
        "product_id",
        "sku",
        "name",
        "brand",
        "category",
        "deleted",
        "is_active",
        "is_available",
        "has_any_image_row",
        "total_image_rows",
    }
    if not products or not required.issubset(products[0].keys()):
        raise WorklistError("inventory", "product-coverage.csv schema incomplete")

    summary = json.loads((source_dir / "summary.json").read_text(encoding="utf-8"))
    measured = {
        "non_deleted_products": int(summary["non_deleted_products"]),
        "products_with_image_rows": int(summary["products_with_image_rows"]),
        "products_without_image_rows": int(summary["products_without_image_rows"]),
        "valid_local_image_rows": int(summary["valid_local_image_rows"]),
        "unique_local_assets": int(summary["unique_local_asset_sha256s"]),
    }
    for key, expected in EXPECTED_INVENTORY_FACTS.items():
        if measured[key] != expected:
            raise WorklistError(
                "inventory",
                f"inventory fact mismatch {key}: got {measured[key]} expected {expected}",
            )

    non_deleted = [p for p in products if p.get("deleted", "").lower() == "false"]
    if len(non_deleted) != EXPECTED_INVENTORY_FACTS["non_deleted_products"]:
        raise WorklistError(
            "inventory",
            f"non-deleted product-coverage rows {len(non_deleted)}",
        )

    by_id = {p["product_id"]: p for p in non_deleted}
    if len(by_id) != len(non_deleted):
        raise WorklistError("inventory", "duplicate product_id in product-coverage")

    brand_sku: dict[tuple[str, str], str] = {}
    for p in non_deleted:
        key = normalize_brand(p.get("brand"))
        if key is None:
            continue
        sku = (p.get("sku") or "").strip()
        if not sku:
            continue
        map_key = (key, sku)
        if map_key in brand_sku and brand_sku[map_key] != p["product_id"]:
            raise WorklistError(
                "inventory",
                f"duplicate brand+SKU mapping: {key}/{sku}",
            )
        brand_sku[map_key] = p["product_id"]

    return {
        "source_dir": str(source_dir),
        "checksums_digest": digest,
        "products": non_deleted,
        "products_by_id": by_id,
        "brand_sku_index": brand_sku,
        "facts": measured,
        "summary": summary,
    }


def _validate_bundle_dir(directory: Path, spec: dict[str, Any]) -> dict[str, Any]:
    _verify_checksums_file(directory)
    assets = _read_csv(directory / "asset-review.csv")
    assignments = _read_csv(directory / "assignment-review.csv")
    state = json.loads((directory / "review-state.json").read_text(encoding="utf-8"))

    if state.get("batch_id") != spec["batch_id"]:
        raise WorklistError(
            "review",
            f"batch_id mismatch: {state.get('batch_id')} != {spec['batch_id']}",
        )
    if int(state.get("review_schema_version", -1)) != 1:
        raise WorklistError("review", "review schema version must be 1")

    if len(assets) != spec["assets"] or len(assignments) != spec["assignments"]:
        raise WorklistError(
            "review",
            f"{spec['batch_id']} count mismatch assets={len(assets)} asgs={len(assignments)}",
        )

    state_blob = json.dumps(state, ensure_ascii=False)
    if "UNREVIEWED" in state_blob or "unreviewed" in state_blob:
        raise WorklistError("review", f"{spec['batch_id']} contains UNREVIEWED")
    for row in assets + assignments:
        for value in row.values():
            if value in ("UNREVIEWED", "unreviewed"):
                raise WorklistError("review", f"{spec['batch_id']} CSV contains UNREVIEWED")
        if row.get("batch_id") and str(row.get("batch_id")) != spec["batch_id"]:
            raise WorklistError("review", f"{spec['batch_id']} CSV batch_id drift")

    if any(r.get("rights_status") != "review_required" for r in assets):
        raise WorklistError("review", f"{spec['batch_id']} rights_status not review_required")

    rr = sum(1 for r in assignments if r.get("assignment_decision") == "REPLACE_REQUIRED")
    mr = sum(1 for r in assignments if r.get("assignment_decision") == "MANUAL_REVIEW")
    if rr != spec["replace_required"] or mr != spec["manual_review"]:
        raise WorklistError(
            "review",
            f"{spec['batch_id']} decision aggregates rr={rr} mr={mr}",
        )

    replace_rows = _read_csv(directory / "replacement-required-assignments.csv")
    if len(replace_rows) != spec["replace_required"]:
        raise WorklistError(
            "review",
            f"{spec['batch_id']} replacement-required CSV count {len(replace_rows)}",
        )

    watermark_path = directory / "watermark-replacement-queue.csv"
    watermark_rows = _read_csv(watermark_path) if watermark_path.is_file() else []

    manual_path = directory / "manual-review-assignments.csv"
    if manual_path.is_file():
        manual_rows = _read_csv(manual_path)
    else:
        manual_rows = [
            r for r in assignments if r.get("assignment_decision") == "MANUAL_REVIEW"
        ]
    if len(manual_rows) != spec["manual_review"]:
        raise WorklistError(
            "review",
            f"{spec['batch_id']} manual-review count {len(manual_rows)}",
        )

    return {
        "spec": spec,
        "directory": str(directory),
        "assets": assets,
        "assignments": assignments,
        "state": state,
        "replace_rows": replace_rows,
        "watermark_rows": watermark_rows,
        "manual_rows": manual_rows,
        "aggregates": {
            "assets": len(assets),
            "assignments": len(assignments),
            "replace_required": rr,
            "manual_review": mr,
            "watermark_queue_rows": len(watermark_rows),
        },
    }


def load_review_bundles(
    review_root: Path,
    *,
    extract_root: Path,
) -> dict[str, Any]:
    """Locate, hash, extract and validate all three completed human-review ZIPs."""
    if not review_root.is_absolute() or not review_root.is_dir():
        raise WorklistError("review", f"invalid review root: {review_root}")

    bundles: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for spec in BUNDLE_SPECS:
        zip_path = review_root / spec["zip_name"]
        matches = sorted(p for p in review_root.glob(spec["zip_name"]) if p.is_file())
        if len(matches) != 1 or not zip_path.is_file():
            raise WorklistError(
                "review",
                f"required human-review ZIP absent or ambiguous: {spec['zip_name']}",
            )
        outer = sha256_file(zip_path)
        if outer != spec["expected_outer_sha256"]:
            raise WorklistError(
                "review",
                f"outer SHA mismatch for {zip_path.name}: {outer}",
            )
        dest = extract_root / spec["label"]
        extract_review_zip(zip_path, dest)
        validated = _validate_bundle_dir(dest, spec)
        validated["outer_sha256"] = outer
        validated["zip_path"] = str(zip_path)
        bundles.append(validated)
        evidence.append(
            {
                "batch_id": spec["batch_id"],
                "zip_name": spec["zip_name"],
                "zip_path": str(zip_path),
                "outer_sha256": outer,
                "extract_dir": str(dest),
                "aggregates": validated["aggregates"],
            }
        )

    total_assets = sum(b["aggregates"]["assets"] for b in bundles)
    total_asgs = sum(b["aggregates"]["assignments"] for b in bundles)
    total_rr = sum(b["aggregates"]["replace_required"] for b in bundles)
    total_mr = sum(b["aggregates"]["manual_review"] for b in bundles)
    if (
        total_assets != CUMULATIVE_REVIEW["assets_reviewed"]
        or total_asgs != CUMULATIVE_REVIEW["assignments_reviewed"]
        or total_rr != CUMULATIVE_REVIEW["replace_required_assignments"]
        or total_mr != CUMULATIVE_REVIEW["manual_review_assignments"]
    ):
        raise WorklistError(
            "review",
            "cumulative review aggregates mismatch "
            f"assets={total_assets} asgs={total_asgs} rr={total_rr} mr={total_mr}",
        )

    return {
        "bundles": bundles,
        "evidence": evidence,
        "cumulative": {
            "assets_reviewed": total_assets,
            "assignments_reviewed": total_asgs,
            "replace_required_assignments": total_rr,
            "manual_review_assignments": total_mr,
        },
    }
