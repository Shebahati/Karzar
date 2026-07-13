"""Shared payment initialization and verification logic."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.services.order_service import transition_order_status
from app.services.payment_ledger_service import (
    record_payment_failed,
    record_payment_initiated,
    record_payment_verified,
)
from app.services.payment_service import (
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
    PaymentInitResult,
    PaymentVerifyFailedError,
    PaymentVerifyResult,
    get_payment_provider,
)


def order_amount_rials(order: Order) -> int:
    amount_toman = Decimal(str(order.estimated_total or 0))
    amount_rials = (amount_toman * Decimal(TOMAN_TO_RIAL)).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    return int(amount_rials)


def resolve_payment_callback_url() -> str:
    return settings.PAYMENT_CALLBACK_URL or "http://localhost:8000/api/v1/payments/callback"


def get_order_payment_authority(order: Order) -> str | None:
    return order.payment_authority


def get_order_payment_ref_id(order: Order) -> str | None:
    return order.payment_ref_id


def build_mock_payment_url(authority: str) -> str:
    callback = resolve_payment_callback_url()
    query = urlencode({"Authority": authority, "Status": "OK"})
    separator = "&" if "?" in callback else "?"
    return f"{callback}{separator}{query}"


def build_gateway_payment_url(authority: str) -> str:
    if settings.PAYMENT_PROVIDER == "mock":
        return build_mock_payment_url(authority)
    return f"https://www.zarinpal.com/pg/StartPay/{authority}"


async def initialize_order_payment(
    db: AsyncSession,
    order: Order,
    *,
    ip_address: str | None = None,
) -> PaymentInitResult:
    if order.mode != OrderMode.PURCHASE:
        raise ValueError("Payment is only available for purchase orders")
    if order.payment_status == PaymentStatus.PAID.value or order.status == OrderStatus.PAID.value:
        raise ValueError("Order is already paid")
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise ValueError("Order is not in payable state")
    if order.estimated_total is None:
        raise ValueError("Order total is missing")

    existing = get_order_payment_authority(order)
    if existing:
        return PaymentInitResult(
            authority=existing,
            payment_url=build_gateway_payment_url(existing),
        )

    callback_url = resolve_payment_callback_url()
    amount_rials = order_amount_rials(order)
    result = await get_payment_provider().init_payment(
        amount_rials=amount_rials,
        description=f"Karzar order {order.tracking_code}",
        callback_url=callback_url,
    )
    order.payment_authority = result.authority
    await db.flush()
    await record_payment_initiated(
        db,
        order,
        authority=result.authority,
        ip_address=ip_address,
    )
    return PaymentInitResult(
        authority=result.authority,
        payment_url=build_gateway_payment_url(result.authority),
    )


async def verify_order_payment(
    db: AsyncSession,
    order: Order,
    *,
    authority: str,
    gateway_status: str | None = None,
    ip_address: str | None = None,
) -> PaymentVerifyResult:
    if order.mode != OrderMode.PURCHASE:
        raise ValueError("Invalid order mode")
    if order.estimated_total is None:
        raise ValueError("Order total is missing")

    if order.payment_status == PaymentStatus.PAID.value:
        return PaymentVerifyResult(success=True, ref_id=get_order_payment_ref_id(order))

    stored = get_order_payment_authority(order)
    if not stored or stored != authority:
        raise PaymentVerifyFailedError("Payment authority does not match this order")
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise PaymentVerifyFailedError("Order is not in payable state")

    if gateway_status is not None and gateway_status.strip().upper() not in {"OK", "100"}:
        order.payment_status = PaymentStatus.FAILED.value
        await record_payment_failed(db, order, authority=authority, ip_address=ip_address)
        await db.flush()
        raise PaymentVerifyFailedError("Gateway returned a failed payment status")

    amount_rials = order_amount_rials(order)
    try:
        result = await get_payment_provider().verify_payment(
            authority=authority,
            amount_rials=amount_rials,
        )
    except (PaymentGatewayError, PaymentGatewayTimeoutError, PaymentVerifyFailedError) as exc:
        order.payment_status = PaymentStatus.FAILED.value
        await record_payment_failed(db, order, authority=authority, ip_address=ip_address)
        await db.flush()
        raise exc

    if result.success:
        if order.status == OrderStatus.PENDING_PAYMENT.value:
            await transition_order_status(db, order, OrderStatus.PAID.value)
        order.payment_status = PaymentStatus.PAID.value
        if result.ref_id:
            order.payment_ref_id = result.ref_id
        await record_payment_verified(
            db,
            order,
            authority=authority,
            ref_id=result.ref_id,
            ip_address=ip_address,
        )
    else:
        order.payment_status = PaymentStatus.FAILED.value
        await record_payment_failed(db, order, authority=authority, ip_address=ip_address)

    await db.flush()
    return result
