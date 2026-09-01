"""Website paid-sales for admin; Hesabfa reads gated off by default.

Hesabfa-sourced sales/stock metrics must not reach the admin panel unless
``HESABFA_ADMIN_READS_ENABLED`` is explicitly true (ops only). Invoice write
and site→Hesabfa item push stay under ``HESABFA_ENABLED``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.core.logging import get_logger
from app.db.models.commerce import (
    Order,
    OrderMode,
    PaymentStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
)
from app.services.hesabfa.client import (
    INVOICE_TYPE_SALE,
    HesabfaClient,
    get_hesabfa_client,
    hesabfa_integration_active,
)
from app.services.hesabfa.exceptions import HesabfaError

logger = get_logger(__name__)


@dataclass(frozen=True)
class SalesSummary:
    website_paid_total_toman: Decimal
    website_paid_order_count: int
    hesabfa_sales_total: Decimal | None
    hesabfa_invoice_count: int | None
    hesabfa_currency_unit: str
    hesabfa_available: bool
    hesabfa_error: str | None = None


async def website_paid_sales(db: AsyncSession) -> tuple[Decimal, int]:
    """Sum paid purchase orders verified through a real (non-mock) payment gateway."""
    verified_non_mock_payment = exists(
        select(PaymentTransaction.id).where(
            PaymentTransaction.order_id == Order.id,
            PaymentTransaction.status == PaymentTransactionStatus.VERIFIED.value,
            PaymentTransaction.gateway != "mock",
        )
    )
    result = await db.execute(
        select(
            func.coalesce(func.sum(Order.estimated_total), 0),
            func.count(Order.id),
        ).where(
            Order.mode == OrderMode.PURCHASE,
            Order.payment_status == PaymentStatus.PAID.value,
            Order.deleted_at.is_(None),
            verified_non_mock_payment,
        )
    )
    total, count = result.one()
    return Decimal(str(total or 0)), int(count or 0)


async def hesabfa_sales_total(
    *,
    client: HesabfaClient | None = None,
    page_size: int = 100,
    max_pages: int = 50,
) -> tuple[Decimal, int]:
    """Sum sale invoice amounts from Hesabfa (ops tooling only)."""
    api = client or get_hesabfa_client()
    total = Decimal("0")
    count = 0
    skip = 0
    for _ in range(max_pages):
        page = await api.get_invoices(
            invoice_type=INVOICE_TYPE_SALE,
            take=page_size,
            skip=skip,
        )
        items = list(page.get("List") or [])
        if not items:
            break
        for inv in items:
            if inv.get("Returned") is True:
                continue
            amount = Decimal(
                str(inv.get("Sum") if inv.get("Sum") is not None else inv.get("Payable") or 0)
            )
            total += amount
            count += 1
        total_count = int(page.get("TotalCount") or 0)
        skip += len(items)
        if skip >= total_count or len(items) < page_size:
            break
    return total, count


def hesabfa_amount_to_toman(amount: Decimal) -> Decimal:
    if settings.HESABFA_CURRENCY_UNIT == "rial":
        return (amount / Decimal(TOMAN_TO_RIAL)).quantize(Decimal("0.01"))
    return amount


async def get_sales_summary(
    db: AsyncSession,
    *,
    client: HesabfaClient | None = None,
) -> SalesSummary:
    """Website paid totals. Hesabfa figures only if admin reads are explicitly enabled."""
    website_total, website_count = await website_paid_sales(db)

    if not settings.HESABFA_ADMIN_READS_ENABLED:
        return SalesSummary(
            website_paid_total_toman=website_total,
            website_paid_order_count=website_count,
            hesabfa_sales_total=None,
            hesabfa_invoice_count=None,
            hesabfa_currency_unit=settings.HESABFA_CURRENCY_UNIT,
            hesabfa_available=False,
            hesabfa_error="hesabfa_admin_reads_disabled",
        )

    if not hesabfa_integration_active():
        return SalesSummary(
            website_paid_total_toman=website_total,
            website_paid_order_count=website_count,
            hesabfa_sales_total=None,
            hesabfa_invoice_count=None,
            hesabfa_currency_unit=settings.HESABFA_CURRENCY_UNIT,
            hesabfa_available=False,
            hesabfa_error="hesabfa_disabled_or_unconfigured",
        )

    try:
        hf_total, hf_count = await hesabfa_sales_total(client=client)
        return SalesSummary(
            website_paid_total_toman=website_total,
            website_paid_order_count=website_count,
            hesabfa_sales_total=hf_total,
            hesabfa_invoice_count=hf_count,
            hesabfa_currency_unit=settings.HESABFA_CURRENCY_UNIT,
            hesabfa_available=True,
        )
    except HesabfaError as exc:
        logger.warning("Hesabfa sales summary failed: %s", exc)
        return SalesSummary(
            website_paid_total_toman=website_total,
            website_paid_order_count=website_count,
            hesabfa_sales_total=None,
            hesabfa_invoice_count=None,
            hesabfa_currency_unit=settings.HESABFA_CURRENCY_UNIT,
            hesabfa_available=False,
            hesabfa_error=str(exc),
        )
