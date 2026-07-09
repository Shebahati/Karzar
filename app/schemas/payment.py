"""Payment API schemas."""

from pydantic import BaseModel, Field


class PaymentInitRequest(BaseModel):
    order_id: int = Field(..., ge=1)


class PaymentInitResponse(BaseModel):
    authority: str
    payment_url: str


class PaymentVerifyRequest(BaseModel):
    order_id: int = Field(..., ge=1)
    authority: str
    status: str | None = None


class PaymentVerifyResponse(BaseModel):
    order_id: int
    payment_status: str
    status: str
    ref_id: str | None = None
