"""Authentication and user account Pydantic schemas."""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_PATTERN = re.compile(r"^09\d{9}$")


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PinVerifyRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=12)


class StepUpTokenResponse(BaseModel):
    secure_token: str
    token_type: str = "step_up"
    expires_in: int


class OtpRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class OtpRequestResponse(BaseModel):
    phone: str
    expires_in: int
    dev_code: Optional[str] = None


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=12)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class CustomerBrief(BaseModel):
    id: int
    phone: str
    full_name: Optional[str] = None


class OtpVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer: CustomerBrief


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


class CurrentUserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: Optional[str]
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
