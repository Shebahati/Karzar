"""Phase 2C discovery — classification rules (read-only; no Product writes)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from scripts.audit_manufacturer_identity_phase2c_discovery import (
    PRIMARY_STATES,
    _reject_apply,
    classify_row,
    filter_non_deleted,
    load_evidence_registry,
    main,
    reconcile,
)


def test_apply_flag_is_rejected():
    with pytest.raises(SystemExit) as ei:
        _reject_apply(["--products-csv", "x.csv", "--apply"])
    assert ei.value.code == 2


def test_sku_alone_never_yields_backfill_exact():
    row = {
        "product_id": "1",
        "name": "محصول بدون کد",
        "sku": "1108-150",
        "brand_name": "INSIZE | اینسایز",
        "manufacturer_code": "",
    }
    out = classify_row(row, evidence={}, collision_codes=set())
    assert out["classification"] == "HOLD_WEAK_EVIDENCE"
    assert out["classification"] != "BACKFILL_EXACT"


def test_title_alone_never_yields_backfill_exact():
    row = {
        "product_id": "2",
        "name": "کولیس دیجیتال کد 1108-150",
        "sku": "SKU-OTHER",
        "brand_name": "INSIZE",
        "manufacturer_code": "",
    }
    out = classify_row(row, evidence={}, collision_codes=set())
    assert out["classification"] in {
        "HOLD_WEAK_EVIDENCE",
        "HOLD_IDENTITY_CONFLICT",
        "MANUAL_REVIEW",
    }
    assert out["classification"] != "BACKFILL_EXACT"


def _complete_evidence(**overrides):
    base = {
        "brand": "INSIZE",
        "manufacturer_code": "1108-150",
        "canonical_candidate_code": "1108-150",
        "raw_source_code": "1108-150",
        "authority_tier": "1",
        "source_type": "oem_product_list",
        "source_id": "insize.product_list",
        "source_path": "/data/insize.pdf",
        "source_sha256": "abc",
        "source_page_index": "1",
        "source_row": "10",
        "source_field_label": "کد کالا",
        "mapping_basis": "oem_field",
        "oem_identity_field_proven": "true",
        "source_item_description": "کولیس",
    }
    base.update(overrides)
    return base


def test_tier1_3_evidence_can_yield_exact():
    evidence = {
        "INSIZE|1108-150": [_complete_evidence()],
    }
    row = {
        "product_id": "3",
        "name": "کولیس کد 1108-150",
        "sku": "1108-150",
        "brand_name": "INSIZE",
        "manufacturer_code": "",
    }
    out = classify_row(row, evidence=evidence, collision_codes=set())
    assert out["classification"] == "BACKFILL_EXACT"
    assert out["candidate_manufacturer_code"] == "1108-150"
    assert str(out["authority_tier"]) == "1"


def test_existing_canonical_without_provenance_is_review():
    row = {
        "product_id": "4",
        "name": "x",
        "sku": "ABC",
        "brand_name": "INSIZE",
        "manufacturer_code": "1108-150",
    }
    out = classify_row(row, evidence={}, collision_codes=set())
    assert out["classification"] == "REVIEW_EXISTING_CANONICAL"


def test_brandless_is_hold_brand_ambiguous():
    row = {
        "product_id": "5",
        "name": "x",
        "sku": "ABC",
        "brand_name": "",
        "manufacturer_code": "",
    }
    out = classify_row(row, evidence={}, collision_codes=set())
    assert out["classification"] == "HOLD_BRAND_AMBIGUOUS"


def test_collision_yields_duplicate_identity():
    evidence = {
        "ASTPOWER|TU-DR230": [
            {
                "authority_tier": "3",
                "source_type": "supplier",
                "source_path_or_url": "local",
            }
        ],
    }
    row = {
        "product_id": "3411",
        "name": "مدل TU-DR230",
        "sku": "TU-DR230",
        "brand_name": "ASTPOWER",
        "manufacturer_code": "",
    }
    out = classify_row(
        row, evidence=evidence, collision_codes={"ASTPOWER|TU-DR230"}
    )
    assert out["classification"] == "HOLD_DUPLICATE_IDENTITY"


def test_title_vs_sku_conflict():
    row = {
        "product_id": "6",
        "name": "کولیس کد 1108-150",
        "sku": "500-196-30",
        "brand_name": "INSIZE",
        "manufacturer_code": "",
    }
    out = classify_row(row, evidence={}, collision_codes=set())
    assert out["classification"] == "HOLD_IDENTITY_CONFLICT"
    from app.domain.phase2c_evidence import CONFLICT_HEURISTIC_UNRESOLVED

    assert out["conflict_status"] == CONFLICT_HEURISTIC_UNRESOLVED


def test_reconcile_exhaustive_and_exclusive():
    rows = [
        classify_row(
            {
                "product_id": str(i),
                "name": f"n{i}",
                "sku": f"S{i}",
                "brand_name": "INSIZE" if i % 2 else "",
                "manufacturer_code": "",
            },
            evidence={},
            collision_codes=set(),
        )
        for i in range(20)
    ]
    rec = reconcile(rows)
    assert rec["reconciles"] is True
    assert rec["non_deleted_total"] == 20
    assert rec["sum_primary_states"] == 20
    assert set(rec["by_state"]) == set(PRIMARY_STATES)


def test_filter_non_deleted():
    rows = [
        {"product_id": "1", "deleted_at": ""},
        {"product_id": "2", "deleted_at": None},
        {"product_id": "3"},
        {"product_id": "4", "deleted_at": "2026-01-01"},
    ]
    kept = filter_non_deleted(rows)
    assert [r["product_id"] for r in kept] == ["1", "2", "3"]


def test_evidence_registry_ignores_tier4(tmp_path: Path):
    p = tmp_path / "ev.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["brand", "manufacturer_code", "authority_tier", "source_type"],
        )
        w.writeheader()
        w.writerow(
            {
                "brand": "INSIZE",
                "manufacturer_code": "1108-150",
                "authority_tier": "4",
                "source_type": "marketplace",
            }
        )
        w.writerow(
            {
                "brand": "INSIZE",
                "manufacturer_code": "500-196-30",
                "authority_tier": "1",
                "source_type": "oem",
            }
        )
    reg = load_evidence_registry(p)
    assert "INSIZE|1108-150" not in reg
    assert "INSIZE|500-196-30" in reg
    assert len(reg["INSIZE|500-196-30"]) == 1


def test_live_authoritative_writes_live_suffix(tmp_path: Path):
    src = tmp_path / "master.csv"
    with src.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "product_id",
                "sku",
                "name",
                "brand_id",
                "brand",
                "manufacturer_code",
                "product_type_id",
                "product_type",
                "deleted_at",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "product_id": "10",
                "sku": "X",
                "name": "n",
                "brand_id": "3",
                "brand": "INSIZE",
                "manufacturer_code": "",
                "product_type_id": "",
                "product_type": "",
                "deleted_at": "",
            }
        )
    out = tmp_path / "out"
    rc = main(
        [
            "--products-csv",
            str(src),
            "--live-authoritative",
            "--out-dir",
            str(out),
        ]
    )
    assert rc == 0
    assert (out / "FULL_CATALOG_IDENTITY_CENSUS_LIVE.csv").exists()
    assert (out / "PHASE2C_AUTHORITATIVE_DISCOVERY.json").exists()


def test_main_status_master_roundtrip(tmp_path: Path):
    src = tmp_path / "master.csv"
    with src.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "product_id",
                "sku",
                "name",
                "brand_id",
                "brand",
                "manufacturer_code",
                "product_type_id",
                "product_type",
                "deleted_at",
            ],
        )
        w.writeheader()
        w.writerow(
            {
                "product_id": "10",
                "sku": "1108-150",
                "name": "کولیس کد 1108-150",
                "brand_id": "3",
                "brand": "INSIZE",
                "manufacturer_code": "",
                "product_type_id": "",
                "product_type": "",
                "deleted_at": "",
            }
        )
        w.writerow(
            {
                "product_id": "11",
                "sku": "X",
                "name": "gone",
                "brand_id": "3",
                "brand": "INSIZE",
                "manufacturer_code": "",
                "product_type_id": "",
                "product_type": "",
                "deleted_at": "2026-01-01",
            }
        )
    out = tmp_path / "out"
    rc = main(["--status-master", str(src), "--out-dir", str(out)])
    assert rc == 0
    summary = (out / "PHASE2C_DISCOVERY.json").read_text(encoding="utf-8")
    assert "STALE_STATUS_MASTER_PARTIAL" in summary
    assert '"non_deleted_total": 1' in summary
    census = list(csv.DictReader((out / "FULL_CATALOG_IDENTITY_CENSUS.csv").open(encoding="utf-8")))
    assert len(census) == 1
    assert census[0]["classification"] != "BACKFILL_EXACT"
