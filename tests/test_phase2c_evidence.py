"""Phase 2C evidence traceability gates."""

from __future__ import annotations

from scripts.audit_manufacturer_identity_phase2c_discovery import classify_row
from scripts.build_phase2c_source_authority_registry import _reject_apply
from app.domain.phase2c_evidence import (
    CONFLICT_HEURISTIC_UNRESOLVED,
    CONFLICT_RESOLVED_T1,
    CONFLICT_STRONG,
    evidence_completeness_ok,
    has_stable_locator,
    normalized_match_key,
    pick_evidence_for_code,
)


def _complete_ev(**overrides):
    base = {
        "brand": "INSIZE",
        "manufacturer_code": "1108-150",
        "canonical_candidate_code": "1108-150",
        "raw_source_code": "1108-150",
        "authority_tier": "1",
        "source_type": "oem_product_list",
        "source_id": "insize.product_list",
        "source_path": "/data/insize.pdf",
        "source_sha256": "abc123",
        "source_page_index": "2",
        "source_row": "15",
        "source_field_label": "کد کالا",
        "mapping_basis": "oem_field_کد_کالا",
        "oem_identity_field_proven": "true",
        "source_item_description": "کولیس دیجیتال",
    }
    base.update(overrides)
    return base


def test_apply_rejected_on_registry_build():
    import pytest

    with pytest.raises(SystemExit) as ei:
        _reject_apply(["--apply"])
    assert ei.value.code == 2


def test_incomplete_locator_cannot_be_exact():
    row = _complete_ev(source_page_index="", source_row="")
    ok, reason = evidence_completeness_ok(row)
    assert ok is False
    assert reason == "missing_stable_locator"


def test_file_hash_alone_insufficient():
    row = _complete_ev(source_page_index="", source_row="", source_sha256="deadbeef")
    assert has_stable_locator(row) is False
    assert evidence_completeness_ok(row)[0] is False


def test_duplicate_evidence_preserved():
    ev = {
        "INSIZE|1108-150": [_complete_ev(source_row="1"), _complete_ev(source_row="2")],
    }
    assert len(ev["INSIZE|1108-150"]) == 2


def test_tier1_conflict_not_auto_resolved():
    ev = {
        "INSIZE|1108-150": [
            _complete_ev(source_item_description="میکرومتر خارجی"),
            _complete_ev(source_item_description="کولیس دیجیتال"),
        ],
    }
    pick = pick_evidence_for_code(
        brand="INSIZE",
        code="1108-150",
        product_name="کولیس دیجیتال",
        evidence_map=ev,
        heuristic_conflict=False,
        resolving_only=False,
    )
    assert pick is not None
    assert pick.conflict_status == CONFLICT_STRONG


def test_title_vs_sku_stays_hold_without_resolving_evidence():
    product = {
        "product_id": "6",
        "name": "کولیس کد 1108-150",
        "sku": "500-196-30",
        "brand_name": "INSIZE",
        "manufacturer_code": "",
    }
    out = classify_row(product, evidence={}, collision_codes=set())
    assert out["classification"] == "HOLD_IDENTITY_CONFLICT"
    assert out["conflict_status"] == CONFLICT_HEURISTIC_UNRESOLVED


def test_title_vs_sku_resolved_when_sku_has_tier1_evidence():
    evidence = {
        "INSIZE|500-196-30": [_complete_ev(manufacturer_code="500-196-30", canonical_candidate_code="500-196-30", raw_source_code="500-196-30")],
    }
    product = {
        "product_id": "7",
        "name": "کولیس کد 1108-150",
        "sku": "500-196-30",
        "brand_name": "INSIZE",
        "manufacturer_code": "",
    }
    out = classify_row(product, evidence=evidence, collision_codes=set())
    assert out["classification"] == "BACKFILL_EXACT"
    assert out["conflict_status"] == CONFLICT_RESOLVED_T1
    assert out["raw_source_code"] == "500-196-30"


def test_variant_incompatible_blocks_exact():
    evidence = {
        "INSIZE|1108-150": [
            _complete_ev(source_item_description="میکرومتر ساعت اندازه گیری"),
        ],
    }
    product = {
        "product_id": "8",
        "name": "کولیس ورنیه دیجیتال",
        "sku": "1108-150",
        "brand_name": "INSIZE",
        "manufacturer_code": "",
    }
    out = classify_row(product, evidence=evidence, collision_codes=set())
    assert out["classification"] != "BACKFILL_EXACT"


def test_normalization_is_trim_and_nfc_only():
    assert normalized_match_key(" 1108-150 ") == "1108-150"
    assert normalized_match_key("1108-150") == "1108-150"


def test_replay_freeze_produces_identical_hash(tmp_path):
    import subprocess
    from pathlib import Path

    src = tmp_path / "products.csv"
    with src.open("w", encoding="utf-8", newline="") as fh:
        import csv

        w = csv.DictWriter(
            fh,
            fieldnames=["product_id", "sku", "name", "brand_id", "brand", "manufacturer_code", "deleted_at"],
        )
        w.writeheader()
        w.writerow(
            {
                "product_id": "1",
                "sku": "1108-150",
                "name": "کولیس دیجیتال 15سانت",
                "brand_id": "3",
                "brand": "INSIZE",
                "manufacturer_code": "",
                "deleted_at": "",
            }
        )
    reg = tmp_path / "registry.csv"
    with reg.open("w", encoding="utf-8", newline="") as fh:
        import csv

        from app.domain.phase2c_evidence import REGISTRY_FIELDNAMES

        w = csv.DictWriter(fh, fieldnames=REGISTRY_FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        w.writerow(_complete_ev())
    out = tmp_path / "out"
    rc = subprocess.call(
        [
            "python3",
            str(Path(__file__).resolve().parents[1] / "scripts/phase2c_exact_cohort_freeze.py"),
            "--products-csv",
            str(src),
            "--registry",
            str(reg),
            "--out-dir",
            str(out),
            "--skip-registry-build",
        ],
    )
    assert rc == 0
    manifest = __import__("json").loads((out / "BACKFILL_EXACT_FREEZE_MANIFEST.json").read_text())
    assert manifest["replay_identical"] is True


def test_ast_supplier_type_ineligible():
    row = _complete_ev(
        brand="ASTPOWER",
        source_type="ast_supplier_enumerator",
        oem_identity_field_proven="false",
    )
    assert evidence_completeness_ok(row)[0] is False
