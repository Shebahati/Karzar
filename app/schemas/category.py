"""Category response schemas for tree and flat representations."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryFlatResponse(CategoryResponse):
    """Flat category row with hierarchy metadata for admin product forms."""

    depth: int = Field(..., ge=1, description="1-based depth; roots are depth 1")
    is_leaf: bool
    is_selectable: bool = Field(
        ...,
        description="True when the category is a leaf below root level (depth >= 2)",
    )
    breadcrumb: List[str] = Field(default_factory=list)
    ancestor_ids: List[int] = Field(default_factory=list)


class CategoryListResponse(BaseModel):
    data: List[CategoryFlatResponse]


class CategoryTreeResponse(CategoryResponse):
    """Recursive tree node with nested subcategories."""

    subcategories: List["CategoryTreeResponse"] = []


CategoryTreeResponse.model_rebuild()


class CategoryTreeListResponse(BaseModel):
    data: List[CategoryTreeResponse]


class FeatureDetailTemplate(BaseModel):
    key: str
    label: str
    type: str
    placeholder: Optional[str] = None


class FeatureTemplate(BaseModel):
    key: str
    label: str
    type: str = "boolean"
    detail: Optional[FeatureDetailTemplate] = None


class TechnicalSpecsTemplate(BaseModel):
    suggested_keys: List[str] = Field(default_factory=list)
    value_options: Dict[str, List[str]] = Field(default_factory=dict)


class DimensionsTemplate(BaseModel):
    suggested_keys: List[str] = Field(default_factory=list)


class CategorySpecTemplateResponse(BaseModel):
    category_id: int
    category_name: str
    breadcrumb: List[str]
    technical_specs: TechnicalSpecsTemplate
    features: List[FeatureTemplate]
    dimensions: DimensionsTemplate
    default_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-filled specification object matching the admin form shape",
    )


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None


class CategoryDeleteResponse(BaseModel):
    id: int
    products_reassigned: int
    new_category_id: Optional[int] = None
    message: str


class CategorySpecLabelsResponse(BaseModel):
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Feature key to Persian label mapping for storefront display",
    )


class CategorySpecFilterOptionsResponse(BaseModel):
    category_id: int
    category_name: str
    technical_specs: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Available values per technical spec key for PLP filters",
    )
