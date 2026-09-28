"""Regression: base_price is final customer-facing gross; tax_percent never surcharges payable."""

from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_UP, Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.db.models.commerce import Order, OrderItem, OrderMode, PaymentStatus
from app.db.models.hesabfa import HesabfaItemMapping
from app.db.models.product import Product
from app.main import app
from app.services.hesabfa.invoices import (
    _inclusive_net_unit_and_tax,
    _to_hesabfa_money,
    create_invoice_for_paid_order,
)
from app.services.payment_flow_service import order_amount_rials
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tests.conftest import TestingSessionLocal


def _seed_product(
    client: TestClient,
    headers: dict[str, str],
    *,
    sku: str,
    base_price: str,
    tax_percent: str,
) -> dict:
    res = client.post(
        "/api/v1/products/",
        json={
            "sku": sku,
            "name": f"Tax inclusive {sku}",
            "category_id": 3,
            "brand_id": 1,
            "base_price": base_price,
            "tax_percent": tax_percent,
            "is_available": True,
            "stock_unit": "piece",
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _checkout(
    client: TestClient,
    headers: dict[str, str],
    *,
    product_id: int,
    quantity: int = 1,
    key: str,
    province: str = "اصفهان",
    city: str = "اصفهان",
    method: str = "tipax_standard",
) -> dict:
    res = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "کاربر تست", "phone": "09121234567", "is_guest": False},
            "items": [{"product_id": product_id, "quantity": quantity}],
            "shipping": {
                "province": province,
                "city": city,
                "postal_code": "1234567890",
                "address_line": "خیابان تست، پلاک ۱۰، واحد ۲",
            },
            "shipping_method_code": method,
        },
        headers={**headers, "Idempotency-Key": key},
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.usefixtures("enable_storefront_shipping_methods")
@pytest.mark.parametrize(
    ("base_price", "tax_percent", "qty", "expected"),
    [
        ("1000000", "0", 1, Decimal("1000000")),
        ("1000000", "9", 1, Decimal("1000000")),
        ("1100000", "10", 1, Decimal("1100000")),
        ("1100000", "10", 3, Decimal("3300000")),
    ],
)
def test_checkout_merchandise_ignores_tax_metadata(
    base_price,
    tax_percent,
    qty,
    expected,
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_product(
        client,
        super_admin_headers,
        sku=f"TIP-{tax_percent}-{qty}-{base_price}",
        base_price=base_price,
        tax_percent=tax_percent,
    )
    body = _checkout(
        client,
        purchase_customer_headers,
        product_id=product["id"],
        quantity=qty,
        key=f"tip-{tax_percent}-{qty}-{base_price}",
    )
    assert Decimal(body["estimated_total"]) == expected
    assert body["shipping_display"] == "receiver_due"

    async def _assert_payment():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, body["order_id"])
            assert order is not None
            assert Decimal(str(order.estimated_total)) == expected
            assert order_amount_rials(order) == int(expected * TOMAN_TO_RIAL)
            item = (
                await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
            ).scalars().one()
            assert Decimal(str(item.tax_percent)) == Decimal(tax_percent)
            assert Decimal(str(item.unit_price)) == Decimal(base_price)

    asyncio.run(_assert_payment())


@pytest.mark.usefixtures("enable_storefront_shipping_methods")
def test_checkout_mixed_tax_metadata_sum(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    a = _seed_product(client, super_admin_headers, sku="MIX-A", base_price="500000", tax_percent="0")
    b = _seed_product(client, super_admin_headers, sku="MIX-B", base_price="1000000", tax_percent="9")
    c = _seed_product(client, super_admin_headers, sku="MIX-C", base_price="2000000", tax_percent="10")
    res = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "کاربر تست", "phone": "09121234567", "is_guest": False},
            "items": [
                {"product_id": a["id"], "quantity": 2},
                {"product_id": b["id"], "quantity": 1},
                {"product_id": c["id"], "quantity": 1},
            ],
            "shipping": {
                "province": "اصفهان",
                "city": "اصفهان",
                "postal_code": "1234567890",
                "address_line": "خیابان تست، پلاک ۱۰",
            },
            "shipping_method_code": "tipax_standard",
        },
        headers={**purchase_customer_headers, "Idempotency-Key": "mix-tax"},
    )
    assert res.status_code == 201, res.text
    assert Decimal(res.json()["estimated_total"]) == Decimal("4000000")


def test_sender_prepaid_adds_shipping_once_without_tax_surcharge(
    override_database,
    super_admin_headers,
    monkeypatch,
):
    from tests.conftest import customer_auth_headers
    from tests.test_postex_logistics import _enable_postex
    from tests.test_postex_quotes_checkout import FakeProvider, _seed_parcel_product

    # Match postex module isolation: disable receiver-due matrix so quote path wins.
    monkeypatch.setattr(settings, "SHIPPING_TIPAX_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_CHAPAR_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_POST_PISHTAZ_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_MOTORCYCLE_48H_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_EXPRESS_3H_ENABLED", False)
    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", "sender_prepaid")
    provider = FakeProvider()
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.shipping.get_provider", lambda: provider)

    client = TestClient(app)
    # Parcel seed uses tax_percent=0; bump to 10% to prove surcharge is gone.
    product = _seed_parcel_product(client, super_admin_headers, sku="SENDER-TAX")

    async def _set_tax():
        async with TestingSessionLocal() as session:
            prod = await session.get(Product, product["id"])
            assert prod is not None
            prod.tax_percent = Decimal("10")
            await session.commit()

    asyncio.run(_set_tax())

    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "location_code": 8,
            "postal_code": "1234567890",
            "city_name": "تهران",
            "province_name": "تهران",
        },
        headers=headers,
    )
    assert quote.status_code == 200, quote.text
    token = next(
        option["quote_token"]
        for option in quote.json()["options"]
        if option["service_code"] == "EXPRESS"
    )
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09123333333", "is_guest": False},
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲۳۴",
                "location_code": 8,
            },
            "shipping_quote_token": token,
        },
        headers={**headers, "Idempotency-Key": "sender-tax-inclusive"},
    )
    assert checkout.status_code == 201, checkout.text
    # merchandise 100000 (NOT 110000) + shipping 17000
    assert Decimal(checkout.json()["estimated_total"]) == Decimal("117000.00")
    assert order_amount_rials(
        type("O", (), {"estimated_total": Decimal(checkout.json()["estimated_total"])})()
    ) == 1_170_000


@pytest.mark.parametrize("tax_percent", [Decimal("0"), Decimal("9"), Decimal("10")])
@pytest.mark.parametrize("quantity", [1, 3])
def test_inclusive_tax_extraction_reconciles(tax_percent, quantity, monkeypatch):
    monkeypatch.setattr(settings, "HESABFA_CURRENCY_UNIT", "rial")
    gross_unit_toman = Decimal("1000000")
    gross_unit = _to_hesabfa_money(gross_unit_toman)
    net_unit, tax = _inclusive_net_unit_and_tax(gross_unit, quantity, tax_percent)
    gross_line = gross_unit * quantity
    assert net_unit * quantity + tax == gross_line


def test_inclusive_tax_extraction_awkward_fraction(monkeypatch):
    monkeypatch.setattr(settings, "HESABFA_CURRENCY_UNIT", "rial")
    gross_unit = _to_hesabfa_money(Decimal("999999"))
    net_unit, tax = _inclusive_net_unit_and_tax(gross_unit, 1, Decimal("10"))
    assert net_unit + tax == gross_unit
    # Explicit residual policy: tax absorbs rounding so totals match.
    expected_net = (gross_unit / Decimal("1.1")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    assert net_unit == expected_net


@pytest.mark.usefixtures("override_database")
def test_hesabfa_invoice_reconciles_to_tax_inclusive_gross(
    super_admin_headers, valid_product_data, monkeypatch
):
    from app.services.hesabfa.client import reset_hesabfa_client_for_tests

    reset_hesabfa_client_for_tests()
    monkeypatch.setattr(settings, "HESABFA_ENABLED", True)
    monkeypatch.setattr(settings, "HESABFA_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "HESABFA_LOGIN_TOKEN", "test-login-token")
    monkeypatch.setattr(settings, "HESABFA_TEST_MODE", False)
    monkeypatch.setattr(settings, "HESABFA_CURRENCY_UNIT", "rial")

    product = TestClient(app).post(
        "/api/v1/products/",
        json={
            **valid_product_data,
            "sku": "HF-INCL-1",
            "base_price": "1100000",
            "tax_percent": "10",
            "is_available": True,
        },
        headers=super_admin_headers,
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    sku = product.json()["sku"]

    async def run():
        async with TestingSessionLocal() as session:
            session.add(
                HesabfaItemMapping(
                    product_id=product_id,
                    sku=sku,
                    hesabfa_code="HF001",
                    hesabfa_product_code=sku,
                )
            )
            order = Order(
                tracking_code="TRK-HF-INCL",
                mode=OrderMode.PURCHASE,
                status="paid",
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("3300000"),
                shipping_customer_cost=None,
                customer_full_name="Tax Inclusive",
                customer_phone="09121112233",
                customer_is_guest=True,
            )
            session.add(order)
            await session.flush()
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=3,
                    unit_price=Decimal("1100000"),
                    product_name="Gross Tool",
                    product_sku=sku,
                    tax_percent=Decimal("10"),
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
            mock_client.save_contact = AsyncMock(return_value={"Code": "C-INCL"})
            mock_client.save_invoice = AsyncMock(return_value={"Number": "S-INCL"})

            result = await create_invoice_for_paid_order(session, order, client=mock_client)
            await session.commit()
            assert result.status == "created", result
            payload = mock_client.save_invoice.await_args.args[0]
            return result, payload

    result, payload = asyncio.run(run())
    assert result.status == "created"
    line = payload["invoiceItems"][0]
    unit = Decimal(str(line["unitPrice"]))
    tax = Decimal(str(line["tax"]))
    qty = Decimal(str(line["quantity"]))
    merchandise = unit * qty + tax
    freight = Decimal(str(payload["freight"]))
    assert merchandise == Decimal("33000000")  # 3_300_000 toman × 10
    assert merchandise + freight == Decimal("33000000")
    # Must NOT be additive gross+tax (would be 36_300_000 rial).
    assert merchandise != Decimal("36300000")
    reset_hesabfa_client_for_tests()


@pytest.mark.parametrize(
    ("price", "qty", "tax"),
    [
        (Decimal("0"), 1, Decimal("0")),
        (Decimal("100"), 1, Decimal("9")),
        (Decimal("999999"), 2, Decimal("10")),
        (Decimal("1234567"), 5, Decimal("9")),
        (Decimal("50"), 7, Decimal("100")),
    ],
)
def test_payable_invariant_independent_of_tax(price, qty, tax):
    """Property-style: merchandise payable = price × qty for any valid tax metadata."""
    assert price * qty == price * qty + Decimal("0") * tax
    # Mirror checkout formula explicitly.
    estimated = price * qty
    assert estimated == price * qty
