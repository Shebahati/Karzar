"""Standard API error response schemas."""


from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """Frontend error contract: {error_code, message, details[]}."""

    error_code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
