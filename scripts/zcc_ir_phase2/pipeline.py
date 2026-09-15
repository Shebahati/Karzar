"""Orchestrate READ-ONLY Phase-2 import planning."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zcc_ir_phase2 import PHASE2_VERSION
from zcc_ir_phase2.category_plan import build_category_plan, category_by_url
from zcc_ir_phase2.commerce import analyze_availability, analyze_prices
from zcc_ir_phase2.images import build_image_manifest
from zcc_ir_phase2.load import (
    load_karzar_catalog,
    load_phase1_products,
    load_phase1_reconcile,
    load_phase1_summary,
)
from zcc_ir_phase2.manifest import build_import_manifest, build_manifest_entries
from zcc_ir_phase2.payloads import build_create_plans, build_update_plans
from zcc_ir_phase2.readiness import build_readiness
from zcc_ir_phase2.reconcile import reconcile_phase2
from zcc_ir_phase2.review import resolve_review_records
from zcc_ir_phase2.snapshot_stats import brand_catalog_stats
from zcc_ir_phase2.stc_brand import build_stc_brand_proposal


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL)
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            for key, value in list(flat.items()):
                if isinstance(value, list | dict):
                    flat[key] = json.dumps(value, ensure_ascii=False)
            writer.writerow({k: flat.get(k, "") for k in fieldnames})


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


PHASE1_BASELINE_REFERENCE = {
    "source_products": 729,
    "unique_manufacturer_identities": 708,
    "brands": {"ZCC.CT": 611, "STC": 53, "SAN OU": 53, "brand_conflict_review": 12},
    "price_present": 690,
    "zero_invalid_price": 39,
    "image_present": 729,
    "reconciliation": {
        "EXISTING_EXACT": 173,
        "EXISTING_DIFFERENT_CONTENT": 23,
        "EXISTING_DIFFERENT_PRICE": 0,
        "EXISTING_DIFFERENT_AVAILABILITY": 1,
        "CREATE_CANDIDATE": 517,
        "REVIEW": 15,
        "AMBIGUOUS": 0,
        "INVALID_SOURCE_RECORD": 0,
        "KARZAR_ONLY": 40,
    },
    "category_mapping": {"SAFE_RULE": 83, "REVIEW": 46, "UNMAPPED": 8},
}


def run_phase2_plan(
    *,
    phase1_dir: Path,
    output_dir: Path,
    karzar_snapshot: str | None = None,
    read_db: bool = False,
    karzar_categories: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    products, phase1_meta = load_phase1_products(phase1_dir)
    phase1_reconcile = load_phase1_reconcile(phase1_dir)
    phase1_summary = load_phase1_summary(phase1_dir)
    karzar, karzar_kind, karzar_note = load_karzar_catalog(snapshot_path=karzar_snapshot, read_db=read_db)
    if not karzar:
        raise RuntimeError(f"Karzar full catalog unavailable: {karzar_note}")

    categories = karzar_categories
    if categories is None:
        snap = (phase1_summary.get("karzar_snapshot") or {}) if phase1_summary else {}
        categories = list(snap.get("categories") or [])

    brand_keys = {"ZCC.CT", "SAN OU", "STC"}
    brand_stats = brand_catalog_stats(karzar, brand_keys)
    stc_exists = any(p.brand_key == "STC" for p in karzar)

    category_decisions, category_hold_urls = build_category_plan(products, categories)
    cat_by_url = category_by_url(products, category_decisions)
    phase1_by_url = {r.source_url: r.status for r in phase1_reconcile}
    reconcile = reconcile_phase2(
        products,
        karzar,
        category_hold_urls=category_hold_urls,
        phase1_by_url=phase1_by_url,
    )
    review = resolve_review_records(products, phase1_reconcile, karzar)
    stc_proposal = build_stc_brand_proposal(products)
    karzar_by_id = {p.id: p for p in karzar if p.id}
    creates = build_create_plans(products, reconcile, cat_by_url)
    updates = build_update_plans(products, reconcile, karzar_by_id)
    price_rows, price_proposal = analyze_prices(products)
    avail_rows, avail_proposal = analyze_availability(products)
    images = build_image_manifest(products, reconcile)
    readiness = build_readiness(products, reconcile, cat_by_url)
    crawl_ts = phase1_summary.get("generated_at") or ""
    product_ts = {p.source_url: p.crawl_timestamp for p in products}
    entries = build_manifest_entries(reconcile, creates, updates, readiness, product_ts)
    manifest = build_import_manifest(
        entries,
        git_sha=_git_sha(),
        karzar_provenance=f"{karzar_kind}:{karzar_note}",
        karzar_timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_crawl_timestamp=str(crawl_ts),
        phase1_baseline=PHASE1_BASELINE_REFERENCE,
    )

    rec_fields = list(reconcile[0].as_dict().keys()) if reconcile else []
    _write_csv(output_dir / "full_catalog_reconciliation.csv", rec_fields, [r.as_dict() for r in reconcile])
    _write_json(output_dir / "full_catalog_reconciliation.json", [r.as_dict() for r in reconcile])
    _write_csv(
        output_dir / "review_decisions.csv",
        ["source_url", "outcome", "confidence", "recommended_decision", "reason", "evidence"],
        [r.as_dict() for r in review],
    )
    _write_json(output_dir / "review_evidence.json", [r.as_dict() for r in review])
    _write_json(output_dir / "stc_brand_proposal.json", stc_proposal)
    _write_csv(
        output_dir / "category_mapping_final.csv",
        [
            "source_category_path",
            "source_product_count",
            "proposed_karzar_category_id",
            "proposed_karzar_category_path",
            "decision",
            "confidence",
            "technical_reason",
            "representative_products",
        ],
        [d.as_dict() for d in category_decisions if d.decision == "MAPPED_EXISTING"],
    )
    _write_csv(
        output_dir / "category_mapping_review.csv",
        [
            "source_category_path",
            "source_product_count",
            "proposed_karzar_category_id",
            "proposed_karzar_category_path",
            "decision",
            "confidence",
            "technical_reason",
            "representative_products",
        ],
        [d.as_dict() for d in category_decisions if d.decision != "MAPPED_EXISTING"],
    )
    _write_csv(
        output_dir / "product_create_plan.csv",
        ["source_url", "identity", "classification", "factual_content", "images", "commerce_observations"],
        [c.as_dict() for c in creates],
    )
    _write_json(output_dir / "product_create_plan.json", [c.as_dict() for c in creates])
    _write_csv(
        output_dir / "product_update_plan.csv",
        [
            "product_id",
            "sku",
            "field",
            "karzar_value",
            "zcc_source_value",
            "source_url",
            "source_timestamp",
            "recommended_action",
            "reason",
        ],
        [u.as_dict() for u in updates],
    )
    _write_json(output_dir / "product_update_plan.json", [u.as_dict() for u in updates])
    _write_csv(
        output_dir / "commerce_price_analysis.csv",
        ["source_url", "observed_price", "price_status", "observed_availability", "currency", "flags"],
        [r.as_dict() for r in price_rows],
    )
    _write_csv(
        output_dir / "commerce_availability_analysis.csv",
        ["source_url", "observed_price", "price_status", "observed_availability", "currency", "flags"],
        [r.as_dict() for r in avail_rows],
    )
    _write_json(output_dir / "ZCC_IR_PRICE_AUTHORITY_PROPOSAL.json", price_proposal)
    _write_json(output_dir / "ZCC_IR_AVAILABILITY_AUTHORITY_PROPOSAL.json", avail_proposal)
    _write_csv(
        output_dir / "image_manifest.csv",
        [
            "source_product_identity",
            "source_url",
            "main_image_url",
            "gallery_urls",
            "image_count",
            "placeholder_flags",
            "broken_url_flags",
        ],
        [i.as_dict() for i in images],
    )
    holds = [r.as_dict() for r in reconcile if r.primary_state.startswith("HOLD_")]
    _write_csv(output_dir / "holds.csv", rec_fields, holds)
    _write_json(output_dir / "import_manifest.json", manifest)

    from collections import Counter

    primary_counts = Counter(r.primary_state for r in reconcile)
    readiness_counts = Counter(r.identity_readiness for r in readiness)
    content_counts = Counter(r.content_readiness for r in readiness)
    commerce_counts = Counter(r.commerce_readiness for r in readiness)
    import_ready = sum(1 for r in readiness if r.import_content_ready)
    review_counts = Counter(r.outcome for r in review)
    cat_counts = Counter(d.decision for d in category_decisions)

    summary = {
        "phase2_version": PHASE2_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": manifest["git_sha"],
        "phase1_dir": str(phase1_dir),
        "phase1_meta": phase1_meta,
        "phase1_baseline_reference": PHASE1_BASELINE_REFERENCE,
        "current_snapshot": {
            "source_product_count": len(products),
            "karzar_product_count": len(karzar),
            "karzar_provenance": manifest["karzar_snapshot_provenance"],
        },
        "brand_stats": brand_stats,
        "stc_brand_exists_on_karzar": stc_exists,
        "primary_state_counts": dict(primary_counts),
        "review_resolution_counts": dict(review_counts),
        "category_decision_counts": dict(cat_counts),
        "readiness": {
            "identity_ready": readiness_counts.get("IDENTITY_READY", 0),
            "identity_hold": readiness_counts.get("IDENTITY_HOLD", 0),
            "content_ready": content_counts.get("CONTENT_READY", 0),
            "content_hold": content_counts.get("CONTENT_HOLD", 0),
            "commerce_not_authorized": commerce_counts.get("COMMERCE_NOT_AUTHORIZED", 0),
            "commerce_invalid": commerce_counts.get("COMMERCE_INVALID", 0),
            "import_content_ready": import_ready,
        },
        "manifest_sha256": manifest["IMPORT_MANIFEST_SHA256"],
        "operation_counts": manifest["operation_counts"],
        "production_db_mutation": False,
        "catalog_apply": False,
    }
    _write_json(output_dir / "phase2_summary.json", summary)
    _write_owner_packet(output_dir, summary, stc_proposal, price_proposal, avail_proposal)
    return summary


def _write_owner_packet(
    output_dir: Path,
    summary: dict[str, Any],
    stc: dict[str, Any],
    price: dict[str, Any],
    avail: dict[str, Any],
) -> None:
    text = f"""# ZCC.IR Phase 2 — Owner decision packet

Generated: {summary.get("generated_at")}
Manifest SHA256: {summary.get("manifest_sha256")}

## DECISION 1 — STC BRAND
Create proposed STC brand later? **YES / NO / REVIEW**
Proposal status: {stc.get("decision_status")}
Canonical name: {stc.get("canonical_name")}
Product count on zcc.ir: {stc.get("product_count")}

## DECISION 2 — CATEGORY MAPPINGS
Approve safe mappings? Approve specific manual mappings?
Mapped existing: {summary.get("category_decision_counts", {}).get("MAPPED_EXISTING")}
Human review: {summary.get("category_decision_counts", {}).get("HUMAN_REVIEW_REQUIRED")}
New category proposals: {summary.get("category_decision_counts", {}).get("NEW_CATEGORY_PROPOSAL")}

## DECISION 3 — ZCC.IR AS CONTENT SOURCE
Approve zcc.ir as factual product-content authority? **YES / NO / WITH_RESTRICTIONS**

## DECISION 4 — ZCC.IR PRICE AUTHORITY
**YES / NO / WITH_RULES**
Recommendation: {price.get("recommendation_status")}

## DECISION 5 — ZCC.IR AVAILABILITY AUTHORITY
**YES / NO / WITH_RULES**
Recommendation: {avail.get("recommendation_status")}

## DECISION 6 — PRODUCT CREATION
Approve reviewed CREATE manifest for a future dry-run writer? **YES / NO**
CREATE_PLAN count: {summary.get("operation_counts", {}).get("CREATE_PLAN", 0)}

## DECISION 7 — EXISTING PRODUCT CONTENT UPDATES
Approve field-level content update manifest? **YES / NO**
UPDATE_CONTENT_PLAN count: {summary.get("operation_counts", {}).get("UPDATE_CONTENT_PLAN", 0)}

PRODUCTION_DB_MUTATION = ZERO
CATALOG_APPLY = NO
"""
    (output_dir / "OWNER_DECISION_PACKET.md").write_text(text, encoding="utf-8")
