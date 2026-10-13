"""Classifier scenarios A–K (stdlib unittest; avoids tests/conftest.py)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLASSIFIER = REPO / "scripts" / "ci" / "classify_changes.py"


def run_classifier(*paths: str, **kwargs: str) -> dict:
    cmd = [sys.executable, str(CLASSIFIER), "--paths", *paths, "--json"]
    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", value])
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


class ClassifierScenarios(unittest.TestCase):
    def test_a_docs_only_r0(self):
        r = run_classifier("docs/DEVELOPMENT.md", "audit/foo/README.md")
        self.assertEqual(r["scenario"], "A")
        self.assertEqual(r["risk_tier"], "R0")
        self.assertFalse(r["run_backend_test_heavy"])

    def test_b_storefront_r1(self):
        r = run_classifier("frontend/Storefront/src/components/Home.tsx")
        self.assertEqual(r["scenario"], "B")
        self.assertEqual(r["risk_tier"], "R1")
        self.assertTrue(r["run_frontend_storefront"])
        self.assertFalse(r["run_frontend_e2e"])

    def test_c_admin_r1(self):
        r = run_classifier("frontend/admin-panel/src/app/page.tsx")
        self.assertEqual(r["scenario"], "C")
        self.assertFalse(r["run_backend_test_heavy"])

    def test_d_backend_r2(self):
        r = run_classifier("app/api/v1/products.py")
        self.assertEqual(r["scenario"], "D")
        self.assertTrue(r["run_backend_test_heavy"])

    def test_e_alembic_r2(self):
        r = run_classifier("alembic/versions/x.py")
        self.assertEqual(r["scenario"], "E")
        self.assertTrue(r["run_aods_openapi"])

    def test_f_openapi_r2(self):
        r = run_classifier("openapi/v1.json")
        self.assertEqual(r["scenario"], "F")

    def test_g_aods_r0(self):
        r = run_classifier("aods/registry/document-registry.yaml")
        self.assertEqual(r["scenario"], "G")
        self.assertEqual(r["risk_tier"], "R0")

    def test_h_workflow_full(self):
        r = run_classifier(".github/workflows/backend-ci.yml")
        self.assertEqual(r["scenario"], "H")
        self.assertEqual(r["risk_tier"], "FULL")

    def test_i_unknown_full(self):
        r = run_classifier("mystery/blob.dat")
        self.assertEqual(r["scenario"], "I")
        self.assertIn("mystery/blob.dat", r["unknown_paths"])

    def test_j_ci_full_label(self):
        r = run_classifier("docs/DEVELOPMENT.md", pr_labels="ci:full")
        self.assertEqual(r["scenario"], "J")

    def test_k_deploy_staging_r1(self):
        r = run_classifier("deploy/staging/Dockerfile")
        self.assertEqual(r["scenario"], "K")
        self.assertTrue(r["run_deploy_staging_guard"])

    def test_storefront_e2e_triggers(self):
        r = run_classifier("frontend/Storefront/package.json")
        self.assertTrue(r["run_frontend_e2e"])


if __name__ == "__main__":
    unittest.main()
