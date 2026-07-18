"""Product review / comment orchestration."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import commerce as crud_commerce
from app.crud import content as crud_content
from app.db.models.content import ProductComment


async def list_comments(db: AsyncSession, product_id: int) -> list[ProductComment]:
    return await crud_content.list_product_comments(db, product_id)


async def create_comment(
    db: AsyncSession,
    *,
    product_id: int,
    user_id: int,
    author_name: str,
    rating: int,
    body: str,
) -> ProductComment:
    is_verified_buyer = await crud_commerce.has_user_purchased_product(
        db,
        user_id=user_id,
        product_id=product_id,
    )
    return await crud_content.create_product_comment(
        db,
        product_id=product_id,
        author_name=author_name,
        rating=rating,
        body=body,
        is_verified_buyer=is_verified_buyer,
    )
