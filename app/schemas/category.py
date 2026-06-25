"""Category response schemas for tree and flat representations."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryFlatResponse(CategoryResponse):
    depth: int
    is_leaf: bool
    is_selectable: bool
    breadcrumb: List[str]
    ancestor_ids: List[int]


class CategoryListResponse(BaseModel):
    data: List[CategoryFlatResponse]


class CategoryTreeResponse(CategoryResponse):
    """Recursive tree node with nested subcategories."""

    subcategories: List["CategoryTreeResponse"] = []


CategoryTreeResponse.model_rebuild()


class CategoryTreeListResponse(BaseModel):
    data: List[CategoryTreeResponse]
