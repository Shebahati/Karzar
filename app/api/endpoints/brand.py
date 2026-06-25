"""Brand listing endpoint for admin product forms."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.db.database import get_db
from app.db.models.product import Brand
from app.schemas.brand import BrandResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=List[BrandResponse],
    summary="List all brands",
    tags=["Brands"],
)
async def list_brands(db: AsyncSession = Depends(get_db)):
    """Return every brand sorted alphabetically by name."""
    try:
        result = await db.execute(select(Brand).order_by(Brand.name.asc(), Brand.id.asc()))
        brands = list(result.scalars().all())
        return brands
    except Exception as exc:
        logger.error("Error fetching brands: %s", exc)
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving brands",
        ) from exc
