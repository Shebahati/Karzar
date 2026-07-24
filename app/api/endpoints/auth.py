"""Authentication endpoints: registration, login, and step-up PIN verification."""

from fastapi import APIRouter, Body, Cookie, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_super_admin
from app.core.auth_cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.rate_limit import get_rate_limiter, reset_in_memory_limiter
from app.core.security import (
    create_step_up_token,
    get_password_hash,
    hash_token,
    verify_admin_pin,
    verify_password,
)
from app.db.database import get_db
from app.db.models.user import User, UserRole
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PinVerifyRequest,
    RefreshTokenRequest,
    StepUpTokenResponse,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth_token_service import issue_auth_tokens, logout_user, rotate_refresh_token
from app.services.otp_service import (
    confirm_password_reset,
    request_otp,
    request_password_reset,
    verify_otp,
)

router = APIRouter()


def _pin_throttle_key(current_user: User) -> str:
    return f"pin:{current_user.phone_number}"


async def _check_pin_rate_limit(current_user: User) -> None:
    retry_after = await get_rate_limiter().retry_after_if_limited(
        _pin_throttle_key(current_user),
        settings.STEP_UP_MAX_ATTEMPTS,
        settings.STEP_UP_ATTEMPT_WINDOW_SECONDS,
    )
    if retry_after is not None:
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
            message="Too many invalid PIN attempts. Please try again later.",
            details=[
                {"field": "pin", "message": f"Rate limited. Retry after {retry_after} seconds."}
            ],
            headers={"Retry-After": str(retry_after)},
        )


async def _check_auth_rate_limit(key: str, field: str, message: str) -> None:
    retry_after = await get_rate_limiter().retry_after_if_limited(
        key,
        settings.AUTH_MAX_ATTEMPTS,
        settings.AUTH_ATTEMPT_WINDOW_SECONDS,
    )
    if retry_after is not None:
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
            message=message,
            details=[{"field": field, "message": f"Rate limited. Retry after {retry_after} seconds."}],
            headers={"Retry-After": str(retry_after)},
        )


async def _record_auth_failure(key: str) -> None:
    await get_rate_limiter().record_failure(key, settings.AUTH_ATTEMPT_WINDOW_SECONDS)


async def _clear_auth_failures(key: str) -> None:
    await get_rate_limiter().clear(key)


async def _record_pin_failure(current_user: User) -> None:
    await get_rate_limiter().record_failure(
        _pin_throttle_key(current_user), settings.STEP_UP_ATTEMPT_WINDOW_SECONDS
    )


async def _clear_pin_failures(current_user: User) -> None:
    await get_rate_limiter().clear(_pin_throttle_key(current_user))


def _reset_pin_rate_limiter_for_tests() -> None:
    """Testing helper to avoid cross-test contamination of in-memory limiter."""
    reset_in_memory_limiter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account (optionally disabled in production)."""
    if not settings.ALLOW_PUBLIC_REGISTER:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.FORBIDDEN,
            message="Public registration is disabled",
        )

    result = await db.execute(
        select(User).where(
            User.phone_number == user_in.phone_number,
            User.deleted_at.is_(None),
        )
    )
    if result.scalars().first():
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Phone number already registered",
            details=[{"field": "phone_number", "message": "already registered"}],
        )

    role = UserRole.B2B_CUSTOMER if user_in.company_name else UserRole.B2C_CUSTOMER
    new_user = User(
        phone_number=user_in.phone_number,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        company_name=user_in.company_name,
        role=role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with phone number (username) and password; returns a JWT."""
    throttle_key = f"login:{form_data.username}"
    await _check_auth_rate_limit(
        throttle_key,
        "username",
        "Too many login attempts. Please try again later.",
    )

    result = await db.execute(
        select(User).where(
            User.phone_number == form_data.username,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        await _record_auth_failure(throttle_key)
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Incorrect phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.FORBIDDEN,
            message="Inactive user account",
        )

    await _clear_auth_failures(throttle_key)
    tokens = await issue_auth_tokens(db, user)
    await db.commit()
    set_auth_cookies(response, tokens)
    return tokens


@router.get("/me", response_model=CurrentUserResponse, summary="Get current authenticated user")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return CurrentUserResponse(
        id=current_user.id,
        phone_number=current_user.phone_number,
        full_name=current_user.full_name,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        is_active=current_user.is_active,
        company_name=current_user.company_name,
        is_b2b=current_user.role == UserRole.B2B_CUSTOMER,
    )


@router.post("/change-password", summary="Change current user password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="New password must be different from current password",
        )
    current_user.hashed_password = get_password_hash(payload.new_password)
    await logout_user(db, current_user)
    await db.commit()
    return {"ok": True}


@router.post("/refresh", response_model=Token, summary="Rotate refresh token")
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: str | None = Cookie(None, alias=REFRESH_COOKIE_NAME),
    payload: RefreshTokenRequest | None = Body(default=None),
):
    from app.crud import platform as crud_platform

    plain = (payload.refresh_token if payload else None) or refresh_cookie
    if not plain or len(plain) < 16:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Invalid or expired refresh token",
        )

    row = await crud_platform.get_valid_refresh_token(db, hash_token(plain))
    if row is None:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Invalid or expired refresh token",
        )

    user = (
        await db.execute(
            select(User).where(User.id == row.user_id, User.deleted_at.is_(None))
        )
    ).scalars().first()
    if user is None or not user.is_active:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Invalid refresh token subject",
        )

    try:
        tokens = await rotate_refresh_token(db, user, plain)
        await db.commit()
        set_auth_cookies(response, tokens)
        return tokens
    except ValueError as exc:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=str(exc),
        ) from exc


@router.post("/logout", summary="Revoke refresh tokens and invalidate access tokens")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await logout_user(db, current_user)
    await db.commit()
    clear_auth_cookies(response)
    return {"ok": True}


@router.post("/password-reset/request", response_model=OtpRequestResponse, summary="Request password reset OTP")
async def password_reset_request(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    throttle_key = f"pwd_reset:{payload.phone}"
    await _check_auth_rate_limit(
        throttle_key,
        "phone",
        "Too many password reset requests. Please try again later.",
    )
    await _record_auth_failure(throttle_key)
    try:
        response = await request_password_reset(db, payload.phone)
        return response
    except ValueError:
        # Prevent phone-number enumeration: always return a generic success payload.
        return OtpRequestResponse(
            phone=payload.phone,
            expires_in=settings.OTP_EXPIRE_SECONDS,
        )


@router.post("/password-reset/confirm", summary="Confirm password reset with OTP")
async def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    throttle_key = f"pwd_reset_confirm:{payload.phone}"
    await _check_auth_rate_limit(
        throttle_key,
        "phone",
        "Too many password reset attempts. Please try again later.",
    )
    try:
        await confirm_password_reset(
            db,
            phone=payload.phone,
            code=payload.code,
            new_password=payload.new_password,
        )
        await _clear_auth_failures(throttle_key)
        return {"ok": True}
    except ValueError as exc:
        await _record_auth_failure(throttle_key)
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=str(exc),
        ) from exc


@router.post("/verify-pin", response_model=StepUpTokenResponse, summary="Verify admin PIN for destructive actions")
async def verify_pin(
    payload: PinVerifyRequest,
    current_user: User = Depends(get_current_super_admin),
):
    """Exchange a valid admin PIN for a short-lived step-up token."""
    await _check_pin_rate_limit(current_user)

    if not settings.ADMIN_STEP_UP_PIN:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.STEP_UP_NOT_CONFIGURED,
            message="Step-up authentication is not configured",
        )

    if not verify_admin_pin(payload.pin):
        await _record_pin_failure(current_user)
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Invalid PIN",
            details=[{"field": "pin", "message": "incorrect PIN"}],
        )

    await _clear_pin_failures(current_user)
    secure_token, expires_in = create_step_up_token(subject=current_user.phone_number)
    return {
        "secure_token": secure_token,
        "token_type": "step_up",
        "expires_in": expires_in,
    }


@router.post("/otp/request", response_model=OtpRequestResponse, summary="Request storefront OTP")
async def otp_request(payload: OtpRequest, db: AsyncSession = Depends(get_db)):
    throttle_key = f"otp_request:{payload.phone}"
    await _check_auth_rate_limit(
        throttle_key,
        "phone",
        "Too many OTP requests. Please try again later.",
    )
    # Count successful sends as well so SMS bombing cannot reset the budget.
    await _record_auth_failure(throttle_key)
    try:
        response = await request_otp(db, payload.phone)
        return response
    except Exception as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error sending OTP",
        ) from exc


@router.post("/otp/verify", response_model=OtpVerifyResponse, summary="Verify storefront OTP")
async def otp_verify(
    payload: OtpVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    throttle_key = f"otp_verify:{payload.phone}"
    await _check_auth_rate_limit(
        throttle_key,
        "phone",
        "Too many OTP verification attempts. Please try again later.",
    )
    try:
        result = await verify_otp(db, payload.phone, payload.code)
        await _clear_auth_failures(throttle_key)
        set_auth_cookies(
            response,
            {
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "expires_in": result.expires_in,
            },
        )
        return result
    except ValueError as exc:
        await _record_auth_failure(throttle_key)
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=str(exc),
        ) from exc
    except Exception as exc:
        await _record_auth_failure(throttle_key)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error verifying OTP",
        ) from exc
