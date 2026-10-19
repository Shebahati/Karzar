"""Regression tests for read-only storefront eligibility snapshot script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.utils.public_catalog import (
    PLACEHOLDER_ILIKE_TOKENS,
    legacy_public_image_gate_sql_conditions,
)
from scripts.ops.storefront_publication_eligibility_snapshot import (
    build_snapshot_payload,
    evaluate_snapshot_identity,
    normalize_database_url,
    run_snapshot_async,
    snapshot_sql_queries,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "storefront_publication_eligibility_snapshot.py"


def test_legacy_sql_includes_all_placeholder_tokens():
    sql = legacy_public_image_gate_sql_conditions("pi")
    for token in PLACEHOLDER_ILIKE_TOKENS:
        assert token in sql


def test_normalize_database_url_strips_sqlalchemy_drivers():
    assert normalize_database_url("postgresql+asyncpg://u:p@h/d").startswith("postgresql://")
    assert "+asyncpg" not in normalize_database_url("postgresql+asyncpg://u:p@h/d")


def test_evaluate_snapshot_identity_partition():
    assert evaluate_snapshot_identity(legacy=80, current=100, imageless_active=20) is True
    assert evaluate_snapshot_identity(legacy=80, current=100, imageless_active=19) is False


def test_build_snapshot_payload_identity_flag():
    payload = build_snapshot_payload(
        {
            "legacy": 10,
            "current": 15,
            "imageless_active": 5,
            "inactive_imaged": 3,
        },
        transaction_read_only="on",
    )
    assert payload["identity_check_current_equals_legacy_plus_imageless_active"] is True
    assert payload["transaction_read_only"] == "on"
    assert payload["driver"] == "asyncpg"


def test_snapshot_sql_queries_keys():
    queries = snapshot_sql_queries()
    assert set(queries) == {"legacy", "current", "imageless_active", "inactive_imaged"}


@pytest.mark.asyncio
async def test_collect_readonly_counts_requires_transaction_read_only_on():
    mock_conn = AsyncMock()
    mock_transaction = MagicMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=None)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=mock_transaction)
    mock_conn.fetchval = AsyncMock(
        side_effect=lambda q: "off" if "transaction_read_only" in q.lower() else 0
    )
    mock_conn.close = AsyncMock()

    with patch("asyncpg.connect", AsyncMock(return_value=mock_conn)):
        from scripts.ops.storefront_publication_eligibility_snapshot import (
            collect_readonly_counts,
        )

        with pytest.raises(RuntimeError, match="transaction_read_only"):
            await collect_readonly_counts("postgresql://u:p@127.0.0.1:5432/db")


@pytest.mark.asyncio
async def test_run_snapshot_async_uses_single_readonly_transaction():
    calls: list[str] = []

    select_returns = {"legacy": 8, "current": 10, "imageless_active": 2, "inactive_imaged": 0}
    select_idx = 0

    async def fake_fetchval(query: str):
        nonlocal select_idx
        calls.append(query.strip().split()[0].upper())
        if "SHOW" in query.upper():
            return "on"
        keys = list(select_returns)
        value = select_returns[keys[select_idx]]
        select_idx += 1
        return value

    mock_conn = AsyncMock()
    mock_transaction = MagicMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=None)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=mock_transaction)
    mock_conn.fetchval = fake_fetchval
    mock_conn.close = AsyncMock()

    with patch("asyncpg.connect", AsyncMock(return_value=mock_conn)):
        payload = await run_snapshot_async("postgresql://u:p@127.0.0.1:5432/db")

    mock_conn.transaction.assert_called_once_with(
        isolation="repeatable_read",
        readonly=True,
    )
    assert payload["transaction_read_only"] == "on"
    assert payload["identity_check_current_equals_legacy_plus_imageless_active"] is True
    assert calls.count("SHOW") == 1
    assert calls.count("SELECT") == 4


def test_cli_exits_when_postgres_password_missing():
    env = {k: v for k, v in __import__("os").environ.items() if k != "POSTGRES_PASSWORD"}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "POSTGRES_PASSWORD" in proc.stderr


def test_cli_importable_from_repository_root():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import scripts.ops.storefront_publication_eligibility_snapshot as m; "
            "assert m.ROOT.name != ''",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
