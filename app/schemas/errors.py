from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)
