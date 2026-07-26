"""Unit tests for Hesabfa client, mapping, stock pull, and invoice hook."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, OrderItem, OrderMode, PaymentStatus
from app.db.models.hesabfa import HesabfaInvoiceRecord, HesabfaItemMapping
from app.db.models.product import Product
from app.main import app
from app.services.hesabfa.client import HesabfaClient, reset_hesabfa_client_for_tests
from app.services.hesabfa.exceptions import HesabfaApiError, HesabfaNotConfiguredError
from app.services.hesabfa.invoices import create_invoice_for_paid_order
from app.services.hesabfa.mapping import sync_item_mappings_by_sku
from app.services.hesabfa.stock_sync import pull_stock_from_hesabfa
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tests.conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_hesabfa(monkeypatch):
    reset_hesabfa_client_for_tests()
    monkeypatch.setattr(settings, "HESABFA_ENABLED", True)
    monkeypatch.setattr(settings, "HESABFA_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "HESABFA_LOGIN_TOKEN", "test-login-token")
    monkeypatch.setattr(settings, "HESABFA_TEST_MODE", False)
    monkeypatch.setattr(settings, "HESABFA_CURRENCY_UNIT", "rial")
    yield
    reset_hesabfa_client_for_tests()


def test_client_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "HESABFA_API_KEY", None)
    monkeypatch.setattr(settings, "HESABFA_LOGIN_TOKEN", None)
    hf = HesabfaClient(api_key=None, login_token=None, user_id=None, password=None)
    assert hf.is_configured() is False
    with pytest.raises(HesabfaNotConfiguredError):
        hf._auth_payload()


def test_client_auth_payload_uses_login_token():
    hf = HesabfaClient(api_key="k", login_token="t")
    payload = hf._auth_payload()
    assert payload == {"apiKey": "k", "loginToken": "t"}


def test_client_raises_on_success_false(monkeypatch):
    hf = HesabfaClient(api_key="k", login_token="t")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"Success": False, "ErrorCode": 101, "ErrorMessage": "bad"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None):
            return FakeResponse()

    monkeypatch.setattr("app.services.hesabfa.client.httpx.AsyncClient", FakeAsyncClient)

    async def run():
        with pytest.raises(HesabfaApiError) as exc:
            await hf.get_items()
        assert exc.value.error_code == 101

    asyncio.run(run())


def _create_product(super_admin_headers, valid_product_data) -> dict:
    response = client.post(
        "/api/v1/products/",
        json=valid_product_data,
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sync_item_mappings_by_sku(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data)
    mock_client = MagicMock()
    mock_client.get_items = AsyncMock(
        return_value={
            "TotalCount": 1,
            "List": [
                {
                    "Code": "000101",
                    "ProductCode": product["sku"],
                    "Name": product["name"],
                    "Stock": 12,
                }
            ],
        }
    )

    async def run():
        async with TestingSessionLocal() as session:
            result = await sync_item_mappings_by_sku(session, client=mock_client)
            await session.commit()
            assert result.matched == 1
            assert result.created == 1
            result2 = await sync_item_mappings_by_sku(session, client=mock_client)
            await session.commit()
            assert result2.created == 0
            assert result2.updated == 1

    asyncio.run(run())


def test_pull_stock_is_disabled_noop(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data)
    product_id = product["id"]
    sku = product["sku"]

    async def setup_and_pull():
        async with TestingSessionLocal() as session:
            session.add(
                HesabfaItemMapping(
                    product_id=product_id,
                    sku=sku,
                    hesabfa_code="000101",
                    hesabfa_product_code=sku,
                )
            )
            await session.commit()

            mock_client = MagicMock()
            mock_client.get_quantity = AsyncMock(
                return_value=[{"Code": "000101", "Quantity": 42, "ProductCode": sku}]
            )
            result = await pull_stock_from_hesabfa(session, client=mock_client)
            await session.commit()
            row = (
                await session.execute(select(Product).where(Product.id == product_id))
            ).scalars().one()
            return result, bool(row.is_available), Decimal(str(row.stock_quantity))

    result, available, qty = asyncio.run(setup_and_pull())
    assert result.disabled is True
    assert result.updated == 0
    assert available is True
    assert qty == Decimal("0")


def test_ensure_product_in_hesabfa_creates_mapping(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data)
    product_id = product["id"]

    async def run():
        async with TestingSessionLocal() as session:
            prod = (
                await session.execute(select(Product).where(Product.id == product_id))
            ).scalars().one()
            mock_client = MagicMock()
            mock_client.get_items = AsyncMock(return_value={"List": [], "TotalCount": 0})
            mock_client.save_item = AsyncMock(
                return_value={"Code": "HF-9", "ProductCode": prod.sku, "Stock": 0}
            )
            from app.services.hesabfa.item_push import ensure_product_in_hesabfa

            mapping = await ensure_product_in_hesabfa(session, prod, client=mock_client)
            await session.commit()
            return mapping, mock_client

    mapping, mock_client = asyncio.run(run())
    assert mapping is not None
    assert mapping.hesabfa_code == "HF-9"
    mock_client.save_item.assert_awaited_once()
    payload = mock_client.save_item.await_args.args[0]
    assert payload["productCode"] == product["sku"]
    assert "Stock" not in payload


def test_invoice_hook_skips_when_unpaid():
    order = SimpleNamespace(
        id=999001,
        mode=OrderMode.PURCHASE,
        payment_status=PaymentStatus.UNPAID.value,
        customer_phone="09120001122",
        customer_full_name="Test",
        user_id=None,
        company_name=None,
        tracking_code="TRK-TEST",
        items=[],
    )

    async def run():
        async with TestingSessionLocal() as session:
            return await create_invoice_for_paid_order(session, order)  # type: ignore[arg-type]

    result = asyncio.run(run())
    assert result.status == "skipped"
    assert result.message == "payment_not_verified"


def test_invoice_hook_skips_in_test_mode(monkeypatch):
    monkeypatch.setattr(settings, "HESABFA_TEST_MODE", True)
    order = SimpleNamespace(
        id=999002,
        mode=OrderMode.PURCHASE,
        payment_status=PaymentStatus.PAID.value,
        customer_phone="09120001122",
        customer_full_name="Test",
        user_id=None,
        company_name=None,
        tracking_code="TRK-TEST2",
        items=[],
    )

    async def run():
        async with TestingSessionLocal() as session:
            return await create_invoice_for_paid_order(session, order)  # type: ignore[arg-type]

    result = asyncio.run(run())
    assert result.status == "skipped"
    assert result.message == "test_mode"


def test_invoice_creates_when_mapped(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data)
    product_id = product["id"]
    sku = product["sku"]

    async def run():
        async with TestingSessionLocal() as session:
            prod = (
                await session.execute(select(Product).where(Product.id == product_id))
            ).scalars().one()
            prod.base_price = Decimal("100000")
            prod.tax_percent = Decimal("9")
            session.add(
                HesabfaItemMapping(
                    product_id=product_id,
                    sku=sku,
                    hesabfa_code="000101",
                    hesabfa_product_code=sku,
                )
            )
            order = Order(
                tracking_code="TRK-HF-1",
                mode=OrderMode.PURCHASE,
                status="paid",
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("200000"),
                customer_full_name="Ali Test",
                customer_phone="09121112233",
                customer_is_guest=True,
            )
            session.add(order)
            await session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=2,
                    unit_price=Decimal("100000"),
                    product_name="Test Insert",
                    product_sku=sku,
                    tax_percent=Decimal("0"),
                )
            )
            await session.commit()

            order = (
                await session.execute(
                    select(Order)
                    .where(Order.id == order.id)
                    .options(selectinload(Order.items))
                )
            ).scalars().one()

            mock_client = MagicMock()
            mock_client.get_contacts = AsyncMock(return_value={"List": [], "TotalCount": 0})
            mock_client.save_contact = AsyncMock(return_value={"Code": "C001"})
            mock_client.save_invoice = AsyncMock(return_value={"Number": "S-100"})

            result = await create_invoice_for_paid_order(session, order, client=mock_client)
            await session.commit()

            record = (
                await session.execute(
                    select(HesabfaInvoiceRecord).where(
                        HesabfaInvoiceRecord.order_id == order.id
                    )
                )
            ).scalars().one()
            return result, record.status, mock_client

    result, record_status, mock_client = asyncio.run(run())
    assert result.status == "created"
    assert result.hesabfa_number == "S-100"
    assert record_status == "created"
    mock_client.save_invoice.assert_awaited_once()
    payload = mock_client.save_invoice.await_args.args[0]
    assert payload["contactCode"] == "C001"
    assert payload["invoiceItems"][0]["itemCode"] == "000101"
    assert payload["invoiceItems"][0]["unitPrice"] == 1_000_000.0


def test_hesabfa_status_endpoint(super_admin_headers):
    response = client.get("/api/v1/hesabfa/status", headers=super_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["configured"] is True
    assert "test_mode" in body


def test_sales_summary_website_only_never_returns_hesabfa(
    super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "HESABFA_ENABLED", True)
    monkeypatch.setattr(settings, "HESABFA_ADMIN_READS_ENABLED", False)
    response = client.get("/api/v1/hesabfa/sales-summary", headers=super_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "website_paid_total_toman" in body
    assert body["hesabfa_available"] is False
    assert body["hesabfa_sales_total"] is None
    assert body["hesabfa_sales_total_toman"] is None
    assert body["hesabfa_invoice_count"] is None
    assert body["hesabfa_error"] == "hesabfa_admin_reads_disabled"


def test_hesabfa_status_reports_admin_reads_disabled(super_admin_headers):
    response = client.get("/api/v1/hesabfa/status", headers=super_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["stock_pull_enabled"] is False
    assert body["admin_reads_enabled"] is False
