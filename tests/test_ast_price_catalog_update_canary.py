"""UPDATE canary partition tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_update_canary import (  # noqa: E402
    STAGE1_COUNT,
    STAGE2_COUNT,
    select_canary_partitions,
)


def _row(pid: int, pct: str, brand: str) -> dict[str, str]:
    return {
        "product_id": str(pid),
        "sku": f"SKU-{pid}",
        "percent_diff": pct,
        "absolute_diff": "1",
        "brand": brand,
    }


class UpdateCanaryTests(unittest.TestCase):
    def test_disjoint_partitions_sum_to_total(self) -> None:
        rows = [_row(i, str(i % 5), f"B{i % 10}") for i in range(1, 200)]
        parts = select_canary_partitions(rows)
        self.assertEqual(len(parts["stage1"]), STAGE1_COUNT)
        self.assertEqual(len(parts["stage2"]), STAGE2_COUNT)
        self.assertEqual(
            len(parts["stage1"]) + len(parts["stage2"]) + len(parts["stage3"]),
            len(rows),
        )
        ids1 = {int(r["product_id"]) for r in parts["stage1"]}
        ids2 = {int(r["product_id"]) for r in parts["stage2"]}
        ids3 = {int(r["product_id"]) for r in parts["stage3"]}
        self.assertFalse(ids1 & ids2)
        self.assertFalse(ids1 & ids3)
        self.assertFalse(ids2 & ids3)

    def test_prefers_low_percent_diff_for_stage1(self) -> None:
        rows = [
            _row(1, "50", "A"),
            _row(2, "1", "B"),
            _row(3, "2", "C"),
            _row(4, "3", "D"),
            _row(5, "4", "E"),
            _row(6, "60", "F"),
        ] + [_row(i, "10", f"X{i}") for i in range(7, 80)]
        parts = select_canary_partitions(rows)
        stage1_ids = {int(r["product_id"]) for r in parts["stage1"]}
        self.assertNotIn(1, stage1_ids)
        self.assertNotIn(6, stage1_ids)


if __name__ == "__main__":
    unittest.main()
