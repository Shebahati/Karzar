"""Append-only payment transaction ledger helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.commerce import Order, PaymentTransaction, PaymentTransactionStatus


def _amount(order: Order) -> Decimal:
    return Decimal(str(order.estimated_total or 0))


async def _append(
    db: AsyncSession,
    order: Order,
    *,
    status: PaymentTransactionStatus,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    provider_data: dict[str, Any] | None = None,
    result_code: int | None = None,
    trace_no: str | None = None,
    rrn: str | None = None,
    merchant_reference: str | None = None,
) -> PaymentTransaction:
    row = PaymentTransaction(
        order_id=order.id,
        amount=_amount(order),
        gateway=settings.PAYMENT_PROVIDER,
        authority=authority,
        ref_id=ref_id,
        status=status.value,
        ip_address=ip_address,
        provider_data=provider_data,
        result_code=result_code,
        trace_no=trace_no,
        rrn=rrn,
        merchant_reference=merchant_reference or order.tracking_code,
    )
    db.add(row)
    await db.flush()
    return row


async def record_payment_initiated(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ip_address: str | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.INITIATED,
        authority=authority,
        ip_address=ip_address,
    )


async def record_payment_callback_received(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    provider_data: dict[str, Any] | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.CALLBACK_RECEIVED,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
        provider_data=provider_data,
    )


async def record_payment_verifying(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.VERIFYING,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
    )


async def record_payment_verified(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    provider_data: dict[str, Any] | None = None,
    result_code: int | None = None,
    trace_no: str | None = None,
    rrn: str | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.VERIFIED,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
        provider_data=provider_data,
        result_code=result_code,
        trace_no=trace_no,
        rrn=rrn,
    )


async def record_payment_failed(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    provider_data: dict[str, Any] | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.FAILED,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
        provider_data=provider_data,
    )


async def record_payment_refunded(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    refund_id: str | None = None,
    ip_address: str | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.REFUNDED,
        authority=authority,
        ref_id=refund_id or ref_id,
        ip_address=ip_address,
    )


async def record_payment_reversed(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    provider_data: dict[str, Any] | None = None,
    result_code: int | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.REVERSED,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
        provider_data=provider_data,
        result_code=result_code,
    )


async def record_payment_reconciliation_required(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    provider_data: dict[str, Any] | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.RECONCILIATION_REQUIRED,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
        provider_data=provider_data,
    )
