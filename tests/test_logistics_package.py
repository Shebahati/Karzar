"""Unit tests for package construction, money, redaction, and status mapping."""

from decimal import Decimal

import pytest
from app.core.constants import TOMAN_TO_RIAL
from app.services.logistics.exceptions import (
    ShippingDataIncompleteError,
    ShippingFreightRequiredError,
)
from app.services.logistics.models import BoxType, QuoteLine, ShipmentStatus
from app.services.logistics.money import irr_to_toman, toman_to_irr
from app.services.logistics.package_builder import build_package
from app.services.logistics.redaction import redact_secrets
from app.services.logistics.status_mapper import can_advance, map_provider_status


def _line(**kwargs) -> QuoteLine:
    base = dict(
        product_id=1,
        sku="SKU-1",
        quantity=1,
        unit_price_toman=Decimal("1000"),
        weight_grams=Decimal("250"),
        length_cm=Decimal("10"),
        width_cm=Decimal("8"),
        height_cm=Decimal("4"),
        is_fragile=False,
        is_liquid=False,
        shipping_class="parcel",
        is_available=True,
        name="Tool",
    )
    base.update(kwargs)
    return QuoteLine(**base)


def test_stack_quantity_along_smallest_axis():
    pkg = build_package([_line(quantity=3)])
    assert pkg.length_cm == 10
    assert pkg.width_cm == 8
    assert pkg.height_cm == 12
    assert pkg.weight_grams == 750


def test_combine_two_skus_preserves_largest_axes():
    a = _line(length_cm=Decimal("20"), width_cm=Decimal("10"), height_cm=Decimal("5"))
    b = _line(
        product_id=2,
        sku="SKU-2",
        length_cm=Decimal("12"),
        width_cm=Decimal("9"),
        height_cm=Decimal("6"),
        weight_grams=Decimal("100"),
    )
    pkg = build_package([a, b])
    assert pkg.length_cm == 20
    assert pkg.width_cm == 10
    assert pkg.height_cm == 11
    assert pkg.weight_grams == 350


def test_missing_dimensions_does_not_invent():
    with pytest.raises(ShippingDataIncompleteError) as exc:
        build_package([_line(length_cm=None)])
    assert exc.value.products[0]["sku"] == "SKU-1"
    assert "package_length_cm" in exc.value.products[0]["missing"]


def test_freight_only_rejected():
    with pytest.raises(ShippingFreightRequiredError):
        build_package([_line(shipping_class="freight_only")])


def test_oversize_no_fitting_box():
    boxes = [BoxType(id=1, name="S", length_cm=5, width_cm=5, height_cm=5)]
    with pytest.raises(ShippingFreightRequiredError):
        build_package(
            [_line(length_cm=Decimal("40"), width_cm=Decimal("30"), height_cm=Decimal("20"))], boxes
        )


def test_selects_smallest_fitting_box():
    boxes = [
        BoxType(id=9, name="L", length_cm=50, width_cm=40, height_cm=30),
        BoxType(id=2, name="M", length_cm=20, width_cm=10, height_cm=10),
    ]
    pkg = build_package([_line()], boxes)
    assert pkg.box_type_id == 2


def test_irr_toman_round_trip():
    assert TOMAN_TO_RIAL == 10
    assert irr_to_toman(150000) == Decimal("15000.00")
    assert toman_to_irr(Decimal("15000.50")) == Decimal("150005")


def test_redact_nested_secrets():
    payload = {
        "x-api-key": "secret",
        "nested": {"Authorization": "Bearer abc", "ok": 1},
        "list": [{"token": "nope", "id": 3}],
    }
    redacted = redact_secrets(payload)
    assert redacted["x-api-key"] == "***REDACTED***"
    assert redacted["nested"]["Authorization"] == "***REDACTED***"
    assert redacted["list"][0]["token"] == "***REDACTED***"
    assert redacted["list"][0]["id"] == 3
    assert redacted["nested"]["ok"] == 1


def test_unknown_status_never_delivered():
    mapped = map_provider_status(event_code="FUTURE_XYZ", event_name="وضعیت جدید")
    assert mapped != ShipmentStatus.DELIVERED
    assert mapped == ShipmentStatus.PROVIDER_UNKNOWN
    assert can_advance(ShipmentStatus.BOOKED.value, mapped.value) is False


def test_delivered_does_not_regress():
    assert can_advance(ShipmentStatus.DELIVERED.value, ShipmentStatus.IN_TRANSIT.value) is False
    mapped = map_provider_status(
        event_code="in_transit",
        current=ShipmentStatus.DELIVERED,
    )
    assert mapped == ShipmentStatus.IN_TRANSIT
    assert can_advance(ShipmentStatus.DELIVERED.value, mapped.value) is False
