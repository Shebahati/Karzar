"""Unit tests for scripts/ci/classify_changes.py (imported directly)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "ci"))

import classify_changes as cc  # noqa: E402


class ClassifyMatrix(unittest.TestCase):
    def test_force_full_exhaustive(self):
        r = cc.classify(["docs/x.md"], force_full=True)
        self.assertEqual(r.risk_tier, "FULL")
        self.assertTrue(r.run_backend_lint and r.run_backend_test_heavy)
        self.assertTrue(r.run_frontend_storefront and r.run_frontend_admin and r.run_frontend_e2e)
        self.assertTrue(r.run_aods_openapi)

    def test_payment_backend_r2_or_r3(self):
        r = cc.classify(["app/api/endpoints/payment.py"])
        self.assertIn(r.risk_tier, {"R2", "R3"})
        self.assertTrue(r.run_backend_test_heavy)

    def test_critical_payment_endpoint_r3(self):
        r = cc.classify(["app/services/payment_flow_service.py"])
        self.assertEqual(r.risk_tier, "R3")

    def test_scripts_unknown_conservative(self):
        r = cc.classify(["scripts/custom_one_off.py"])
        self.assertEqual(r.risk_tier, "R3")

    def test_aods_governance_not_tools(self):
        r = cc.classify(["aods/registry/document-registry.yaml"])
        self.assertEqual(r.risk_tier, "R0")
        self.assertFalse(r.run_backend_test_heavy)

    def test_aods_tools_strong(self):
        r = cc.classify(["aods/tools/aods_validate.py"])
        self.assertEqual(r.risk_tier, "R2")
        self.assertTrue(r.run_backend_test_heavy and r.run_aods_openapi)

    def test_domains_populated(self):
        r = cc.classify(["frontend/Storefront/src/middleware.ts"])
        self.assertIn("storefront", r.domains)


if __name__ == "__main__":
    unittest.main()
