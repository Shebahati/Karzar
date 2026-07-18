"""Storefront content endpoints: blog, hero slides, contact."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.request_throttle import enforce_public_throttle
from app.crud import content as crud_content
from app.db.database import get_db
from app.schemas.storefront import (
    ArticleListResponse,
    ArticleTeaser,
    BlogPostResponse,
    ContactRequest,
    ContactResponse,
    HeroSlideListResponse,
    HeroSlideResponse,
)
from app.services.checkout_service import submit_contact

router = APIRouter()


@router.get("/blog/", response_model=ArticleListResponse, tags=["Storefront"])
async def list_articles(db: AsyncSession = Depends(get_db)):
    articles = await crud_content.list_published_articles(db)
    return {
        "data": [
            ArticleTeaser(
                id=article.id,
                slug=article.slug,
                title=article.title,
                excerpt=article.excerpt,
                cover_image=article.cover_image or "",
                published_at=article.published_at,
                reading_minutes=article.reading_minutes,
            )
            for article in articles
        ]
    }


@router.get("/blog/{slug}", response_model=BlogPostResponse, tags=["Storefront"])
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    article = await crud_content.get_article_by_slug(db, slug)
    if not article:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Article '{slug}' not found",
        )
    return BlogPostResponse(
        id=article.id,
        slug=article.slug,
        title=article.title,
        excerpt=article.excerpt,
        cover_image=article.cover_image or "",
        published_at=article.published_at,
        reading_minutes=article.reading_minutes,
        author=article.author,
        tags=list(article.tags or []),
        related_product_ids=list(article.related_product_ids or []),
        blocks=list(article.blocks or []),
    )


# Backward-compatible alias for storefront contract (/articles/).
@router.get("/articles/", response_model=ArticleListResponse, tags=["Storefront"], include_in_schema=True)
async def list_articles_alias(db: AsyncSession = Depends(get_db)):
    return await list_articles(db)


@router.get("/articles/{slug}", response_model=BlogPostResponse, tags=["Storefront"], include_in_schema=True)
async def get_article_alias(slug: str, db: AsyncSession = Depends(get_db)):
    return await get_article(slug, db)


@router.get("/hero-slides/", response_model=HeroSlideListResponse, tags=["Storefront"])
async def list_hero_slides(db: AsyncSession = Depends(get_db)):
    slides = await crud_content.list_active_hero_slides(db)
    return {
        "data": [
            HeroSlideResponse(
                id=slide.id,
                title=slide.title,
                subtitle=slide.subtitle or "",
                cta_label=slide.cta_label or "",
                cta_href=slide.cta_href or "",
                image=slide.image,
                accent=slide.accent,
            )
            for slide in slides
        ]
    }


@router.post("/contact", response_model=ContactResponse, tags=["Storefront"])
async def contact_us(
    payload: ContactRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await enforce_public_throttle(
        request,
        scope="contact",
        max_requests=settings.PUBLIC_THROTTLE_CONTACT_MAX,
        window_seconds=settings.PUBLIC_THROTTLE_CONTACT_WINDOW,
    )
    try:
        return await submit_contact(db, payload)
    except Exception as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error submitting contact form",
        ) from exc
