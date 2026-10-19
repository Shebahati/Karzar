"""Regression tests for INSIZE +10% apply operator hardening."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from app.domain.insize_price_110 import (
    EXPECTED_VPS_HOSTNAME,
    FROZEN_MANIFEST_SHA256,
    evaluate_api_verification,
    evaluate_db_post_apply_verification,
    validate_frozen_manifest_authority,
)
from scripts.ops.insize_price_110_apply_once import (
    api_spot_check,
    collect_production_identity_proof,
    require_frozen_manifest_for_mutation,
    runtime_gate_errors,
    verify_cohort_membership,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "insize_price_110_apply_once.py"
FROZEN_CSV = ROOT / "audit/insize-price-110/INSIZE_PRICE_110_MANIFEST_20261019T122730Z.csv"


def _valid_proof(**overrides):
    base = {
        "host_proof": EXPECTED_VPS_HOSTNAME,
        "database_proof": "karzar_staging",
        "pg_system_identifier": "7664189378775347234",
        "container_proof": "lathe_postgres",
        "karzar_data_plane": None,
        "gates": {
            "host_ok": True,
            "container_ok": True,
            "db_ok": True,
            "user_ok": True,
            "volume_ok": True,
            "pg_system_identifier_ok": True,
            "alembic_ok": True,
            "transaction_read_only_on": True,
        },
        "identity_errors": [],
    }
    base.update(overrides)
    return base


def test_runtime_gate_errors_health_fail_closed():
    errors = runtime_gate_errors(
        collector_identity={"vps_hostname": EXPECTED_VPS_HOSTNAME, "postgres_container": "lathe_postgres", "postgres_db_name": "karzar_staging"},
        health={"all_pass": False},
        proof=_valid_proof(),
    )
    assert "health_all_pass_failed" in errors


def test_runtime_gate_errors_collector_hostname_mismatch():
    errors = runtime_gate_errors(
        collector_identity={
            "vps_hostname": "wrong",
            "postgres_container": "lathe_postgres",
            "postgres_db_name": "karzar_staging",
        },
        health={"all_pass": True},
        proof=_valid_proof(),
    )
    assert "collector_hostname_disagrees_with_ssh_proof" in errors


def test_verify_cohort_membership_detects_extra_product():
    manifest = [{"product_id": "1"}, {"product_id": "2"}]
    result = verify_cohort_membership(manifest, [1, 2, 3])
    assert result["ok"] is False
    assert result["extra_in_live"] == [3]


@patch("scripts.ops.insize_price_110_apply_once._run_ssh_psql")
@patch("scripts.ops.insize_price_110_apply_once._run_ssh_psql_script")
@patch("scripts.ops.insize_price_110_apply_once.subprocess.run")
def test_collect_production_identity_proof_marks_bad_pg_system(
    subprocess_run, psql_script, psql_scalar
):
    def fake_run(cmd, **kwargs):
        cmd_s = " ".join(cmd)
        if "hostname" in cmd_s and "docker" not in cmd_s:
            return type("R", (), {"stdout": EXPECTED_VPS_HOSTNAME})()
        if "Mounts" in cmd_s:
            return type("R", (), {"stdout": "karzar_postgres_data"})()
        if ".Name" in cmd_s:
            return type("R", (), {"stdout": "/lathe_postgres"})()
        return type("R", (), {"stdout": ""})()

    subprocess_run.side_effect = fake_run
    psql_script.return_value = "PROOF:transaction_read_only:on\n"

    def fake_psql(sql, **kwargs):
        if "current_database" in sql:
            return "karzar_staging\n"
        if "current_user" in sql:
            return "karzar_staging\n"
        if "pg_control_system" in sql:
            return "wrong\n"
        if "alembic_version" in sql:
            return "a3f410b5c6d7\n"
        return ""

    psql_scalar.side_effect = fake_psql
    proof = collect_production_identity_proof("karzar-vps")
    assert proof["gates"]["pg_system_identifier_ok"] is False
    assert proof["identity_errors"]


def test_api_spot_check_partial_failure_not_vacuous_success():
    manifest = [
        {
            "product_id": i,
            "slug": f"slug-{i}",
            "proposed_base_price": "110.00",
            "is_active": True,
        }
        for i in range(1, 8)
    ]

    def fake_urlopen(url, timeout=15):
        raise OSError("network down")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = api_spot_check(manifest, minimum_verified=5)
    assert result["api_verification_ok"] is False
    assert result["public_price_verified_count"] == 0
    assert result["all_match"] is False


def test_require_frozen_manifest_blocks_apply_without_csv():
    import argparse

    args = argparse.Namespace(apply=True, rehearsal=False, manifest_csv=None, confirm_manifest_sha="")
    assert require_frozen_manifest_for_mutation(args) == 2


def test_require_frozen_manifest_blocks_wrong_confirm_sha():
    import argparse

    args = argparse.Namespace(
        apply=True,
        rehearsal=False,
        manifest_csv=FROZEN_CSV,
        confirm_manifest_sha="not-the-frozen-sha",
    )
    assert require_frozen_manifest_for_mutation(args) == 2


def test_cli_apply_without_manifest_csv_exits_2():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply", "--confirm-manifest-sha", FROZEN_MANIFEST_SHA256],
        cwd=ROOT,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "manifest-csv" in proc.stderr.lower()


@patch("scripts.ops.insize_price_110_apply_once.sha256_file", return_value="alternate_sha")
def test_validate_frozen_manifest_authority_via_domain(_sha_mock):
    import csv

    with FROZEN_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    result = validate_frozen_manifest_authority(rows, csv_sha256="alternate_sha")
    assert result["ok"] is False


def test_db_verification_incomplete_with_commit_facts():
    db_eval = evaluate_db_post_apply_verification(
        {
            "target_rows": 206,
            "price_exact_match": 206,
            "formula_matches": 206,
            "change_log_rows_with_reason": 206,
            "distinct_changed_product_ids": 206,
            "duplicate_mutations": 0,
            "sum_base_price_post": "1.00",
        },
        expected_rows=206,
        expected_sum=None,
    )
    assert db_eval["db_verification_ok"] is True
    api_eval = evaluate_api_verification([], required_verified=5)
    assert api_eval["api_verification_ok"] is False
