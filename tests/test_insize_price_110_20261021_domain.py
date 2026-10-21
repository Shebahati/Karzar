"""Unit tests for INSIZE +10% price APPLY domain helpers."""

from decimal import Decimal
from pathlib import Path

from app.domain.insize_price_110_20261021 import (
    CHANGE_REASON,
    EXPECTED_POST_APPLY_BASE_SUM,
    EXPECTED_PRICED_COHORT_ROWS,
    FROZEN_MANIFEST_SHA256,
    build_manifest_row,
    build_rollback_sql,
    classify_api_sample_result,
    cohort_id_set_diff,
    discount_impact_row,
    evaluate_api_verification,
    evaluate_db_post_apply_verification,
    evaluate_frozen_handoff_readiness,
    handoff_must_not_reference_legacy_rollback,
    proposed_base_price,
    resolve_post_commit_status,
    validate_frozen_manifest_authority,
    validate_production_identity_gates,
)

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "audit" / "insize-price-110-20261021" / "HUMAN_APPLY_HANDOFF.md"


def test_proposed_base_price_round_half_up():
    assert proposed_base_price(Decimal("1000.00")) == Decimal("1100.00")
    assert proposed_base_price(Decimal("1000.01")) == Decimal("1100.01")
    assert proposed_base_price(Decimal("1000.05")) == Decimal("1100.06")


def test_change_reason_exact():
    assert CHANGE_REASON == "INSIZE +10% owner-authorized price update 2026-10-21"


def test_discount_impact_when_new_meets_compare_at():
    impact = discount_impact_row(
        old_base=Decimal("900.00"),
        new_base=Decimal("990.00"),
        original_price=Decimal("990.00"),
    )
    assert impact is not None
    assert impact["before"] == "discounted"
    assert impact["after"] == "no_discount_equal"


def test_discount_impact_unchanged_when_still_discounted():
    assert (
        discount_impact_row(
            old_base=Decimal("900.00"),
            new_base=Decimal("990.00"),
            original_price=Decimal("1000.00"),
        )
        is None
    )


def test_discount_impact_boundary_above_compare_at():
    impact = discount_impact_row(
        old_base=Decimal("1000.00"),
        new_base=Decimal("1100.00"),
        original_price=Decimal("1000.00"),
    )
    assert impact is not None
    assert impact["after"] == "above_compare_at"


def test_build_manifest_row():
    row = build_manifest_row(
        {
            "id": 1,
            "sku": "X",
            "name": "n",
            "slug": "s",
            "brand_id": 3,
            "brand_name": "INSIZE | اینسایز",
            "old_base_price": "100.00",
            "original_price": None,
            "is_active": True,
            "is_available": False,
            "deleted_at": None,
        }
    )
    assert row["proposed_base_price"] == "110.00"
    assert row["discount_impact"] is None


def test_cohort_id_set_diff():
    diff = cohort_id_set_diff({1, 2, 3}, {2, 3, 4})
    assert diff["extra_in_live"] == [4]
    assert diff["missing_from_live"] == [1]


def test_validate_production_identity_gates_rejects_bad_host():
    proof = {
        "host_proof": "wrong-host",
        "database_proof": "karzar_staging",
        "pg_system_identifier": "7664189378775347234",
        "gates": {
            "host_ok": False,
            "container_ok": True,
            "db_ok": True,
            "user_ok": True,
            "volume_ok": True,
            "pg_system_identifier_ok": True,
            "alembic_ok": True,
            "transaction_read_only_on": True,
        },
    }
    assert validate_production_identity_gates(proof)


def test_validate_frozen_manifest_authority_rejects_wrong_sha():
    manifest = [{"product_id": i} for i in range(1, EXPECTED_PRICED_COHORT_ROWS + 1)]
    bad = validate_frozen_manifest_authority(manifest, csv_sha256="deadbeef")
    assert bad["ok"] is False
    assert "frozen_manifest_sha256_mismatch" in bad["errors"]


def test_validate_frozen_manifest_authority_requires_unique_206():
    manifest = [{"product_id": 1}] * EXPECTED_PRICED_COHORT_ROWS
    bad = validate_frozen_manifest_authority(manifest, csv_sha256=FROZEN_MANIFEST_SHA256)
    assert bad["ok"] is False
    assert "unique_product_ids_not_206" in bad["errors"]


def test_evaluate_frozen_handoff_readiness_blocks_idempotency():
    ready = evaluate_frozen_handoff_readiness(
        manifest_authority={"ok": True, "errors": []},
        cohort_membership={"ok": True},
        drift_report={"ok": True},
        idempotency={"already_present": True},
        priced_census=EXPECTED_PRICED_COHORT_ROWS,
    )
    assert ready["ok"] is False
    assert "idempotency_logs_present" in ready["blockers"]


def test_handoff_doc_does_not_reference_executable_legacy_rollback():
    if not HANDOFF.is_file():
        return
    text = HANDOFF.read_text(encoding="utf-8")
    assert handoff_must_not_reference_legacy_rollback(text)


def test_build_real_apply_sql_enforces_full_cohort_gate():
    import pytest
    from app.domain.insize_price_110_20261021 import build_real_apply_sql

    rows = [
        {
            "product_id": 1,
            "sku": "A",
            "old_base_price": "100.00",
            "proposed_base_price": "110.00",
            "authorized_original_price_exception": False,
        }
    ]
    with pytest.raises(ValueError, match="commercial contract"):
        build_real_apply_sql(rows, expected_rows=1, manifest_sha256="abc")


def test_db_post_apply_requires_formula_and_sum():
    verify = {
        "target_rows": 2,
        "price_exact_match": 2,
        "formula_matches": 1,
        "change_log_rows_with_reason": 2,
        "distinct_changed_product_ids": 2,
        "duplicate_mutations": 0,
        "sum_base_price_post": str(EXPECTED_POST_APPLY_BASE_SUM),
    }
    result = evaluate_db_post_apply_verification(
        verify,
        expected_rows=2,
        expected_sum=EXPECTED_POST_APPLY_BASE_SUM,
    )
    assert result["db_verification_ok"] is False


def test_api_verification_fails_when_all_http_fail():
    samples = [
        classify_api_sample_result(
            row={"product_id": 1, "slug": "a", "proposed_base_price": "10.00", "is_active": True},
            http_ok=False,
            http_status=None,
            api_base_price=None,
            error="timeout",
        )
    ]
    summary = evaluate_api_verification(samples, required_verified=1)
    assert summary["api_verification_ok"] is False
    assert summary["http_failed_count"] == 1


def test_api_verification_inactive_404_not_counted_as_verified():
    sample = classify_api_sample_result(
        row={
            "product_id": 1,
            "slug": "inactive",
            "proposed_base_price": "10.00",
            "is_active": False,
        },
        http_ok=False,
        http_status=404,
        api_base_price=None,
    )
    assert sample["verification"] == "inactive_not_public"
    assert sample["counts_as_public_price_verified"] is False


def test_resolve_post_commit_status_partial_when_api_incomplete():
    status, line = resolve_post_commit_status(
        db_committed=True,
        db_verification_ok=True,
        api_verification_ok=False,
    )
    assert status == "PARTIALLY_VERIFIED"
    assert "INCOMPLETE" in line


def test_rollback_sql_is_atomic_and_uses_applied_price_guard():
    import pytest

    with pytest.raises(ValueError, match="commercial contract"):
        build_rollback_sql(
            [
                {
                    "product_id": 1,
                    "sku": "A",
                    "old_base_price": "100.00",
                    "proposed_base_price": "110.00",
                    "authorized_original_price_exception": False,
                }
            ]
        )



def test_authorized_exception_clears_original_in_manifest():
    from app.domain.insize_price_110_20261021 import build_manifest_row

    row = build_manifest_row(
        {
            "id": 1944,
            "sku": "3203-1506",
            "name": "n",
            "slug": "s",
            "brand_id": 3,
            "brand_name": "INSIZE | اینسایز",
            "old_base_price": "44038500.00",
            "original_price": "47100000.00",
            "is_active": True,
            "is_available": True,
            "deleted_at": None,
        }
    )
    assert row["authorized_original_price_exception"] is True
    assert row["proposed_original_price"] is None
    assert row["proposed_base_price"] == "48442350.00"


def test_discount_semantics_allows_authorized_exceptions():
    from app.domain.insize_price_110_20261021 import (
        build_manifest_row,
        find_discount_semantics_blockers,
    )

    row = build_manifest_row(
        {
            "id": 3639,
            "sku": "S3-2824",
            "name": "n",
            "slug": "s",
            "brand_id": 3,
            "brand_name": "INSIZE | اینسایز",
            "old_base_price": "49929000.00",
            "original_price": "53400000.00",
            "is_active": True,
            "is_available": True,
            "deleted_at": None,
        }
    )
    assert find_discount_semantics_blockers([row]) == []


def test_merchandising_exception_comparison_toman():
    from app.domain.insize_price_110_20261021 import (
        build_manifest_row,
        merchandising_exception_comparison,
    )

    row = build_manifest_row(
        {
            "id": 1944,
            "sku": "3203-1506",
            "name": "n",
            "slug": "s",
            "brand_id": 3,
            "brand_name": "INSIZE | اینسایز",
            "old_base_price": "44038500.00",
            "original_price": "47100000.00",
            "is_active": True,
            "is_available": True,
            "deleted_at": None,
        }
    )
    cmp = merchandising_exception_comparison(row)
    assert cmp["currency"] == "TOMAN"
    assert cmp["proposed_original_price_toman"] is None
    assert cmp["proposed_storefront_display"] == "no_compare_at"
