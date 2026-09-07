"""Purchase checkout kill switch: PURCHASE_CHECKOUT_ENABLED."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, PaymentTransaction
from app.main import app
from app.schemas.storefront import CheckoutRequest
from app.services import checkout_service
from app.services.checkout_service import PurchaseCheckoutDisabledError
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal, customer_auth_headers

client = TestClient(app)

_PURCHASE_MESSAGE = (
    "خرید آنلاین موقتاً در حال به‌روزرسانی است. "
    "لطفاً کمی بعد دوباره تلاش کنید یا درخواست استعلام ثبت کنید."
)


def _purchase_payload(product_id: int, *, phone: str = "09125550909") -> dict:
    return {
        "mode": "purchase",
        "customer": {"full_name": "خریدار", "phone": phone},
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping": {
            "province": "تهران",
            "city": "تهران",
            "postal_code": "1234567890",
            "address_line": "خیابان تست پلاک ۱",
        },
    }


def _count_orders_and_payments() -> tuple[int, int]:
    async def _count() -> tuple[int, int]:
        async with TestingSessionLocal() as session:
            orders = (
                await session.execute(select(func.count()).select_from(Order))
            ).scalar_one()
            payments = (
                await session.execute(select(func.count()).select_from(PaymentTransaction))
            ).scalar_one()
            return int(orders), int(payments)

    return asyncio.run(_count())


def test_purchase_disabled_rejects_before_any_side_effect(monkeypatch):
    """Unit: kill switch fires before order/payment/stock/cart/expiry work."""
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", False)

    cancel_expired = AsyncMock()
    create_order = AsyncMock()
    record_sale = AsyncMock()
    init_payment = AsyncMock()
    clear_cart = AsyncMock()
    get_products = AsyncMock()

    monkeypatch.setattr(
        "app.services.checkout_service.cancel_expired_pending_payment_orders",
        cancel_expired,
    )
    monkeypatch.setattr(
        "app.services.checkout_service.crud_commerce.create_order",
        create_order,
    )
    monkeypatch.setattr(
        "app.services.checkout_service.record_sale_movement",
        record_sale,
    )
    monkeypatch.setattr(
        "app.services.checkout_service.initialize_order_payment",
        init_payment,
    )
    monkeypatch.setattr(
        "app.services.checkout_service.clear_cart_for_checkout",
        clear_cart,
    )
    monkeypatch.setattr(
        "app.services.checkout_service.crud_product.get_products_for_update",
        get_products,
    )

    payload = CheckoutRequest.model_validate(_purchase_payload(42))
    user = SimpleNamespace(id=1, role="b2c_customer", company_name=None)

    with pytest.raises(PurchaseCheckoutDisabledError):
        asyncio.run(
            checkout_service.submit_checkout(
                db=AsyncMock(),
                payload=payload,
                current_user=user,
            )
        )

    cancel_expired.assert_not_called()
    get_products.assert_not_called()
    create_order.assert_not_called()
    record_sale.assert_not_called()
    init_payment.assert_not_called()
    clear_cart.assert_not_called()


@pytest.mark.usefixtures("override_database")
def test_purchase_disabled_api_returns_503_without_mutations(
    super_admin_headers, valid_product_data, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", False)

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "KILL-SW-1"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    auth = customer_auth_headers("09125550909")
    guest = "kill-switch-cart-token-32chars-xx!"
    put = client.put(
        "/api/v1/cart/items",
        headers={**auth, "X-Cart-Token": guest},
        json={"lane": "purchase", "product_id": product_id, "quantity": 1},
    )
    assert put.status_code == 200

    orders_before, payments_before = _count_orders_and_payments()

    response = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product_id),
        headers={**auth, "X-Cart-Token": guest},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED"
    assert body["message"] == _PURCHASE_MESSAGE

    orders_after, payments_after = _count_orders_and_payments()
    assert orders_after == orders_before
    assert payments_after == payments_before

    cart = client.get(
        "/api/v1/cart?lane=purchase",
        headers={**auth, "X-Cart-Token": guest},
    )
    assert cart.status_code == 200
    assert cart.json()["item_count"] == 1

    stock = client.get(
        f"/api/v1/products/{product_id}/stock",
        headers=super_admin_headers,
    )
    assert stock.status_code == 200
    assert stock.json()["is_available"] is True


@pytest.mark.usefixtures("override_database")
def test_inquiry_succeeds_when_purchase_disabled(
    super_admin_headers, valid_product_data, monkeypatch
):
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", False)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "KILL-SW-INQ", "is_available": False},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]

    response = client.post(
        "/api/v1/checkout",
        json={
            "mode": "inquiry",
            "customer": {"full_name": "استعلام", "phone": "09125550910"},
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )
    assert response.status_code == 201
    assert response.json()["mode"] == "inquiry"
    assert response.json()["status"] == "inquiry_review"


@pytest.mark.usefixtures("override_database")
def test_purchase_enabled_path_unchanged(
    super_admin_headers, valid_product_data, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "KILL-SW-OK"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    auth = customer_auth_headers("09125550911")

    response = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product_id, phone="09125550911"),
        headers=auth,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["mode"] == "purchase"
    assert body["status"] == "pending_payment"
    assert body["payment_url"] is not None
    assert body["authority"] is not None


def test_settings_default_disables_purchase_when_env_missing():
    """Missing env must not silently enable purchase (safe default)."""
    from app.core.config import Settings

    field = Settings.model_fields["PURCHASE_CHECKOUT_ENABLED"]
    assert field.default is False


def test_purchase_disabled_error_is_stable_code():
    from app.core.errors import ErrorCode

    assert (
        ErrorCode.PURCHASE_CHECKOUT_TEMPORARILY_DISABLED.value
        == "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED"
    )
