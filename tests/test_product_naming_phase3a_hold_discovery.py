"""Phase 3A HOLD resolution discovery — invariants (no live DB required)."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest
from app.domain.product_naming_phase3a import (
    EXPECTED_REASON_COUNTS,
    HOLD_CANARY_MULTI_FUNCTION,
    HOLD_CANARY_OWNER_TITLE,
    OEM_REGISTRY_REL,
    PHASE2D_AUDIT_REL,
    PHASE2D_CANDIDATES_REL,
    PHASE2D_EXPECTED_APPLIED_ROWS,
    PHASE2D_EXPECTED_HOLD_ROWS,
    PHASE2D_HOLDS_REL,
    PHASE2D_HOLDS_SHA256,
    PHASE2D_OEM_REL,
    assert_matrix_invariants,
    assert_no_applied_intersection,
    build_root_cause_matrix,
    load_candidates,
    load_holds,
    normalize_brand_bucket,
    reconcile_reason_counts,
    reject_mutation_flags,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]


def _matrix():
    holds = load_holds(ROOT / PHASE2D_HOLDS_REL)
    candidates = load_candidates(ROOT / PHASE2D_CANDIDATES_REL)
    assert_no_applied_intersection(holds, candidates)
    audit = {
        r["product_id"]: r
        for r in csv.DictReader((ROOT / PHASE2D_AUDIT_REL).open(encoding="utf-8"))
    }
    oem = {
        r["product_id"]: r
        for r in csv.DictReader((ROOT / PHASE2D_OEM_REL).open(encoding="utf-8"))
    }
    registry: dict[str, dict[str, str]] = {}
    for r in csv.DictReader((ROOT / OEM_REGISTRY_REL).open(encoding="utf-8")):
        code = (r.get("manufacturer_code") or "").strip()
        if code and code not in registry:
            registry[code] = r
    return build_root_cause_matrix(
        holds=holds,
        audit_by_id=audit,
        oem_by_id=oem,
        registry_by_code=registry,
        live_by_id=None,
    )


def test_holds_exact_1303_and_sha():
    path = ROOT / PHASE2D_HOLDS_REL
    assert sha256_file(path) == PHASE2D_HOLDS_SHA256
    holds = load_holds(path)
    assert len(holds) == PHASE2D_EXPECTED_HOLD_ROWS


def test_applied_47_excluded():
    holds = load_holds(ROOT / PHASE2D_HOLDS_REL)
    cands = load_candidates(ROOT / PHASE2D_CANDIDATES_REL)
    assert len(cands) == PHASE2D_EXPECTED_APPLIED_ROWS
    assert_no_applied_intersection(holds, cands)


def test_hold_ids_unique():
    holds = load_holds(ROOT / PHASE2D_HOLDS_REL)
    ids = [r["product_id"] for r in holds]
    assert len(ids) == len(set(ids))


def test_reason_counts_reconcile():
    holds = load_holds(ROOT / PHASE2D_HOLDS_REL)
    counts, errors = reconcile_reason_counts(holds)
    assert errors == []
    assert counts == EXPECTED_REASON_COUNTS


def test_brand_reconciliation_finds_empty_brand_row():
    holds = load_holds(ROOT / PHASE2D_HOLDS_REL)
    empty = [r for r in holds if not (r.get("brand") or "").strip()]
    assert len(empty) == 1
    assert empty[0]["product_id"] == "1789"
    assert empty[0]["manufacturer_code"] == "1114-150"
    assert empty[0]["_hold_reason"] == "HOLD_PRODUCT_TYPE_NAMING_POLICY"
    bucket = normalize_brand_bucket(
        "",
        current_name=empty[0]["current_name"],
        brand_name="",
    )
    assert bucket == "INSIZE_INFERRED"


def test_matrix_primary_blocker_lane_wave_and_projected():
    rows = _matrix()
    assert assert_matrix_invariants(rows) == []
    assert len(rows) == PHASE2D_EXPECTED_HOLD_ROWS
    assert all(r.primary_blocker for r in rows)
    assert all(r.resolution_lane for r in rows)
    assert sum(1 for _ in rows) == PHASE2D_EXPECTED_HOLD_ROWS
    projected = Counter(r.projected_unlock_state for r in rows)
    assert sum(projected.values()) == PHASE2D_EXPECTED_HOLD_ROWS
    waves = Counter(r.wave for r in rows)
    assert sum(waves.values()) == PHASE2D_EXPECTED_HOLD_ROWS
    # exclusive membership: each product one wave
    assert len({r.product_id for r in rows}) == PHASE2D_EXPECTED_HOLD_ROWS


def test_canaries():
    rows = _matrix()
    owner = [r for r in rows if r.manufacturer_code == HOLD_CANARY_OWNER_TITLE]
    multi = [r for r in rows if r.manufacturer_code == HOLD_CANARY_MULTI_FUNCTION]
    assert len(owner) == 1
    assert owner[0].historical_hold_reason == "HOLD_OWNER_CANONICAL_TITLE_REVIEW"
    assert owner[0].resolution_lane == "G_OWNER_TITLE"
    assert len(multi) == 1
    assert multi[0].historical_hold_reason == "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT"
    assert multi[0].resolution_lane == "H_MULTI_FUNCTION"


def test_dasqua_terma_not_insize_oem_authority():
    rows = _matrix()
    bad = [
        r
        for r in rows
        if r.historical_hold_reason == "HOLD_MISSING_PRODUCT_TYPE"
        and r.brand_bucket.startswith(("DASQUA", "TERMA"))
        and r.resolution_sublane in {"A1_EXACT_OEM_PRODUCT_FAMILY", "A2_EXACT_MANUFACTURER_LISTING"}
    ]
    assert bad == []


def test_mutation_flags_rejected():
    with pytest.raises(SystemExit) as ei:
        reject_mutation_flags(["--apply"])
    assert ei.value.code == 2


def test_no_sku_shape_only_pt_assignment_in_phase3a_tooling():
    # Discovery must not emit future_mutation that claims PT from SKU alone without source lane.
    rows = _matrix()
    for r in rows:
        if r.future_mutation_type == "PRODUCT_TYPE_ASSIGNMENT":
            assert r.historical_hold_reason == "HOLD_MISSING_PRODUCT_TYPE"
            # A6 explicitly marks no authoritative source — still future PT work, but not auto-assigned.
            assert r.resolution_sublane.startswith("A")
