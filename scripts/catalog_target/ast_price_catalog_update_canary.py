"""Immutable UPDATE canary stage manifests (disjoint product-ID allowlists)."""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from catalog_target.ast_price_catalog_manifest_acceptance import manifest_file_sha256

UpdateStage = Literal["stage1", "stage2", "stage3", "full"]

STAGE1_COUNT = 5
STAGE2_COUNT = 50
STAGE2_INCLUDES_STAGE1 = False

STAGE_FILES = {
    "stage1": "UPDATE_CANARY_STAGE1_5.csv",
    "stage2": "UPDATE_CANARY_STAGE2_50.csv",
    "stage3": "UPDATE_CANARY_STAGE3_REMAINDER.csv",
    "full": "UPDATE_PRODUCTS.csv",
}


def product_id_allowlist_sha256(product_ids: list[int]) -> str:
    body = ",".join(str(i) for i in sorted(set(product_ids)))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _risk_key(row: dict[str, Any]) -> tuple[Decimal, Decimal, str]:
    pct_raw = (row.get("percent_diff") or "0").strip()
    abs_raw = (row.get("absolute_diff") or "0").strip()
    try:
        pct = abs(Decimal(pct_raw))
    except Exception:
        pct = Decimal("999")
    try:
        absd = abs(Decimal(abs_raw))
    except Exception:
        absd = Decimal("999999999")
    return (pct, absd, str(row.get("sku") or ""))


def select_canary_partitions(update_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Low-risk, brand-diverse selection — not largest absolute_diff."""
    if len(update_rows) < STAGE1_COUNT + STAGE2_COUNT:
        raise ValueError("UPDATE manifest too small for canary partition")

    ranked = sorted(update_rows, key=_risk_key)
    stage1: list[dict[str, Any]] = []
    seen_brands: set[str] = set()
    for row in ranked:
        brand = str(row.get("brand") or row.get("brand_id") or "")
        if brand in seen_brands and len(stage1) < STAGE1_COUNT:
            continue
        stage1.append(row)
        seen_brands.add(brand)
        if len(stage1) >= STAGE1_COUNT:
            break
    if len(stage1) < STAGE1_COUNT:
        stage1 = ranked[:STAGE1_COUNT]

    used_ids = {int(r["product_id"]) for r in stage1}
    remaining = [r for r in ranked if int(r["product_id"]) not in used_ids]

    stage2: list[dict[str, Any]] = []
    for row in remaining:
        pid = int(row["product_id"])
        if pid in used_ids:
            continue
        stage2.append(row)
        used_ids.add(pid)
        if len(stage2) >= STAGE2_COUNT:
            break

    stage3 = [r for r in update_rows if int(r["product_id"]) not in used_ids]
    if len(stage1) + len(stage2) + len(stage3) != len(update_rows):
        raise ValueError("canary_partition_integrity_failed")
    overlap = (set(int(r["product_id"]) for r in stage1) & set(int(r["product_id"]) for r in stage2)) | (
        set(int(r["product_id"]) for r in stage1) & set(int(r["product_id"]) for r in stage3)
    ) | (set(int(r["product_id"]) for r in stage2) & set(int(r["product_id"]) for r in stage3))
    if overlap:
        raise ValueError(f"canary_partition_overlap:{sorted(overlap)}")

    return {"stage1": stage1, "stage2": stage2, "stage3": stage3, "full": list(update_rows)}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_update_canary_artifacts(
    *,
    audit_dir: Path,
    update_rows: list[dict[str, Any]],
    master_manifest_sha256: str,
) -> dict[str, Any]:
    partitions = select_canary_partitions(update_rows)
    work_dir = audit_dir / "work"
    sanitized_dir = audit_dir / "sanitized"
    work_dir.mkdir(parents=True, exist_ok=True)
    sanitized_dir.mkdir(parents=True, exist_ok=True)

    registry: dict[str, Any] = {
        "master_update_manifest_sha256": master_manifest_sha256,
        "stage2_includes_stage1": STAGE2_INCLUDES_STAGE1,
        "total_update_rows": len(update_rows),
        "stages": {},
    }
    for stage in ("stage1", "stage2", "stage3"):
        rows = partitions[stage]
        rel = STAGE_FILES[stage]
        path = work_dir / rel
        _write_csv(path, rows)
        pids = [int(r["product_id"]) for r in rows]
        registry["stages"][stage] = {
            "manifest_relpath": f"work/{rel}",
            "manifest_sha256": manifest_file_sha256(path),
            "row_count": len(rows),
            "product_id_allowlist_sha256": product_id_allowlist_sha256(pids),
            "product_ids": pids,
            "includes_prior_stage_rows": False,
        }

    registry["stages"]["full"] = {
        "manifest_relpath": "UPDATE_PRODUCTS.csv",
        "manifest_sha256": master_manifest_sha256,
        "row_count": len(update_rows),
        "product_id_allowlist_sha256": product_id_allowlist_sha256(
            [int(r["product_id"]) for r in update_rows]
        ),
        "includes_prior_stage_rows": True,
    }
    out = sanitized_dir / "UPDATE_CANARY_MANIFESTS.json"
    out.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return registry


def resolve_stage_update_path(audit_dir: Path, stage: UpdateStage) -> Path:
    if stage == "full":
        return audit_dir / "UPDATE_PRODUCTS.csv"
    return audit_dir / "work" / STAGE_FILES[stage]


def load_canary_registry(audit_dir: Path) -> dict[str, Any]:
    path = audit_dir / "sanitized" / "UPDATE_CANARY_MANIFESTS.json"
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))
