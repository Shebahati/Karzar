"""Unit tests for INSIZE 10% discount removal cohort discovery (no DB)."""

from __future__ import annotations

from decimal import Decimal
from scripts.ops.insize_discount_10_remove import (
    build_manifest,
    select_discount_removal_cohort,
    validate_discount_removal_cohort,
)


def _row(
    *,
    pid: int,
    base: str,
    original: str | None,
    sku: str = "SKU-1",
) -> dict[str, object]:
    return {
        "id": pid,
        "sku": sku,
        "name": "n",
        "slug": "s",
        "base_price": Decimal(base),
        "original_price": Decimal(original) if original is not None else None,
        "is_active": True,
        "is_available": True,
        "deleted_at": None,
        "brand_id": 3,
        "category_id": 1,
        "product_type_id": None,
        "brand_name": "INSIZE | اینسایز",
        "has_image": True,
    }


def test_removal_manifest_uses_original_as_new_base():
    row = _row(pid=1, base="900", original="1000")
    manifest = build_manifest([row])
    assert len(manifest) == 1
    m = manifest[0]
    assert m["pre_base_price"] == "900"
    assert m["pre_original_price"] == "1000"
    assert m["computed_post_base_price"] == "1000"
    assert m["computed_post_original_price"] is None


def test_cohort_requires_discount_apply_log_match():
    row = _row(pid=1, base="900", original="1000")
    apply_index = {
        1: {
            "base_old": Decimal("1000"),
            "base_new": Decimal("900"),
            "original_old": None,
            "original_new": Decimal("1000"),
        }
    }
    cohort, _meta = select_discount_removal_cohort([row], apply_index)
    assert len(cohort) == 1
    validation = validate_discount_removal_cohort([row], apply_index)
    assert validation["ok"] is True

    drift_index = {
        1: {
            "base_old": Decimal("1000"),
            "base_new": Decimal("899"),
            "original_old": None,
            "original_new": Decimal("1000"),
        }
    }
    bad = validate_discount_removal_cohort([row], drift_index)
    assert bad["ok"] is False
