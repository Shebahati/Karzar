from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
import re

PHONE_PATTERN = re.compile(r"^09\d{9}$")


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    phone_number: str = Field(..., description="Iranian mobile number, e.g. 09123456789")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class UserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: Optional[str]
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
