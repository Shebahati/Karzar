# app/api/endpoints/auth.py
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models.user import User
from app.schemas.auth import UserCreate, UserResponse, Token, PinVerifyRequest, StepUpTokenResponse
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_step_up_token,
    verify_admin_pin,
)
from app.api.deps import get_current_super_admin

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
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
    if not settings.ADMIN_STEP_UP_PIN:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.STEP_UP_NOT_CONFIGURED,
            message="Step-up authentication is not configured",
        )

    if not verify_admin_pin(payload.pin):
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Invalid PIN",
            details=[{"field": "pin", "message": "incorrect PIN"}],
        )

    secure_token, expires_in = create_step_up_token(subject=current_user.phone_number)
    return {
        "secure_token": secure_token,
        "token_type": "step_up",
        "expires_in": expires_in,
    }
