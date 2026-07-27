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
        description="True when the category is a leaf at depth 2 or 3 (not an L1 root)",
    )
    breadcrumb: list[str] = Field(default_factory=list)
    ancestor_ids: list[int] = Field(default_factory=list)
    product_count: int | None = Field(None, ge=0)
    icon: str | None = None
    image_url: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    spec_template_key: str | None = None
    megamenu_hidden: bool = False
    megamenu_as_leaf: bool = False
    megamenu_bold: bool | None = None


class CategoryListResponse(BaseModel):
    data: list[CategoryFlatResponse]


class CategoryTreeResponse(CategoryResponse):
    """Recursive tree node with nested subcategories."""

    icon: str | None = Field(None, description="react-iconly icon name (roots only)")
    image_url: str | None = Field(None, description="Category card image URL")
    product_count: int | None = Field(None, ge=0)
    megamenu_hidden: bool = False
    megamenu_as_leaf: bool = False
    megamenu_bold: bool | None = None
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
    icon: str | None = Field(None, max_length=50)
    image_url: str | None = Field(None, max_length=500)
    meta_title: str | None = Field(None, max_length=255)
    meta_description: str | None = Field(None, max_length=500)
    spec_template_key: str | None = Field(None, max_length=50)
    megamenu_hidden: bool = False
    megamenu_as_leaf: bool = False
    megamenu_bold: bool | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_id: int | None = None
    slug: str | None = Field(None, min_length=1, max_length=200)
    icon: str | None = Field(None, max_length=50)
    image_url: str | None = Field(None, max_length=500)
    meta_title: str | None = Field(None, max_length=255)
    meta_description: str | None = Field(None, max_length=500)
    spec_template_key: str | None = Field(None, max_length=50)
    megamenu_hidden: bool | None = None
    megamenu_as_leaf: bool | None = None
    megamenu_bold: bool | None = None
    unset_megamenu_bold: bool = False


class CategoryImageUploadResponse(BaseModel):
    id: int
    image_url: str


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
