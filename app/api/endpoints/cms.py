"""Admin CMS endpoints for articles, hero slides, comments, and contact tickets."""


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.core.errors import ErrorCode, api_error
from app.crud import content as crud_content
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.cms import (
    ArticleAdminListResponse,
    ArticleAdminResponse,
    ArticleCreateRequest,
    ArticleUpdateRequest,
    ContactSubmissionListResponse,
    ContactSubmissionResponse,
    HeroSlideAdminListResponse,
    HeroSlideCreateRequest,
    HeroSlideUpdateRequest,
    ProductCommentAdminListResponse,
)
from app.schemas.common import build_pagination_meta
from app.schemas.storefront import HeroSlideResponse, ProductCommentResponse

router = APIRouter()


def _article_to_admin(article) -> ArticleAdminResponse:
    return ArticleAdminResponse(
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
        is_published=article.is_published,
    )


@router.get("/articles", response_model=ArticleAdminListResponse, tags=["CMS"])
async def list_articles_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    articles, total = await crud_content.list_all_articles(db, skip=skip, limit=limit)
    return {
        "data": [_article_to_admin(article) for article in articles],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }


@router.post("/articles", response_model=ArticleAdminResponse, status_code=status.HTTP_201_CREATED, tags=["CMS"])
async def create_article_admin(
    payload: ArticleCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    existing = await crud_content.get_article_by_slug_admin(db, payload.slug)
    if existing:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Article slug already exists",
        )
    article = await crud_content.create_article(db, **payload.model_dump())
    await db.commit()
    return _article_to_admin(article)


@router.put("/articles/{article_id}", response_model=ArticleAdminResponse, tags=["CMS"])
async def update_article_admin(
    article_id: int,
    payload: ArticleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    article = await crud_content.get_article_by_id(db, article_id)
    if not article:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Article not found")
    if payload.slug and payload.slug != article.slug:
        duplicate = await crud_content.get_article_by_slug_admin(db, payload.slug)
        if duplicate:
            raise api_error(status.HTTP_409_CONFLICT, error_code=ErrorCode.CONFLICT, message="Article slug already exists")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    return _article_to_admin(article)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMS"])
async def delete_article_admin(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    article = await crud_content.get_article_by_id(db, article_id)
    if not article:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Article not found")
    await crud_content.delete_article_row(db, article)
    await db.commit()


@router.get("/hero-slides", response_model=HeroSlideAdminListResponse, tags=["CMS"])
async def list_hero_slides_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    slides = await crud_content.list_all_hero_slides(db)
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


@router.post("/hero-slides", response_model=HeroSlideResponse, status_code=status.HTTP_201_CREATED, tags=["CMS"])
async def create_hero_slide_admin(
    payload: HeroSlideCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    slide = await crud_content.create_hero_slide(db, **payload.model_dump())
    await db.commit()
    return HeroSlideResponse(
        id=slide.id,
        title=slide.title,
        subtitle=slide.subtitle or "",
        cta_label=slide.cta_label or "",
        cta_href=slide.cta_href or "",
        image=slide.image,
        accent=slide.accent,
    )


@router.put("/hero-slides/{slide_id}", response_model=HeroSlideResponse, tags=["CMS"])
async def update_hero_slide_admin(
    slide_id: int,
    payload: HeroSlideUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    slide = await crud_content.get_hero_slide_by_id(db, slide_id)
    if not slide:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Hero slide not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(slide, field, value)
    await db.commit()
    await db.refresh(slide)
    return HeroSlideResponse(
        id=slide.id,
        title=slide.title,
        subtitle=slide.subtitle or "",
        cta_label=slide.cta_label or "",
        cta_href=slide.cta_href or "",
        image=slide.image,
        accent=slide.accent,
    )


@router.delete("/hero-slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMS"])
async def delete_hero_slide_admin(
    slide_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    slide = await crud_content.get_hero_slide_by_id(db, slide_id)
    if not slide:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Hero slide not found")
    await crud_content.delete_hero_slide_row(db, slide)
    await db.commit()


@router.get("/product-comments", response_model=ProductCommentAdminListResponse, tags=["CMS"])
async def list_product_comments_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: int | None = Query(None),
):
    comments, total = await crud_content.list_all_product_comments(
        db, skip=skip, limit=limit, product_id=product_id
    )
    return {
        "data": [
            ProductCommentResponse.model_validate(comment, from_attributes=True) for comment in comments
        ],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }


@router.delete("/product-comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMS"])
async def delete_product_comment_admin(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    comment = await crud_content.get_product_comment_by_id(db, comment_id)
    if not comment:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Comment not found")
    await crud_content.delete_product_comment_row(db, comment)
    await db.commit()


@router.get("/contact-submissions", response_model=ContactSubmissionListResponse, tags=["CMS"])
async def list_contact_submissions_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    phone: str | None = Query(None),
):
    submissions, total = await crud_content.list_contact_submissions(
        db, skip=skip, limit=limit, search=search, phone=phone
    )
    return {
        "data": [
            ContactSubmissionResponse(
                id=row.id,
                ticket_code=row.ticket_code,
                full_name=row.full_name,
                phone=row.phone,
                subject=row.subject,
                message=row.message,
                created_at=row.created_at,
            )
            for row in submissions
        ],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }
