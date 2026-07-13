"""Brand business logic for admin CRUD."""


from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.crud import brand as crud_brand
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate

logger = get_logger(__name__)


class BrandService:
    @staticmethod
    async def list_brands(db: AsyncSession) -> list[BrandResponse]:
        brands = await crud_brand.list_brands(db)
        responses: list[BrandResponse] = []
        for brand in brands:
            count = await crud_brand.count_products_for_brand(db, brand.id)
            responses.append(
                BrandResponse(
                    id=brand.id,
                    name=brand.name,
                    slug=brand.slug,
                    country=brand.country,
                    product_count=count,
                )
            )
        return responses

    @staticmethod
    async def create_brand(db: AsyncSession, payload: BrandCreate) -> BrandResponse:
        existing = await crud_brand.get_brand_by_name(db, payload.name.strip())
        if existing:
            raise api_error(
                400,
                error_code=ErrorCode.BAD_REQUEST,
                message="Brand with this name already exists",
                details=[{"field": "name", "message": "نام برند تکراری است."}],
            )
        brand = await crud_brand.create_brand(
            db, name=payload.name.strip(), country=payload.country
        )
        await db.commit()
        await db.refresh(brand)
        return BrandResponse(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            country=brand.country,
            product_count=0,
        )

    @staticmethod
    async def update_brand(db: AsyncSession, brand_id: int, payload: BrandUpdate) -> BrandResponse:
        brand = await crud_brand.get_brand_by_id(db, brand_id)
        if brand is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Brand with ID '{brand_id}' not found",
            )

        if payload.name is not None:
            normalized = payload.name.strip()
            duplicate = await crud_brand.get_brand_by_name(db, normalized)
            if duplicate and duplicate.id != brand_id:
                raise api_error(
                    400,
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Brand with this name already exists",
                    details=[{"field": "name", "message": "نام برند تکراری است."}],
                )
            brand = await crud_brand.update_brand(db, brand, name=normalized)

        if "country" in payload.model_fields_set:
            brand = await crud_brand.update_brand(
                db,
                brand,
                country=payload.country,
                unset_country=payload.country is None,
            )

        await db.commit()
        await db.refresh(brand)
        count = await crud_brand.count_products_for_brand(db, brand.id)
        return BrandResponse(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            country=brand.country,
            product_count=count,
        )

    @staticmethod
    async def delete_brand(db: AsyncSession, brand_id: int) -> dict:
        brand = await crud_brand.get_brand_by_id(db, brand_id)
        if brand is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Brand with ID '{brand_id}' not found",
            )

        cleared = await crud_brand.clear_brand_on_products(db, brand_id)
        await crud_brand.delete_brand_row(db, brand)
        await db.commit()
        logger.info("Deleted brand %s; cleared brand_id on %s product(s)", brand_id, cleared)
        return {"id": brand_id, "products_cleared": cleared}
