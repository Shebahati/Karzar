"""Create Hesabfa sale invoices after payment verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.core.logging import get_logger
from app.db.models.commerce import Order, OrderMode, PaymentStatus
from app.db.models.hesabfa import HesabfaInvoiceRecord, HesabfaItemMapping
from app.services.hesabfa.client import (
    INVOICE_TYPE_SALE,
    HesabfaClient,
    get_hesabfa_client,
    hesabfa_integration_active,
)
from app.services.hesabfa.contacts import ensure_hesabfa_contact
from app.services.hesabfa.exceptions import HesabfaError

logger = get_logger(__name__)


@dataclass(frozen=True)
class InvoiceSyncResult:
    status: str
    hesabfa_number: str | None = None
    message: str | None = None


def _to_hesabfa_money(amount_toman: Decimal) -> Decimal:
    unit = settings.HESABFA_CURRENCY_UNIT
    if unit == "rial":
        return (amount_toman * Decimal(TOMAN_TO_RIAL)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    return amount_toman.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _line_tax(unit_price: Decimal, quantity: int, tax_percent: Decimal) -> Decimal:
    if tax_percent <= 0:
        return Decimal("0")
    base = unit_price * Decimal(quantity)
    return (base * tax_percent / Decimal("100")).quantize(
        Decimal("1") if settings.HESABFA_CURRENCY_UNIT == "rial" else Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


async def create_invoice_for_paid_order(
    db: AsyncSession,
    order: Order,
    *,
    client: HesabfaClient | None = None,
) -> InvoiceSyncResult:
    """Idempotent Hesabfa sale invoice after payment verify.

    Skips gracefully when integration is off, test mode blocks writes,
    payment is not verified, or order is inquiry.
    """
    if not hesabfa_integration_active():
        return InvoiceSyncResult(status="skipped", message="hesabfa_disabled")

    if settings.HESABFA_TEST_MODE:
        # Still record intent so ops can see the hook fired without writing docs.
        logger.info(
            "Hesabfa TEST_MODE: skipping invoice create for order_id=%s",
            order.id,
        )
        return InvoiceSyncResult(status="skipped", message="test_mode")

    if order.mode != OrderMode.PURCHASE:
        return InvoiceSyncResult(status="skipped", message="not_purchase")

    if order.payment_status != PaymentStatus.PAID.value:
        return InvoiceSyncResult(status="skipped", message="payment_not_verified")

    existing = (
        await db.execute(
            select(HesabfaInvoiceRecord).where(HesabfaInvoiceRecord.order_id == order.id)
        )
    ).scalars().first()
    if existing and existing.status == "created" and existing.hesabfa_number:
        return InvoiceSyncResult(
            status="already_created",
            hesabfa_number=existing.hesabfa_number,
        )

    record = existing or HesabfaInvoiceRecord(
        order_id=order.id,
        status="pending",
        payload_tag=f"order:{order.id}",
    )
    if existing is None:
        db.add(record)
        await db.flush()

    api = client or get_hesabfa_client()
    try:
        # Ensure items are loaded
        if not order.items:
            refreshed = (
                await db.execute(
                    select(Order)
                    .where(Order.id == order.id)
                    .options(selectinload(Order.items))
                )
            ).scalars().first()
            if refreshed is None:
                raise ValueError("Order not found")
            order = refreshed

        contact = await ensure_hesabfa_contact(
            db,
            phone=order.customer_phone,
            full_name=order.customer_full_name,
            user_id=order.user_id,
            company_name=order.company_name,
            client=api,
        )

        product_ids = [item.product_id for item in order.items]
        mappings = (
            await db.execute(
                select(HesabfaItemMapping).where(
                    HesabfaItemMapping.product_id.in_(product_ids)
                )
            )
        ).scalars().all()
        mapping_by_product = {m.product_id: m for m in mappings}

        missing = [
            item.product_id
            for item in order.items
            if item.product_id not in mapping_by_product
        ]
        if missing:
            raise ValueError(
                f"Order items missing Hesabfa SKU mapping for product_ids={missing}"
            )

        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        invoice_items = []
        for idx, item in enumerate(order.items, start=1):
            mapping = mapping_by_product[item.product_id]
            # Prefer immutable order-line snapshot; never re-read live catalog price/name/tax.
            unit_toman = Decimal(str(item.unit_price or 0))
            if unit_toman <= 0:
                raise ValueError(
                    f"Order item product_id={item.product_id} has no snapshotted unit_price"
                )
            unit_price = _to_hesabfa_money(unit_toman)
            tax = _line_tax(
                unit_price,
                item.quantity,
                Decimal(str(item.tax_percent or 0)),
            )
            invoice_items.append(
                {
                    "rowNumber": idx,
                    "description": item.product_name,
                    "itemCode": mapping.hesabfa_code,
                    "unit": "عدد",
                    "quantity": item.quantity,
                    "unitPrice": float(unit_price),
                    "discount": 0,
                    "tax": float(tax),
                }
            )

        invoice_payload = {
            "date": now,
            "dueDate": now,
            "contactCode": contact.hesabfa_code,
            "contactTitle": order.customer_full_name,
            "reference": order.tracking_code,
            "note": f"Karzar web order {order.tracking_code}",
            "sent": False,
            "invoiceType": INVOICE_TYPE_SALE,
            "status": 2,
            "tag": f"order:{order.id}",
            "freight": 0,
            "currency": settings.HESABFA_CURRENCY_CODE,
            "invoiceItems": invoice_items,
        }
        saved = await api.save_invoice(invoice_payload)
        number = str(saved.get("Number") or saved.get("number") or "").strip() or None
        record.status = "created"
        record.hesabfa_number = number
        record.error_message = None
        record.payload_tag = f"order:{order.id}"
        record.next_attempt_at = None
        await db.flush()
        logger.info(
            "Hesabfa invoice created order_id=%s number=%s",
            order.id,
            number,
        )
        return InvoiceSyncResult(status="created", hesabfa_number=number)
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)[:1000]
        record.attempt_count = int(record.attempt_count or 0) + 1
        delay = min(3600, 60 * (2 ** max(0, record.attempt_count - 1)))
        record.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
        await db.flush()
        logger.exception("Hesabfa invoice failed order_id=%s", order.id)
        if isinstance(exc, HesabfaError):
            return InvoiceSyncResult(status="failed", message=str(exc))
        return InvoiceSyncResult(status="failed", message=str(exc))


async def maybe_create_invoice_after_payment(
    db: AsyncSession,
    order: Order,
) -> InvoiceSyncResult | None:
    """Best-effort hook used by payment verify — never raises to callers."""
    try:
        return await create_invoice_for_paid_order(db, order)
    except Exception:
        logger.exception(
            "Hesabfa invoice hook crashed for order_id=%s (payment still valid)",
            order.id,
        )
        return InvoiceSyncResult(status="failed", message="hook_exception")
