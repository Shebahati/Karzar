"""Storefront OTP authentication and password reset service."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.crud import content as crud_content
from app.db.models.content import OtpPurpose
from app.db.models.user import User, UserRole
from app.schemas.auth import CustomerBrief, OtpRequestResponse, OtpVerifyResponse
from app.services.auth_token_service import issue_auth_tokens, logout_user
from app.services.sms_service import SmsMessage, get_sms_provider


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(100000):05d}"


async def request_otp(db: AsyncSession, phone: str) -> OtpRequestResponse:
    code = _generate_otp_code()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)
    await crud_content.create_otp_code(
        db, phone=phone, code=code, expires_at=expires_at, purpose=OtpPurpose.LOGIN
    )
    await db.commit()

    body = settings.OTP_MESSAGE_TEMPLATE.format(code=code)
    await get_sms_provider().send(SmsMessage(receptor=phone, body=body, template_token=code))

    response = OtpRequestResponse(
        phone=phone,
        expires_in=settings.OTP_EXPIRE_SECONDS,
    )
    if settings.DEBUG and settings.OTP_DEV_ECHO:
        response.dev_code = code
    return response


async def verify_otp(db: AsyncSession, phone: str, code: str) -> OtpVerifyResponse:
    otp = await crud_content.get_valid_otp(db, phone, code, purpose=OtpPurpose.LOGIN)
    if not otp:
        raise ValueError("Invalid or expired OTP code")

    result = await db.execute(
        select(User).where(User.phone_number == phone, User.deleted_at.is_(None))
    )
    user = result.scalars().first()
    if user is None:
        user = User(
            phone_number=phone,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=None,
            role=UserRole.B2C_CUSTOMER,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    elif not user.is_active:
        raise ValueError("Inactive user account")

    await crud_content.delete_otp(db, otp)
    tokens = await issue_auth_tokens(db, user)
    await db.commit()

    return OtpVerifyResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        customer=CustomerBrief(
            id=user.id,
            phone=user.phone_number,
            full_name=user.full_name,
        ),
    )


async def request_password_reset(db: AsyncSession, phone: str) -> OtpRequestResponse:
    result = await db.execute(
        select(User).where(User.phone_number == phone, User.deleted_at.is_(None))
    )
    user = result.scalars().first()
    if user is None:
        raise ValueError("No account found for this phone number")

    code = _generate_otp_code()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)
    await crud_content.create_otp_code(
        db,
        phone=phone,
        code=code,
        expires_at=expires_at,
        purpose=OtpPurpose.PASSWORD_RESET,
    )
    await db.commit()

    body = f"کد بازیابی رمز عبور کارزار: {code}"
    await get_sms_provider().send(SmsMessage(receptor=phone, body=body, template_token=code))

    response = OtpRequestResponse(phone=phone, expires_in=settings.OTP_EXPIRE_SECONDS)
    if settings.DEBUG and settings.OTP_DEV_ECHO:
        response.dev_code = code
    return response


async def confirm_password_reset(
    db: AsyncSession,
    *,
    phone: str,
    code: str,
    new_password: str,
) -> None:
    otp = await crud_content.get_valid_otp(
        db, phone, code, purpose=OtpPurpose.PASSWORD_RESET
    )
    if not otp:
        raise ValueError("Invalid or expired reset code")

    result = await db.execute(
        select(User).where(User.phone_number == phone, User.deleted_at.is_(None))
    )
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise ValueError("No active account found for this phone number")

    user.hashed_password = get_password_hash(new_password)
    await crud_content.delete_otp(db, otp)
    await logout_user(db, user)
    await db.commit()
