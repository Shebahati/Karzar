"""Classifier scenarios A–M (stdlib unittest; avoids tests/conftest.py)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLASSIFIER = REPO / "scripts" / "ci" / "classify_changes.py"

FULL_FLAGS = (
    "run_backend_lint",
    "run_backend_test_heavy",
    "run_aods_fast",
    "run_aods_openapi",
    "run_frontend_storefront",
    "run_frontend_admin",
    "run_frontend_e2e",
)


def run_classifier(*paths: str, **kwargs: str) -> dict:
    cmd = [sys.executable, str(CLASSIFIER), "--paths", *paths, "--json"]
    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", value])
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def assert_full_matrix(r: dict) -> None:
    for key in FULL_FLAGS:
        assert r[key], f"expected {key}=true for exhaustive FULL, got {r}"


class ClassifierScenarios(unittest.TestCase):
    def test_a_docs_only_r0(self):
        r = run_classifier("docs/DEVELOPMENT.md", "audit/foo/README.md")
        self.assertEqual(r["scenario"], "A")
        self.assertEqual(r["risk_tier"], "R0")
        self.assertFalse(r["run_backend_test_heavy"])

    def test_b_storefront_r1(self):
        r = run_classifier("frontend/Storefront/src/components/home/designed-hero.tsx")
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

    def test_e_alembic_r3(self):
        r = run_classifier("alembic/versions/x.py")
        self.assertEqual(r["scenario"], "E")
        self.assertEqual(r["risk_tier"], "R3")
        self.assertTrue(r["run_aods_openapi"])

    def test_f_openapi_r2(self):
        r = run_classifier("openapi/v1.json")
        self.assertEqual(r["scenario"], "F")

    def test_g_aods_governance_r0(self):
        r = run_classifier("aods/registry/document-registry.yaml")
        self.assertEqual(r["scenario"], "G")
        self.assertEqual(r["risk_tier"], "R0")

    def test_g2_aods_tools_r2(self):
        r = run_classifier("aods/tools/aods_validate.py")
        self.assertEqual(r["scenario"], "G2")
        self.assertEqual(r["risk_tier"], "R2")
        self.assertTrue(r["run_backend_test_heavy"])
        self.assertTrue(r["run_aods_openapi"])

    def test_h_workflow_full(self):
        r = run_classifier(".github/workflows/backend-ci.yml")
        self.assertEqual(r["scenario"], "H")
        self.assertEqual(r["risk_tier"], "FULL")
        assert_full_matrix(r)

    def test_i_unknown_full_exhaustive(self):
        r = run_classifier("unknown/new-top-level/file.txt")
        self.assertEqual(r["scenario"], "I")
        self.assertIn("unknown/new-top-level/file.txt", r["unknown_paths"])
        assert_full_matrix(r)

    def test_i_unknown_docs_path_full(self):
        r = run_classifier("docs/foo.md")
        self.assertEqual(r["scenario"], "A")
        self.assertEqual(r["risk_tier"], "R0")

    def test_j_ci_full_label_exhaustive(self):
        r = run_classifier("docs/foo.md", pr_labels="ci:full")
        self.assertEqual(r["scenario"], "J")
        assert_full_matrix(r)

    def test_k_deploy_r3(self):
        r = run_classifier("deploy/staging/Dockerfile")
        self.assertEqual(r["scenario"], "K")
        self.assertEqual(r["risk_tier"], "R3")
        self.assertTrue(r["run_deploy_staging_guard"])
        self.assertTrue(r["run_backend_test_heavy"])

    def test_m_scripts_audit_r1(self):
        r = run_classifier("scripts/audit_product_naming_v1.py")
        self.assertEqual(r["scenario"], "M")
        self.assertEqual(r["risk_tier"], "R1")
        self.assertTrue(r["run_audit_script_validation"])
        self.assertFalse(r["run_backend_lint"])
        self.assertFalse(r["run_backend_test_heavy"])

    def test_scripts_apply_r3(self):
        r = run_classifier("scripts/apply_manufacturer_identity_phase2c.py")
        self.assertEqual(r["risk_tier"], "R3")
        self.assertTrue(r["run_backend_test_heavy"])

    def test_storefront_checkout_e2e(self):
        r = run_classifier("frontend/Storefront/src/app/checkout/page.tsx")
        self.assertTrue(r["run_frontend_e2e"])

    def test_storefront_e2e_triggers_package(self):
        r = run_classifier("frontend/Storefront/package.json")
        self.assertTrue(r["run_frontend_e2e"])



    def test_script_audit_allowlisted_r1(self):
        r = run_classifier("scripts/audit_product_naming_v1.py")
        self.assertEqual(r["risk_tier"], "R1")
        self.assertEqual(r["scenario"], "M")
        self.assertTrue(r["run_audit_script_validation"])
        self.assertFalse(r["run_backend_test_heavy"])
        self.assertFalse(r["run_backend_lint"])
        self.assertIn("scripts/audit_product_naming_v1.py", r["changed_readonly_audit_scripts"])

    def test_script_audit_apply_production_r3(self):
        r = run_classifier("scripts/audit_apply_production.py")
        self.assertEqual(r["risk_tier"], "R3")
        self.assertTrue(r["run_backend_test_heavy"])
        self.assertFalse(r.get("run_audit_script_validation"))

    def test_script_audit_price_writer_r3(self):
        r = run_classifier("scripts/audit_price_writer.py")
        self.assertEqual(r["risk_tier"], "R3")

    def test_script_apply_catalog_r3(self):
        r = run_classifier("scripts/apply_catalog.py")
        self.assertEqual(r["risk_tier"], "R3")

    def test_script_custom_unknown_r3(self):
        r = run_classifier("scripts/custom_unknown.py")
        self.assertEqual(r["risk_tier"], "R3")

    def test_script_mutation_overrides_audit_name(self):
        r = run_classifier("scripts/audit_apply_production.py")
        self.assertEqual(r["risk_tier"], "R3")
        self.assertNotEqual(r.get("scenario"), "M")


    def test_readonly_audit_allowlist_integrity(self):
        proc = subprocess.run(
            [sys.executable, str(CLASSIFIER), "--validate-allowlist"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr or proc.stdout,
        )

if __name__ == "__main__":
    unittest.main()
