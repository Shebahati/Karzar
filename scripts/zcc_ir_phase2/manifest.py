"""Deterministic import manifest (plan operations only)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from zcc_ir_phase2 import PHASE2_VERSION
from zcc_ir_phase2.canonical_hash import canonical_import_plan_sha256
from zcc_ir_phase2.payloads import CreatePlanRow, UpdatePlanRow
from zcc_ir_phase2.readiness import ReadinessRow
from zcc_ir_phase2.reconcile import Phase2ReconcileRow

ALLOWED_OPERATIONS = frozenset({"NOOP", "CREATE_PLAN", "UPDATE_CONTENT_PLAN", "HOLD"})
FORBIDDEN_OPERATIONS = frozenset({"CREATE", "UPDATE", "DELETE", "DEACTIVATE", "APPLY"})


def _operation_for_row(rec: Phase2ReconcileRow) -> str:
    if rec.primary_state == "NOOP_EXISTING_EXACT":
        return "NOOP"
    if rec.primary_state == "CREATE_CANDIDATE":
        return "CREATE_PLAN"
    if rec.primary_state == "UPDATE_CONTENT_CANDIDATE":
        return "UPDATE_CONTENT_PLAN"
    return "HOLD"


def build_manifest_entries(
    reconcile: list[Phase2ReconcileRow],
    creates: list[CreatePlanRow],
    updates: list[UpdatePlanRow],
    readiness: list[ReadinessRow],
    products_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    create_by_url = {c.source_url: c for c in creates}
    ready_by_url = {r.source_url: r for r in readiness}
    update_by_product: dict[str, list[UpdatePlanRow]] = {}
    for row in updates:
        update_by_product.setdefault(row.product_id, []).append(row)
    entries: list[dict[str, Any]] = []
    for rec in reconcile:
        op = _operation_for_row(rec)
        create = create_by_url.get(rec.source_url)
        ready = ready_by_url.get(rec.source_url)
        entries.append(
            {
                "operation": op,
                "source_identity": {
                    "source_url": rec.source_url,
                    "brand": rec.brand_normalized,
                    "manufacturer_code": rec.manufacturer_code,
                    "source_internal_sku": rec.source_internal_sku,
                },
                "target_identity": {
                    "karzar_id": rec.karzar_id,
                    "karzar_sku": rec.karzar_sku,
                },
                "target_product_id": rec.karzar_id,
                "brand_id": None,
                "proposed_brand_reference": rec.brand_normalized,
                "category_id": (create.classification.get("category_id") if create else None),
                "planned_fields": create.as_dict() if create else {},
                "source_url": rec.source_url,
                "source_timestamp": products_meta.get(rec.source_url),
                "identity_confidence": "high" if rec.match_method else "low",
                "category_confidence": (
                    create.classification.get("classification_confidence") if create else "none"
                ),
                "content_ready": ready.content_readiness == "CONTENT_READY" if ready else False,
                "commerce_ready": False,
                "blocking_flags": rec.blocking_flags,
                "evidence": rec.evidence,
                "primary_state": rec.primary_state,
                "price_state": rec.price_state,
                "availability_state": rec.availability_state,
                "field_updates": [
                    u.as_dict() for u in update_by_product.get(rec.karzar_id or "", [])
                ],
            }
        )
    entries.sort(key=lambda e: e["source_url"])
    return entries


def manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_import_manifest(
    entries: list[dict[str, Any]],
    *,
    git_sha: str,
    karzar_provenance: str,
    karzar_timestamp: str,
    source_crawl_timestamp: str,
    phase1_baseline: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "phase2_version": PHASE2_VERSION,
        "git_sha": git_sha,
        "karzar_snapshot_provenance": karzar_provenance,
        "karzar_snapshot_timestamp": karzar_timestamp,
        "source_crawl_timestamp": source_crawl_timestamp,
        "phase1_baseline_reference": phase1_baseline,
        "entries": entries,
        "operation_counts": {},
    }
    counts: dict[str, int] = {}
    for entry in entries:
        op = entry["operation"]
        counts[op] = counts.get(op, 0) + 1
    body["operation_counts"] = counts
    body["CANONICAL_IMPORT_PLAN_SHA256"] = canonical_import_plan_sha256(body)
    # Legacy field: same as canonical identity (volatile metadata excluded).
    body["IMPORT_MANIFEST_SHA256"] = body["CANONICAL_IMPORT_PLAN_SHA256"]
    return body
