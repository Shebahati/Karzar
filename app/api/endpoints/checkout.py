"""Storefront checkout endpoint."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.request_throttle import enforce_public_throttle
from app.crud import platform as crud_platform
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.storefront import CheckoutRequest, CheckoutResponse
from app.services.checkout_service import PurchaseAuthRequiredError, submit_checkout

router = APIRouter()


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Storefront"],
)
async def checkout(
    payload: CheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_cart_token: str | None = Header(None, alias="X-Cart-Token"),
):
    idempotency_scope = "checkout"
    if current_user is not None:
        idempotency_scope = f"checkout:user:{current_user.id}"
    elif x_cart_token and x_cart_token.strip():
        guest_fingerprint = sha256(x_cart_token.strip().encode("utf-8")).hexdigest()[:12]
        idempotency_scope = f"co:guest:{guest_fingerprint}"

    await enforce_public_throttle(
        request,
        scope="checkout",
        max_requests=settings.PUBLIC_THROTTLE_CHECKOUT_MAX,
        window_seconds=settings.PUBLIC_THROTTLE_CHECKOUT_WINDOW,
    )
    if idempotency_key and idempotency_key.strip():
        normalized_key = idempotency_key.strip()
        cached = await crud_platform.get_idempotency_record(
            db, scope=idempotency_scope, key=normalized_key
        )
        if cached is not None and cached.status_code > 0:
            return JSONResponse(status_code=cached.status_code, content=cached.response_body)
        reserved = await crud_platform.reserve_idempotency_record(
            db,
            scope=idempotency_scope,
            key=normalized_key,
            expires_at=datetime.now(UTC) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
        )
        if not reserved:
            existing = await crud_platform.get_idempotency_record(
                db, scope=idempotency_scope, key=normalized_key
            )
            if existing is not None and existing.status_code > 0:
                return JSONResponse(status_code=existing.status_code, content=existing.response_body)
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message="Another request with this Idempotency-Key is currently in progress",
            )
        await db.commit()

    try:
        result = await submit_checkout(
            db,
            payload,
            current_user=current_user,
            guest_cart_token=x_cart_token,
        )
    except PurchaseAuthRequiredError as exc:
        if idempotency_key and idempotency_key.strip():
            await crud_platform.delete_idempotency_record(
                db,
                scope=idempotency_scope,
                key=idempotency_key.strip(),
            )
            await db.commit()
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.PURCHASE_AUTH_REQUIRED,
            message="برای ثبت سفارش خرید باید وارد حساب کاربری شوید.",
        ) from exc
    except ValueError as exc:
        if idempotency_key and idempotency_key.strip():
            await crud_platform.delete_idempotency_record(
                db,
                scope=idempotency_scope,
                key=idempotency_key.strip(),
            )
            await db.commit()
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
        ) from exc
    except Exception as exc:
        if idempotency_key and idempotency_key.strip():
            await crud_platform.delete_idempotency_record(
                db,
                scope=idempotency_scope,
                key=idempotency_key.strip(),
            )
            await db.commit()
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error processing checkout",
        ) from exc

    if idempotency_key and idempotency_key.strip():
        await crud_platform.finalize_idempotency_record(
            db,
            scope=idempotency_scope,
            key=idempotency_key.strip(),
            status_code=status.HTTP_201_CREATED,
            response_body=result.model_dump(mode="json"),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
        )
    await db.commit()
    return result
