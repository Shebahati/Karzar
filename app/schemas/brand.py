"""Brand request/response schemas."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BrandResponse(BaseModel):
    id: int
    name: str
    country: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country: Optional[str] = Field(None, max_length=50)


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
