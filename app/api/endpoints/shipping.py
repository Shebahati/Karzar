"""Karzar logistics endpoints. No generic Postex proxy."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import NoReturn

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user, get_current_super_admin
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.security import verify_step_up_token
from app.crud import commerce as crud_commerce
from app.crud import platform as crud_platform
from app.crud import product as crud_product
from app.db.database import get_db
from app.db.models.logistics import Shipment
from app.db.models.user import User
from app.schemas.shipping import (
    PostexHealthResponse,
    ShipmentAdminResponse,
    ShipmentCancelRequest,
    ShipmentEditRequest,
    ShipmentFinalPackageRequest,
    ShipmentManualPortalCorrectionRequest,
    ShipmentManualPortalRegistrationRequest,
    ShipmentManualRegisterRequest,
    ShipmentSelectServiceRequest,
    ShippingCityListResponse,
    ShippingCityResponse,
    ShippingMethodOptionResponse,
    ShippingOptionsRequest,
    ShippingOptionsResponse,
    ShippingQuoteRequest,
    ShippingQuoteResponse,
    ShippingStatusResponse,
)
from app.services.logistics.booking_worker import book_shipment, request_shipment_cancellation
from app.services.logistics.exceptions import (
    LogisticsError,
    ProviderError,
    ShipmentStateError,
    ShippingDataIncompleteError,
    ShippingFreightRequiredError,
)
from app.services.logistics.fingerprints import canonical_cart_items
from app.services.logistics.fulfillment_mode import configured_fulfillment_mode
from app.services.logistics.manual_fulfillment import (
    manual_deliver,
    manual_handoff,
    manual_register,
)
from app.services.logistics.manual_portal_guard import (
    lock_order_and_shipment,
    reject_generic_postex_provider_path,
    reject_postex_admin_automation_path,
)
from app.services.logistics.manual_portal_service import (
    confirm_manual_delivery,
    confirm_manual_physical_handoff,
    correct_manual_portal_registration,
    register_manual_portal_shipment,
)
from app.services.logistics.models import (
    READY_ELIGIBLE_STATUSES,
    TERMINAL_SHIPMENT_STATUSES,
    Destination,
    ShipmentStatus,
)
from app.services.logistics.service import (
    admin_shipment_view,
    apply_tracking_to_order,
    create_quote,
    get_provider,
    get_shipment_for_order,
    ingest_tracking_events,
    last_success_timestamps,
    list_public_cities,
    package_quote_fingerprint,
    postex_enabled,
    quote_packed_shipment,
    receiver_due_booking_ready,
    require_postex_booking_enabled,
    schedule_receiver_booking,
    select_packed_service,
    set_final_package,
    shipment_payment_mode,
)
from app.services.logistics.shipping_methods import (
    RECEIVER_DUE_PRICE_LABEL,
    ShippingDestination,
    list_available_methods,
    postex_checkout_enabled,
    public_purchase_shipping_available,
    storefront_shipping_enabled,
)
from app.services.logistics.shipping_payment import (
    ShippingPaymentMode,
    default_shipping_payment_mode,
    postex_booking_enabled,
)

router = APIRouter()


def _http_for(exc: LogisticsError) -> tuple[int, str]:
    mapping = {
        "SHIPPING_DATA_INCOMPLETE": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.SHIPPING_DATA_INCOMPLETE,
        ),
        "SHIPPING_FREIGHT_REQUIRED": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.SHIPPING_FREIGHT_REQUIRED,
        ),
        "SHIPPING_UNAVAILABLE": (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SHIPPING_UNAVAILABLE,
        ),
        "SHIPPING_QUOTE_EXPIRED": (status.HTTP_409_CONFLICT, ErrorCode.SHIPPING_QUOTE_EXPIRED),
        "SHIPPING_DESTINATION_INVALID": (
            status.HTTP_409_CONFLICT,
            ErrorCode.SHIPPING_DESTINATION_INVALID,
        ),
        "SHIPPING_QUOTE_MISMATCH": (status.HTTP_409_CONFLICT, ErrorCode.SHIPPING_QUOTE_MISMATCH),
        "SHIPPING_QUOTE_CONSUMED": (status.HTTP_409_CONFLICT, ErrorCode.SHIPPING_QUOTE_CONSUMED),
        "SHIPPING_QUOTE_STALE": (status.HTTP_409_CONFLICT, ErrorCode.SHIPPING_QUOTE_STALE),
        "SHIPMENT_NOT_FOUND": (status.HTTP_404_NOT_FOUND, ErrorCode.SHIPMENT_NOT_FOUND),
        "SHIPMENT_STATE_INVALID": (status.HTTP_409_CONFLICT, ErrorCode.SHIPMENT_STATE_INVALID),
        "SHIPPING_PROVIDER_CUTOFF": (status.HTTP_409_CONFLICT, ErrorCode.SHIPPING_PROVIDER_CUTOFF),
        "SHIPPING_PROVIDER_AUTH": (status.HTTP_502_BAD_GATEWAY, ErrorCode.SHIPPING_UNAVAILABLE),
        "SHIPPING_PROVIDER_VALIDATION": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.VALIDATION_FAILED,
        ),
        "SHIPPING_PROVIDER_NOT_FOUND": (status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND),
        "SHIPPING_BOOKING_DISABLED": (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SHIPPING_BOOKING_DISABLED,
        ),
        "VALIDATION_FAILED": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.VALIDATION_FAILED,
        ),
        "SHIPPING_METHOD_REQUIRED": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.SHIPPING_METHOD_REQUIRED,
        ),
        "SHIPPING_METHOD_INVALID": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ErrorCode.SHIPPING_METHOD_INVALID,
        ),
        "SHIPPING_METHOD_UNAVAILABLE": (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ErrorCode.SHIPPING_METHOD_UNAVAILABLE,
        ),
        "SHIPPING_METHOD_DESTINATION_NOT_ELIGIBLE": (
            status.HTTP_409_CONFLICT,
            ErrorCode.SHIPPING_METHOD_DESTINATION_NOT_ELIGIBLE,
        ),
        "CONFLICT": (status.HTTP_409_CONFLICT, ErrorCode.CONFLICT),
    }
    code = getattr(exc, "error_code", "SHIPPING_ERROR")
    http_status, error_code = mapping.get(
        code, (status.HTTP_400_BAD_REQUEST, ErrorCode.BAD_REQUEST)
    )
    return http_status, error_code


def _raise_logistics(exc: LogisticsError) -> NoReturn:
    http_status, error_code = _http_for(exc)
    details = None
    if isinstance(exc, ShippingDataIncompleteError):
        details = [{"field": "products", "message": str(item)} for item in exc.products]
    raise api_error(
        http_status,
        error_code=error_code,
        message=str(exc),
        details=details,
    ) from exc


def _reject_generic_postex_provider_path(shipment: Shipment) -> None:
    try:
        reject_generic_postex_provider_path(shipment)
    except ShipmentStateError as exc:
        _raise_logistics(exc)


async def _shipment_or_raise(
    db: AsyncSession, order_id: int, shipment_id: int, *, for_update: bool = False
) -> Shipment:
    try:
        return await get_shipment_for_order(db, order_id, shipment_id, for_update=for_update)
    except LogisticsError as exc:
        _raise_logistics(exc)


@router.get("/shipping/status", response_model=ShippingStatusResponse)
async def shipping_status() -> ShippingStatusResponse:
    methods_on = storefront_shipping_enabled()
    postex_checkout_on = postex_checkout_enabled()
    enabled = public_purchase_shipping_available()
    mode = None
    if methods_on:
        mode = ShippingPaymentMode.RECEIVER_DUE
    elif postex_checkout_on:
        mode = default_shipping_payment_mode()
    return ShippingStatusResponse(
        enabled=enabled,
        quote_ttl_seconds=settings.POSTEX_QUOTE_TTL_SECONDS,
        shipping_payment_mode=mode.value if mode else None,
        checkout_quote_required=bool(
            postex_checkout_on
            and not methods_on
            and mode == ShippingPaymentMode.SENDER_PREPAID
        ),
        booking_enabled=postex_booking_enabled(),
        method_selection_enabled=methods_on,
        fulfillment_mode=(
            configured_fulfillment_mode().value if postex_enabled() else None
        ),
    )


@router.post("/shipping/options", response_model=ShippingOptionsResponse)
async def shipping_options(payload: ShippingOptionsRequest) -> ShippingOptionsResponse:
    if not storefront_shipping_enabled():
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SHIPPING_UNAVAILABLE,
            message="سرویس ارسال فعال نیست.",
        )
    destination = ShippingDestination(
        province=payload.province,
        city=payload.city,
        postal_code=payload.postal_code,
    )
    options = [
        ShippingMethodOptionResponse(
            code=m.code.value,
            title=m.title,
            payment_mode=m.payment_mode.value,
            price=None,
            price_label=m.price_label or RECEIVER_DUE_PRICE_LABEL,
        )
        for m in list_available_methods(destination)
    ]
    return ShippingOptionsResponse(options=options)


@router.get("/shipping/cities", response_model=ShippingCityListResponse)
async def shipping_cities(
    _: User = Depends(get_current_active_user),
):
    try:
        rows = await list_public_cities()
    except LogisticsError as exc:
        _raise_logistics(exc)
    return ShippingCityListResponse(data=[ShippingCityResponse(**row) for row in rows])


@router.post("/shipping/quotes", response_model=ShippingQuoteResponse)
async def create_shipping_quote(
    payload: ShippingQuoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not postex_enabled():
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SHIPPING_UNAVAILABLE,
            message="ارسال پستی فعال نیست.",
        )
    items = canonical_cart_items(
        [{"product_id": line.product_id, "quantity": line.quantity} for line in payload.items]
    )
    products = await crud_product.get_products_by_ids(db, [item["product_id"] for item in items])
    try:
        result = await create_quote(
            db,
            user_id=current_user.id,
            items=items,
            destination=Destination(
                location_code=payload.location_code,
                city_name=payload.city_name,
                province_name=payload.province_name,
                postal_code=payload.postal_code,
            ),
            products=products,
        )
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    return ShippingQuoteResponse(**result)


@router.get(
    "/admin/shipping/health",
    response_model=PostexHealthResponse,
    tags=["Admin Shipping"],
)
async def postex_health(_: User = Depends(get_current_super_admin)):
    configured = bool((settings.POSTEX_API_KEY or "").strip())
    whoami_ok: bool | None = None
    if postex_enabled() and configured:
        try:
            await get_provider().whoami()
            whoami_ok = True
        except Exception:
            whoami_ok = False
    return PostexHealthResponse(
        enabled=postex_enabled(),
        configured=configured,
        whoami_ok=whoami_ok,
        last_success=last_success_timestamps(),
    )


@router.get(
    "/admin/shipping/wallet",
    tags=["Admin Shipping"],
)
async def postex_wallet(_: User = Depends(get_current_super_admin)):
    if not postex_enabled():
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SHIPPING_UNAVAILABLE,
            message="ارسال پستی فعال نیست.",
        )
    try:
        return await get_provider().wallet_balance()
    except LogisticsError as exc:
        _raise_logistics(exc)


@router.get(
    "/orders/{order_id}/shipments",
    response_model=list[ShipmentAdminResponse],
    tags=["Admin Shipping"],
)
async def list_order_shipments(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    rows = (
        (
            await db.execute(
                select(Shipment)
                .where(Shipment.order_id == order_id)
                .options(selectinload(Shipment.events))
                .order_by(Shipment.id)
            )
        )
        .scalars()
        .all()
    )
    return [ShipmentAdminResponse(**admin_shipment_view(row)) for row in rows]


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual/register",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_register(
    order_id: int,
    shipment_id: int,
    payload: ShipmentManualRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    try:
        shipment = await manual_register(
            db,
            order=order,
            shipment=shipment,
            tracking_code=payload.tracking_code,
            provider_reference=payload.provider_reference,
            note=payload.note,
            courier_name=payload.courier_name,
            courier_phone=payload.courier_phone,
            mission_reference=payload.mission_reference,
            actor_user_id=current_user.id,
        )
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual/handoff",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_handoff(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    try:
        shipment = await manual_handoff(
            db,
            order=order,
            shipment=shipment,
            actor_user_id=current_user.id,
        )
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual/deliver",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_deliver(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    try:
        shipment = await manual_deliver(
            db,
            order=order,
            shipment=shipment,
            actor_user_id=current_user.id,
        )
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/final-package",
    tags=["Admin Shipping"],
)
async def admin_set_final_package(
    order_id: int,
    shipment_id: int,
    payload: ShipmentFinalPackageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """Record sealed outbound parcel measurements. No Postex HTTP."""
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    _reject_generic_postex_provider_path(shipment)
    order = await crud_commerce.get_order_by_id(db, order_id)
    if order is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="سفارش یافت نشد.",
        )
    try:
        shipment = await set_final_package(
            db,
            order=order,
            shipment=shipment,
            length_cm=payload.length_cm,
            width_cm=payload.width_cm,
            height_cm=payload.height_cm,
            weight_grams=payload.weight_grams,
            is_fragile=payload.is_fragile,
            is_liquid=payload.is_liquid,
            actor_user_id=current_user.id,
        )
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return admin_shipment_view(shipment)


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/packed-quote",
    tags=["Admin Shipping"],
)
async def admin_packed_quote(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    """Quote Postex for a measured receiver_due parcel (payment_type=RECEIVER)."""
    if not postex_enabled():
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.SHIPPING_UNAVAILABLE,
            message="ارسال پستی فعال نیست.",
        )
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    try:
        reject_postex_admin_automation_path(shipment)
    except LogisticsError as exc:
        _raise_logistics(exc)
    order = await crud_commerce.get_order_by_id(db, order_id)
    if order is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="سفارش یافت نشد.",
        )
    try:
        result = await quote_packed_shipment(db, order=order, shipment=shipment)
    except ShippingFreightRequiredError as exc:
        # Durable freight_required before returning the user-facing error.
        await db.commit()
        _raise_logistics(exc)
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    return result


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/select-service",
    tags=["Admin Shipping"],
)
async def admin_select_packed_service(
    order_id: int,
    shipment_id: int,
    payload: ShipmentSelectServiceRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    try:
        reject_postex_admin_automation_path(shipment)
    except LogisticsError as exc:
        _raise_logistics(exc)
    order = await crud_commerce.get_order_by_id(db, order_id)
    if order is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="سفارش یافت نشد.",
        )
    try:
        shipment = await select_packed_service(
            db,
            order=order,
            shipment=shipment,
            carrier_code=payload.carrier_code,
            service_code=payload.service_code,
        )
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return admin_shipment_view(shipment)


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/schedule-booking",
    tags=["Admin Shipping"],
)
async def admin_schedule_receiver_booking(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    """Mark receiver_due shipment ready_to_book (not worker-claimable)."""
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    try:
        reject_postex_admin_automation_path(shipment)
    except LogisticsError as exc:
        _raise_logistics(exc)
    order = await crud_commerce.get_order_by_id(db, order_id)
    if order is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="سفارش یافت نشد.",
        )
    try:
        shipment = await schedule_receiver_booking(db, order=order, shipment=shipment)
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return admin_shipment_view(shipment)


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/book",
    tags=["Admin Shipping"],
)
async def admin_book_shipment(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    try:
        reject_postex_admin_automation_path(shipment)
    except LogisticsError as exc:
        _raise_logistics(exc)
    try:
        require_postex_booking_enabled()
    except LogisticsError as exc:
        _raise_logistics(exc)
    if shipment.status in {status.value for status in TERMINAL_SHIPMENT_STATUSES}:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="این مرسوله قابل رزرو مجدد نیست.",
        )
    if shipment.status == ShipmentStatus.AWAITING_PACKAGING.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="ابتدا بسته‌بندی، نرخ‌گیری و آماده‌سازی ثبت را تکمیل کنید.",
        )
    order = await crud_commerce.get_order_by_id(db, order_id)
    if order is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="سفارش یافت نشد.",
        )
    if shipment_payment_mode(shipment, order) == ShippingPaymentMode.RECEIVER_DUE:
        if shipment.status != ShipmentStatus.READY_TO_BOOK.value and shipment.status not in {
            ShipmentStatus.ERROR.value,
            ShipmentStatus.CREATION_UNCERTAIN.value,
            ShipmentStatus.PENDING_BOOKING.value,
            ShipmentStatus.BOOKING.value,
        }:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.SHIPMENT_STATE_INVALID,
                message="مرسوله پس‌کرایه باید در وضعیت آماده ثبت باشد.",
            )
        if shipment.status == ShipmentStatus.READY_TO_BOOK.value:
            missing = receiver_due_booking_ready(shipment)
            if missing:
                raise api_error(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    error_code=ErrorCode.SHIPPING_DATA_INCOMPLETE,
                    message="پیش‌نیاز ثبت مرسوله ناقص است.",
                    details=[{"field": "missing", "message": str(missing)}],
                )
            packed = (shipment.provider_data or {}).get("packed_quote") or {}
            if packed.get("package_fingerprint") != package_quote_fingerprint(shipment, order):
                raise api_error(
                    status.HTTP_409_CONFLICT,
                    error_code=ErrorCode.SHIPPING_QUOTE_STALE,
                    message="نرخ ذخیره‌شده با بسته/مقصد فعلی هم‌خوانی ندارد.",
                )
            # Explicit book only: do not set booking_next_attempt_at for worker claim.
            shipment.status = ShipmentStatus.PENDING_BOOKING.value
            shipment.booking_next_attempt_at = None
            await db.flush()
    await book_shipment(db, shipment.id)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return admin_shipment_view(shipment)


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/ready",
    tags=["Admin Shipping"],
)
async def admin_mark_ready(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    _reject_generic_postex_provider_path(shipment)
    try:
        require_postex_booking_enabled()
    except LogisticsError as exc:
        _raise_logistics(exc)
    if not shipment.provider_parcel_no:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="شناسه مرسوله پستکس موجود نیست.",
        )
    if shipment.status not in {status.value for status in READY_ELIGIBLE_STATUSES}:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="این مرسوله در وضعیت فعلی قابل آماده به ارسال شدن نیست.",
        )
    if (
        shipment.status == ShipmentStatus.READY_FOR_PICKUP.value
        and shipment.ready_to_accept
    ):
        return admin_shipment_view(shipment)
    try:
        await get_provider().mark_ready([int(shipment.provider_parcel_no)])
    except LogisticsError as exc:
        _raise_logistics(exc)
    shipment.ready_to_accept = True
    shipment.status = ShipmentStatus.READY_FOR_PICKUP.value
    await db.commit()
    return admin_shipment_view(shipment)


@router.get(
    "/orders/{order_id}/shipments/{shipment_id}/label",
    tags=["Admin Shipping"],
)
async def admin_shipment_label(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    shipment = await _shipment_or_raise(db, order_id, shipment_id)
    _reject_generic_postex_provider_path(shipment)
    if not shipment.provider_parcel_no:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="برچسب پس از ثبت مرسوله در دسترس است.",
        )
    try:
        pdf = await get_provider().fetch_label_pdf(str(shipment.provider_parcel_no))
    except LogisticsError as exc:
        _raise_logistics(exc)
    filename = f"karzar-label-{shipment.provider_parcel_no}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/refresh-tracking",
    tags=["Admin Shipping"],
)
async def admin_refresh_tracking(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    shipment = await _shipment_or_raise(db, order_id, shipment_id)
    _reject_generic_postex_provider_path(shipment)
    if not shipment.provider_parcel_no:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="مرسوله هنوز در پستکس ثبت نشده است.",
        )
    try:
        events = await get_provider().tracking_events(str(shipment.provider_parcel_no))
        await ingest_tracking_events(db, shipment, events)
        order = await crud_commerce.get_order_by_id(db, order_id)
        if order is not None:
            await apply_tracking_to_order(db, order)
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    return admin_shipment_view(shipment)


_EDITABLE_STATUSES = {
    ShipmentStatus.BOOKED.value,
    ShipmentStatus.READY_FOR_PICKUP.value,
}


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/edit",
    tags=["Admin Shipping"],
)
async def admin_edit_shipment(
    order_id: int,
    shipment_id: int,
    payload: ShipmentEditRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    from app.services.logistics.service import build_parcel_update_request

    shipment = await _shipment_or_raise(db, order_id, shipment_id)
    _reject_generic_postex_provider_path(shipment)
    try:
        require_postex_booking_enabled()
    except LogisticsError as exc:
        _raise_logistics(exc)
    if shipment.status not in _EDITABLE_STATUSES:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="ویرایش مرسوله در این وضعیت مجاز نیست.",
        )
    if not shipment.provider_parcel_no:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SHIPMENT_STATE_INVALID,
            message="مرسوله هنوز در پستکس ثبت نشده است.",
        )
    order = await crud_commerce.get_order_by_id(db, order_id)
    if order is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="سفارش یافت نشد.",
        )
    body = build_parcel_update_request(
        order,
        shipment,
        address_line=payload.address_line,
        postal_code=payload.postal_code,
        first_name=payload.first_name,
        last_name=payload.last_name,
        mobile_no=payload.mobile_no,
    )
    try:
        await get_provider().update_parcel(str(shipment.provider_parcel_no), body)
    except ProviderError as exc:
        if getattr(exc, "http_status", None) in {400, 409, 422}:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.SHIPPING_PROVIDER_CUTOFF,
                message="پستکس ویرایش را در این مرحله نپذیرفت.",
            ) from exc
        _raise_logistics(exc)
    await db.commit()
    return admin_shipment_view(shipment)


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/cancel",
    tags=["Admin Shipping"],
)
async def admin_cancel_shipment(
    order_id: int,
    shipment_id: int,
    payload: ShipmentCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
):
    if not x_step_up_token:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_REQUIRED,
            message="Step-up authentication required to cancel a shipment",
        )
    step_up_payload = verify_step_up_token(x_step_up_token)
    if step_up_payload.get("sub") != current_user.phone_number:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )
    consumed = await crud_platform.consume_step_up_jti(
        db,
        jti=step_up_payload["jti"],
        expires_at=datetime.fromtimestamp(step_up_payload["exp"], tz=UTC),
    )
    if not consumed:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Step-up token has already been used",
        )
    shipment = await _shipment_or_raise(db, order_id, shipment_id, for_update=True)
    _reject_generic_postex_provider_path(shipment)
    try:
        shipment = await request_shipment_cancellation(db, shipment_id, payload.reason)
    except ProviderError as exc:
        if getattr(exc, "http_status", None) in {400, 409, 422}:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.SHIPPING_PROVIDER_CUTOFF,
                message="پستکس انصراف را در این مرحله نپذیرفت.",
            ) from exc
        _raise_logistics(exc)
    except LogisticsError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return admin_shipment_view(shipment)


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_portal_register(
    order_id: int,
    shipment_id: int,
    payload: ShipmentManualPortalRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """Record Postex portal tracking/parcel refs. No Postex HTTP."""
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    try:
        shipment = await register_manual_portal_shipment(
            db,
            order=order,
            shipment=shipment,
            tracking_code=payload.tracking_code,
            provider_parcel_no=payload.provider_parcel_no,
            carrier_code=payload.carrier_code,
            service_code=payload.service_code,
            internal_note=payload.internal_note,
            actor_user_id=current_user.id,
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual-portal/correct",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_portal_correct(
    order_id: int,
    shipment_id: int,
    payload: ShipmentManualPortalCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
):
    if not x_step_up_token:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_REQUIRED,
            message="Step-up authentication required to correct a manual-portal shipment",
        )
    step_up_payload = verify_step_up_token(x_step_up_token)
    if step_up_payload.get("sub") != current_user.phone_number:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )
    consumed = await crud_platform.consume_step_up_jti(
        db,
        jti=step_up_payload["jti"],
        expires_at=datetime.fromtimestamp(step_up_payload["exp"], tz=UTC),
    )
    if not consumed:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Step-up token has already been used",
        )
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    update_fields = frozenset(payload.model_fields_set)
    try:
        shipment = await correct_manual_portal_registration(
            db,
            order=order,
            shipment=shipment,
            tracking_code=payload.tracking_code,
            update_fields=update_fields,
            provider_parcel_no=payload.provider_parcel_no,
            carrier_code=payload.carrier_code,
            service_code=payload.service_code,
            internal_note=payload.internal_note,
            actor_user_id=current_user.id,
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_portal_handoff(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """Confirm physical handoff to carrier. No Postex HTTP."""
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    try:
        order, shipment = await confirm_manual_physical_handoff(
            db,
            order=order,
            shipment=shipment,
            actor_user_id=current_user.id,
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))


@router.post(
    "/orders/{order_id}/shipments/{shipment_id}/manual-portal/deliver",
    response_model=ShipmentAdminResponse,
    tags=["Admin Shipping"],
)
async def admin_manual_portal_deliver(
    order_id: int,
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """Confirm customer delivery for manual-portal shipment. No Postex HTTP."""
    try:
        order, shipment = await lock_order_and_shipment(
            db, order_id=order_id, shipment_id=shipment_id
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    try:
        order, shipment = await confirm_manual_delivery(
            db,
            order=order,
            shipment=shipment,
            actor_user_id=current_user.id,
        )
    except ShipmentStateError as exc:
        _raise_logistics(exc)
    await db.commit()
    await db.refresh(shipment, ["events"])
    return ShipmentAdminResponse(**admin_shipment_view(shipment))
