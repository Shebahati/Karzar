"""Payment API schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class PaymentRefundMode(StrEnum):
    AUTOMATED = "automated"
    EXTERNAL_CONFIRMATION = "external_confirmation"


class PaymentInitRequest(BaseModel):
    order_id: int = Field(..., ge=1)


class PaymentInitResponse(BaseModel):
    authority: str
    payment_url: str


class PaymentVerifyRequest(BaseModel):
    """Verify by authority (preferred). ``order_id`` is optional when authority is known."""

    authority: str = Field(..., min_length=1, max_length=128)
    order_id: int | None = Field(None, ge=1)
    status: str | None = None


class PaymentVerifyResponse(BaseModel):
    order_id: int
    payment_status: str
    status: str
    ref_id: str | None = None
    tracking_code: str | None = None


class PaymentRefundRequest(BaseModel):
    order_id: int = Field(..., ge=1)


class PaymentRefundResponse(BaseModel):
    order_id: int
    payment_status: str
    status: str
    refund_id: str | None = None


class PaymentCapabilitiesResponse(BaseModel):
    provider: str
    automated_refund_supported: bool
    external_refund_confirmation_supported: bool
    refund_mode: PaymentRefundMode


class PaymentExternalRefundConfirmationRequest(BaseModel):
    order_id: int = Field(..., ge=1)
    external_reference: str = Field(..., min_length=1, max_length=64)
    evidence_note: str | None = Field(None, max_length=500)

    @field_validator("external_reference")
    @classmethod
    def validate_external_reference(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 3:
            raise ValueError("external_reference must be at least 3 characters after trimming")
        if len(trimmed) > 64:
            raise ValueError("external_reference must be at most 64 characters after trimming")
        return trimmed

    @field_validator("evidence_note")
    @classmethod
    def validate_evidence_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class PaymentExternalRefundConfirmationResponse(BaseModel):
    order_id: int
    payment_status: str
    status: str
    refund_id: str
    cancelled: bool
    reconciliation_required: bool
