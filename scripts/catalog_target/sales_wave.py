"""INSIZE Sales Wave 1 allowlist (READ-ONLY plan). No APPLY writer."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from catalog_target.apply_contract import FutureApplyReadiness, StaleSnapshotGuard

if TYPE_CHECKING:
    from catalog_target.reconcile import ManifestRow, ReconciliationResult
else:
    ManifestRow = Any  # noqa: N816
    ReconciliationResult = Any  # noqa: N816

INSIZE_SALES_WAVE_1_PLAN_FIELDS = [
    "id",
    "sku",
    "normalized_sku",
    "current_brand",
    "current_base_price",
    "proposed_base_price",
    "base_price_change",
    "current_is_available",
    "proposed_is_available",
    "is_available_change",
    "current_is_active",
    "proposed_is_active",
    "is_active_change",
    "image_count",
    "primary_image_url",
    "media_ready",
    "commerce_ready",
    "public_sell_ready",
    "reconciliation_state",
    "source_product",
    "source_price",
    "source_inventory",
    "inventory_status",
    "inclusion_reasons",
    "target_provenance",
]

CREATE_REQUIRED_FIELDS = (
    "sku",
    "slug",
    "name",
    "category_id",
    "brand_id",
    "base_price",
    "is_active",
    "is_available",
)


def _bool_text(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _sha256_file(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_in_insize_sales_wave_1(row: ManifestRow) -> tuple[bool, list[str]]:
    """Deterministic allowlist gate. REVIEW/CREATE/DEACTIVATE never qualify."""
    reasons: list[str] = []
    if row.brand != "INSIZE":
        return False, ["not_insize"]
    if not row.target_member:
        return False, ["not_target_member"]
    if row.reconciliation_state == "REVIEW":
        return False, ["review_blocked"]
    if row.reconciliation_state == "CREATE":
        return False, ["create_excluded_from_sales_wave_1"]
    if row.reconciliation_state in {"DEACTIVATE", "NOOP_INACTIVE_NON_TARGET"}:
        return False, ["non_target_action"]
    if not row.current_id:
        return False, ["unmatched_current"]
    if row.current_deleted_at:
        return False, ["deleted_current"]
    if not row.exact_distributor_match:
        return False, ["no_exact_distributor_match"]
    if row.inventory_status != "موجود":
        return False, ["distributor_not_available"]
    if row.proposed_is_available is not True:
        return False, ["proposed_unavailable"]
    try:
        price = Decimal(row.proposed_base_price) if row.proposed_base_price else None
    except Exception:  # noqa: BLE001
        price = None
    if price is None or price <= 0:
        return False, ["non_positive_proposed_price"]
    if row.review_reason:
        return False, ["has_review_reason"]
    if not row.commerce_ready:
        return False, ["not_commerce_ready"]
    if not row.media_ready:
        return False, ["not_media_ready"]
    if not row.public_sell_ready:
        return False, ["not_public_sell_ready"]
    if row.reconciliation_state not in {"KEEP", "UPDATE"}:
        return False, [f"state_not_allowed:{row.reconciliation_state}"]
    # Deterministic transition present (KEEP still allowed when already correct).
    reasons.extend(
        [
            "brand_insize",
            "target_member",
            "matched_current",
            "not_deleted",
            "exact_distributor_match",
            "status_available",
            "positive_proposed_price",
            "no_review_reason",
            "media_ready",
            "commerce_ready",
            "public_sell_ready",
            f"state_{row.reconciliation_state}",
        ]
    )
    return True, reasons


def build_insize_sales_wave_1_rows(result: ReconciliationResult) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in result.rows:
        ok, reasons = row_in_insize_sales_wave_1(row)
        if not ok:
            continue
        out.append(
            {
                "id": row.current_id,
                "sku": row.sku,
                "normalized_sku": row.normalized_sku,
                "current_brand": row.current_brand,
                "current_base_price": row.current_base_price,
                "proposed_base_price": row.proposed_base_price,
                "base_price_change": row.base_price_change,
                "current_is_available": _bool_text(row.current_is_available),
                "proposed_is_available": _bool_text(row.proposed_is_available),
                "is_available_change": row.is_available_change,
                "current_is_active": _bool_text(row.current_is_active),
                "proposed_is_active": _bool_text(row.proposed_is_active),
                "is_active_change": row.is_active_change,
                "image_count": "" if row.current_image_count is None else str(row.current_image_count),
                "primary_image_url": row.current_primary_image_url,
                "media_ready": _bool_text(row.media_ready),
                "commerce_ready": _bool_text(row.commerce_ready),
                "public_sell_ready": _bool_text(row.public_sell_ready),
                "reconciliation_state": row.reconciliation_state,
                "source_product": row.source_product,
                "source_price": row.source_price,
                "source_inventory": row.source_inventory,
                "inventory_status": row.inventory_status,
                "inclusion_reasons": ";".join(reasons),
                "target_provenance": row.provenance,
            }
        )
    out.sort(key=lambda item: (item["sku"], item["id"]))
    return out


def assess_create_readiness(result: ReconciliationResult) -> dict[str, Any]:
    creates = [r for r in result.rows if r.target_member and r.reconciliation_state == "CREATE"]
    by_brand: dict[str, dict[str, Any]] = {}
    for row in creates:
        bucket = by_brand.setdefault(
            row.brand,
            {
                "count": 0,
                "media_ready": 0,
                "missing_required_fields": Counter(),
            },
        )
        bucket["count"] += 1
        if row.media_ready:
            bucket["media_ready"] += 1
        # CREATE never has a current row; required payload fields are not inventable here.
        for field_name in CREATE_REQUIRED_FIELDS:
            if field_name == "sku" and row.sku:
                continue
            if field_name == "base_price" and row.proposed_base_price:
                try:
                    if Decimal(row.proposed_base_price) > 0:
                        continue
                except Exception:  # noqa: BLE001
                    pass
            if field_name == "is_active" and row.proposed_is_active is True:
                continue
            if field_name == "is_available" and row.proposed_is_available is True:
                continue
            # slug/name/category_id/brand_id never supplied by Target membership alone.
            bucket["missing_required_fields"][field_name] += 1
    for brand, payload in by_brand.items():
        payload["missing_required_fields"] = dict(payload["missing_required_fields"])
    return {
        "CREATE_APPLY_READY": False,
        "total_create": len(creates),
        "media_ready_create": sum(1 for r in creates if r.media_ready),
        "by_brand": by_brand,
        "reason": "CREATE excluded from Sales Wave 1; required DB fields/media not safely supplied",
    }


def assess_deactivate_audit(result: ReconciliationResult) -> dict[str, Any]:
    deacts = [r for r in result.rows if r.reconciliation_state == "DEACTIVATE"]
    by_brand = Counter(r.brand or "UNKNOWN" for r in deacts)
    return {
        "DEACTIVATE_APPLY_READY": False,
        "total_deactivate": len(deacts),
        "by_brand": dict(sorted(by_brand.items(), key=lambda item: (-item[1], item[0]))),
        "reason": "DEACTIVATE is a separate catalog-cleanup wave; not required for INSIZE sales",
    }


def assess_review_breakdown(result: ReconciliationResult) -> dict[str, Any]:
    reviews = [r for r in result.rows if r.target_member and r.reconciliation_state == "REVIEW"]
    by_brand = Counter(r.brand for r in reviews)
    reasons: Counter[str] = Counter()
    for row in reviews:
        parts = [p for p in (row.review_reason or "").split(";") if p]
        if not parts:
            reasons["(none)"] += 1
        for part in parts:
            reasons[part] += 1
    return {
        "total_target_review": len(reviews),
        "by_brand": dict(sorted(by_brand.items())),
        "reasons": reasons.most_common(),
        "allowlist_policy": "REVIEW hard-blocked from every apply allowlist",
    }


@dataclass
class SalesWaveArtifacts:
    plan_rows: list[dict[str, str]] = field(default_factory=list)
    readiness: FutureApplyReadiness = field(default_factory=FutureApplyReadiness)
    create_audit: dict[str, Any] = field(default_factory=dict)
    deactivate_audit: dict[str, Any] = field(default_factory=dict)
    review_audit: dict[str, Any] = field(default_factory=dict)
    excluded_commerce_no_media: list[dict[str, str]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def build_sales_wave_artifacts(
    result: ReconciliationResult,
    *,
    snapshot_path: Path | None = None,
    snapshot_timestamp: str = "",
) -> SalesWaveArtifacts:
    plan_rows = build_insize_sales_wave_1_rows(result)
    create_audit = assess_create_readiness(result)
    deactivate_audit = assess_deactivate_audit(result)
    review_audit = assess_review_breakdown(result)

    insize = [r for r in result.rows if r.target_member and r.brand == "INSIZE"]
    commerce = [r for r in insize if r.commerce_ready]
    media = [r for r in insize if r.media_ready]
    public = [r for r in insize if r.public_sell_ready]
    excluded = [
        {
            "sku": r.sku,
            "current_id": r.current_id,
            "reconciliation_state": r.reconciliation_state,
            "commerce_ready": "true",
            "media_ready": "false",
            "reason": "commerce_ready_but_not_media_ready",
        }
        for r in insize
        if r.commerce_ready and not r.media_ready
    ]

    checksum = _sha256_file(snapshot_path)
    ready = bool(plan_rows) and result.current_site_snapshot_valid and result.current_site_reconciliation_ready
    readiness = FutureApplyReadiness(
        insize_sales_wave_1_ready=ready,
        create_apply_ready=False,
        deactivate_apply_ready=False,
        global_apply_ready=False,
        stale_snapshot_guard=StaleSnapshotGuard().as_dict(),
        reasons=[
            "plan_derived_from_reconciliation" if plan_rows else "empty_allowlist",
            "CREATE_APPLY_READY=false",
            "DEACTIVATE_APPLY_READY=false",
            "GLOBAL_APPLY_READY=false_until_authorized_writer",
            "writer_not_implemented",
        ],
    )

    active_changes = sum(1 for r in plan_rows if r["is_active_change"] == "true")
    price_changes = sum(1 for r in plan_rows if r["base_price_change"] == "true")
    avail_changes = sum(1 for r in plan_rows if r["is_available_change"] == "true")

    summary = {
        "wave": "INSIZE_SALES_WAVE_1",
        "insize_target": len(insize),
        "insize_commerce_ready": len(commerce),
        "insize_media_ready": len(media),
        "insize_public_sell_ready": len(public),
        "insize_sales_wave_1_count": len(plan_rows),
        "allowlist_active_changes": active_changes,
        "allowlist_price_changes": price_changes,
        "allowlist_availability_changes": avail_changes,
        "excluded_commerce_ready_no_media": len(excluded),
        "baseline_sha": result.baseline_sha,
        "generated_at": result.generated_at,
        "snapshot_timestamp": snapshot_timestamp,
        "snapshot_sha256": checksum,
        "snapshot_path_basename": snapshot_path.name if snapshot_path else "",
        "target_manifest_ready": result.target_manifest_ready,
        "current_site_snapshot_valid": result.current_site_snapshot_valid,
        "current_site_reconciliation_ready": result.current_site_reconciliation_ready,
    }
    return SalesWaveArtifacts(
        plan_rows=plan_rows,
        readiness=readiness,
        create_audit=create_audit,
        deactivate_audit=deactivate_audit,
        review_audit=review_audit,
        excluded_commerce_no_media=excluded,
        summary=summary,
    )


def write_sales_wave_outputs(artifacts: SalesWaveArtifacts, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_csv = output_dir / "insize_sales_wave_1_plan.csv"
    with plan_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INSIZE_SALES_WAVE_1_PLAN_FIELDS)
        writer.writeheader()
        for row in artifacts.plan_rows:
            writer.writerow(row)

    payload = {
        "production_db_mutation": "ZERO",
        "apply_writer_implemented": False,
        "summary": artifacts.summary,
        "readiness": artifacts.readiness.as_dict(),
        "create_audit": artifacts.create_audit,
        "deactivate_audit": artifacts.deactivate_audit,
        "review_audit": artifacts.review_audit,
        "excluded_commerce_ready_no_media": artifacts.excluded_commerce_no_media,
        "allowlist_count": len(artifacts.plan_rows),
        "allowlist_skus": [r["sku"] for r in artifacts.plan_rows],
    }
    (output_dir / "insize_sales_wave_1_plan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
