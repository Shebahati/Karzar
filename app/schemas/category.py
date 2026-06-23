"""Category response schemas for tree and flat representations."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeResponse(CategoryResponse):
    """Recursive tree node with nested subcategories."""

    subcategories: List["CategoryTreeResponse"] = []


CategoryTreeResponse.model_rebuild()


class CategoryTreeListResponse(BaseModel):
    data: List[CategoryTreeResponse]
