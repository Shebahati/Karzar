"""Product 1789 brand repair tooling must refuse real APPLY / COMMIT."""

from __future__ import annotations

import pytest
from scripts.ops import product_1789_brand_repair_rehearsal as mod


def test_reject_real_apply_flags():
    with pytest.raises(SystemExit):
        mod.reject_real_apply(["--apply"])
    with pytest.raises(SystemExit):
        mod.reject_real_apply(["--real-apply"])
    with pytest.raises(SystemExit):
        mod.reject_real_apply(["--commit"])


def test_rehearsal_sql_contains_rollback_not_commit():
    sql = mod.build_rehearsal_sql()
    assert "ROLLBACK" in sql.upper()
    assert "COMMIT" not in sql.upper()
    assert "brand_id = 3" in sql
    assert mod.REHEARSAL_REASON in sql


def test_current_state_hash_stable():
    h1 = mod.current_state_hash(
        product_id=1789,
        sku="1114-150",
        manufacturer_code="1114-150",
        brand_id=None,
        is_available="true",
        base_price="7980000.00",
        deleted_at=None,
        updated_at="2026-10-04 11:19:55.937259+00",
    )
    h2 = mod.current_state_hash(
        product_id=1789,
        sku="1114-150",
        manufacturer_code="1114-150",
        brand_id=None,
        is_available="true",
        base_price="7980000.00",
        deleted_at=None,
        updated_at="2026-10-04 11:19:55.937259+00",
    )
    assert h1 == h2
    assert len(h1) == 64
