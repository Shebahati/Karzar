"""Authentication endpoints: registration, login, and step-up PIN verification."""

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.security import (
    create_access_token,
    create_step_up_token,
    get_password_hash,
    verify_admin_pin,
    verify_password,
)
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.auth import PinVerifyRequest, StepUpTokenResponse, Token, UserCreate, UserResponse

router = APIRouter()
_PIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)


def _pin_throttle_key(current_user: User) -> str:
    return current_user.phone_number


def _prune_old_attempts(attempts: deque[float], now: float) -> None:
    window = settings.STEP_UP_ATTEMPT_WINDOW_SECONDS
    while attempts and (now - attempts[0]) > window:
        attempts.popleft()


def _check_pin_rate_limit(current_user: User) -> None:
    now = time.monotonic()
    key = _pin_throttle_key(current_user)
    attempts = _PIN_ATTEMPTS[key]
    _prune_old_attempts(attempts, now)
    if len(attempts) >= settings.STEP_UP_MAX_ATTEMPTS:
        retry_after = max(1, int(settings.STEP_UP_ATTEMPT_WINDOW_SECONDS - (now - attempts[0])))
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
            message="Too many invalid PIN attempts. Please try again later.",
            details=[
                {
                    "field": "pin",
                    "message": f"Rate limited. Retry after {retry_after} seconds.",
                }
            ],
            headers={"Retry-After": str(retry_after)},
        )


def _record_pin_failure(current_user: User) -> None:
    now = time.monotonic()
    key = _pin_throttle_key(current_user)
    attempts = _PIN_ATTEMPTS[key]
    _prune_old_attempts(attempts, now)
    attempts.append(now)


def _clear_pin_failures(current_user: User) -> None:
    _PIN_ATTEMPTS.pop(_pin_throttle_key(current_user), None)


def _reset_pin_rate_limiter_for_tests() -> None:
    """Testing helper to avoid cross-test contamination of in-memory limiter."""
    _PIN_ATTEMPTS.clear()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account (optionally disabled in production)."""
    if not settings.ALLOW_PUBLIC_REGISTER:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.FORBIDDEN,
            message="Public registration is disabled",
        )

    result = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
    if result.scalars().first():
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Phone number already registered",
            details=[{"field": "phone_number", "message": "already registered"}],
        )

    new_user = User(
        phone_number=user_in.phone_number,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticate with phone number (username) and password; returns a JWT."""
    result = await db.execute(select(User).where(User.phone_number == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
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

    access_token = create_access_token(subject=user.phone_number)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/verify-pin", response_model=StepUpTokenResponse, summary="Verify admin PIN for destructive actions")
async def verify_pin(
    payload: PinVerifyRequest,
    current_user: User = Depends(get_current_super_admin),
):
    """Exchange a valid admin PIN for a short-lived step-up token."""
    _check_pin_rate_limit(current_user)

    if not settings.ADMIN_STEP_UP_PIN:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.STEP_UP_NOT_CONFIGURED,
            message="Step-up authentication is not configured",
        )

    if not verify_admin_pin(payload.pin):
        _record_pin_failure(current_user)
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Invalid PIN",
            details=[{"field": "pin", "message": "incorrect PIN"}],
        )

    _clear_pin_failures(current_user)
    secure_token, expires_in = create_step_up_token(subject=current_user.phone_number)
    return {
        "secure_token": secure_token,
        "token_type": "step_up",
        "expires_in": expires_in,
    }
