from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeResponse(CategoryResponse):
    subcategories: List["CategoryTreeResponse"] = []


CategoryTreeResponse.model_rebuild()
