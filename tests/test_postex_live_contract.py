"""Regression: live Postex quote contract (2026-09-10 Owner-authorized read-only).

No live Postex calls. Fixture is sanitized (no PII / no API key).
"""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import pytest
from app.core.config import settings
from app.services.logistics.exceptions import (
    ProviderCurrencyError,
    ShippingUnavailableError,
)
from app.services.logistics.models import Destination, OriginAddress, PackageSpec
from app.services.logistics.money import IRR, irr_to_toman, provider_total_toman
from app.services.logistics.postex.couriers import (
    MINIMAL_VALUE_ADDED_SERVICE,
    parse_quote_services_config,
    parse_shipping_methods,
)
from app.services.logistics.postex.mapper import parse_quotes, resolve_quote_currency
from app.services.logistics.postex.provider import PostexProvider

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/postex/live-quote-2026-09-10.json"


def _live_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_live_fixture_parses_money_and_display_fields():
    payload = _live_fixture()
    result = parse_quotes(payload)
    assert len(result.options) == 1
    opt = result.options[0]
    assert opt.provider_currency == IRR
    assert opt.provider_amount == Decimal("1298000")
    assert opt.pickup_amount_toman == irr_to_toman(1200000)
    assert opt.pickup_amount_toman == Decimal("120000.00")
    assert opt.provider_amount_toman == Decimal("129800.00")
    assert opt.customer_amount_toman == Decimal("249800.00")
    assert opt.customer_amount_toman == irr_to_toman(2498000)
    assert opt.provider_total_toman == Decimal("249800.00")
    assert opt.provider_total_toman != opt.provider_amount_toman
    assert provider_total_toman(
        provider_amount_toman=opt.provider_amount_toman,
        pickup_amount_toman=opt.pickup_amount_toman,
    ) == Decimal("249800.00")
    # pickup + service == total_cost (no VAT double-count)
    assert Decimal("1200000") + opt.provider_amount == Decimal("2498000")
    assert opt.service_name == "پست پیشتاز"
    assert opt.carrier_code == "IR_POST"
    assert opt.service_code == "EXPRESS"
    assert opt.eta_text == "از 84 تا 168 ساعت کاری"


def test_provider_total_zero_pickup_equals_service_component():
    total = provider_total_toman(
        provider_amount_toman=Decimal("129800.00"),
        pickup_amount_toman=None,
    )
    assert total == Decimal("129800.00")
    assert total == provider_total_toman(
        provider_amount_toman=Decimal("129800.00"),
        pickup_amount_toman=Decimal("0"),
    )


def test_currency_read_from_response():
    assert resolve_quote_currency(_live_fixture()) == IRR


def test_absent_currency_falls_back_to_irr_explicitly():
    payload = {
        "pickup_price": 1000,
        "shipping_prices": [
            {"service_price": [{"serviceType": "EXPRESS", "totalPrice": 2000}]}
        ],
    }
    result = parse_quotes(payload)
    assert result.options[0].provider_currency == IRR


def test_non_irr_currency_fails_closed():
    payload = _live_fixture()
    payload["currency"] = "USD"
    with pytest.raises(ProviderCurrencyError, match="USD"):
        parse_quotes(payload)


def test_total_cost_inconsistency_fails_closed():
    payload = _live_fixture()
    payload["total_cost"] = 1
    with pytest.raises(ShippingUnavailableError, match="total_cost"):
        parse_quotes(payload)


def test_nested_vat_not_added_to_customer_total():
    """Live vat=100000 sits inside totalPrice; must not be added again."""
    payload = _live_fixture()
    opt = parse_quotes(payload).options[0]
    assert opt.customer_amount_toman == Decimal("249800.00")
    assert opt.customer_amount_toman != irr_to_toman(2498000 + 100000)


def test_parse_shipping_methods_from_live_shape():
    payload = {
        "isSuccess": True,
        "data": [
            {
                "courierServiceId": 18,
                "courierServiceName": "پست پیشتاز",
                "courierCode": "IR_POST",
                "courierServiceCode": "EXPRESS",
                "isActive": True,
            },
            {
                "courierServiceId": 10,
                "courierServiceName": "چاپار",
                "courierCode": "CHAPAR",
                "courierServiceCode": "CHAPAR",
                "isActive": True,
            },
        ],
    }
    methods = parse_shipping_methods(payload)
    assert {(m.courier_code, m.service_type) for m in methods} == {
        ("IR_POST", "EXPRESS"),
        ("CHAPAR", "CHAPAR"),
    }


def test_quote_services_config_default_is_live_verified():
    services = parse_quote_services_config("IR_POST:EXPRESS")
    assert len(services) == 1
    assert services[0].as_quote_courier() == {
        "courier_code": "IR_POST",
        "service_type": "EXPRESS",
    }


def test_provider_quote_sends_courier_and_value_added_service(monkeypatch):
    captured: dict = {"bodies": [], "paths": []}

    class FakeClient:
        async def get_json(self, path, *, operation=None, params=None):
            assert path == "/shipping-methods"
            return {
                "isSuccess": True,
                "data": [
                    {
                        "courierServiceId": 18,
                        "courierServiceName": "پست پیشتاز",
                        "courierCode": "IR_POST",
                        "courierServiceCode": "EXPRESS",
                        "isActive": True,
                    }
                ],
            }

        async def post_json(self, path, body, *, operation=None, mutating=False):
            captured["paths"].append(path)
            captured["bodies"].append(body)
            assert mutating is False
            return _live_fixture()

    monkeypatch.setattr(settings, "POSTEX_QUOTE_SERVICES", "IR_POST:EXPRESS")
    provider = PostexProvider(client=FakeClient())  # type: ignore[arg-type]
    origin = OriginAddress(
        city_code=1,
        city_name="تهران",
        postal_code="1234567890",
        address="test",
        first_name="a",
        last_name="b",
        mobile="09120000000",
    )
    destination = Destination(location_code=175, city_name="اصفهان")
    package = PackageSpec(
        length_cm=20, width_cm=15, height_cm=10, weight_grams=500, box_type_id=5
    )

    result = asyncio.run(
        provider.quote(
            origin=origin,
            destination=destination,
            package=package,
            declared_value_irr=1000000,
            payment_type="SENDER",
            collection_type="pick_up",
        )
    )
    assert captured["paths"] == ["/shipping/quotes"]
    assert len(captured["bodies"]) == 1
    body = captured["bodies"][0]
    assert body["collection_type"] == "pick_up"
    assert body["from_city_code"] == 1
    assert "parcels" in body
    assert body["courier"] == {"courier_code": "IR_POST", "service_type": "EXPRESS"}
    assert body["value_added_service"] == MINIMAL_VALUE_ADDED_SERVICE
    assert body["value_added_service"]["request_label"] is False
    assert body["parcels"][0]["to_city_code"] == 175
    assert body["parcels"][0]["parcel_properties"]["box_type_id"] == 5
    assert result.options[0].customer_amount_toman == Decimal("249800.00")
