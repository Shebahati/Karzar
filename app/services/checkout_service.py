"""Checkout and contact submission business logic."""

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.crud import commerce as crud_commerce
from app.crud import content as crud_content
from app.crud import product as crud_product
from app.db.models.commerce import OrderMode, OrderStatus, PaymentStatus
from app.db.models.user import User
from app.schemas.storefront import (
    CheckoutRequest,
    CheckoutResponse,
    ContactRequest,
    ContactResponse,
)
from app.services.cart_service import clear_cart_for_checkout, resolve_checkout_defaults
from app.services.logistics.exceptions import (
    LogisticsError,
    ShippingMethodRequiredError,
    ShippingUnavailableError,
)
from app.services.logistics.fingerprints import merge_line_quantities
from app.services.logistics.models import Destination
from app.services.logistics.money import provider_total_toman
from app.services.logistics.service import (
    assert_quote_prices_current,
    bind_quote_to_order,
    consume_quote,
    validate_postex_destination_location_code,
)
from app.services.logistics.shipping_methods import (
    ShippingDestination,
    postex_checkout_enabled,
    public_purchase_shipping_available,
    resolve_shipping_method,
    storefront_shipping_enabled,
)
from app.services.logistics.shipping_payment import (
    ShippingPaymentMode,
    default_shipping_payment_mode,
)
from app.services.order_expiry_service import cancel_expired_pending_payment_orders
from app.services.order_service import record_initial_status_event, status_label
from app.services.payment_flow_service import initialize_order_payment
from app.services.stock_ledger_service import record_sale_movement
from app.utils.decimal_utils import to_decimal as _to_decimal
from app.utils.storefront_catalog import decimal_to_api_string

logger = get_logger(__name__)

_NO_PUBLIC_SHIPPING_MSG = "در حال حاضر روش ارسال فعالی برای ثبت سفارش وجود ندارد."


class PurchaseAuthRequiredError(ValueError):
    """Raised when purchase checkout is attempted without authentication."""


class PurchaseCheckoutDisabledError(RuntimeError):
    """Raised when purchase checkout is temporarily disabled by ops kill switch."""


def _merge_quantities(payload: CheckoutRequest) -> dict[int, int]:
    """Aggregate quantities per product so duplicate lines are validated together."""
    return merge_line_quantities(
        [{"product_id": line.product_id, "quantity": line.quantity} for line in payload.items]
    )


async def submit_checkout(
    db: AsyncSession,
    payload: CheckoutRequest,
    current_user: User | None = None,
    *,
    guest_cart_token: str | None = None,
) -> CheckoutResponse:
    if not payload.items:
        raise ValueError("At least one item is required")

    mode_str, company_name = resolve_checkout_defaults(
        current_user, payload.mode, payload.company_name
    )
    mode = OrderMode(mode_str)
    is_purchase = mode == OrderMode.PURCHASE
    # Kill switch before auth/shipping checks and any DB side effects.
    if is_purchase and not settings.PURCHASE_CHECKOUT_ENABLED:
        raise PurchaseCheckoutDisabledError()
    if is_purchase and current_user is None:
        raise PurchaseAuthRequiredError()
    if is_purchase and payload.shipping is None:
        raise ValueError("shipping is required for purchase mode")
    if is_purchase and not public_purchase_shipping_available():
        raise ShippingUnavailableError(_NO_PUBLIC_SHIPPING_MSG)

    shipping_quote = None
    shipping_cost = Decimal("0")
    shipping_payment_mode: ShippingPaymentMode | None = None
    resolved_provider: str | None = None
    resolved_carrier: str | None = None
    resolved_service: str | None = None
    resolved_method_code: str | None = None

    if is_purchase and storefront_shipping_enabled():
        if not (payload.shipping_method_code or "").strip():
            raise ShippingMethodRequiredError("انتخاب روش ارسال الزامی است.")
        assert payload.shipping is not None
        resolved = resolve_shipping_method(
            payload.shipping_method_code.strip(),
            ShippingDestination(
                province=payload.shipping.province,
                city=payload.shipping.city,
                postal_code=payload.shipping.postal_code,
            ),
        )
        shipping_payment_mode = resolved.payment_mode
        resolved_provider = resolved.provider
        resolved_carrier = resolved.carrier_code
        resolved_service = resolved.service_code
        resolved_method_code = resolved.code.value
        shipping_cost = Decimal("0")
        logger.info(
            "checkout_shipping_method_selected code=%s provider=%s service=%s payment_mode=%s",
            resolved.code.value,
            resolved.provider,
            resolved.service_code,
            resolved.payment_mode.value,
        )
    elif is_purchase and postex_checkout_enabled():
        shipping_payment_mode = default_shipping_payment_mode()
        if payload.shipping is None or payload.shipping.location_code is None:
            raise LogisticsError(
                "کد شهر مقصد برای ارسال الزامی است.",
                error_code="SHIPPING_QUOTE_MISMATCH",
            )
        await validate_postex_destination_location_code(payload.shipping.location_code)
        if shipping_payment_mode == ShippingPaymentMode.RECEIVER_DUE:
            shipping_cost = Decimal("0")
        else:
            if not payload.shipping_quote_token:
                raise LogisticsError(
                    "انتخاب سرویس ارسال الزامی است.",
                    error_code="SHIPPING_QUOTE_REQUIRED",
                )
            shipping_quote = await consume_quote(
                db,
                token=payload.shipping_quote_token,
                user_id=current_user.id,
                items=[
                    {"product_id": pid, "quantity": qty}
                    for pid, qty in _merge_quantities(payload).items()
                ],
                destination=Destination(
                    location_code=payload.shipping.location_code,
                    city_name=payload.shipping.city,
                    province_name=payload.shipping.province,
                    postal_code=payload.shipping.postal_code,
                ),
            )
            shipping_cost = _to_decimal(shipping_quote.customer_amount_toman)
    elif is_purchase:
        raise ShippingUnavailableError(_NO_PUBLIC_SHIPPING_MSG)

    if is_purchase:
        await cancel_expired_pending_payment_orders(db)

    quantities = _merge_quantities(payload)

    # Lock the referenced product rows so concurrent purchases cannot oversell.
    products = await crud_product.get_products_for_update(db, list(quantities.keys()))
    if shipping_quote is not None:
        assert_quote_prices_current(shipping_quote, products, quantities)

    line_items = []
    estimated_total = Decimal("0.0")
    has_priced_item = False
    stock_reservations: list[tuple[int, int]] = []

    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if not product or not product.is_active:
            raise ValueError(f"Product {product_id} is not available")

        if is_purchase and not getattr(product, "is_available", True):
            raise ValueError(f"Product {product_id} is not available")

        unit_price = product.base_price
        if is_purchase and unit_price is None:
            raise ValueError(
                f"Product {product_id} has no price and cannot be purchased; "
                "use inquiry mode instead"
            )

        if unit_price is not None:
            has_priced_item = True
            line_total = _to_decimal(unit_price) * quantity
            tax_rate = _to_decimal(product.tax_percent or 0) / Decimal("100")
            estimated_total += line_total + (line_total * tax_rate)

        if is_purchase:
            stock_reservations.append((product_id, quantity))

        line_items.append(
            {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "product_name": product.name,
                "product_sku": product.sku,
                "tax_percent": product.tax_percent or Decimal("0"),
            }
        )

    if is_purchase and shipping_payment_mode != ShippingPaymentMode.RECEIVER_DUE:
        estimated_total += shipping_cost

    customer_is_guest = payload.customer.is_guest
    if current_user is not None:
        customer_is_guest = False

    status_value = (
        OrderStatus.PENDING_PAYMENT.value if is_purchase else OrderStatus.INQUIRY_REVIEW.value
    )

    receiver_due = shipping_payment_mode == ShippingPaymentMode.RECEIVER_DUE
    if resolved_provider:
        order_shipping_provider = resolved_provider
    elif shipping_quote is not None:
        order_shipping_provider = shipping_quote.provider
    elif postex_checkout_enabled() and shipping_payment_mode is not None:
        order_shipping_provider = "postex"
    else:
        order_shipping_provider = None

    shipping_snapshot: dict[str, Any] | None = None
    if payload.shipping is not None:
        shipping_snapshot = payload.shipping.model_dump()
        if resolved_method_code:
            shipping_snapshot["shipping_method_code"] = resolved_method_code

    order = await crud_commerce.create_order(
        db,
        tracking_prefix="KZ-",
        mode=mode,
        status=status_value,
        payment_status=PaymentStatus.UNPAID.value,
        estimated_total=estimated_total if has_priced_item and is_purchase else None,
        customer_full_name=payload.customer.full_name,
        customer_phone=payload.customer.phone,
        customer_is_guest=customer_is_guest,
        company_name=company_name,
        note=payload.note,
        shipping=shipping_snapshot,
        user_id=current_user.id if current_user else None,
        items=line_items,
        shipping_provider=order_shipping_provider,
        shipping_quote_id=None if receiver_due else (shipping_quote.id if shipping_quote else None),
        shipping_customer_cost=(
            None if receiver_due else (shipping_quote.customer_amount_toman if shipping_quote else None)
        ),
        shipping_provider_quoted_cost=(
            None
            if receiver_due
            else (
                provider_total_toman(
                    provider_amount_toman=shipping_quote.provider_amount_toman,
                    pickup_amount_toman=shipping_quote.pickup_amount_toman,
                )
                if shipping_quote
                else None
            )
        ),
        shipping_carrier_code=(
            resolved_carrier
            if receiver_due and resolved_provider
            else (None if receiver_due else (shipping_quote.carrier_code if shipping_quote else None))
        ),
        shipping_service_code=(
            resolved_service
            if receiver_due and resolved_provider
            else (None if receiver_due else (shipping_quote.service_code if shipping_quote else None))
        ),
        shipping_payment_mode=shipping_payment_mode.value if shipping_payment_mode else None,
    )
    if shipping_quote is not None:
        await bind_quote_to_order(db, shipping_quote, order.id)
    await record_initial_status_event(db, order, description="سفارش ثبت شد")

    if is_purchase:
        for product_id, quantity in stock_reservations:
            await record_sale_movement(
                db,
                product_id=product_id,
                quantity=quantity,
                order_id=order.id,
                user_id=current_user.id if current_user else None,
            )

    payment_url: str | None = None
    authority: str | None = None
    if is_purchase and current_user is not None:
        payment = await initialize_order_payment(db, order, ip_address=None)
        payment_url = payment.payment_url
        authority = payment.authority

    await clear_cart_for_checkout(
        db,
        mode=mode_str,
        user=current_user,
        guest_token=guest_cart_token,
    )
    await db.flush()

    if shipping_payment_mode == ShippingPaymentMode.RECEIVER_DUE:
        shipping_display = "receiver_due"
    elif shipping_payment_mode == ShippingPaymentMode.SENDER_PREPAID:
        shipping_display = "prepaid"
    else:
        shipping_display = "none"

    return CheckoutResponse(
        order_id=order.id,
        tracking_code=order.tracking_code,
        mode=mode_str,
        status=order.status,
        status_label=status_label(order.status),
        estimated_total=decimal_to_api_string(order.estimated_total),
        created_at=order.created_at,
        payment_url=payment_url,
        authority=authority,
        shipping_payment_mode=shipping_payment_mode.value if shipping_payment_mode else None,
        shipping_display=shipping_display,
    )


async def submit_contact(db: AsyncSession, payload: ContactRequest) -> ContactResponse:
    submission = await crud_content.create_contact_submission(
        db,
        ticket_prefix="TK-",
        full_name=payload.full_name,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
    )
    await db.flush()
    return ContactResponse(ok=True, ticket=submission.ticket_code)
