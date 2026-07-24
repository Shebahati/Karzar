"""Payment API schemas."""

from pydantic import BaseModel, Field


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
