"""Storefront content endpoints: blog, hero slides, contact, checkout."""

from datetime import UTC

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.request_throttle import enforce_public_throttle
from app.crud import content as crud_content
from app.crud import platform as crud_platform
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.storefront import (
    ArticleListResponse,
    ArticleTeaser,
    BlogPostResponse,
    CheckoutRequest,
    CheckoutResponse,
    ContactRequest,
    ContactResponse,
    HeroSlideListResponse,
    HeroSlideResponse,
)
from app.services.checkout_service import PurchaseAuthRequiredError, submit_checkout, submit_contact

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
    await enforce_public_throttle(
        request,
        scope="checkout",
        max_requests=settings.PUBLIC_THROTTLE_CHECKOUT_MAX,
        window_seconds=settings.PUBLIC_THROTTLE_CHECKOUT_WINDOW,
    )
    if idempotency_key and idempotency_key.strip():
        cached = await crud_platform.get_idempotency_record(
            db, scope="checkout", key=idempotency_key.strip()
        )
        if cached is not None:
            return JSONResponse(status_code=cached.status_code, content=cached.response_body)

    try:
        result = await submit_checkout(
            db,
            payload,
            current_user=current_user,
            guest_cart_token=x_cart_token,
        )
    except PurchaseAuthRequiredError as exc:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.PURCHASE_AUTH_REQUIRED,
            message="برای ثبت سفارش خرید باید وارد حساب کاربری شوید.",
        ) from exc
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
        ) from exc
    except Exception as exc:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error processing checkout",
        ) from exc

    if idempotency_key and idempotency_key.strip():
        from datetime import datetime, timedelta

        await crud_platform.store_idempotency_record(
            db,
            scope="checkout",
            key=idempotency_key.strip(),
            status_code=status.HTTP_201_CREATED,
            response_body=result.model_dump(mode="json"),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
        )
        await db.commit()

    return result
