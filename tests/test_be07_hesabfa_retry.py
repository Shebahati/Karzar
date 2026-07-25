"""BE-07: Hesabfa invoice failure records next_attempt_at and retry worker re-pushes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models.commerce import Order, OrderItem, OrderMode, PaymentStatus
from app.db.models.hesabfa import HesabfaInvoiceRecord, HesabfaItemMapping
from app.main import app
from app.services.hesabfa.client import reset_hesabfa_client_for_tests
from app.services.hesabfa.invoice_retry import retry_failed_hesabfa_invoices
from app.services.hesabfa.invoices import create_invoice_for_paid_order
from tests.conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture
def _hesabfa_live(monkeypatch):
    reset_hesabfa_client_for_tests()
    monkeypatch.setattr(settings, "HESABFA_ENABLED", True)
    monkeypatch.setattr(settings, "HESABFA_TEST_MODE", False)
    monkeypatch.setattr(settings, "HESABFA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "HESABFA_LOGIN_TOKEN", "test-token")
    yield
    reset_hesabfa_client_for_tests()


def _create_product(super_admin_headers, valid_product_data) -> dict:
    response = client.post(
        "/api/v1/products/", json=valid_product_data, headers=super_admin_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invoice_failure_schedules_retry(
    _hesabfa_live, super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data)
    product_id = product["id"]
    sku = product["sku"]

    mock_client = MagicMock()
    mock_client.is_configured = MagicMock(return_value=True)
    mock_client.get_contacts = AsyncMock(return_value={"List": [], "TotalCount": 0})
    mock_client.save_contact = AsyncMock(return_value={"Code": "C001"})
    mock_client.save_invoice = AsyncMock(side_effect=RuntimeError("hesabfa down"))

    async def run():
        async with TestingSessionLocal() as session:
            session.add(
                HesabfaItemMapping(
                    product_id=product_id,
                    sku=sku,
                    hesabfa_code="000101",
                    hesabfa_product_code=sku,
                )
            )
            order = Order(
                tracking_code="TRK-BE07-1",
                mode=OrderMode.PURCHASE,
                status="paid",
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("100000"),
                customer_full_name="Ali Test",
                customer_phone="09121110001",
                customer_is_guest=True,
            )
            session.add(order)
            await session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=1,
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
            result = await create_invoice_for_paid_order(session, order, client=mock_client)
            await session.commit()
            record = (
                await session.execute(
                    select(HesabfaInvoiceRecord).where(
                        HesabfaInvoiceRecord.order_id == order.id
                    )
                )
            ).scalars().one()
            return result.status, record.status, record.attempt_count, record.next_attempt_at

    status, record_status, attempts, next_at = asyncio.run(run())
    assert status == "failed"
    assert record_status == "failed"
    assert attempts >= 1
    assert next_at is not None


def test_retry_worker_creates_invoice_after_failure(
    _hesabfa_live, super_admin_headers, valid_product_data, monkeypatch
):
    product = _create_product(super_admin_headers, valid_product_data)
    product_id = product["id"]
    sku = product["sku"]

    mock_client = MagicMock()
    mock_client.is_configured = MagicMock(return_value=True)
    mock_client.get_contacts = AsyncMock(return_value={"List": [], "TotalCount": 0})
    mock_client.save_contact = AsyncMock(return_value={"Code": "C001"})
    mock_client.save_invoice = AsyncMock(
        side_effect=[RuntimeError("temporary"), {"Number": "S-777"}]
    )
    monkeypatch.setattr(
        "app.services.hesabfa.invoices.get_hesabfa_client",
        lambda: mock_client,
    )

    async def run():
        async with TestingSessionLocal() as session:
            session.add(
                HesabfaItemMapping(
                    product_id=product_id,
                    sku=sku,
                    hesabfa_code="000042",
                    hesabfa_product_code=sku,
                )
            )
            order = Order(
                tracking_code="TRK-BE07-2",
                mode=OrderMode.PURCHASE,
                status="paid",
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("50000"),
                customer_full_name="Ali Test",
                customer_phone="09121110002",
                customer_is_guest=True,
            )
            session.add(order)
            await session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=1,
                    unit_price=Decimal("50000"),
                    product_name=product.get("name") or "Bit",
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

            first = await create_invoice_for_paid_order(session, order, client=mock_client)
            assert first.status == "failed"
            record = (
                await session.execute(
                    select(HesabfaInvoiceRecord).where(
                        HesabfaInvoiceRecord.order_id == order.id
                    )
                )
            ).scalars().one()
            record.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()

            created = await retry_failed_hesabfa_invoices(session, limit=10)
            await session.commit()
            refreshed = (
                await session.execute(
                    select(HesabfaInvoiceRecord).where(
                        HesabfaInvoiceRecord.order_id == order.id
                    )
                )
            ).scalars().one()
            return created, refreshed.status, refreshed.hesabfa_number

    created, status, number = asyncio.run(run())
    assert created >= 1
    assert status == "created"
    assert number == "S-777"
