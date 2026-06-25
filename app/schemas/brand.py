"""Brand response schemas for the catalog API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class BrandResponse(BaseModel):
    id: int
    name: str
    country: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
