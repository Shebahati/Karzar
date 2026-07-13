"""Brand request/response schemas."""


from pydantic import BaseModel, ConfigDict, Field


class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str
    country: str | None = None
    logo_url: str | None = None
    product_count: int | None = Field(None, ge=0)

    model_config = ConfigDict(from_attributes=True)


class BrandListResponse(BaseModel):
    data: list[BrandResponse]


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country: str | None = Field(None, max_length=50)


class BrandUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    country: str | None = Field(None, max_length=50)
