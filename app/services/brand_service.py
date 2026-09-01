"""Brand business logic for admin CRUD."""


from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.crud import brand as crud_brand
from app.db.models.product import Brand
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate
from app.utils.product_presenter import absolutize_asset_url

logger = get_logger(__name__)


def brand_to_response(brand: Brand, product_count: int | None = None) -> BrandResponse:
    return BrandResponse(
        id=brand.id,
        name=brand.name,
        slug=brand.slug,
        country=brand.country,
        logo_url=absolutize_asset_url(brand.logo_url),
        meta_title=brand.meta_title,
        meta_description=brand.meta_description,
        product_count=product_count,
    )


class BrandService:
    @staticmethod
    async def list_brands(
        db: AsyncSession,
        *,
        storefront_product_counts: bool = False,
    ) -> list[BrandResponse]:
        brands = await crud_brand.list_brands(db)
        responses: list[BrandResponse] = []
        for brand in brands:
            count = await crud_brand.count_products_for_brand(
                db,
                brand.id,
                storefront_public_only=storefront_product_counts,
            )
            responses.append(brand_to_response(brand, count))
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
            db,
            name=payload.name.strip(),
            country=payload.country,
            logo_url=payload.logo_url,
        )
        await db.commit()
        await db.refresh(brand)
        return brand_to_response(brand, 0)

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

        if "logo_url" in payload.model_fields_set:
            brand = await crud_brand.update_brand(
                db,
                brand,
                logo_url=payload.logo_url,
                unset_logo=payload.logo_url is None,
            )

        if "meta_title" in payload.model_fields_set:
            brand = await crud_brand.update_brand(
                db,
                brand,
                meta_title=payload.meta_title,
                unset_meta_title=payload.meta_title is None,
            )

        if "meta_description" in payload.model_fields_set:
            brand = await crud_brand.update_brand(
                db,
                brand,
                meta_description=payload.meta_description,
                unset_meta_description=payload.meta_description is None,
            )

        await db.commit()
        await db.refresh(brand)
        count = await crud_brand.count_products_for_brand(db, brand.id)
        return brand_to_response(brand, count)

    @staticmethod
    async def set_logo_url(db: AsyncSession, brand_id: int, logo_url: str) -> BrandResponse:
        brand = await crud_brand.get_brand_by_id(db, brand_id)
        if brand is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Brand with ID '{brand_id}' not found",
            )
        brand = await crud_brand.update_brand(db, brand, logo_url=logo_url)
        await db.commit()
        await db.refresh(brand)
        count = await crud_brand.count_products_for_brand(db, brand.id)
        return brand_to_response(brand, count)

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
