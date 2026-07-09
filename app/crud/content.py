"""CRUD for CMS tables: articles, hero slides, comments, contact."""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.content import Article, ContactSubmission, HeroSlide, OtpCode, ProductComment


async def list_published_articles(db: AsyncSession) -> List[Article]:
    stmt = (
        select(Article)
        .where(Article.is_published.is_(True))
        .order_by(Article.published_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_article_by_slug(db: AsyncSession, slug: str) -> Optional[Article]:
    stmt = select(Article).where(Article.slug == slug, Article.is_published.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_active_hero_slides(db: AsyncSession) -> List[HeroSlide]:
    stmt = (
        select(HeroSlide)
        .where(HeroSlide.is_active.is_(True))
        .order_by(HeroSlide.sort_order.asc(), HeroSlide.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_product_comments(db: AsyncSession, product_id: int) -> List[ProductComment]:
    stmt = (
        select(ProductComment)
        .where(ProductComment.product_id == product_id)
        .order_by(ProductComment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_contact_submission(
    db: AsyncSession,
    *,
    ticket_prefix: str,
    full_name: str,
    phone: str,
    subject: str,
    message: str,
) -> ContactSubmission:
    submission = ContactSubmission(
        ticket_code=f"pending-{uuid.uuid4().hex}",
        full_name=full_name,
        phone=phone,
        subject=subject,
        message=message,
    )
    db.add(submission)
    await db.flush()
    submission.ticket_code = f"{ticket_prefix}{submission.id:05d}"
    await db.flush()
    await db.refresh(submission)
    return submission


async def create_otp_code(
    db: AsyncSession,
    *,
    phone: str,
    code: str,
    expires_at,
) -> OtpCode:
    existing = await db.execute(select(OtpCode).where(OtpCode.phone == phone))
    for row in existing.scalars().all():
        await db.delete(row)

    otp = OtpCode(phone=phone, code=code, expires_at=expires_at)
    db.add(otp)
    await db.flush()
    return otp


async def get_valid_otp(db: AsyncSession, phone: str, code: str) -> Optional[OtpCode]:
    from datetime import datetime, timezone

    stmt = select(OtpCode).where(
        OtpCode.phone == phone,
        OtpCode.code == code,
        OtpCode.expires_at > datetime.now(timezone.utc),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_otp(db: AsyncSession, otp: OtpCode) -> None:
    await db.delete(otp)
    await db.flush()
