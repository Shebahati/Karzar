"""Storefront OTP authentication service."""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.crud import content as crud_content
from app.db.models.user import User, UserRole
from app.schemas.auth import OtpRequestResponse, OtpVerifyResponse, CustomerBrief


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(100000):05d}"


async def request_otp(db: AsyncSession, phone: str) -> OtpRequestResponse:
    code = _generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)
    await crud_content.create_otp_code(db, phone=phone, code=code, expires_at=expires_at)
    await db.commit()

    response = OtpRequestResponse(
        phone=phone,
        expires_in=settings.OTP_EXPIRE_SECONDS,
    )
    if settings.DEBUG and settings.OTP_DEV_ECHO:
        response.dev_code = code
    return response


async def verify_otp(db: AsyncSession, phone: str, code: str) -> OtpVerifyResponse:
    otp = await crud_content.get_valid_otp(db, phone, code)
    if not otp:
        raise ValueError("Invalid or expired OTP code")

    result = await db.execute(select(User).where(User.phone_number == phone))
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
    await db.commit()

    access_token = create_access_token(subject=user.phone_number)
    return OtpVerifyResponse(
        access_token=access_token,
        customer=CustomerBrief(
            id=user.id,
            phone=user.phone_number,
            full_name=user.full_name,
        ),
    )
