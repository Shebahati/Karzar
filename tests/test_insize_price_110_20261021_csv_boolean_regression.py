"""CSV boolean + frozen manifest regression (INSIZE-PRICE-110-20261021)."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.domain.insize_price_110_20261021 import (
    AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS,
    EXPECTED_ORIGINAL_EXCEPTION_COUNT,
    EXPECTED_PRICED_COHORT_ROWS,
    EXPECTED_TOTAL_EVENT_LOG_ROWS,
    FROZEN_MANIFEST_SHA256,
    build_real_apply_sql,
    build_rollback_sql,
    normalize_manifest_from_csv_rows,
    parse_csv_bool,
    rehearsal_contract_summary,
    validate_owner_frozen_commercial_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FROZEN_CSV = ROOT / "audit/insize-price-110-20261021/INSIZE_PRICE_110_20261021_MANIFEST_20261021T133454Z.csv"
SCRIPT = ROOT / "scripts/ops/insize_price_110_20261021_apply_once.py"


def test_python_truthiness_would_misread_csv_false():
    assert bool("False") is True
    assert parse_csv_bool("False", field="authorized_original_price_exception") is False


def test_frozen_csv_dictreader_contract():
    with FROZEN_CSV.open(encoding="utf-8", newline="") as fh:
        raw = list(csv.DictReader(fh))
    assert len(raw) == EXPECTED_PRICED_COHORT_ROWS
    naive_truthy = sum(1 for r in raw if r.get("authorized_original_price_exception"))
    assert naive_truthy == EXPECTED_PRICED_COHORT_ROWS  # documents the defect
    manifest = normalize_manifest_from_csv_rows(raw)
    contract = validate_owner_frozen_commercial_contract(manifest)
    assert contract["ok"] is True
    assert contract["exception_product_ids"] == sorted(AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS)


def test_apply_sql_has_exactly_two_exception_flags():
    with FROZEN_CSV.open(encoding="utf-8", newline="") as fh:
        manifest = normalize_manifest_from_csv_rows(list(csv.DictReader(fh)))
    sql = build_real_apply_sql(
        manifest,
        expected_rows=EXPECTED_PRICED_COHORT_ROWS,
        manifest_sha256=FROZEN_MANIFEST_SHA256,
    )
    assert sql.count(", TRUE)") == EXPECTED_ORIGINAL_EXCEPTION_COUNT
    assert sql.count(", FALSE)") == EXPECTED_PRICED_COHORT_ROWS - EXPECTED_ORIGINAL_EXCEPTION_COUNT
    assert f"exception_n integer := {EXPECTED_ORIGINAL_EXCEPTION_COUNT}" in sql
    assert f"expected_total_logs integer := {EXPECTED_TOTAL_EVENT_LOG_ROWS}" in sql


def test_rollback_sql_from_frozen_csv():
    with FROZEN_CSV.open(encoding="utf-8", newline="") as fh:
        manifest = normalize_manifest_from_csv_rows(list(csv.DictReader(fh)))
    sql = build_rollback_sql(manifest)
    assert "rollback guard failed" in sql
    assert "expected_exception_n integer := 2" in sql


def test_rehearsal_contract_summary_constants():
    summary = rehearsal_contract_summary()
    assert summary["total_event_logs"] == 208
    assert summary["original_price_updates"] == 2


@pytest.mark.integration
def test_operator_rehearsal_round_trip_via_ssh():
    """Live SERIALIZABLE rehearsal; requires SSH to karzar-vps."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--rehearsal",
            "--manifest-csv",
            str(FROZEN_CSV),
            "--confirm-manifest-sha",
            FROZEN_MANIFEST_SHA256,
        ],
        cwd=ROOT,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0 and "ssh" in (proc.stderr + proc.stdout).lower():
        pytest.skip("SSH rehearsal unavailable in this environment")
    assert proc.returncode == 0, proc.stderr[-500:]
    assert "REHEARSAL_OK" in proc.stdout
