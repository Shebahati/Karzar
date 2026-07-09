"""Category business logic delegating to the CRUD and tree-builder layers."""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.crud import category as crud_category
from app.db.models.product import Category
from app.schemas.category import (
    CategoryCreate,
    CategoryDeleteResponse,
    CategoryFlatResponse,
    CategorySpecFilterOptionsResponse,
    CategorySpecLabelsResponse,
    CategorySpecTemplateResponse,
    CategoryTreeResponse,
    CategoryUpdate,
    DimensionsTemplate,
    FeatureTemplate,
    TechnicalSpecsTemplate,
)
from app.services.spec_template_service import (
    collect_storefront_spec_labels,
    extract_spec_filter_options,
    resolve_spec_template,
)
from app.utils.category_depth import build_category_metadata, is_selectable_product_category
from app.utils.category_tree import build_category_tree

logger = get_logger(__name__)


class CategoryService:
    @staticmethod
    async def get_category_tree(db: AsyncSession) -> List[CategoryTreeResponse]:
        categories = await crud_category.get_all_categories(db)
        try:
            return build_category_tree(categories)
        except ValueError as exc:
            logger.error("Invalid category hierarchy: %s", exc)
            raise

    @staticmethod
    async def get_flat_categories(db: AsyncSession) -> List[CategoryFlatResponse]:
        categories = await crud_category.get_all_categories(db)
        metadata = build_category_metadata(categories)

        return [
            CategoryFlatResponse(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
                depth=metadata[category.id]["depth"],
                is_leaf=metadata[category.id]["is_leaf"],
                is_selectable=is_selectable_product_category(metadata[category.id]),
                breadcrumb=metadata[category.id]["breadcrumb"],
                ancestor_ids=metadata[category.id]["ancestor_ids"],
            )
            for category in categories
        ]

    @staticmethod
    async def get_spec_template(
        db: AsyncSession, category_id: int
    ) -> CategorySpecTemplateResponse:
        categories = await crud_category.get_all_categories(db)
        by_id = {category.id: category for category in categories}
        category = by_id.get(category_id)

        if category is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Category with ID '{category_id}' not found",
            )

        meta = build_category_metadata(categories)[category_id]
        if not is_selectable_product_category(meta):
            raise api_error(
                400,
                error_code=ErrorCode.BAD_REQUEST,
                message="Spec templates are only available for assignable leaf categories",
                details=[
                    {
                        "field": "category_id",
                        "message": "دسته باید یک زیردستهٔ برگ قابل انتخاب باشد.",
                    }
                ],
            )

        raw = resolve_spec_template(category, by_id)
        default_values = _build_default_values(raw)

        return CategorySpecTemplateResponse(
            category_id=category.id,
            category_name=category.name,
            breadcrumb=meta["breadcrumb"],
            technical_specs=TechnicalSpecsTemplate(**raw["technical_specs"]),
            features=[FeatureTemplate(**feature) for feature in raw["features"]],
            dimensions=DimensionsTemplate(**raw["dimensions"]),
            default_values=default_values,
        )

    @staticmethod
    async def get_spec_filter_options(
        db: AsyncSession, category_id: int
    ) -> CategorySpecFilterOptionsResponse:
        categories = await crud_category.get_all_categories(db)
        by_id = {category.id: category for category in categories}
        category = by_id.get(category_id)
        if category is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Category with ID '{category_id}' not found",
            )

        meta = build_category_metadata(categories)[category_id]
        raw = resolve_spec_template(category, by_id)
        return CategorySpecFilterOptionsResponse(
            category_id=category.id,
            category_name=category.name,
            technical_specs=extract_spec_filter_options(raw),
        )

    @staticmethod
    def get_storefront_spec_labels() -> CategorySpecLabelsResponse:
        return CategorySpecLabelsResponse(labels=collect_storefront_spec_labels())

    @staticmethod
    async def create_category(db: AsyncSession, payload: CategoryCreate) -> CategoryFlatResponse:
        categories = await crud_category.get_all_categories(db)
        by_id = {category.id: category for category in categories}

        if payload.parent_id is not None and payload.parent_id not in by_id:
            raise api_error(
                400,
                error_code=ErrorCode.BAD_REQUEST,
                message="Parent category not found",
                details=[{"field": "parent_id", "message": "دسته‌بندی والد یافت نشد."}],
            )

        normalized_name = payload.name.strip()
        await _ensure_unique_category_name(
            db,
            name=normalized_name,
            parent_id=payload.parent_id,
        )

        category = await crud_category.create_category(
            db, name=normalized_name, parent_id=payload.parent_id
        )
        await db.commit()

        refreshed = await crud_category.get_all_categories(db)
        metadata = build_category_metadata(refreshed)[category.id]
        return CategoryFlatResponse(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            depth=metadata["depth"],
            is_leaf=metadata["is_leaf"],
            is_selectable=is_selectable_product_category(metadata),
            breadcrumb=metadata["breadcrumb"],
            ancestor_ids=metadata["ancestor_ids"],
        )

    @staticmethod
    async def update_category(
        db: AsyncSession, category_id: int, payload: CategoryUpdate
    ) -> CategoryFlatResponse:
        category = await crud_category.get_category_by_id(db, category_id)
        if category is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Category with ID '{category_id}' not found",
            )

        categories = await crud_category.get_all_categories(db)
        by_id = {row.id: row for row in categories}

        if payload.parent_id is not None:
            if payload.parent_id == category_id:
                raise api_error(
                    400,
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Category cannot be its own parent",
                )
            if payload.parent_id not in by_id:
                raise api_error(
                    400,
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Parent category not found",
                )
            if _creates_cycle(category_id, payload.parent_id, by_id):
                raise api_error(
                    400,
                    error_code=ErrorCode.BAD_REQUEST,
                    message="Invalid parent assignment (cycle detected)",
                )

        if payload.name is not None:
            normalized_name = payload.name.strip()
            target_parent_id = (
                payload.parent_id
                if "parent_id" in payload.model_fields_set
                else category.parent_id
            )
            await _ensure_unique_category_name(
                db,
                name=normalized_name,
                parent_id=target_parent_id,
                exclude_id=category_id,
            )
            category = await crud_category.update_category(
                db, category, name=normalized_name
            )
        if "parent_id" in payload.model_fields_set:
            if payload.name is None:
                await _ensure_unique_category_name(
                    db,
                    name=category.name,
                    parent_id=payload.parent_id,
                    exclude_id=category_id,
                )
            category = await crud_category.update_category(
                db,
                category,
                parent_id=payload.parent_id,
                unset_parent=payload.parent_id is None,
            )

        await db.commit()
        refreshed = await crud_category.get_all_categories(db)
        metadata = build_category_metadata(refreshed)[category.id]
        return CategoryFlatResponse(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            depth=metadata["depth"],
            is_leaf=metadata["is_leaf"],
            is_selectable=is_selectable_product_category(metadata),
            breadcrumb=metadata["breadcrumb"],
            ancestor_ids=metadata["ancestor_ids"],
        )

    @staticmethod
    async def delete_category_with_reassignment(
        db: AsyncSession, category_id: int
    ) -> CategoryDeleteResponse:
        category = await crud_category.get_category_by_id(db, category_id)
        if category is None:
            raise api_error(
                404,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Category with ID '{category_id}' not found",
            )

        child_count = await crud_category.count_subcategories(db, category_id)
        if child_count > 0:
            raise api_error(
                400,
                error_code=ErrorCode.BAD_REQUEST,
                message="Cannot delete a category that has subcategories",
                details=[
                    {
                        "field": "category_id",
                        "message": "ابتدا زیردسته‌های این دسته را حذف کنید.",
                    }
                ],
            )

        categories = await crud_category.get_all_categories(db)
        metadata = build_category_metadata(categories)[category_id]
        depth = metadata["depth"]

        if depth == 1:
            new_category_id: Optional[int] = None
            message = "Root category deleted; products are now uncategorized."
        else:
            new_category_id = category.parent_id
            message = "Category deleted; products reassigned to parent category."

        reassigned = await crud_category.reassign_products_category(
            db, category_id, new_category_id
        )
        await crud_category.delete_category_row(db, category)
        await db.commit()

        logger.info(
            "Deleted category %s (depth=%s); reassigned %s product(s) to category_id=%s",
            category_id,
            depth,
            reassigned,
            new_category_id,
        )

        return CategoryDeleteResponse(
            id=category_id,
            products_reassigned=reassigned,
            new_category_id=new_category_id,
            message=message,
        )


def _creates_cycle(
    category_id: int,
    new_parent_id: int,
    by_id: dict[int, Category],
) -> bool:
    """Return True if assigning new_parent_id under category_id would create a cycle."""
    current_id: Optional[int] = new_parent_id
    visited: set[int] = set()
    while current_id is not None:
        if current_id == category_id:
            return True
        if current_id in visited:
            break
        visited.add(current_id)
        parent = by_id.get(current_id)
        current_id = parent.parent_id if parent else None
    return False


async def _ensure_unique_category_name(
    db: AsyncSession,
    *,
    name: str,
    parent_id: Optional[int],
    exclude_id: Optional[int] = None,
) -> None:
    existing = await crud_category.get_category_by_parent_and_name(
        db, name=name, parent_id=parent_id
    )
    if existing is not None and (exclude_id is None or existing.id != exclude_id):
        raise api_error(
            400,
            error_code=ErrorCode.BAD_REQUEST,
            message="Category name already exists under this parent",
            details=[{"field": "name", "message": "نام دسته در این سطح تکراری است."}],
        )


def _build_default_values(template: dict) -> dict:
    """Shape default form values for the admin panel specifications section."""
    tech_keys = template["technical_specs"]["suggested_keys"]
    dim_keys = template["dimensions"]["suggested_keys"]

    feature_defaults: dict = {}
    for feature in template["features"]:
        feature_defaults[feature["key"]] = False
        detail = feature.get("detail")
        if detail:
            if detail["type"] == "string_array":
                feature_defaults[detail["key"]] = []
            elif detail["type"] == "string":
                feature_defaults[detail["key"]] = ""

    return {
        "technical_specs": [{"key": key, "value": ""} for key in tech_keys],
        "features": feature_defaults,
        "dimensions": [{"key": key, "value": None} for key in dim_keys],
    }
