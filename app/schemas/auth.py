"""Authentication and user account Pydantic schemas."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_PATTERN = re.compile(r"^09\d{9}$")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class PinVerifyRequest(BaseModel):
    pin: str = Field(..., min_length=6, max_length=12)

    @field_validator("pin")
    @classmethod
    def validate_pin_digits(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("PIN must contain only numeric characters")
        return value


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
    dev_code: str | None = None


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
    full_name: str | None = None


class OtpVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    customer: CustomerBrief


class UserCreate(BaseModel):
    phone_number: str = Field(..., description="Iranian mobile number, e.g. 09123456789")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = None
    company_name: str | None = Field(None, max_length=120)

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
    full_name: str | None
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CurrentUserResponse(BaseModel):
    id: int
    phone_number: str
    full_name: str | None
    role: str
    is_active: bool
    company_name: str | None = None
    is_b2b: bool = False


class RefreshTokenRequest(BaseModel):
    """Body refresh is optional when the HttpOnly refresh cookie is present."""

    refresh_token: str | None = Field(default=None, max_length=256)

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if len(value) < 16:
            raise ValueError("refresh_token must be at least 16 characters")
        return value


class PasswordResetRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class PasswordResetConfirmRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=12)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not PHONE_PATTERN.match(normalized):
            raise ValueError("Phone number must be a valid Iranian mobile number (09XXXXXXXXX)")
        return normalized


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
