"""Hesabfa item activation is independent of site publication state."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import settings
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.hesabfa.activation_reconcile import (
    ACTIVATION_APPLY_STATUS,
    DryRunHesabfaClient,
    DryRunSession,
    MappingView,
    SiteProductView,
    classify_catalog,
    load_remote_items,
    parse_remote_active,
    summarize,
)
from app.services.hesabfa.exceptions import HesabfaError
from app.services.hesabfa.item_lifecycle import (
    HESABFA_ITEM_ACTIVE,
    hesabfa_item_should_be_active,
)
from app.services.hesabfa.item_push import (
    build_hesabfa_item_payload,
    ensure_product_in_hesabfa,
)
from app.services.product_service import ProductService
from sqlalchemy import text

from tests.conftest import TestingSessionLocal

ROOT = Path(__file__).resolve().parents[1]
STOCK_KEYS = ("Stock", "stock", "Quantity", "quantity", "openingQty", "OpeningQuantity")


def _product(**overrides: object) -> SimpleNamespace:
    fields: dict[str, object] = {
        "id": 11,
        "sku": "SKU-1",
        "name": "Shell",
        "description": "desc",
        "deleted_at": None,
        "is_active": True,
        "is_available": True,
        "base_price": None,
        "stock_quantity": 0,
        "stock_unit": SimpleNamespace(value="piece"),
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _assert_active_shell(payload: dict, sku: str) -> None:
    assert payload["active"] is True
    assert payload["productCode"] == sku
    assert payload["sellPrice"] == 0.0
    assert payload["buyPrice"] == 0
    for key in STOCK_KEYS:
        assert key not in payload


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeDB:
    def __init__(self, existing: object = None) -> None:
        self.existing = existing
        self.added: list[object] = []

    async def execute(self, _stmt: object) -> _FakeResult:
        return _FakeResult(self.existing)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def test_policy_ignores_site_lifecycle() -> None:
    assert HESABFA_ITEM_ACTIVE is True
    assert hesabfa_item_should_be_active(None) is True
    inactive = _product(is_active=False, is_available=False, base_price=None, stock_quantity=5)
    assert hesabfa_item_should_be_active(inactive) is True


def test_payload_active_for_published_product() -> None:
    payload = build_hesabfa_item_payload(_product(is_active=True))
    _assert_active_shell(payload, "SKU-1")


def test_payload_active_for_inactive_product() -> None:
    payload = build_hesabfa_item_payload(_product(is_active=False))
    _assert_active_shell(payload, "SKU-1")


def test_payload_active_for_unavailable_product() -> None:
    payload = build_hesabfa_item_payload(_product(is_active=True, is_available=False))
    _assert_active_shell(payload, "SKU-1")


def test_payload_active_for_draft_unpriced_product() -> None:
    payload = build_hesabfa_item_payload(
        _product(is_active=False, is_available=False, base_price=None)
    )
    _assert_active_shell(payload, "SKU-1")


def test_writers_do_not_copy_site_is_active() -> None:
    offenders: list[str] = []
    roots = [ROOT / "app", ROOT / "scripts"]
    for root in roots:
        for path in root.rglob("*.py"):
            text_value = path.read_text(encoding="utf-8")
            if '"active": bool(product.is_active)' in text_value:
                offenders.append(str(path))
            if 'payload["active"] = False' in text_value:
                offenders.append(str(path))
    assert offenders == []


def test_duplicate_product_code_does_not_save(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hesabfa import item_push

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)
    client = MagicMock()
    client.get_items = AsyncMock(
        return_value={
            "List": [
                {"Code": "A", "ProductCode": "SKU-1"},
                {"Code": "B", "ProductCode": "sku-1"},
            ],
            "TotalCount": 2,
        }
    )
    client.save_item = AsyncMock()

    async def run() -> None:
        await ensure_product_in_hesabfa(_FakeDB(), _product(), client=client)

    with pytest.raises(HesabfaError, match="ambiguous"):
        asyncio.run(run())
    client.save_item.assert_not_called()


def test_soft_deleted_product_is_not_deactivated(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hesabfa import item_push

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)
    client = MagicMock()
    client.save_item = AsyncMock()
    client.get_items = AsyncMock()

    async def run() -> object:
        return await ensure_product_in_hesabfa(
            _FakeDB(),
            _product(deleted_at="2026-01-01T00:00:00Z", is_active=False),
            client=client,
        )

    skipped = asyncio.run(run())
    assert skipped.action == "skipped"
    assert skipped.mapping is None
    assert skipped.save_performed is False
    client.save_item.assert_not_called()
    client.get_items.assert_not_called()


def _mock_hesabfa(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    monkeypatch.setattr(settings, "HESABFA_ENABLED", True)
    monkeypatch.setattr(settings, "HESABFA_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "HESABFA_LOGIN_TOKEN", "test-login-token")
    client = MagicMock()
    client.get_items = AsyncMock(return_value={"List": [], "TotalCount": 0})

    async def _save(item: dict) -> dict:
        code = str(item.get("productCode") or "ITEM")
        return {"Code": f"HF-{code}", "ProductCode": code}

    client.save_item = AsyncMock(side_effect=_save)
    monkeypatch.setattr("app.services.hesabfa.item_push.get_hesabfa_client", lambda: client)
    return client


@pytest.mark.usefixtures("override_database")
def test_create_draft_pushes_active_shell(
    monkeypatch: pytest.MonkeyPatch, valid_product_data: dict
) -> None:
    client = _mock_hesabfa(monkeypatch)
    payload_in = dict(valid_product_data)
    payload_in["sku"] = "DRAFT-1"
    payload_in["is_active"] = False
    payload_in["is_available"] = False
    payload_in["base_price"] = None

    async def run() -> tuple[object, dict]:
        async with TestingSessionLocal() as session:
            product = await ProductService.create_product_with_validation(
                session, ProductCreate(**payload_in)
            )
            saved = client.save_item.await_args.args[0]
            return product, saved

    product, saved = asyncio.run(run())
    assert product.is_active is False
    assert product.is_available is False
    assert product.base_price is None
    assert client.save_item.await_count == 1
    assert "code" not in saved
    assert "Code" not in saved
    _assert_active_shell(saved, "DRAFT-1")


@pytest.mark.usefixtures("override_database")
def test_update_deactivation_keeps_hesabfa_active(
    monkeypatch: pytest.MonkeyPatch, valid_product_data: dict
) -> None:
    client = _mock_hesabfa(monkeypatch)

    async def run() -> tuple[object, list[dict]]:
        async with TestingSessionLocal() as session:
            created = await ProductService.create_product_with_validation(
                session, ProductCreate(**valid_product_data)
            )
            updated = await ProductService.update_product_with_validation(
                session,
                created.id,
                ProductUpdate(is_active=False),
            )
            payloads = [call.args[0] for call in client.save_item.await_args_list]
            return updated, payloads

    updated, payloads = asyncio.run(run())
    assert updated is not None
    assert updated.is_active is False
    assert len(payloads) == 1
    assert payloads[0]["active"] is True
    assert "code" not in payloads[0]
    assert "Code" not in payloads[0]
    for key in STOCK_KEYS:
        assert key not in payloads[0]


@pytest.mark.usefixtures("override_database")
def test_soft_delete_does_not_call_hesabfa(
    monkeypatch: pytest.MonkeyPatch, valid_product_data: dict
) -> None:
    client = _mock_hesabfa(monkeypatch)

    async def run() -> int:
        async with TestingSessionLocal() as session:
            created = await ProductService.create_product_with_validation(
                session, ProductCreate(**valid_product_data)
            )
            calls_after_create = client.save_item.await_count
            deleted = await ProductService.delete_product(session, created.id)
            assert deleted is True
            refreshed = await session.get(type(created), created.id)
            skipped = await ensure_product_in_hesabfa(session, refreshed, client=client)
            assert skipped.action == "skipped"
            assert skipped.save_performed is False
            assert refreshed.deleted_at is not None
            return calls_after_create

    calls_after_create = asyncio.run(run())
    assert calls_after_create == 1
    assert client.save_item.await_count == 1


def test_parse_remote_active_does_not_guess() -> None:
    assert parse_remote_active({"Active": True}) is True
    assert parse_remote_active({"active": 0}) is False
    assert parse_remote_active({"Name": "x"}) is None


def test_classifier_actions_and_summary(tmp_path: Path) -> None:
    products = [
        SiteProductView(1, "ACTIVE", True, True, True),
        SiteProductView(2, "SITE-OFF", False, False, False),
        SiteProductView(3, "NEED-ACT", False, False, False),
        SiteProductView(4, "MISSING", False, False, False),
        SiteProductView(5, "LINK", True, False, False),
        SiteProductView(6, "DUP", True, False, False),
        SiteProductView(7, "STALE", True, False, False),
        SiteProductView(8, "GONE", False, False, False),
        SiteProductView(9, "UNAVAIL", True, False, True),
        SiteProductView(10, "DRAFT", False, False, False),
    ]
    mappings = [
        MappingView(1, "ACTIVE", "C1", "ACTIVE"),
        MappingView(2, "SITE-OFF", "C2", "SITE-OFF"),
        MappingView(3, "NEED-ACT", "C3", "NEED-ACT"),
        MappingView(7, "STALE", "C7-OLD", "STALE"),
        MappingView(8, "GONE", "C8", "GONE"),
        MappingView(9, "UNAVAIL", "C9", "UNAVAIL"),
    ]
    remote = [
        {"Code": "C1", "ProductCode": "ACTIVE", "Active": True},
        {"Code": "C2", "ProductCode": "SITE-OFF", "Active": True},
        {"Code": "C3", "ProductCode": "NEED-ACT", "Active": False, "SellPrice": 120000},
        {"Code": "C5", "ProductCode": "LINK", "Active": True},
        {"Code": "C6A", "ProductCode": "DUP", "Active": True},
        {"Code": "C6B", "ProductCode": "DUP", "Active": False},
        {"Code": "C7-NEW", "ProductCode": "STALE", "Active": True},
        {"Code": "C9", "ProductCode": "UNAVAIL", "Active": False},
    ]
    rows = classify_catalog(products, mappings, remote)
    by_sku = {row.sku: row for row in rows}
    assert by_sku["ACTIVE"].action == "MAPPED_ACTIVE"
    assert by_sku["ACTIVE"].price_risk is False
    assert by_sku["SITE-OFF"].action == "MAPPED_ACTIVE"
    assert by_sku["SITE-OFF"].desired_hesabfa_active is True
    assert by_sku["NEED-ACT"].action == "RECONCILIATION_REQUIRED"
    assert by_sku["NEED-ACT"].reason == "mapped_inactive"
    assert by_sku["NEED-ACT"].price_risk is True
    assert by_sku["MISSING"].action == "UNMAPPED"
    assert by_sku["LINK"].action == "LINK_EXISTING"
    assert by_sku["DUP"].action == "AMBIGUOUS"
    assert by_sku["DUP"].reason == "duplicate_remote_product_code"
    assert by_sku["STALE"].action == "AMBIGUOUS"
    assert by_sku["STALE"].reason == "mapping_code_mismatch"
    assert by_sku["GONE"].action == "MISSING_REMOTE_ITEM"
    assert by_sku["GONE"].reason == "mapping_remote_missing"
    assert by_sku["UNAVAIL"].action == "RECONCILIATION_REQUIRED"
    assert by_sku["UNAVAIL"].reason == "mapped_inactive"
    assert by_sku["DRAFT"].action == "UNMAPPED"
    assert all(row.desired_hesabfa_active is True for row in rows)

    summary = summarize(rows, population_total=len(products), remote_writes=0, database_writes=0)
    assert summary["TOTAL_SITE_NON_DELETED"] == 10
    assert summary["MAPPED"] == 6
    assert summary["REMOTE_MATCHED"] == 6
    assert summary["REMOTE_ALREADY_ACTIVE"] == 4
    assert summary["REMOTE_INACTIVE"] == 2
    assert summary["REMOTE_MISSING"] == 3
    assert summary["MAPPING_MISSING_REMOTE_FOUND"] == 1
    assert summary["MAPPING_STALE"] == 2
    assert summary["AMBIGUOUS"] == 2
    assert summary["ERRORS"] == 1
    assert summary["WOULD_ACTIVATE"] == 0
    assert summary["RECONCILIATION_REQUIRED"] == 2
    assert summary["PRICE_RISK"] == 1
    assert summary["WOULD_CREATE"] == 2
    assert summary["WOULD_LINK"] == 1
    assert summary["DRY_RUN"] is True
    assert summary["REMOTE_WRITES"] == 0
    assert summary["DATABASE_WRITES"] == 0
    assert summary["ACTIVATION_APPLY"] == ACTIVATION_APPLY_STATUS
    assert summary["ITEM_SAVE_CONTRACT"] == "UNKNOWN"
    assert summary["REMOTE_ACTIVE_UNKNOWN"] == 0
    assert summary["AMBIGUITY_BREAKDOWN"]["DUPLICATE_REMOTE_PRODUCT_CODE"]["count"] == 1
    assert summary["AMBIGUITY_BREAKDOWN"]["MAPPING_CODE_MISMATCH"]["count"] == 1
    assert summary["AMBIGUITY_BREAKDOWN"]["DUPLICATE_SITE_SKU"]["count"] == 0
    assert summary["ERROR_BREAKDOWN"]["MAPPING_REMOTE_MISSING"]["count"] == 1
    assert summary["ERROR_BREAKDOWN"]["REMOTE_ACTIVE_UNKNOWN"]["count"] == 0
    cohorts = summary["COHORTS"]
    assert cohorts["SITE_INACTIVE__HF_ACTIVE"] == 1
    assert cohorts["SITE_INACTIVE__HF_INACTIVE"] == 1
    assert cohorts["SITE_UNAVAILABLE__HF_INACTIVE"] == 2
    assert cohorts["SITE_UNPRICED__HF_INACTIVE"] == 1
    assert cohorts["SITE_ACTIVE__HF_MISSING"] == 0
    assert cohorts["SITE_INACTIVE__HF_MISSING"] == 3

    from app.services.hesabfa.activation_reconcile import write_artifacts

    write_artifacts(tmp_path, rows, summary)
    written = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert written["REMOTE_WRITES"] == 0
    assert "apiKey" not in (tmp_path / "reconciliation.csv").read_text(encoding="utf-8")
    assert (tmp_path / "sha256sums.txt").is_file()
    error_rows = (tmp_path / "errors.csv").read_text(encoding="utf-8").strip().splitlines()
    assert len(error_rows) == 2
    assert error_rows[1].startswith("8,GONE,")
    assert "DUP" in (tmp_path / "ambiguous.csv").read_text(encoding="utf-8")


def test_foreign_hesabfa_code_is_ambiguous() -> None:
    products = [SiteProductView(2, "NEW", False, False, False)]
    mappings = [MappingView(1, "OLD", "C1", "OLD")]
    remote = [{"Code": "C1", "ProductCode": "NEW", "Active": True}]
    rows = classify_catalog(products, mappings, remote)
    assert rows[0].action == "AMBIGUOUS"
    assert rows[0].reason == "hesabfa_code_owned_by_other_product"


def test_dry_run_client_blocks_item_save() -> None:
    inner = MagicMock()
    inner.get_items = AsyncMock(
        side_effect=[
            {"List": [{"Code": "1", "ProductCode": "A", "Active": True}], "TotalCount": 1},
            {"List": [], "TotalCount": 1},
        ]
    )
    client = DryRunHesabfaClient(inner)
    page = asyncio.run(load_remote_items(client, page_size=1))
    assert len(page.items) == 1
    assert page.reported_total == 1
    assert page.pages_fetched == 1
    assert client.remote_writes == 0

    async def forbidden() -> None:
        await client.save_item({"active": True})

    with pytest.raises(RuntimeError, match="item/save"):
        asyncio.run(forbidden())
    assert client.remote_writes == 1


def test_unknown_active_is_separate_from_duplicate_product_code() -> None:
    products = [
        SiteProductView(1, "UNK", True, True, True),
        SiteProductView(2, "DUP", False, False, False),
    ]
    remote = [
        {"Code": "C1", "ProductCode": "UNK", "Name": "no-flag"},
        {"Code": "A", "ProductCode": "DUP", "Active": True},
        {"Code": "B", "ProductCode": "DUP", "Active": False},
    ]
    rows = classify_catalog(products, [], remote)
    summary = summarize(rows, population_total=2)
    assert summary["REMOTE_ACTIVE_UNKNOWN"] == 1
    assert summary["AMBIGUOUS"] == 1
    assert summary["ERROR_BREAKDOWN"]["REMOTE_ACTIVE_UNKNOWN"]["samples"] == [
        {"site_product_id": 1, "sku": "UNK"}
    ]
    assert summary["AMBIGUITY_BREAKDOWN"]["DUPLICATE_REMOTE_PRODUCT_CODE"]["count"] == 1
    assert summary["COHORTS"]["SITE_ACTIVE__HF_MISSING"] == 0
    assert summary["COHORTS"]["SITE_INACTIVE__HF_MISSING"] == 0


def test_product_code_lookup_reads_past_the_first_page() -> None:
    import inspect

    from app.services.hesabfa.item_push import _find_hesabfa_item_by_product_code

    source = inspect.getsource(_find_hesabfa_item_by_product_code)
    assert "take=100" not in source
    assert "skip=0" not in source

    client = MagicMock()
    client.get_items = AsyncMock(
        side_effect=[
            {"List": [{"Code": "1", "ProductCode": "AAA"}], "TotalCount": 2},
            {"List": [{"Code": "2", "ProductCode": "TARGET"}], "TotalCount": 2},
        ]
    )

    async def run() -> dict:
        return await _find_hesabfa_item_by_product_code(client, "target", page_size=1)

    found = asyncio.run(run())
    assert found["Code"] == "2"
    assert client.get_items.await_count == 2


def test_incomplete_pagination_does_not_report_missing() -> None:
    from app.services.hesabfa.item_push import _find_hesabfa_item_by_product_code

    client = MagicMock()
    client.get_items = AsyncMock(
        return_value={"List": [{"Code": "1", "ProductCode": "AAA"}], "TotalCount": 5}
    )

    async def run() -> None:
        await _find_hesabfa_item_by_product_code(client, "TARGET")

    with pytest.raises(HesabfaError, match="pagination incomplete"):
        asyncio.run(run())


def test_duplicate_product_code_across_pages_raises() -> None:
    from app.services.hesabfa.item_push import _find_hesabfa_item_by_product_code

    client = MagicMock()
    client.get_items = AsyncMock(
        side_effect=[
            {"List": [{"Code": "1", "ProductCode": "SKU"}], "TotalCount": 2},
            {"List": [{"Code": "2", "ProductCode": "sku"}], "TotalCount": 2},
        ]
    )

    async def run() -> None:
        await _find_hesabfa_item_by_product_code(client, "SKU", page_size=1)

    with pytest.raises(HesabfaError, match="ambiguous"):
        asyncio.run(run())


def test_get_items_without_total_count_raises() -> None:
    from app.services.hesabfa.item_push import paginate_get_items

    client = MagicMock()
    client.get_items = AsyncMock(return_value={"List": []})

    async def run() -> None:
        await paginate_get_items(client, page_size=1)

    with pytest.raises(HesabfaError, match="TotalCount"):
        asyncio.run(run())


def test_pagination_repeated_page_fails_closed() -> None:
    from app.services.hesabfa.item_push import paginate_get_items

    client = MagicMock()
    client.get_items = AsyncMock(
        return_value={"List": [{"Code": "1", "ProductCode": "A"}], "TotalCount": 2}
    )

    async def run() -> None:
        await paginate_get_items(client, page_size=1)

    with pytest.raises(HesabfaError, match="repeated a page"):
        asyncio.run(run())


def test_pagination_duplicate_remote_code_fails_closed() -> None:
    from app.services.hesabfa.item_push import paginate_get_items

    client = MagicMock()
    client.get_items = AsyncMock(
        side_effect=[
            {"List": [{"Code": "1", "ProductCode": "A"}], "TotalCount": 2},
            {"List": [{"Code": "1", "ProductCode": "B"}], "TotalCount": 2},
        ]
    )

    async def run() -> None:
        await paginate_get_items(client, page_size=1)

    with pytest.raises(HesabfaError, match="duplicate remote Code"):
        asyncio.run(run())


def test_existing_code_cannot_build_zero_price_save() -> None:
    with pytest.raises(HesabfaError, match="existing Hesabfa code"):
        build_hesabfa_item_payload(_product(), hesabfa_code="HF-9")


def test_mapped_item_with_remote_price_is_not_saved(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hesabfa import item_push

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)
    mapping = SimpleNamespace(hesabfa_code="HF-9", sku="SKU-1", product_id=11)
    client = MagicMock()
    client.get_items = AsyncMock(
        return_value={
            "List": [
                {
                    "Code": "HF-9",
                    "ProductCode": "SKU-1",
                    "Active": False,
                    "BuyPrice": 90000,
                    "SellPrice": 150000,
                }
            ],
            "TotalCount": 1,
        }
    )
    client.save_item = AsyncMock()

    async def run() -> object:
        return await ensure_product_in_hesabfa(
            _FakeDB(mapping),
            _product(is_active=False, is_available=False, base_price=None),
            client=client,
        )

    result = asyncio.run(run())
    assert result.action == "existing_item_preserved"
    assert result.save_performed is False
    assert result.mapping is mapping
    client.save_item.assert_not_called()
    client.get_items.assert_not_called()


def test_discovered_priced_item_is_linked_without_save(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hesabfa import item_push

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)
    client = MagicMock()
    client.get_items = AsyncMock(
        return_value={
            "List": [
                {
                    "Code": "HF-9",
                    "ProductCode": "SKU-1",
                    "Active": False,
                    "SellPrice": 150000,
                    "BuyPrice": 0,
                }
            ],
            "TotalCount": 1,
        }
    )
    client.save_item = AsyncMock()

    async def run() -> object:
        return await ensure_product_in_hesabfa(
            _FakeDB(),
            _product(is_active=True, is_available=False, base_price=None),
            client=client,
        )

    result = asyncio.run(run())
    assert result.action == "existing_item_preserved"
    assert result.save_performed is False
    assert result.mapping.hesabfa_code == "HF-9"
    client.save_item.assert_not_called()


def test_unmapped_create_is_distinct_and_active(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hesabfa import item_push

    monkeypatch.setattr(item_push, "hesabfa_integration_active", lambda: True)
    client = MagicMock()
    client.get_items = AsyncMock(return_value={"List": [], "TotalCount": 0})
    client.save_item = AsyncMock(return_value={"Code": "HF-NEW", "ProductCode": "SKU-1"})

    async def run() -> object:
        return await ensure_product_in_hesabfa(
            _FakeDB(),
            _product(is_active=False, is_available=False, base_price=None),
            client=client,
        )

    result = asyncio.run(run())
    assert result.action == "created"
    assert result.save_performed is True
    assert result.mapping.hesabfa_code == "HF-NEW"
    client.save_item.assert_awaited_once()
    payload = client.save_item.await_args.args[0]
    assert payload["active"] is True
    assert "code" not in payload
    assert "Code" not in payload
    _assert_active_shell(payload, "SKU-1")


def test_mapped_inactive_remote_is_finding_only() -> None:
    products = [SiteProductView(1, "OFF", False, False, False)]
    mappings = [MappingView(1, "OFF", "C1", "OFF")]
    remote = [
        {
            "Code": "C1",
            "ProductCode": "OFF",
            "Active": False,
            "BuyPrice": 10,
            "SellPrice": 20,
        }
    ]
    rows = classify_catalog(products, mappings, remote)
    assert rows[0].action == "RECONCILIATION_REQUIRED"
    assert rows[0].reason == "mapped_inactive"
    assert rows[0].price_risk is True
    summary = summarize(rows, population_total=1)
    assert summary["WOULD_ACTIVATE"] == 0
    assert summary["RECONCILIATION_REQUIRED"] == 1
    assert summary["REMOTE_WRITES"] == 0


@pytest.mark.usefixtures("override_database")
def test_storefront_changes_do_not_save_mapped_item(
    monkeypatch: pytest.MonkeyPatch, valid_product_data: dict
) -> None:
    client = _mock_hesabfa(monkeypatch)

    async def run() -> int:
        async with TestingSessionLocal() as session:
            created = await ProductService.create_product_with_validation(
                session, ProductCreate(**valid_product_data)
            )
            assert client.save_item.await_count == 1
            updated = await ProductService.update_product_with_validation(
                session,
                created.id,
                ProductUpdate(is_active=False, is_available=False, base_price=None),
            )
            assert updated is not None
            assert updated.is_active is False
            assert updated.is_available is False
            assert updated.base_price is None
            hidden = await ProductService.set_availability_with_validation(
                session, created.id, False
            )
            assert hidden is not None
            assert await ProductService.delete_product(session, created.id) is True
            return client.save_item.await_count

    assert asyncio.run(run()) == 1


def test_dry_run_session_rejects_writes() -> None:
    inner = MagicMock()
    inner.execute = AsyncMock()
    guard = DryRunSession(inner)

    async def commit() -> None:
        await guard.commit()

    with pytest.raises(RuntimeError, match="commit"):
        asyncio.run(commit())
    assert guard.database_writes == 1


@pytest.mark.usefixtures("override_database")
def test_catalog_page_includes_inactive_and_skips_deleted(
    monkeypatch: pytest.MonkeyPatch, valid_product_data: dict
) -> None:
    _mock_hesabfa(monkeypatch)

    async def run() -> tuple[int, list[str]]:
        async with TestingSessionLocal() as session:
            kept = await ProductService.create_product_with_validation(
                session,
                ProductCreate(
                    **{**valid_product_data, "sku": "KEEP-OFF", "is_active": False}
                ),
            )
            removed = await ProductService.create_product_with_validation(
                session,
                ProductCreate(**{**valid_product_data, "sku": "REMOVED", "is_active": True}),
            )
            removed_id = removed.id
            kept_id = kept.id
            assert await ProductService.delete_product(session, removed_id) is True
            guard = DryRunSession(session)
            from app.services.hesabfa.activation_reconcile import fetch_catalog_page

            total, products, _mappings, _dupes = await fetch_catalog_page(
                guard, after_id=0, batch_size=50
            )
            skus = [row.sku for row in products if row.id in {kept_id, removed_id}]
            await session.rollback()
            assert guard.database_writes == 0
            return total, skus

    total, skus = asyncio.run(run())
    assert total >= 1
    assert skus == ["KEEP-OFF"]


@pytest.mark.usefixtures("override_database")
def test_read_only_transaction_rejects_update(
    monkeypatch: pytest.MonkeyPatch, valid_product_data: dict
) -> None:
    from app.services.hesabfa.activation_reconcile import (
        enforce_database_read_only,
        fetch_catalog_snapshot,
        release_database_read_only,
    )
    from sqlalchemy.exc import DBAPIError

    _mock_hesabfa(monkeypatch)

    async def run() -> dict:
        async with TestingSessionLocal() as session:
            kept = await ProductService.create_product_with_validation(
                session,
                ProductCreate(
                    **{
                        **valid_product_data,
                        "sku": "KEEP-OFF",
                        "is_active": False,
                        "base_price": None,
                    }
                ),
            )
            kept_sku = kept.sku
            removed = await ProductService.create_product_with_validation(
                session,
                ProductCreate(**{**valid_product_data, "sku": "REMOVED", "is_active": True}),
            )
            assert await ProductService.delete_product(session, removed.id) is True
            guard = DryRunSession(session)
            mode = await enforce_database_read_only(guard)
            try:
                snapshot = await fetch_catalog_snapshot(guard)
                # SQLite: OperationalError "readonly database".
                # PostgreSQL: DBAPIError ReadOnlySQLTransactionError.
                with pytest.raises(DBAPIError, match="read-?only"):
                    await session.execute(text("UPDATE products SET name = name"))
            finally:
                await release_database_read_only(guard, mode)
            if mode.startswith("sqlite"):
                flag = (await session.execute(text("PRAGMA query_only"))).scalar_one()
                assert int(flag) == 0
            assert guard.database_writes == 0
            skus = {row.sku for row in snapshot["products"]}
            return {
                "mode": mode,
                "baseline": snapshot["baseline"],
                "row_count": len(snapshot["products"]),
                "has_kept": kept_sku in skus,
                "has_removed": "REMOVED" in skus,
            }

    result = asyncio.run(run())
    assert result["mode"] in {
        "sqlite:query_only=1",
        "postgresql:transaction_read_only=on",
    }
    assert result["has_kept"] is True
    assert result["has_removed"] is False
    baseline = result["baseline"]
    assert baseline["TOTAL_PRODUCTS"] == baseline["TOTAL_NON_DELETED"] + baseline["TOTAL_SOFT_DELETED"]
    assert result["row_count"] == baseline["TOTAL_NON_DELETED"]
    assert baseline["TOTAL_SOFT_DELETED"] >= 1
    assert baseline["NON_DELETED_INACTIVE"] >= 1
    assert (
        baseline["NON_DELETED_ACTIVE"] + baseline["NON_DELETED_INACTIVE"]
        == baseline["TOTAL_NON_DELETED"]
    )


def test_read_only_enforcement_fails_closed_for_unknown_dialect() -> None:
    from app.services.hesabfa.activation_reconcile import enforce_database_read_only

    class Foreign:
        bind = SimpleNamespace(dialect=SimpleNamespace(name="mysql"))

        async def execute(self, _statement: object, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("unknown dialect must not run SQL")

    with pytest.raises(RuntimeError, match="no database-enforced read-only"):
        asyncio.run(enforce_database_read_only(Foreign()))


def test_postgres_read_only_requires_show_on() -> None:
    from app.services.hesabfa.activation_reconcile import enforce_database_read_only

    class Result:
        def __init__(self, value: str) -> None:
            self.value = value

        def scalar_one(self) -> str:
            return self.value

    class Postgres:
        def __init__(self, shown: str) -> None:
            self.shown = shown
            self.sql: list[str] = []
            self.bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        async def execute(self, statement: object, *_args: object, **_kwargs: object) -> Result:
            self.sql.append(str(statement))
            return Result(self.shown)

    accepted = Postgres("on")
    mode = asyncio.run(enforce_database_read_only(accepted))
    assert mode == "postgresql:transaction_read_only=on"
    assert accepted.sql == ["SET TRANSACTION READ ONLY", "SHOW transaction_read_only"]

    refused = Postgres("off")
    with pytest.raises(RuntimeError, match="transaction_read_only"):
        asyncio.run(enforce_database_read_only(refused))


def _reconcile_cli():
    import sys

    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import hesabfa_product_activation_reconcile as reconcile

    return reconcile


def test_cli_dry_run_is_read_only_and_resumable(tmp_path: Path) -> None:
    reconcile = _reconcile_cli()

    products = tmp_path / "products.json"
    remote = tmp_path / "remote.json"
    mappings = tmp_path / "mappings.json"
    products.write_text(
        json.dumps(
            [
                {
                    "id": index,
                    "sku": f"SKU-{index}",
                    "is_active": False,
                    "is_available": False,
                    "price_present": False,
                }
                for index in (1, 2, 3)
            ]
        ),
        encoding="utf-8",
    )
    remote.write_text("[]", encoding="utf-8")
    mappings.write_text("[]", encoding="utf-8")
    output = tmp_path / "out"
    code = reconcile.main(
        [
            "--dry-run",
            "--batch-size",
            "1",
            "--max-batches",
            "1",
            "--products-snapshot",
            str(products),
            "--mappings-snapshot",
            str(mappings),
            "--remote-snapshot",
            str(remote),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    first = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert first["SCANNED"] == 1
    assert first["WOULD_CREATE"] == 1
    assert first["REMOTE_WRITES"] == 0
    assert first["DATABASE_WRITES"] == 0
    assert first["DRY_RUN"] is True
    resumed = reconcile.main(
        [
            "--resume",
            "--batch-size",
            "1",
            "--max-batches",
            "10",
            "--products-snapshot",
            str(products),
            "--mappings-snapshot",
            str(mappings),
            "--remote-snapshot",
            str(remote),
            "--output",
            str(output),
        ]
    )
    assert resumed == 0
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["TOTAL_SITE_NON_DELETED"] == 3
    assert summary["SCANNED"] == 3
    assert summary["WOULD_CREATE"] == 3
    assert summary["REMOTE_WRITES"] == 0
    assert summary["DATABASE_WRITES"] == 0
    assert summary["SCAN_COMPLETE"] is True


def test_cli_apply_is_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reconcile = _reconcile_cli()

    output = tmp_path / "blocked"
    assert reconcile.main(["--apply", "--output", str(output)]) == 2
    monkeypatch.setenv("KARZAR_ALLOW_PRODUCTION_WRITE", "1")
    monkeypatch.setenv("KARZAR_INGESTION_CATEGORY", "B")
    assert (
        reconcile.main(
            ["--apply", "--confirm-production-write", "--output", str(output)]
        )
        == 3
    )
    assert not (output / "summary.json").exists()


def test_cli_refuses_live_scan_without_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "HESABFA_ENABLED", False)
    reconcile = _reconcile_cli()
    with pytest.raises(SystemExit, match="credentials"):
        reconcile.main(["--output", str(tmp_path / "live")])
    assert not (tmp_path / "live" / "summary.json").exists()


def test_cli_rejects_snapshot_without_remote(tmp_path: Path) -> None:
    reconcile = _reconcile_cli()

    products = tmp_path / "products.json"
    products.write_text("[]", encoding="utf-8")
    assert (
        reconcile.main(
            [
                "--products-snapshot",
                str(products),
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )


def test_raw_update_sql_is_rejected_by_dry_run_guard() -> None:
    inner = MagicMock()
    inner.execute = AsyncMock()
    guard = DryRunSession(inner)

    async def run() -> None:
        await guard.execute(text("UPDATE products SET is_active = false"))

    with pytest.raises(RuntimeError, match="non-SELECT"):
        asyncio.run(run())
    inner.execute.assert_not_called()
    assert guard.database_writes == 1
