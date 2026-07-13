"""Append-only payment transaction ledger helpers."""

from __future__ import annotations

from decimal import Decimal

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
) -> PaymentTransaction:
    row = PaymentTransaction(
        order_id=order.id,
        amount=_amount(order),
        gateway=settings.PAYMENT_PROVIDER,
        authority=authority,
        ref_id=ref_id,
        status=status.value,
        ip_address=ip_address,
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


async def record_payment_verified(
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
        status=PaymentTransactionStatus.VERIFIED,
        authority=authority,
        ref_id=ref_id,
        ip_address=ip_address,
    )


async def record_payment_failed(
    db: AsyncSession,
    order: Order,
    *,
    authority: str | None = None,
    ip_address: str | None = None,
) -> PaymentTransaction:
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.FAILED,
        authority=authority,
        ip_address=ip_address,
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
    # Keep refund_id in ref_id when gateway returns a dedicated refund reference.
    return await _append(
        db,
        order,
        status=PaymentTransactionStatus.REFUNDED,
        authority=authority,
        ref_id=refund_id or ref_id,
        ip_address=ip_address,
    )
