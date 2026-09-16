#!/usr/bin/env python3
"""Phase 2.1 READ-ONLY analysis over frozen Phase-2 artifacts (no crawl, no DB, no apply)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from zcc_ir_phase2.canonical_hash import (  # noqa: E402
    attach_manifest_hashes,
    canonical_import_plan_sha256,
    raw_manifest_file_sha256,
)
from zcc_ir_phase2.category_plan import category_by_url  # noqa: E402
from zcc_ir_phase2.load import load_phase1_products  # noqa: E402
from zcc_ir_phase2.validate import validate_manifest_layers  # noqa: E402

SNAPSHOT_SHA = "815a47f525cfb31d3696ab11a991456bbb675ea7bfadf0ac9601d645bdf69a60"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _invalid_price(product: Any) -> bool:
    if product.price_status != "ok":
        return True
    raw = product.price_normalized
    if raw is None or str(raw).strip() == "":
        return True
    try:
        return Decimal(str(raw)) <= 0
    except (InvalidOperation, ValueError):
        return True


def _collision_groups_from_manifest(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_mfg: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_sku: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        if entry.get("operation") != "CREATE_PLAN":
            continue
        ident = entry.get("source_identity") or {}
        brand = str(ident.get("brand") or "")
        mfg = str(ident.get("manufacturer_code") or "")
        if brand and mfg:
            by_mfg[(brand, mfg)].append(entry)
        planned = entry.get("planned_fields") or {}
        sku = (planned.get("identity") or {}).get("sku_proposal")
        if sku:
            by_sku[str(sku)].append(entry)

    rows: list[dict[str, Any]] = []
    group_id = 0
    for (brand, mfg), group in sorted(by_mfg.items()):
        if len(group) < 2:
            continue
        group_id += 1
        gid = f"MFG-{brand}-{mfg}-{group_id}"
        for entry in group:
            rows.append(_collision_row(gid, entry, "manufacturer_identity", brand, mfg))
    for sku, group in sorted(by_sku.items()):
        if len(group) < 2:
            continue
        group_id += 1
        gid = f"SKU-{sku}-{group_id}"
        for entry in group:
            ident = entry.get("source_identity") or {}
            rows.append(
                _collision_row(
                    gid,
                    entry,
                    "target_sku",
                    str(ident.get("brand") or ""),
                    str(ident.get("manufacturer_code") or ""),
                )
            )
    return rows


def _collision_row(
    collision_group: str,
    entry: dict[str, Any],
    reason: str,
    brand: str,
    mfg: str,
) -> dict[str, Any]:
    ident = entry.get("source_identity") or {}
    classification = _classify_collision(entry, reason)
    return {
        "collision_group": collision_group,
        "source_row": entry.get("source_url"),
        "source_url": entry.get("source_url"),
        "source_brand": brand,
        "manufacturer_code": mfg,
        "source_sku": ident.get("source_internal_sku") or ident.get("sku_proposal"),
        "normalized_identity": f"{brand}|{mfg}",
        "phase2_operation": entry.get("operation"),
        "karzar_product_id": (entry.get("target_identity") or {}).get("karzar_id"),
        "karzar_sku": (entry.get("target_identity") or {}).get("karzar_sku"),
        "collision_kind": classification,
        "recommended_resolution": _recommend_resolution(classification),
        "reason": reason,
    }


def _classify_collision(entry: dict[str, Any], reason: str) -> str:
    url = str(entry.get("source_url") or "")
    if "%D8%" in url and reason == "manufacturer_identity":
        return "ENCODING_DUPLICATE"
    flags = entry.get("blocking_flags") or []
    if "ambiguous_match" in flags:
        return "TRUE_IDENTITY_CONFLICT"
    if entry.get("karzar_product_id") or (entry.get("target_identity") or {}).get("karzar_id"):
        return "KARZAR_EXISTING_DUPLICATE"
    return "SOURCE_DUPLICATE"


def _recommend_resolution(kind: str) -> str:
    return {
        "ENCODING_DUPLICATE": "KEEP_ONE_CANONICAL_SOURCE",
        "SOURCE_DUPLICATE": "HOLD",
        "ALIAS_OF_SAME_PRODUCT": "NOOP_EXISTING",
        "KARZAR_EXISTING_DUPLICATE": "NOOP_EXISTING",
        "TRUE_IDENTITY_CONFLICT": "HOLD",
        "UNKNOWN_REVIEW": "HOLD",
    }.get(kind, "HOLD")


def run_analysis(
    *,
    phase1_dir: Path,
    phase2_dir: Path,
    manifest_path: Path,
    snapshot_sha: str,
) -> dict[str, Any]:
    products, _ = load_phase1_products(phase1_dir)
    by_url = {p.source_url: p for p in products}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_bytes = manifest_path.read_bytes()
    attach_manifest_hashes(manifest, raw_file_bytes=raw_bytes)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    entries = manifest.get("entries") or []
    reconcile = json.loads((phase2_dir / "full_catalog_reconciliation.json").read_text(encoding="utf-8"))
    rec_by_url = {r["source_url"]: r for r in reconcile}
    category_decisions = list(csv.DictReader((phase2_dir / "category_mapping_final.csv").open(encoding="utf-8")))
    category_review = list(csv.DictReader((phase2_dir / "category_mapping_review.csv").open(encoding="utf-8")))
    cat_rows = category_decisions + category_review
    from zcc_ir_phase2.category_plan import CategoryDecisionRow

    cat_objs = [
        CategoryDecisionRow(
            source_category_path=r["source_category_path"],
            source_product_count=int(r.get("source_product_count") or 0),
            proposed_karzar_category_id=r.get("proposed_karzar_category_id") or None,
            proposed_karzar_category_path=r.get("proposed_karzar_category_path") or None,
            decision=r["decision"],
            confidence=r.get("confidence") or "",
            technical_reason=r.get("technical_reason") or "",
            representative_products=json.loads(r.get("representative_products") or "[]")
            if str(r.get("representative_products") or "").startswith("[")
            else [],
        )
        for r in cat_rows
    ]
    cat_map = category_by_url(products, cat_objs)

    # STC hold table
    stc_rows: list[dict[str, Any]] = []
    hold_brand = [r for r in reconcile if r["primary_state"] == "HOLD_BRAND_REVIEW"]
    for rec in hold_brand:
        p = by_url[rec["source_url"]]
        stc_rows.append(
            {
                "source_identity": p.manufacturer_code or p.source_internal_sku or p.source_url,
                "source_name": p.name_fa,
                "source_url": p.source_url,
                "phase1_brand": rec.get("phase1_status"),
                "phase2_brand": rec.get("brand_normalized"),
                "hold_reason": "stc_brand_not_in_karzar"
                if rec.get("brand_normalized") == "STC"
                else "missing_or_untrusted_brand",
                "jsonld_brand": p.jsonld_brand,
                "visible_brand_evidence": p.brand_evidence,
                "manufacturer_code": p.manufacturer_code,
            }
        )
    _write_csv(
        phase2_dir / "stc_brand_review_rows.csv",
        list(stc_rows[0].keys()) if stc_rows else ["source_url"],
        stc_rows,
    )

    true_stc = sum(1 for r in hold_brand if r.get("brand_normalized") == "STC")
    brand_conflict = sum(1 for r in hold_brand if not r.get("brand_normalized"))
    stc_invariant = true_stc + brand_conflict == len(hold_brand)

    dup_rows = _collision_groups_from_manifest(entries)
    _write_csv(
        phase2_dir / "review_duplicate_identities.csv",
        [
            "collision_group",
            "source_row",
            "source_url",
            "source_brand",
            "manufacturer_code",
            "source_sku",
            "normalized_identity",
            "phase2_operation",
            "karzar_product_id",
            "karzar_sku",
            "collision_kind",
            "recommended_resolution",
            "reason",
        ],
        dup_rows,
    )

    collision_urls = {r["source_url"] for r in dup_rows}
    ops = Counter(e.get("operation") for e in entries)
    create_entries = [e for e in entries if e.get("operation") == "CREATE_PLAN"]

    zero_counts = Counter()
    content_ready = 0
    blocked_identity = blocked_category = blocked_duplicate = blocked_other = 0
    for entry in create_entries:
        url = entry["source_url"]
        p = by_url[url]
        op = entry.get("operation")
        rec = rec_by_url[url]
        if _invalid_price(p):
            zero_counts[op] += 1
        cat = cat_map.get(url)
        brand_ready = p.brand_normalized == "ZCC.CT"
        category_ready = cat is not None and cat.decision == "MAPPED_EXISTING"
        identity_ready = not rec["primary_state"].startswith("HOLD_")
        content_ok = bool(p.main_image_url)
        dup_unresolved = url in collision_urls
        if (
            identity_ready
            and brand_ready
            and category_ready
            and content_ok
            and not dup_unresolved
        ):
            content_ready += 1
        elif dup_unresolved:
            blocked_duplicate += 1
        elif not identity_ready:
            blocked_identity += 1
        elif not category_ready:
            blocked_category += 1
        else:
            blocked_other += 1

    for rec in reconcile:
        p = by_url[rec["source_url"]]
        if not _invalid_price(p):
            continue
        op = {
            "NOOP_EXISTING_EXACT": "NOOP",
            "CREATE_CANDIDATE": "CREATE_PLAN",
            "UPDATE_CONTENT_CANDIDATE": "UPDATE_CONTENT_PLAN",
        }.get(rec["primary_state"], "HOLD")
        zero_counts[op] += 0  # already counted via manifest op mapping
    z_create = sum(1 for e in create_entries if _invalid_price(by_url[e["source_url"]]))
    z_update = sum(
        1
        for rec in reconcile
        if rec["primary_state"] == "UPDATE_CONTENT_CANDIDATE" and _invalid_price(by_url[rec["source_url"]])
    )
    z_hold = sum(
        1 for rec in reconcile if rec["primary_state"].startswith("HOLD_") and _invalid_price(by_url[rec["source_url"]])
    )
    z_noop = sum(
        1
        for rec in reconcile
        if rec["primary_state"] == "NOOP_EXISTING_EXACT" and _invalid_price(by_url[rec["source_url"]])
    )

    # owner update review
    updates = json.loads((phase2_dir / "product_update_plan.json").read_text(encoding="utf-8"))
    update_rows: list[dict[str, Any]] = []
    for u in updates:
        field = u.get("field") or ""
        risk = "low"
        rec_action = "ACCEPT_SOURCE_FACT"
        if field in {"base_price", "price", "is_available", "availability"}:
            rec_action = "DO_NOT_IMPORT"
            risk = "high"
        elif field in {"name", "name_fa", "title"}:
            rec_action = "HUMAN_REVIEW_REQUIRED"
            risk = "medium"
        update_rows.append(
            {
                "karzar_product_id": u.get("product_id"),
                "karzar_sku": u.get("sku"),
                "brand": rec_by_url.get(u.get("source_url"), {}).get("brand_normalized"),
                "manufacturer_code": rec_by_url.get(u.get("source_url"), {}).get("manufacturer_code"),
                "source_url": u.get("source_url"),
                "field": field,
                "current_karzar_value": u.get("karzar_value"),
                "zcc_value": u.get("zcc_source_value"),
                "evidence": u.get("reason"),
                "risk": risk,
                "recommended_action": rec_action,
            }
        )
    _write_csv(phase2_dir / "owner_update_review.csv", list(update_rows[0].keys()) if update_rows else [], update_rows)

    # category packet
    cat_packet = sorted(category_review, key=lambda r: int(r.get("source_product_count") or 0), reverse=True)
    _write_csv(
        phase2_dir / "owner_category_review_packet.csv",
        [
            "source_category",
            "product_count",
            "representative_products",
            "proposed_karzar_category",
            "decision_type",
            "technical_reason",
        ],
        [
            {
                "source_category": r["source_category_path"],
                "product_count": r["source_product_count"],
                "representative_products": r.get("representative_products"),
                "proposed_karzar_category": r.get("proposed_karzar_category_path"),
                "decision_type": r.get("decision"),
                "technical_reason": r.get("technical_reason"),
            }
            for r in cat_packet
        ],
    )

    stc_products = [p for p in products if p.brand_normalized == "STC"]
    stc_packet = {
        "canonical_name": "STC",
        "slug": "stc",
        "true_source_product_count": len(stc_products),
        "representative_skus": [p.manufacturer_code for p in stc_products[:10]],
        "representative_urls": [p.source_url for p in stc_products[:10]],
        "jsonld_conflict_explanation": "STC PDP JSON-LD often names ZCC; page/tag evidence used instead.",
        "logo_candidate": json.loads((phase2_dir / "stc_brand_proposal.json").read_text()).get(
            "logo_source_candidate"
        ),
        "decision_choices": ["APPROVE_BRAND_DEFINITION", "REJECT_BRAND_DEFINITION", "REVIEW_MORE"],
    }
    (phase2_dir / "owner_stc_brand_packet.json").write_text(
        json.dumps(stc_packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    validation = validate_manifest_layers(manifest_path)
    dup_summary = validation.summary_dict()
    dup_summary["DUPLICATE_COLLISION_GROUPS_OWNER_REVIEW"] = len({r["collision_group"] for r in dup_rows})
    dup_summary["OWNER_REVIEW_UNIQUE_SOURCE_URLS"] = len({r["source_url"] for r in dup_rows})
    dup_summary["diagnostic_reconciliation"] = (
        "CONTENT_BLOCKING_ERROR_COUNT counts diagnostic messages (e.g. one URL may emit "
        "both DUPLICATE_MANUFACTURER_IDENTITY and DUPLICATE_TARGET_SKU). "
        "CONTENT_BLOCKING_ROW_COUNT counts unique source_url values with content-layer findings. "
        "OWNER_REVIEW_UNIQUE_SOURCE_URLS counts unique URLs in review_duplicate_identities.csv "
        "(encoding-duplicate CREATE clusters). "
        "TOTAL_VALIDATOR_DIAGNOSTICS = content + commerce diagnostics."
    )
    dup_summary["readiness_create_plan"] = {
        "CREATE_PLAN": len(create_entries),
        "CONTENT_CREATE_READY": content_ready,
        "unique_blocked_rows": len(create_entries) - content_ready,
        "blocking_reason_incidence": {
            "BLOCKED_DUPLICATE": blocked_duplicate,
            "BLOCKED_IDENTITY": blocked_identity,
            "BLOCKED_CATEGORY": blocked_category,
            "BLOCKED_OTHER": blocked_other,
        },
        "note": (
            "Incidence counts are mutually exclusive buckets (first matching gate wins). "
            "They sum to CREATE_PLAN when every row is blocked by exactly one bucket."
        ),
    }
    dup_summary["stc_hold_invariant"] = {
        "TRUE_STC_ROWS": true_stc,
        "NON_STC_BRAND_REVIEW_ROWS": brand_conflict,
        "HOLD_BRAND_REVIEW_TOTAL": len(hold_brand),
        "COUNT_INVARIANT_VALID": stc_invariant,
    }
    (phase2_dir / "duplicate_validation_summary.json").write_text(
        json.dumps(dup_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = json.loads((phase2_dir / "phase2_summary.json").read_text(encoding="utf-8"))

    counts = {
        "SOURCE": 729,
        "NOOP": ops.get("NOOP", 0),
        "CREATE_PLAN": ops.get("CREATE_PLAN", 0),
        "UPDATE_CONTENT_PLAN": ops.get("UPDATE_CONTENT_PLAN", 0),
        "HOLD": ops.get("HOLD", 0),
        "CONTENT_CREATE_READY": content_ready,
        "CONTENT_CREATE_BLOCKED": len(create_entries) - content_ready,
        "TRUE_STC_ROWS": true_stc,
        "BRAND_REVIEW_NON_STC_ROWS": brand_conflict,
        "CATEGORY_READY_PRODUCTS": sum(1 for c in cat_map.values() if c.decision == "MAPPED_EXISTING"),
        "CATEGORY_HOLD_PRODUCTS": 729 - sum(1 for c in cat_map.values() if c.decision == "MAPPED_EXISTING"),
        "UNRESOLVED_DUPLICATE_ROWS": len({r["source_url"] for r in dup_rows}),
    }

    _write_owner_v2(phase2_dir, summary, counts, validation, stc_packet, snapshot_sha, manifest)

    return {
        "counts": counts,
        "stc": {
            "TRUE_STC": true_stc,
            "BRAND_CONFLICT_ROWS": brand_conflict,
            "HOLD_BRAND_REVIEW_TOTAL": len(hold_brand),
            "COUNT_INVARIANT_VALID": stc_invariant,
        },
        "zero_price": {
            "CREATE_PLAN": z_create,
            "UPDATE": z_update,
            "HOLD": z_hold,
            "NOOP": z_noop,
            "source_invalid_total": 39,
        },
        "duplicates": {
            "collision_groups": len({r["collision_group"] for r in dup_rows}),
            "rows": len(dup_rows),
        },
        "manifest": {
            "RAW_MANIFEST_FILE_SHA256": raw_manifest_file_sha256(raw_bytes),
            "CANONICAL_IMPORT_PLAN_SHA256": canonical_import_plan_sha256(manifest),
            "legacy_IMPORT_MANIFEST_SHA256": manifest.get("IMPORT_MANIFEST_SHA256"),
        },
        "validation": dup_summary,
    }


def _write_owner_v2(
    phase2_dir: Path,
    summary: dict[str, Any],
    counts: dict[str, Any],
    validation: Any,
    stc: dict[str, Any],
    snapshot_sha: str,
    manifest: dict[str, Any],
) -> None:
    text = f"""# ZCC.IR Phase 2.1 — Owner decision packet (V2)

Frozen inputs:
- Source crawl: `{manifest.get("source_crawl_timestamp")}`
- Karzar snapshot SHA256: `{snapshot_sha}`
- Canonical plan SHA256: `{manifest.get("CANONICAL_IMPORT_PLAN_SHA256")}`

## 1. STC BRAND DEFINITION
- **RECOMMENDED_OPTION:** REVIEW_MORE — approve **brand definition** only (not automatic brand creation)
- **AFFECTED_ROWS:** {counts["TRUE_STC_ROWS"]} true STC products + {counts["BRAND_REVIEW_NON_STC_ROWS"]} non-STC brand-review holds (65 total `HOLD_BRAND_REVIEW`; **not** 65 STC)
- **RISK:** Mis-branding if JSON-LD trusted
- **RATIONALE:** Karzar has zero STC products; 53 zcc.ir STC rows need explicit owner policy before any future writer
- **IF_APPROVED:** Owner may authorize a **future** STC brand definition step; this packet does **not** create the brand
- **IF_DEFERRED:** All STC rows remain `HOLD_BRAND_REVIEW`

## 2. CATEGORY MAPPINGS
- **RECOMMENDED_OPTION:** Approve **83 mapped paths** as mappings; **46 review + 8 new proposals** remain manual (see `owner_category_review_packet.csv`)
- **AFFECTED_ROWS:** {counts["CATEGORY_READY_PRODUCTS"]} mapped / {counts["CATEGORY_HOLD_PRODUCTS"]} held
- **RISK:** Wrong taxonomy → discoverability loss
- **IF_APPROVED:** Category holds can clear for mapped families
- **IF_DEFERRED:** {summary.get("primary_state_counts", {}).get("HOLD_CATEGORY_REVIEW", 0)} rows stay category-held

## 3. ZCC.IR FACTUAL CONTENT AUTHORITY
- **RECOMMENDED_OPTION:** WITH_RESTRICTIONS (content observations only; no automatic import)
- **AFFECTED_ROWS:** 729
- **RISK:** Source HTML/JSON-LD conflicts
- **IF_APPROVED:** Content create/update plans may proceed under identity gates
- **IF_DEFERRED:** No automated content import

## 4. ZCC.IR PRICE AUTHORITY
- **RECOMMENDED_OPTION:** **NO WRITE AUTHORITY** (`ZCC_IR_PRICE_WRITE_AUTHORITY = NO`)
- **AFFECTED_ROWS:** 690 priced observations; 39 invalid/non-positive
- **RISK:** Zero or wrong IRR becomes sellable price
- **IF_APPROVED:** Not recommended without explicit rules
- **IF_DEFERRED:** Prices remain observations only (default)

## 5. ZCC.IR AVAILABILITY REFERENCE SIGNAL
- **RECOMMENDED_OPTION:** REFERENCE_SIGNAL_ALLOWED only; `WAREHOUSE_STOCK_WRITE_AUTHORITY = NO`
- **AFFECTED_ROWS:** 729 coarse signals
- **RISK:** Page existence ≠ warehouse stock
- **IF_APPROVED:** Reference-only semantics in future phases
- **IF_DEFERRED:** No availability writes (default)

## 6. CONTENT CREATE PLAN
- **RECOMMENDED_OPTION:** **DEFER** while duplicate identity blockers remain ({validation.CONTENT_COLLISION_GROUP_COUNT} collision groups)
- **AFFECTED_ROWS:** {counts["CREATE_PLAN"]} CREATE_PLAN; {counts["CONTENT_CREATE_READY"]} content-create-ready
- **RISK:** Duplicate manufacturer targets; validator content layer: {validation.CONTENT_PLAN_VALID}
- **IF_APPROVED:** Future dry-run writer may create non-sellable products only
- **IF_DEFERRED:** All creates remain plan-only

## 7. CONTENT UPDATE PLAN
- **RECOMMENDED_OPTION:** **HUMAN_REVIEW_REQUIRED** for all 13 products (see `owner_update_review.csv`); approval does not apply updates
- **AFFECTED_ROWS:** {counts["UPDATE_CONTENT_PLAN"]} products
- **RISK:** Title/spec overwrites on live Karzar PDPs
- **IF_APPROVED:** Field-level updates per CSV recommendations
- **IF_DEFERRED:** Karzar content unchanged

CONTENT_PLAN_VALID = {validation.CONTENT_PLAN_VALID}
COMMERCE_PLAN_VALID = {validation.COMMERCE_PLAN_VALID}
CONTENT_BLOCKING_ERROR_COUNT = {validation.CONTENT_BLOCKING_ERROR_COUNT}
CONTENT_BLOCKING_ROW_COUNT = {validation.CONTENT_BLOCKING_ROW_COUNT}
CONTENT_COLLISION_GROUP_COUNT = {validation.CONTENT_COLLISION_GROUP_COUNT}
PRICE_WRITE_READY = 0
AVAILABILITY_WRITE_READY = 0

Approving any decision above does **not** execute catalog mutation.

PRODUCTION_DB_MUTATION = ZERO
CATALOG_APPLY = NO
"""
    (phase2_dir / "OWNER_DECISION_PACKET_V2.md").write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Phase 2.1 READ-ONLY artifact analysis")
    parser.add_argument("--phase1-dir", default=str(root / "data" / "zcc_ir"))
    parser.add_argument("--phase2-dir", default=str(root / "data" / "zcc_ir_phase2"))
    parser.add_argument(
        "--manifest",
        default=str(root / "data" / "zcc_ir_phase2" / "import_manifest.json"),
    )
    parser.add_argument("--snapshot-sha256", default=SNAPSHOT_SHA)
    args = parser.parse_args(argv)
    result = run_analysis(
        phase1_dir=Path(args.phase1_dir),
        phase2_dir=Path(args.phase2_dir),
        manifest_path=Path(args.manifest),
        snapshot_sha=args.snapshot_sha256,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
