"""CRUD for CMS tables: articles, hero slides, comments, contact."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.otp import create_otp_code, delete_otp, get_valid_otp  # noqa: F401
from app.db.models.content import (
    Article,
    ContactSubmission,
    HeroSlide,
    ProductComment,
)


async def list_published_articles(db: AsyncSession) -> list[Article]:
    stmt = (
        select(Article)
        .where(Article.is_published.is_(True))
        .order_by(Article.published_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_article_by_slug(db: AsyncSession, slug: str) -> Article | None:
    stmt = select(Article).where(Article.slug == slug, Article.is_published.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_active_hero_slides(db: AsyncSession) -> list[HeroSlide]:
    stmt = (
        select(HeroSlide)
        .where(HeroSlide.is_active.is_(True))
        .order_by(HeroSlide.sort_order.asc(), HeroSlide.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_product_comments(db: AsyncSession, product_id: int) -> list[ProductComment]:
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


async def list_all_articles(db: AsyncSession, *, skip: int = 0, limit: int = 50) -> tuple[list[Article], int]:
    total = (await db.execute(select(func.count()).select_from(Article))).scalar_one()
    stmt = select(Article).order_by(Article.published_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_article_by_id(db: AsyncSession, article_id: int) -> Article | None:
    result = await db.execute(select(Article).where(Article.id == article_id))
    return result.scalar_one_or_none()


async def get_article_by_slug_admin(db: AsyncSession, slug: str) -> Article | None:
    result = await db.execute(select(Article).where(Article.slug == slug))
    return result.scalar_one_or_none()


async def create_article(db: AsyncSession, **fields) -> Article:
    article = Article(**fields)
    db.add(article)
    await db.flush()
    await db.refresh(article)
    return article


async def delete_article_row(db: AsyncSession, article: Article) -> None:
    await db.delete(article)
    await db.flush()


async def list_all_hero_slides(db: AsyncSession) -> list[HeroSlide]:
    stmt = select(HeroSlide).order_by(HeroSlide.sort_order.asc(), HeroSlide.id.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_hero_slide_by_id(db: AsyncSession, slide_id: int) -> HeroSlide | None:
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    return result.scalar_one_or_none()


async def create_hero_slide(db: AsyncSession, **fields) -> HeroSlide:
    slide = HeroSlide(**fields)
    db.add(slide)
    await db.flush()
    await db.refresh(slide)
    return slide


async def delete_hero_slide_row(db: AsyncSession, slide: HeroSlide) -> None:
    await db.delete(slide)
    await db.flush()


async def create_product_comment(
    db: AsyncSession,
    *,
    product_id: int,
    author_name: str,
    rating: int,
    body: str,
    is_verified_buyer: bool,
) -> ProductComment:
    comment = ProductComment(
        product_id=product_id,
        author_name=author_name,
        rating=rating,
        body=body,
        is_verified_buyer=is_verified_buyer,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return comment


async def get_product_comment_by_id(db: AsyncSession, comment_id: int) -> ProductComment | None:
    result = await db.execute(select(ProductComment).where(ProductComment.id == comment_id))
    return result.scalar_one_or_none()


async def list_all_product_comments(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    product_id: int | None = None,
) -> tuple[list[ProductComment], int]:
    filters = []
    if product_id is not None:
        filters.append(ProductComment.product_id == product_id)
    count_stmt = select(func.count()).select_from(ProductComment)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = select(ProductComment).order_by(ProductComment.created_at.desc()).offset(skip).limit(limit)
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def delete_product_comment_row(db: AsyncSession, comment: ProductComment) -> None:
    await db.delete(comment)
    await db.flush()


async def list_contact_submissions(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    phone: str | None = None,
) -> tuple[list[ContactSubmission], int]:
    filters = []
    if phone:
        filters.append(ContactSubmission.phone == phone.strip())
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                ContactSubmission.full_name.ilike(pattern),
                ContactSubmission.phone.ilike(pattern),
                ContactSubmission.subject.ilike(pattern),
                ContactSubmission.ticket_code.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(ContactSubmission)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(ContactSubmission)
        .order_by(ContactSubmission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total
