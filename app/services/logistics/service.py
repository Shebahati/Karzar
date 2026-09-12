"""Karzar logistics application service (provider-neutral)."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import Order, OrderStatus
from app.db.models.logistics import Shipment, ShipmentEvent, ShippingQuote
from app.db.models.product import Product
from app.services.logistics.exceptions import (
    LogisticsError,
    ShipmentNotFoundError,
    ShipmentStateError,
    ShippingDataIncompleteError,
    ShippingFreightRequiredError,
    ShippingQuoteConsumedError,
    ShippingQuoteExpiredError,
    ShippingQuoteMismatchError,
    ShippingQuoteStaleError,
    ShippingUnavailableError,
)
from app.services.logistics.fingerprints import (
    canonical_cart_items,
    cart_fingerprint,
    destination_fingerprint,
)
from app.services.logistics.models import (
    PHYSICAL_HANDOFF_STATUSES,
    RECEIVER_PRE_CREATE_MUTABLE_STATUSES,
    SHIPMENT_STATUS_LABELS_FA,
    Destination,
    OriginAddress,
    QuoteLine,
    ShipmentStatus,
)
from app.services.logistics.money import toman_to_irr
from app.services.logistics.package_builder import build_package, select_box
from app.services.logistics.postex.provider import PostexProvider
from app.services.logistics.redaction import redact_secrets
from app.services.logistics.shipping_payment import (
    ShippingPaymentMode,
    default_shipping_payment_mode,
    postex_booking_enabled,
    postex_payment_type_for_mode,
)
from app.services.logistics.status_mapper import can_advance, map_provider_status
from app.utils.decimal_utils import to_decimal as _to_decimal

logger = get_logger(__name__)

PROVIDER_POSTEX = "postex"

_city_cache: tuple[float, list] | None = None
_box_cache: tuple[float, list] | None = None
_last_success_at: dict[str, datetime] = {}


def as_utc(value: datetime) -> datetime:
    """Treat SQLite naive timestamps as UTC; PostgreSQL already returns aware values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def postex_enabled() -> bool:
    return bool(settings.POSTEX_ENABLED)


def _postex_payment_type_for_quote() -> str:
    return postex_payment_type_for_mode(default_shipping_payment_mode())


def require_postex_booking_enabled() -> None:
    if not postex_booking_enabled():
        raise LogisticsError(
            "ثبت مرسوله پستکس غیرفعال است.",
            error_code="SHIPPING_BOOKING_DISABLED",
        )


def shipment_payment_mode(shipment: Shipment, order: Order | None = None) -> ShippingPaymentMode:
    raw = (shipment.shipping_payment_mode or (order.shipping_payment_mode if order else None) or "").strip()
    if raw:
        return ShippingPaymentMode(raw)
    # Legacy rows without snapshot: treat as sender_prepaid (historical SENDER-only).
    return ShippingPaymentMode.SENDER_PREPAID


def receiver_due_booking_ready(shipment: Shipment) -> list[str]:
    """Return missing prerequisite codes for receiver_due PENDING_BOOKING."""
    missing: list[str] = []
    if shipment.package_length_cm is None or shipment.package_length_cm <= 0:
        missing.append("package_length_cm")
    if shipment.package_width_cm is None or shipment.package_width_cm <= 0:
        missing.append("package_width_cm")
    if shipment.package_height_cm is None or shipment.package_height_cm <= 0:
        missing.append("package_height_cm")
    if shipment.package_weight_grams is None or shipment.package_weight_grams <= 0:
        missing.append("package_weight_grams")
    if shipment.package_is_fragile is None:
        missing.append("package_is_fragile")
    if shipment.package_is_liquid is None:
        missing.append("package_is_liquid")
    if not (shipment.carrier_code or "").strip():
        missing.append("carrier_code")
    if not (shipment.service_code or "").strip():
        missing.append("service_code")
    if shipment.provider_box_type_id is None:
        missing.append("provider_box_type_id")
    return missing


def origin_from_settings() -> OriginAddress:
    if settings.POSTEX_ORIGIN_CITY_CODE is None:
        raise ShippingUnavailableError("POSTEX_ORIGIN_CITY_CODE is required")
    return OriginAddress(
        city_code=int(settings.POSTEX_ORIGIN_CITY_CODE),
        city_name=settings.POSTEX_ORIGIN_CITY_NAME,
        postal_code=(settings.POSTEX_ORIGIN_POSTAL_CODE or "").strip(),
        address=(settings.POSTEX_ORIGIN_ADDRESS or "").strip(),
        first_name=(settings.POSTEX_ORIGIN_FIRST_NAME or "").strip(),
        last_name=(settings.POSTEX_ORIGIN_LAST_NAME or "").strip(),
        mobile=(settings.POSTEX_ORIGIN_MOBILE or "").strip(),
        company_name=settings.POSTEX_ORIGIN_COMPANY_NAME,
        lat=settings.POSTEX_ORIGIN_LAT,
        lon=settings.POSTEX_ORIGIN_LON,
    )


def get_provider() -> PostexProvider:
    return PostexProvider()


def _note_success(operation: str) -> None:
    _last_success_at[operation] = datetime.now(UTC)


def last_success_timestamps() -> dict[str, str]:
    return {key: value.isoformat() for key, value in _last_success_at.items()}


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split()
    if not parts:
        return "مشتری", "کارزار"
    if len(parts) == 1:
        return parts[0], "-"
    return parts[0], " ".join(parts[1:])


def _quote_lines_from_products(
    products: dict[int, Product],
    quantities: dict[int, int],
) -> list[QuoteLine]:
    lines: list[QuoteLine] = []
    for product_id, quantity in quantities.items():
        product = products[product_id]
        lines.append(
            QuoteLine(
                product_id=product.id,
                sku=product.sku,
                quantity=quantity,
                unit_price_toman=_to_decimal(product.base_price or 0),
                weight_grams=product.weight_grams,
                length_cm=product.package_length_cm,
                width_cm=product.package_width_cm,
                height_cm=product.package_height_cm,
                is_fragile=product.shipping_is_fragile,
                is_liquid=product.shipping_is_liquid,
                shipping_class=product.shipping_class,
                is_available=bool(product.is_available),
                name=product.name,
            )
        )
    return lines


async def _cached_boxes(provider: PostexProvider) -> list:
    global _box_cache
    now = datetime.now(UTC).timestamp()
    if _box_cache and now - _box_cache[0] < settings.POSTEX_REFERENCE_CACHE_SECONDS:
        return _box_cache[1]
    boxes = await provider.list_boxes()
    _box_cache = (now, boxes)
    _note_success("boxes")
    return boxes


async def _cached_cities(provider: PostexProvider) -> list:
    global _city_cache
    now = datetime.now(UTC).timestamp()
    if _city_cache and now - _city_cache[0] < settings.POSTEX_REFERENCE_CACHE_SECONDS:
        return _city_cache[1]
    cities = await provider.list_cities()
    _city_cache = (now, cities)
    _note_success("cities")
    return cities


def clear_reference_caches() -> None:
    global _city_cache, _box_cache
    _city_cache = None
    _box_cache = None


async def list_public_cities() -> list[dict[str, Any]]:
    if not postex_enabled():
        return []
    try:
        cities = await _cached_cities(get_provider())
    except Exception as exc:
        logger.exception("postex city list failed")
        raise ShippingUnavailableError("سرویس شهرهای ارسال در دسترس نیست.") from exc
    return [
        {
            "code": city.code,
            "name": city.name,
            "province_code": city.province_code,
            "province_name": city.province_name,
        }
        for city in cities
    ]


async def create_quote(
    db: AsyncSession,
    *,
    user_id: int,
    items: list[dict[str, int]],
    destination: Destination,
    products: dict[int, Product],
) -> dict[str, Any]:
    if not postex_enabled():
        raise ShippingUnavailableError("ارسال پستی فعال نیست.")

    items = canonical_cart_items(items)
    quantities = {int(item["product_id"]): int(item["quantity"]) for item in items}
    for product_id in quantities:
        product = products.get(product_id)
        if product is None or not product.is_active:
            raise ValueError(f"Product {product_id} is not available")
        if not product.is_available:
            raise ValueError(f"Product {product_id} is not available")
        if product.base_price is None:
            raise ValueError(f"Product {product_id} has no price")

    lines = _quote_lines_from_products(products, quantities)
    provider = get_provider()
    try:
        boxes = await _cached_boxes(provider)
    except LogisticsError:
        raise
    except Exception as exc:
        logger.exception("postex boxes failed")
        raise ShippingUnavailableError("سرویس بسته‌بندی در دسترس نیست.") from exc

    package = build_package(lines, boxes)
    declared_toman = sum((line.unit_price_toman * line.quantity for line in lines), Decimal("0"))
    declared_irr = toman_to_irr(declared_toman)

    try:
        quote = await provider.quote(
            origin=origin_from_settings(),
            destination=destination,
            package=package,
            declared_value_irr=declared_irr,
            payment_type=_postex_payment_type_for_quote(),
            collection_type=settings.POSTEX_COLLECTION_TYPE,
        )
        _note_success("quotes")
    except LogisticsError:
        raise
    except Exception as exc:
        logger.exception("postex quote failed")
        raise ShippingUnavailableError(
            "محاسبه هزینه ارسال در دسترس نیست. دوباره تلاش کنید."
        ) from exc

    group_id = str(uuid4())
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.POSTEX_QUOTE_TTL_SECONDS)
    dest_fp = destination_fingerprint(
        location_code=destination.location_code,
        postal_code=destination.postal_code,
    )
    cart_fp = cart_fingerprint(items)
    package_snapshot = {
        "length_cm": package.length_cm,
        "width_cm": package.width_cm,
        "height_cm": package.height_cm,
        "weight_grams": package.weight_grams,
        "box_type_id": package.box_type_id,
        "box_name": package.box_name,
        "is_fragile": package.is_fragile,
        "is_liquid": package.is_liquid,
        "declared_value_irr": str(declared_irr),
        "product_unit_prices_toman": {
            str(product_id): str(_to_decimal(products[product_id].base_price or 0))
            for product_id in quantities
        },
    }
    persisted: list[ShippingQuote] = []
    for option in quote.options:
        row = ShippingQuote(
            token=secrets.token_urlsafe(32),
            group_id=group_id,
            user_id=user_id,
            provider=PROVIDER_POSTEX,
            destination_fingerprint=dest_fp,
            cart_fingerprint=cart_fp,
            destination_location_code=destination.location_code,
            carrier_code=option.carrier_code,
            service_code=option.service_code,
            service_name=option.service_name,
            provider_amount=option.provider_amount,
            provider_currency=option.provider_currency,
            provider_amount_toman=option.provider_amount_toman,
            customer_amount_toman=option.customer_amount_toman,
            pickup_amount_toman=option.pickup_amount_toman,
            expires_at=expires_at,
            package_snapshot=package_snapshot,
            raw_provider_response=redact_secrets(quote.raw_provider_response),
        )
        db.add(row)
        persisted.append(row)
    await db.flush()
    return {
        "quote_group_id": group_id,
        "expires_at": expires_at,
        "options": [
            {
                "quote_token": row.token,
                "carrier_code": row.carrier_code,
                "service_code": row.service_code,
                "title": row.service_name,
                "amount_toman": str(row.customer_amount_toman),
                "eta": next(
                    (opt.eta_text for opt in quote.options if opt.service_code == row.service_code),
                    None,
                ),
                "expires_at": expires_at,
            }
            for row in persisted
        ],
    }


async def consume_quote(
    db: AsyncSession,
    *,
    token: str,
    user_id: int,
    items: list[dict[str, int]],
    destination: Destination,
) -> ShippingQuote:
    result = await db.execute(
        select(ShippingQuote).where(ShippingQuote.token == token).with_for_update()
    )
    quote = result.scalars().first()
    if quote is None:
        raise ShippingQuoteMismatchError("توکن ارسال نامعتبر است.")
    if quote.user_id != user_id:
        raise ShippingQuoteMismatchError("توکن ارسال متعلق به این کاربر نیست.")
    if quote.consumed_order_id is not None:
        raise ShippingQuoteConsumedError("این نرخ ارسال قبلاً استفاده شده است.")
    if as_utc(quote.expires_at) <= datetime.now(UTC):
        raise ShippingQuoteExpiredError("مهلت نرخ ارسال تمام شده است. دوباره انتخاب کنید.")
    cart_fp = cart_fingerprint(items)
    dest_fp = destination_fingerprint(
        location_code=destination.location_code,
        postal_code=destination.postal_code,
    )
    if quote.cart_fingerprint != cart_fp:
        raise ShippingQuoteMismatchError("سبد خرید با نرخ ارسال هم‌خوانی ندارد.")
    if quote.destination_fingerprint != dest_fp:
        raise ShippingQuoteMismatchError("مقصد با نرخ ارسال هم‌خوانی ندارد.")
    if quote.destination_location_code != destination.location_code:
        raise ShippingQuoteMismatchError("کد شهر مقصد با نرخ ارسال هم‌خوانی ندارد.")
    return quote


def assert_quote_prices_current(
    quote: ShippingQuote,
    products: dict[int, Product],
    quantities: dict[int, int],
) -> None:
    """Fail closed when locked product prices no longer match the bound quote."""
    snapshot = quote.package_snapshot or {}
    stored_declared = snapshot.get("declared_value_irr")
    lines = _quote_lines_from_products(products, quantities)
    declared_toman = sum((line.unit_price_toman * line.quantity for line in lines), Decimal("0"))
    declared_irr = toman_to_irr(declared_toman)
    if stored_declared is None or Decimal(str(stored_declared)) != declared_irr:
        raise ShippingQuoteStaleError(
            "قیمت کالا تغییر کرده است. دوباره نرخ ارسال بگیرید."
        )
    stored_prices = snapshot.get("product_unit_prices_toman") or {}
    for product_id in quantities:
        product = products.get(product_id)
        if product is None or product.base_price is None:
            raise ShippingQuoteStaleError(
                "قیمت کالا تغییر کرده است. دوباره نرخ ارسال بگیرید."
            )
        current = str(_to_decimal(product.base_price))
        if str(stored_prices.get(str(product_id))) != current:
            raise ShippingQuoteStaleError(
                "قیمت کالا تغییر کرده است. دوباره نرخ ارسال بگیرید."
            )


async def bind_quote_to_order(db: AsyncSession, quote: ShippingQuote, order_id: int) -> None:
    await db.execute(
        update(ShippingQuote)
        .where(ShippingQuote.group_id == quote.group_id)
        .values(consumed_order_id=order_id)
    )
    await db.flush()


async def ensure_shipment_for_paid_order(db: AsyncSession, order: Order) -> Shipment | None:
    """Create the internal fulfillment row. Does not call Postex."""
    if not postex_enabled() or not order.shipping_provider:
        return None
    await db.execute(select(Order).where(Order.id == order.id).with_for_update())
    existing = (
        (await db.execute(select(Shipment).where(Shipment.order_id == order.id).limit(1)))
        .scalars()
        .first()
    )
    if existing:
        return existing
    mode_raw = (order.shipping_payment_mode or "").strip()
    mode = ShippingPaymentMode(mode_raw) if mode_raw else ShippingPaymentMode.SENDER_PREPAID
    snapshot = {}
    quote_service_name = None
    if order.shipping_quote_id:
        quote = (
            (
                await db.execute(
                    select(ShippingQuote).where(ShippingQuote.id == order.shipping_quote_id)
                )
            )
            .scalars()
            .first()
        )
        snapshot = (quote.package_snapshot if quote else {}) or {}
        quote_service_name = quote.service_name if quote else None

    if mode == ShippingPaymentMode.RECEIVER_DUE:
        shipment = Shipment(
            public_id=str(uuid4()),
            order_id=order.id,
            quote_id=None,
            provider=order.shipping_provider or PROVIDER_POSTEX,
            status=ShipmentStatus.AWAITING_PACKAGING.value,
            shipping_payment_mode=mode.value,
            carrier_code=None,
            service_code=None,
            service_name=None,
            provider_quoted_cost=None,
            customer_shipping_cost=None,
            package_length_cm=None,
            package_width_cm=None,
            package_height_cm=None,
            package_weight_grams=None,
            package_is_fragile=None,
            package_is_liquid=None,
            declared_value_irr=None,
            booking_next_attempt_at=None,
            provider_data={"payment_mode": mode.value},
        )
        db.add(shipment)
        await db.flush()
        await _append_event(
            db,
            shipment,
            status=ShipmentStatus.AWAITING_PACKAGING.value,
            description="پرداخت سفارش تأیید شد؛ مرسوله در انتظار بسته‌بندی و اندازه‌گیری است",
            provider_status=None,
            provider_code=None,
            occurred_at=datetime.now(UTC),
            payload={"order_id": order.id, "shipping_payment_mode": mode.value},
        )
        return shipment

    shipment = Shipment(
        public_id=str(uuid4()),
        order_id=order.id,
        quote_id=order.shipping_quote_id,
        provider=order.shipping_provider or PROVIDER_POSTEX,
        status=ShipmentStatus.PENDING_BOOKING.value,
        shipping_payment_mode=mode.value,
        carrier_code=order.shipping_carrier_code,
        service_code=order.shipping_service_code,
        service_name=quote_service_name,
        provider_quoted_cost=order.shipping_provider_quoted_cost,
        customer_shipping_cost=order.shipping_customer_cost,
        package_length_cm=snapshot.get("length_cm"),
        package_width_cm=snapshot.get("width_cm"),
        package_height_cm=snapshot.get("height_cm"),
        package_weight_grams=snapshot.get("weight_grams"),
        package_is_fragile=snapshot.get("is_fragile"),
        package_is_liquid=snapshot.get("is_liquid"),
        provider_box_type_id=snapshot.get("box_type_id"),
        declared_value_irr=Decimal(str(snapshot["declared_value_irr"]))
        if snapshot.get("declared_value_irr")
        else None,
        booking_next_attempt_at=datetime.now(UTC),
        provider_data={"package": snapshot, "payment_mode": mode.value},
    )
    db.add(shipment)
    await db.flush()
    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.PENDING_BOOKING.value,
        description="پرداخت تأیید شد؛ رزرو مرسوله زمان‌بندی شد",
        provider_status=None,
        provider_code=None,
        occurred_at=datetime.now(UTC),
        payload={"order_id": order.id, "shipping_payment_mode": mode.value},
    )
    return shipment


def _contact_from_order(order: Order) -> dict[str, str]:
    first, last = _split_name(order.customer_full_name)
    contact: dict[str, str] = {
        "first_name": first,
        "last_name": last,
        "mobile_no": order.customer_phone,
    }
    company = (order.company_name or "").strip()
    if company:
        contact["company_name"] = company
    return contact


def build_parcel_create_request(order: Order, shipment: Shipment) -> dict[str, Any]:
    missing = []
    if shipment.package_length_cm is None or shipment.package_length_cm <= 0:
        missing.append("package_length_cm")
    if shipment.package_width_cm is None or shipment.package_width_cm <= 0:
        missing.append("package_width_cm")
    if shipment.package_height_cm is None or shipment.package_height_cm <= 0:
        missing.append("package_height_cm")
    if shipment.package_weight_grams is None or shipment.package_weight_grams <= 0:
        missing.append("package_weight_grams")
    if not (shipment.carrier_code or "").strip():
        missing.append("carrier_code")
    if not (shipment.service_code or "").strip():
        missing.append("service_code")
    box_type_id = shipment.provider_box_type_id or (shipment.provider_data or {}).get(
        "package", {}
    ).get("box_type_id")
    if box_type_id is None:
        missing.append("box_type_id")
    mode = shipment_payment_mode(shipment, order)
    # receiver_due requires explicit hazard booleans (admin final package).
    # sender_prepaid may inherit from quote package snapshot (legacy bool()).
    if mode == ShippingPaymentMode.RECEIVER_DUE:
        if shipment.package_is_fragile is None and (shipment.provider_data or {}).get(
            "package", {}
        ).get("is_fragile") is None:
            missing.append("is_fragile")
        if shipment.package_is_liquid is None and (shipment.provider_data or {}).get(
            "package", {}
        ).get("is_liquid") is None:
            missing.append("is_liquid")
    if missing:
        raise ShippingDataIncompleteError(
            "اطلاعات بسته‌بندی مرسوله ناقص است.",
            products=[{"shipment_id": shipment.id, "missing": missing}],
        )

    origin = origin_from_settings()
    shipping = order.shipping or {}
    city_id = int(shipping.get("location_code") or shipping.get("city_id") or 0)
    if city_id <= 0:
        raise ShippingDataIncompleteError(
            "کد شهر مقصد نامعتبر است.",
            products=[{"missing": ["location_code"]}],
        )
    dest_contact = _contact_from_order(order)
    items = []
    for item in order.items:
        items.append(
            {
                "description": item.product_name,
                "sku": item.product_sku,
                "quantity": item.quantity,
                "price": int(toman_to_irr(item.unit_price or 0)),
            }
        )
    pkg = (shipment.provider_data or {}).get("package") or {}
    is_fragile = (
        shipment.package_is_fragile
        if shipment.package_is_fragile is not None
        else bool(pkg.get("is_fragile"))
    )
    is_liquid = (
        shipment.package_is_liquid
        if shipment.package_is_liquid is not None
        else bool(pkg.get("is_liquid"))
    )
    parcel_properties = {
        "length": shipment.package_length_cm,
        "width": shipment.package_width_cm,
        "height": shipment.package_height_cm,
        "total_weight": shipment.package_weight_grams,
        "box_type_id": box_type_id,
        "is_fragile": bool(is_fragile),
        "is_liquid": bool(is_liquid),
        "total_value": int(shipment.declared_value_irr or 0),
        "total_value_currency": "IRR",
    }
    return {
        "collection_type": settings.POSTEX_COLLECTION_TYPE,
        "custom_batch_no": order.tracking_code,
        "custom_channel": "karzar-api",
        "parcels": [
            {
                "from": {
                    "contact": {
                        "first_name": origin.first_name,
                        "last_name": origin.last_name,
                        "mobile_no": origin.mobile,
                        "company_name": origin.company_name,
                    },
                    "location": {
                        "city_id": origin.city_code,
                        "city_name": origin.city_name,
                        "post_code": origin.postal_code,
                        "address": origin.address,
                        "lat": origin.lat,
                        "lon": origin.lon,
                    },
                },
                "to": {
                    "contact": dest_contact,
                    "location": {
                        "city_id": city_id,
                        "city_name": shipping.get("city"),
                        "post_code": shipping.get("postal_code"),
                        "address": shipping.get("address_line") or "",
                    },
                },
                "parcel_items": items,
                "parcel_properties": parcel_properties,
                "courier": {
                    "name": shipment.carrier_code or "",
                    "service_type": shipment.service_code or "",
                    "payment_type": postex_payment_type_for_mode(mode),
                },
                "custom_order_no": shipment.public_id,
                "custom_reference_no": order.tracking_code,
                "ready_to_accept": False,
            }
        ],
    }


def build_parcel_update_request(
    order: Order,
    shipment: Shipment,
    *,
    address_line: str | None = None,
    postal_code: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    mobile_no: str | None = None,
) -> dict[str, Any]:
    """Official UpdateParcelRequest: to + parcel_items + parcel_properties."""
    shipping = dict(order.shipping or {})
    contact = _contact_from_order(order)
    if first_name:
        contact["first_name"] = first_name
    if last_name:
        contact["last_name"] = last_name
    if mobile_no:
        contact["mobile_no"] = mobile_no
    items = []
    for item in order.items:
        items.append(
            {
                "description": item.product_name,
                "sku": item.product_sku,
                "quantity": item.quantity,
                "price": int(toman_to_irr(item.unit_price or 0)),
            }
        )
    return {
        "to": {
            "contact": contact,
            "location": {
                "address": address_line or shipping.get("address_line") or "",
                "post_code": postal_code or shipping.get("postal_code"),
                "city_id": shipping.get("location_code") or shipping.get("city_id"),
                "city_name": shipping.get("city"),
            },
        },
        "parcel_items": items,
        "parcel_properties": {
            "length": shipment.package_length_cm,
            "width": shipment.package_width_cm,
            "height": shipment.package_height_cm,
            "total_weight": shipment.package_weight_grams,
            "box_type_id": (shipment.provider_data or {}).get("package", {}).get("box_type_id"),
            "is_fragile": bool((shipment.provider_data or {}).get("package", {}).get("is_fragile")),
            "is_liquid": bool((shipment.provider_data or {}).get("package", {}).get("is_liquid")),
            "total_value": int(shipment.declared_value_irr or 0),
            "total_value_currency": "IRR",
        },
    }


async def _append_event(
    db: AsyncSession,
    shipment: Shipment,
    *,
    status: str,
    description: str | None,
    provider_status: str | None,
    provider_code: str | None,
    occurred_at: datetime | None,
    payload: dict[str, Any] | None,
    location: str | None = None,
) -> None:
    blob = f"{status}|{provider_status}|{provider_code}|{occurred_at}|{description}"
    dedupe = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:64]
    existing = (
        await db.execute(
            select(ShipmentEvent.id).where(
                ShipmentEvent.shipment_id == shipment.id,
                ShipmentEvent.dedupe_key == dedupe,
            )
        )
    ).first()
    if existing:
        return
    db.add(
        ShipmentEvent(
            shipment_id=shipment.id,
            status=status,
            provider_status=provider_status,
            provider_code=provider_code,
            provider_occurred_at=occurred_at,
            description=description,
            location=location,
            dedupe_key=dedupe,
            payload=redact_secrets(payload) if payload else None,
        )
    )
    await db.flush()


async def apply_tracking_to_order(db: AsyncSession, order: Order) -> None:
    """Map shipment physical states onto OrderStatus without regressing terminals."""
    from app.services.order_service import transition_order_status

    loaded = await db.execute(select(Shipment).where(Shipment.order_id == order.id))
    shipments = list(loaded.scalars().all())
    required = [s for s in shipments if s.status != ShipmentStatus.CANCELLED.value]
    if not required:
        return
    if order.status == OrderStatus.DELIVERED.value:
        return
    if order.status == OrderStatus.CANCELLED.value:
        return

    handoff = any(s.status in {v.value for v in PHYSICAL_HANDOFF_STATUSES} for s in required)
    all_delivered = all(s.status == ShipmentStatus.DELIVERED.value for s in required)

    primary = required[0]
    if primary.tracking_code and not order.postal_tracking_code:
        # Compatibility mirror of the primary shipment barcode only.
        order.postal_tracking_code = primary.tracking_code

    if (
        handoff
        and order.status == OrderStatus.PROCESSING.value
        and primary.tracking_code
        and len(primary.tracking_code) >= 10
    ):
        await transition_order_status(
            db,
            order,
            OrderStatus.SHIPPED.value,
            actor="system",
            postal_tracking_code=primary.tracking_code,
            event_description="شواهد رهگیری پستکس: مرسوله وارد شبکه ارسال شد",
        )
        if primary.shipped_at is None:
            primary.shipped_at = datetime.now(UTC)

    if all_delivered and order.status == OrderStatus.SHIPPED.value:
        await transition_order_status(
            db,
            order,
            OrderStatus.DELIVERED.value,
            actor="system",
            event_description="همه مرسوله‌های الزامی تحویل شدند",
        )
        for shipment in required:
            if shipment.delivered_at is None:
                shipment.delivered_at = datetime.now(UTC)


async def ingest_tracking_events(db: AsyncSession, shipment: Shipment, events: list) -> None:
    current = shipment.status
    for event in events:
        mapped = map_provider_status(
            event_code=event.provider_code,
            event_name=event.provider_status,
            event_desc=event.description,
            current=current,
        )
        await _append_event(
            db,
            shipment,
            status=mapped.value,
            description=event.description,
            provider_status=event.provider_status,
            provider_code=event.provider_code,
            occurred_at=event.occurred_at,
            payload=event.payload,
            location=event.location,
        )
        if can_advance(current, mapped.value):
            current = mapped.value
            shipment.status = mapped.value
            if mapped == ShipmentStatus.CANCELLED and shipment.cancelled_at is None:
                shipment.cancelled_at = datetime.now(UTC)
            if mapped == ShipmentStatus.DELIVERED and shipment.delivered_at is None:
                shipment.delivered_at = datetime.now(UTC)
    shipment.last_tracking_sync_at = datetime.now(UTC)
    await db.flush()


def public_shipment_view(shipment: Shipment) -> dict[str, Any]:
    return {
        "id": shipment.public_id,
        "status": shipment.status,
        "status_label": SHIPMENT_STATUS_LABELS_FA.get(shipment.status, shipment.status),
        "shipping_payment_mode": shipment.shipping_payment_mode,
        "carrier_code": shipment.carrier_code,
        "service_code": shipment.service_code,
        "service_name": shipment.service_name,
        "tracking_code": shipment.tracking_code,
        "shipped_at": shipment.shipped_at,
        "delivered_at": shipment.delivered_at,
        "events": [
            {
                "status": event.status,
                "status_label": SHIPMENT_STATUS_LABELS_FA.get(event.status, event.status),
                "provider_status": event.provider_status,
                "occurred_at": event.provider_occurred_at or event.created_at,
                "description": event.description,
            }
            for event in (shipment.events or [])
        ],
    }


def admin_shipment_view(shipment: Shipment) -> dict[str, Any]:
    view = public_shipment_view(shipment)
    view.update(
        {
            "internal_id": shipment.id,
            "provider": shipment.provider,
            "provider_parcel_no": shipment.provider_parcel_no,
            "quote_id": shipment.quote_id,
            "shipping_payment_mode": shipment.shipping_payment_mode,
            "package": {
                "length_cm": shipment.package_length_cm,
                "width_cm": shipment.package_width_cm,
                "height_cm": shipment.package_height_cm,
                "weight_grams": shipment.package_weight_grams,
                "is_fragile": shipment.package_is_fragile,
                "is_liquid": shipment.package_is_liquid,
                "measured_at": shipment.package_measured_at,
                "provider_box_type_id": shipment.provider_box_type_id,
            },
            "customer_shipping_cost": str(shipment.customer_shipping_cost)
            if shipment.customer_shipping_cost is not None
            else None,
            "provider_quoted_cost": str(shipment.provider_quoted_cost)
            if shipment.provider_quoted_cost is not None
            else None,
            "provider_quoted_at": shipment.provider_quoted_at,
            "provider_actual_cost": str(shipment.provider_actual_cost)
            if shipment.provider_actual_cost is not None
            else None,
            "ready_to_accept": shipment.ready_to_accept,
            "booking_attempts": shipment.booking_attempts,
            "last_tracking_sync_at": shipment.last_tracking_sync_at,
            "last_error_code": shipment.last_error_code,
            "last_error_message": shipment.last_error_message,
            "cancellation_requested_at": shipment.cancellation_requested_at,
        }
    )
    return view


def package_quote_fingerprint(shipment: Shipment, order: Order) -> str:
    """Deterministic fingerprint of measured parcel + destination for quote binding."""
    shipping = order.shipping or {}
    payload = {
        "length_cm": shipment.package_length_cm,
        "width_cm": shipment.package_width_cm,
        "height_cm": shipment.package_height_cm,
        "weight_grams": shipment.package_weight_grams,
        "is_fragile": shipment.package_is_fragile,
        "is_liquid": shipment.package_is_liquid,
        "location_code": int(shipping.get("location_code") or 0),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clear_packed_quote_evidence(shipment: Shipment) -> None:
    """Invalidate quote/service/box evidence after package measurement change."""
    shipment.provider_box_type_id = None
    shipment.provider_quoted_at = None
    shipment.provider_quoted_cost = None
    shipment.carrier_code = None
    shipment.service_code = None
    shipment.service_name = None
    data = dict(shipment.provider_data or {})
    data.pop("packed_quote", None)
    pkg = dict(data.get("package") or {})
    for key in ("box_type_id", "box_name", "quote_fingerprint"):
        pkg.pop(key, None)
    data["package"] = pkg
    shipment.provider_data = data


def _require_receiver_pre_create(shipment: Shipment) -> None:
    if create_attempt_started_safe(shipment):
        raise ShipmentStateError("پس از شروع ثبت مرسوله، تغییر بسته/نرخ مجاز نیست.")
    if shipment.status not in {s.value for s in RECEIVER_PRE_CREATE_MUTABLE_STATUSES}:
        raise ShipmentStateError("وضعیت مرسوله برای این عملیات مناسب نیست.")


async def set_final_package(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    length_cm: int,
    width_cm: int,
    height_cm: int,
    weight_grams: int,
    is_fragile: bool,
    is_liquid: bool,
    actor_user_id: int | None = None,
) -> Shipment:
    """Admin measures the sealed outbound parcel. No Postex HTTP."""
    if shipment.status not in {
        ShipmentStatus.AWAITING_PACKAGING.value,
        ShipmentStatus.READY_TO_BOOK.value,
        ShipmentStatus.FREIGHT_REQUIRED.value,
    }:
        raise ShipmentStateError("ثبت بسته فقط پیش از ایجاد مرسوله پستکس مجاز است.")
    if create_attempt_started_safe(shipment):
        raise ShipmentStateError("مرسوله پس از شروع ثبت قابل اندازه‌گیری مجدد نیست.")
    for label, value in (
        ("length_cm", length_cm),
        ("width_cm", width_cm),
        ("height_cm", height_cm),
        ("weight_grams", weight_grams),
    ):
        if value is None or int(value) <= 0:
            raise LogisticsError(
                f"{label} باید بزرگ‌تر از صفر باشد.",
                error_code="VALIDATION_FAILED",
            )

    clear_packed_quote_evidence(shipment)
    shipment.status = ShipmentStatus.AWAITING_PACKAGING.value
    shipment.booking_next_attempt_at = None
    shipment.package_length_cm = int(length_cm)
    shipment.package_width_cm = int(width_cm)
    shipment.package_height_cm = int(height_cm)
    shipment.package_weight_grams = int(weight_grams)
    shipment.package_is_fragile = bool(is_fragile)
    shipment.package_is_liquid = bool(is_liquid)
    shipment.package_measured_at = datetime.now(UTC)
    # Declared merchandise value from order items (IRR).
    declared = Decimal("0")
    for item in order.items:
        if item.unit_price is not None:
            declared += toman_to_irr(_to_decimal(item.unit_price) * item.quantity)
    shipment.declared_value_irr = declared
    data = dict(shipment.provider_data or {})
    data["package"] = {
        "length_cm": shipment.package_length_cm,
        "width_cm": shipment.package_width_cm,
        "height_cm": shipment.package_height_cm,
        "weight_grams": shipment.package_weight_grams,
        "is_fragile": shipment.package_is_fragile,
        "is_liquid": shipment.package_is_liquid,
        "measured_at": shipment.package_measured_at.isoformat(),
        "actor_user_id": actor_user_id,
    }
    shipment.provider_data = data
    await db.flush()
    await _append_event(
        db,
        shipment,
        status=shipment.status,
        description="ابعاد و وزن نهایی مرسوله ثبت شد",
        provider_status=None,
        provider_code=None,
        occurred_at=datetime.now(UTC),
        payload=data["package"],
    )
    return shipment


def create_attempt_started_safe(shipment: Shipment) -> bool:
    if (shipment.provider_parcel_no or "").strip():
        return True
    if shipment.status in {
        ShipmentStatus.BOOKING.value,
        ShipmentStatus.CREATION_UNCERTAIN.value,
        ShipmentStatus.BOOKED.value,
    }:
        return True
    data = shipment.provider_data or {}
    if data.get("create_attempted"):
        return True
    return int(shipment.booking_attempts or 0) > 0


async def quote_packed_shipment(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
) -> dict[str, Any]:
    """Quote Postex for a measured final parcel (RECEIVER payment_type). No create."""
    if shipment_payment_mode(shipment, order) != ShippingPaymentMode.RECEIVER_DUE:
        raise LogisticsError(
            "نرخ‌گیری بسته‌بندی‌شده فقط برای پس‌کرایه است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    _require_receiver_pre_create(shipment)
    if shipment.package_length_cm is None or shipment.package_weight_grams is None:
        raise ShippingDataIncompleteError(
            "ابتدا ابعاد و وزن نهایی را ثبت کنید.",
            products=[{"shipment_id": shipment.id, "missing": ["final_package"]}],
        )
    if shipment.package_is_fragile is None or shipment.package_is_liquid is None:
        raise ShippingDataIncompleteError(
            "پرچم شکننده/مایع باید صریح باشد.",
            products=[{"shipment_id": shipment.id, "missing": ["hazards"]}],
        )

    from app.services.logistics.models import PackageSpec

    package = PackageSpec(
        length_cm=int(shipment.package_length_cm),
        width_cm=int(shipment.package_width_cm or 0),
        height_cm=int(shipment.package_height_cm or 0),
        weight_grams=int(shipment.package_weight_grams),
        is_fragile=bool(shipment.package_is_fragile),
        is_liquid=bool(shipment.package_is_liquid),
    )
    provider = get_provider()
    boxes = await _cached_boxes(provider)
    try:
        fitted = select_box(package, boxes)
    except ShippingFreightRequiredError:
        # Persist before the API layer commits and returns freight-required.
        shipment.status = ShipmentStatus.FREIGHT_REQUIRED.value
        shipment.booking_next_attempt_at = None
        clear_packed_quote_evidence(shipment)
        await db.flush()
        raise

    shipping = order.shipping or {}
    city_id = int(shipping.get("location_code") or 0)
    destination = Destination(
        location_code=city_id,
        city_name=shipping.get("city"),
        province_name=shipping.get("province"),
        postal_code=shipping.get("postal_code"),
    )
    quote = await provider.quote(
        origin=origin_from_settings(),
        destination=destination,
        package=fitted,
        declared_value_irr=shipment.declared_value_irr or Decimal("0"),
        payment_type=postex_payment_type_for_mode(ShippingPaymentMode.RECEIVER_DUE),
        collection_type=settings.POSTEX_COLLECTION_TYPE,
    )
    fingerprint = package_quote_fingerprint(shipment, order)
    # New quote invalidates prior service selection.
    shipment.carrier_code = None
    shipment.service_code = None
    shipment.service_name = None
    shipment.provider_box_type_id = fitted.box_type_id
    shipment.provider_quoted_at = datetime.now(UTC)
    # Audit only — does not change order.estimated_total / SEP.
    if quote.options:
        from app.services.logistics.money import provider_total_toman

        first = quote.options[0]
        shipment.provider_quoted_cost = provider_total_toman(
            provider_amount_toman=first.provider_amount_toman,
            pickup_amount_toman=first.pickup_amount_toman,
        )
    data = dict(shipment.provider_data or {})
    data["packed_quote"] = {
        "quoted_at": shipment.provider_quoted_at.isoformat(),
        "box_type_id": fitted.box_type_id,
        "package_fingerprint": fingerprint,
        "options": [
            {
                "carrier_code": o.carrier_code,
                "service_code": o.service_code,
                "service_name": o.service_name,
                "customer_amount_toman": str(o.customer_amount_toman),
                "provider_amount_toman": str(o.provider_amount_toman),
                "pickup_amount_toman": str(o.pickup_amount_toman)
                if o.pickup_amount_toman is not None
                else None,
            }
            for o in quote.options
        ],
    }
    data["package"] = {
        **(data.get("package") or {}),
        "box_type_id": fitted.box_type_id,
        "box_name": fitted.box_name,
        "quote_fingerprint": fingerprint,
        # Keep measured dims (do not overwrite with box dims).
        "length_cm": package.length_cm,
        "width_cm": package.width_cm,
        "height_cm": package.height_cm,
        "weight_grams": package.weight_grams,
        "is_fragile": package.is_fragile,
        "is_liquid": package.is_liquid,
    }
    shipment.provider_data = data
    if shipment.status == ShipmentStatus.READY_TO_BOOK.value:
        shipment.status = ShipmentStatus.AWAITING_PACKAGING.value
        shipment.booking_next_attempt_at = None
    await db.flush()
    return {
        "shipment": admin_shipment_view(shipment),
        "options": data["packed_quote"]["options"],
        "package_fingerprint": fingerprint,
        "order_estimated_total_unchanged": str(order.estimated_total)
        if order.estimated_total is not None
        else None,
    }


async def select_packed_service(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    carrier_code: str,
    service_code: str,
) -> Shipment:
    if shipment_payment_mode(shipment, order) != ShippingPaymentMode.RECEIVER_DUE:
        raise LogisticsError(
            "انتخاب سرویس بسته‌بندی‌شده فقط برای پس‌کرایه است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    _require_receiver_pre_create(shipment)
    packed = (shipment.provider_data or {}).get("packed_quote") or {}
    stored_fp = packed.get("package_fingerprint")
    current_fp = package_quote_fingerprint(shipment, order)
    if not stored_fp or stored_fp != current_fp:
        raise LogisticsError(
            "نرخ ذخیره‌شده با بسته/مقصد فعلی هم‌خوانی ندارد؛ دوباره نرخ بگیرید.",
            error_code="SHIPPING_QUOTE_STALE",
        )
    options = packed.get("options") or []
    match = next(
        (
            o
            for o in options
            if o.get("carrier_code") == carrier_code and o.get("service_code") == service_code
        ),
        None,
    )
    if match is None:
        raise LogisticsError("سرویس انتخاب‌شده در نرخ‌گیری یافت نشد.", error_code="VALIDATION_FAILED")
    shipment.carrier_code = carrier_code
    shipment.service_code = service_code
    shipment.service_name = match.get("service_name")
    if match.get("provider_amount_toman") is not None:
        from decimal import Decimal as D

        from app.services.logistics.money import provider_total_toman

        pickup = match.get("pickup_amount_toman")
        shipment.provider_quoted_cost = provider_total_toman(
            provider_amount_toman=D(str(match["provider_amount_toman"])),
            pickup_amount_toman=D(str(pickup)) if pickup is not None else None,
        )
    await db.flush()
    await _append_event(
        db,
        shipment,
        status=shipment.status,
        description=f"سرویس {carrier_code}/{service_code} انتخاب شد",
        provider_status=None,
        provider_code=None,
        occurred_at=datetime.now(UTC),
        payload={
            "carrier_code": carrier_code,
            "service_code": service_code,
            "package_fingerprint": current_fp,
        },
    )
    return shipment


async def schedule_receiver_booking(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
) -> Shipment:
    """Mark receiver_due shipment ready_to_book. Worker must NOT claim this status."""
    if shipment_payment_mode(shipment, order) != ShippingPaymentMode.RECEIVER_DUE:
        raise LogisticsError(
            "آماده‌سازی رزرو پس‌کرایه فقط برای receiver_due است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    _require_receiver_pre_create(shipment)
    shipping = order.shipping or {}
    if not int(shipping.get("location_code") or 0):
        raise ShippingDataIncompleteError(
            "کد شهر مقصد الزامی است.",
            products=[{"missing": ["location_code"]}],
        )
    packed = (shipment.provider_data or {}).get("packed_quote") or {}
    stored_fp = packed.get("package_fingerprint")
    current_fp = package_quote_fingerprint(shipment, order)
    if not stored_fp or stored_fp != current_fp:
        raise LogisticsError(
            "نرخ ذخیره‌شده با بسته/مقصد فعلی هم‌خوانی ندارد؛ دوباره نرخ بگیرید.",
            error_code="SHIPPING_QUOTE_STALE",
        )
    missing = receiver_due_booking_ready(shipment)
    if missing:
        raise ShippingDataIncompleteError(
            "پیش‌نیاز رزرو ناقص است.",
            products=[{"missing": missing}],
        )
    shipment.status = ShipmentStatus.READY_TO_BOOK.value
    # Explicit admin /book only — never queue for the background worker.
    shipment.booking_next_attempt_at = None
    await db.flush()
    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.READY_TO_BOOK.value,
        description="مرسوله آماده ثبت صریح در پستکس است",
        provider_status=None,
        provider_code=None,
        occurred_at=datetime.now(UTC),
        payload={
            "shipping_payment_mode": ShippingPaymentMode.RECEIVER_DUE.value,
            "package_fingerprint": current_fp,
        },
    )
    return shipment


async def get_shipment_for_order(
    db: AsyncSession, order_id: int, shipment_id: int, *, for_update: bool = False
) -> Shipment:
    stmt = (
        select(Shipment)
        .where(Shipment.id == shipment_id, Shipment.order_id == order_id)
        .options(selectinload(Shipment.events))
    )
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    shipment = (await db.execute(stmt)).scalars().first()
    if shipment is None:
        raise ShipmentNotFoundError("مرسوله یافت نشد")
    return shipment
