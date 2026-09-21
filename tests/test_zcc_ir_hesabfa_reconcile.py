"""Safety tests for ZCC Hesabfa reconciliation (ticket #353)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import zcc_ir_hesabfa_reconcile as reconcile  # noqa: E402
from zcc_ir_hesabfa_reconcile_input import (  # noqa: E402
    DEFAULT_EXECUTION_INPUT,
    EXPECTED_COUNT,
    PINNED_EXECUTION_INPUT_SHA256,
    load_execution_input,
    sha256_file,
)


def test_execution_input_pinned_and_deterministic():
    first = DEFAULT_EXECUTION_INPUT.read_bytes()
    second = DEFAULT_EXECUTION_INPUT.read_bytes()
    assert first == second
    assert hashlib.sha256(first).hexdigest() == PINNED_EXECUTION_INPUT_SHA256
    document = load_execution_input(DEFAULT_EXECUTION_INPUT)
    assert document["count"] == EXPECTED_COUNT
    assert len(document["records"]) == EXPECTED_COUNT


def test_offline_plan_is_deterministic(tmp_path: Path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    code_a = reconcile.main(
        [
            "--execution-input",
            str(DEFAULT_EXECUTION_INPUT),
            "--output",
            str(out_a),
            "--ticket",
            "353",
        ]
    )
    code_b = reconcile.main(
        [
            "--execution-input",
            str(DEFAULT_EXECUTION_INPUT),
            "--output",
            str(out_b),
            "--ticket",
            "353",
        ]
    )
    assert code_a == 0 and code_b == 0
    plan_a = json.loads((out_a / "plan.json").read_text(encoding="utf-8"))
    plan_b = json.loads((out_b / "plan.json").read_text(encoding="utf-8"))
    assert reconcile.digest(plan_a) == reconcile.digest(plan_b)
    assert plan_a["count"] == 201
    assert {e["failure_class"] for e in plan_a["entries"]} == {
        "getItems_failed_before_save",
        "save_returned_failure_lookup_first",
    }


def test_redact_secrets():
    text = reconcile.redact_secrets(
        "Bearer abc.def.ghi HESABFA_API_KEY=supersecret KARZAR_CATEGORY_B_ADMIN_TOKEN=tok"
    )
    assert "supersecret" not in text
    assert "tok" not in text
    assert "[REDACTED]" in text


def test_circuit_breaker_trips_on_repeated_failure_class():
    breaker = reconcile.CircuitBreaker(3)
    breaker.observe("probe_failed", is_failure=True)
    breaker.observe("probe_failed", is_failure=True)
    with pytest.raises(RuntimeError, match="circuit breaker"):
        breaker.observe("probe_failed", is_failure=True)


def test_apply_and_precheck_are_mutually_exclusive(tmp_path: Path):
    out = tmp_path / "out"
    with pytest.raises(SystemExit):
        reconcile.main(
            [
                "--execution-input",
                str(DEFAULT_EXECUTION_INPUT),
                "--output",
                str(out),
                "--ticket",
                "353",
                "--apply",
                "--precheck-only",
            ]
        )


def test_wrong_ticket_rejected(tmp_path: Path):
    out = tmp_path / "out"
    with pytest.raises(SystemExit):
        reconcile.main(
            [
                "--execution-input",
                str(DEFAULT_EXECUTION_INPUT),
                "--output",
                str(out),
                "--ticket",
                "344",
            ]
        )


def test_reconcile_links_existing_without_save(monkeypatch):
    import asyncio

    from app.services.hesabfa import item_push
    from app.services.hesabfa.item_push import reconcile_product_item_shell

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)

    product = SimpleNamespace(
        id=7362,
        sku="ZCC-FMA01-063-A22-SE12-05",
        name="test",
        description=None,
        deleted_at=None,
        is_active=False,
        is_available=False,
        base_price=None,
        stock_quantity=0,
        stock_unit=SimpleNamespace(value="piece"),
    )
    client = MagicMock()
    client.get_items = AsyncMock(
        return_value={
            "List": [{"Code": "HF-1", "ProductCode": product.sku}],
            "TotalCount": 1,
        }
    )
    client.save_item = AsyncMock()

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeDB:
        def __init__(self):
            self.added = []

        async def execute(self, _stmt):
            return FakeResult()

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    db = FakeDB()

    async def run():
        return await reconcile_product_item_shell(db, product, client=client, allow_save=True)

    result = asyncio.run(run())
    assert result.action == "linked_existing"
    assert result.save_performed is False
    assert result.hesabfa_code == "HF-1"
    client.save_item.assert_not_called()
    assert len(db.added) == 1


def test_reconcile_creates_when_absent_then_rereads(monkeypatch):
    import asyncio

    from app.services.hesabfa import item_push
    from app.services.hesabfa.item_push import reconcile_product_item_shell

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)

    product = SimpleNamespace(
        id=7362,
        sku="ZCC-ABSENT-1",
        name="test",
        description=None,
        deleted_at=None,
        is_active=False,
        is_available=False,
        base_price=None,
        stock_quantity=0,
        stock_unit=SimpleNamespace(value="piece"),
    )
    client = MagicMock()
    client.get_items = AsyncMock(
        side_effect=[
            {"List": [], "TotalCount": 0},
            {"List": [], "TotalCount": 0},
            {"List": [{"Code": "HF-9", "ProductCode": product.sku}], "TotalCount": 1},
        ]
    )
    client.save_item = AsyncMock(return_value={"Code": "HF-9", "ProductCode": product.sku})

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeDB:
        def __init__(self):
            self.added = []

        async def execute(self, _stmt):
            return FakeResult()

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            return None

    async def run():
        return await reconcile_product_item_shell(
            FakeDB(), product, client=client, allow_save=True
        )

    result = asyncio.run(run())
    assert result.action == "created"
    assert result.save_performed is True
    client.save_item.assert_awaited_once()
    payload = client.save_item.await_args.args[0]
    assert payload["productCode"] == product.sku
    assert payload["active"] is False
    assert payload["sellPrice"] == 0.0
    assert payload["buyPrice"] == 0


def test_reconcile_refuses_active_product(monkeypatch):
    import asyncio

    from app.services.hesabfa import item_push
    from app.services.hesabfa.exceptions import HesabfaError
    from app.services.hesabfa.item_push import reconcile_product_item_shell

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)
    product = SimpleNamespace(
        id=1,
        sku="ZCC-X",
        name="x",
        description=None,
        deleted_at=None,
        is_active=True,
        is_available=False,
        base_price=None,
        stock_quantity=0,
        stock_unit=SimpleNamespace(value="piece"),
    )

    async def run():
        await reconcile_product_item_shell(MagicMock(), product, client=MagicMock())

    with pytest.raises(HesabfaError, match="active/available"):
        asyncio.run(run())


def test_backup_validation(tmp_path: Path):
    backups = tmp_path / "backups"
    backups.mkdir()
    path = backups / "karzar_20260921_120000.sql.gz"
    path.write_bytes(b"abc")
    digest = sha256_file(path)
    reconcile.validate_backup(path, digest)
    with pytest.raises(RuntimeError, match="SHA-256"):
        reconcile.validate_backup(path, "0" * 64)


def test_scope_excludes_ensured_prefix_and_stays_in_range():
    document = load_execution_input(DEFAULT_EXECUTION_INPUT)
    ids = {int(r["product_id"]) for r in document["records"]}
    assert len(ids) == 201
    assert min(ids) >= 7291 and max(ids) <= 7599
