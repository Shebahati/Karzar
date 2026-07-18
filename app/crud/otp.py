"""CRUD for OTP codes."""

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content import OtpCode, OtpPurpose
from app.utils.otp_hash import hash_otp_code


async def create_otp_code(
    db: AsyncSession,
    *,
    phone: str,
    code: str,
    expires_at,
    purpose: OtpPurpose = OtpPurpose.LOGIN,
) -> OtpCode:
    existing = await db.execute(
        select(OtpCode).where(OtpCode.phone == phone, OtpCode.purpose == purpose)
    )
    for row in existing.scalars().all():
        await db.delete(row)

    otp = OtpCode(phone=phone, code=hash_otp_code(code), expires_at=expires_at, purpose=purpose)
    db.add(otp)
    await db.flush()
    return otp


async def get_valid_otp(
    db: AsyncSession,
    phone: str,
    code: str,
    *,
    purpose: OtpPurpose = OtpPurpose.LOGIN,
) -> OtpCode | None:
    from datetime import datetime

    stmt = select(OtpCode).where(
        OtpCode.phone == phone,
        OtpCode.code == hash_otp_code(code),
        OtpCode.purpose == purpose,
        OtpCode.expires_at > datetime.now(UTC),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_otp(db: AsyncSession, otp: OtpCode) -> None:
    await db.delete(otp)
    await db.flush()
