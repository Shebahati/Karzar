"""Category response schemas for tree and flat representations."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryFlatResponse(CategoryResponse):
    """Flat category row with hierarchy metadata for admin product forms."""

    depth: int = Field(..., ge=1, description="1-based depth; roots are depth 1")
    is_leaf: bool
    is_selectable: bool = Field(
        ...,
        description="True only when depth==3 and the category is a leaf node",
    )
    breadcrumb: list[str] = Field(default_factory=list)
    ancestor_ids: list[int] = Field(default_factory=list)
    product_count: int | None = Field(None, ge=0)


class CategoryListResponse(BaseModel):
    data: list[CategoryFlatResponse]


class CategoryTreeResponse(CategoryResponse):
    """Recursive tree node with nested subcategories."""

    icon: str | None = Field(None, description="react-iconly icon name (roots only)")
    product_count: int | None = Field(None, ge=0)
    subcategories: list["CategoryTreeResponse"] = []


CategoryTreeResponse.model_rebuild()


class CategoryTreeListResponse(BaseModel):
    data: list[CategoryTreeResponse]


class FeatureDetailTemplate(BaseModel):
    key: str
    label: str
    type: str
    placeholder: str | None = None


class FeatureTemplate(BaseModel):
    key: str
    label: str
    type: str = "boolean"
    detail: FeatureDetailTemplate | None = None


class TechnicalSpecsTemplate(BaseModel):
    suggested_keys: list[str] = Field(default_factory=list)
    value_options: dict[str, list[str]] = Field(default_factory=dict)


class DimensionsTemplate(BaseModel):
    suggested_keys: list[str] = Field(default_factory=list)


class CategorySpecTemplateResponse(BaseModel):
    category_id: int
    category_name: str
    breadcrumb: list[str]
    technical_specs: TechnicalSpecsTemplate
    features: list[FeatureTemplate]
    dimensions: DimensionsTemplate
    default_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-filled specification object matching the admin form shape",
    )


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_id: int | None = None


class CategoryDeleteResponse(BaseModel):
    id: int
    products_reassigned: int
    new_category_id: int | None = None
    message: str


class CategorySpecLabelsResponse(BaseModel):
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Feature key to Persian label mapping for storefront display",
    )


class CategorySpecFilterOptionsResponse(BaseModel):
    category_id: int
    category_name: str
    technical_specs: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Available values per technical spec key for PLP filters",
    )
