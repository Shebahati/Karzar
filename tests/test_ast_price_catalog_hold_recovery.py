"""CREATE HOLD recovery classification tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_hold_recovery import is_create_recovery_hold  # noqa: E402


class HoldRecoveryClassificationTests(unittest.TestCase):
    def test_update_large_swing_excluded(self) -> None:
        self.assertFalse(
            is_create_recovery_hold(
                {"hold_reason": "QA_LARGE_PRICE_SWING", "qa_flags": "QA_LARGE_PRICE_SWING"}
            )
        )

    def test_create_visual_qa_included(self) -> None:
        self.assertTrue(
            is_create_recovery_hold(
                {"hold_reason": "HOLD_VISUAL_PDF_QA_REQUIRED", "qa_flags": ""}
            )
        )


if __name__ == "__main__":
    unittest.main()
