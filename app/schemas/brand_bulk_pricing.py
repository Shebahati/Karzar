"""Schemas for brand bulk base_price adjustment (Feature D)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.utils.storefront_catalog import decimal_to_api_string

AdjustmentMode = Literal["percent"]
AdjustmentDirection = Literal["increase", "decrease"]


class BrandBulkPricingAdjustRequest(BaseModel):
    brand_id: int = Field(..., ge=1)
    mode: AdjustmentMode
    direction: AdjustmentDirection
    amount: Decimal = Field(..., gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal, info):
        mode = info.data.get("mode")
        if mode == "percent":
            if value <= Decimal("0"):
                raise ValueError("percent must be positive")
            if value >= Decimal("100") and info.data.get("direction") == "decrease":
                raise ValueError("decrease percent must be less than 100")
            if value > Decimal("100"):
                raise ValueError("percent amount cannot exceed 100")
        return value


class BrandBulkPricingPreviewLine(BaseModel):
    product_id: int
    sku: str
    old_base_price: str | None
    new_base_price: str | None
    original_price: str | None
    line_status: str
    conflict_reason: str | None = None


class BrandBulkPricingPreviewResponse(BaseModel):
    brand_id: int
    mode: AdjustmentMode
    direction: AdjustmentDirection
    amount: str
    manifest_sha256: str
    catalog_fingerprint_sha256: str
    total_products: int
    eligible_count: int
    conflict_count: int
    skipped_count: int
    lines: list[BrandBulkPricingPreviewLine]


class BrandBulkPricingConfirmRequest(BrandBulkPricingAdjustRequest):
    manifest_sha256: str = Field(..., min_length=64, max_length=64)


class BrandBulkPricingOperationSummary(BaseModel):
    id: int
    brand_id: int
    status: str
    mode: AdjustmentMode
    direction: AdjustmentDirection
    amount: str
    manifest_sha256: str
    catalog_fingerprint_sha256: str
    actor_user_id: int | None
    confirmed_at: datetime
    applied_at: datetime | None = None
    eligible_count: int
    conflict_count: int


class BrandBulkPricingOperationDetail(BrandBulkPricingOperationSummary):
    lines: list[BrandBulkPricingPreviewLine]
    apply_error: str | None = None


class BrandBulkPricingOperationListResponse(BaseModel):
    data: list[BrandBulkPricingOperationSummary]
    total: int


class BrandBulkPricingApplyResponse(BaseModel):
    operation_id: int
    status: str
    applied_count: int
    skipped_count: int
    conflict_count: int
    drift_detected: bool = False


def line_from_values(
    *,
    product_id: int,
    sku: str,
    old_base: Decimal | None,
    new_base: Decimal | None,
    original: Decimal | None,
    line_status: str,
    conflict_reason: str | None = None,
) -> BrandBulkPricingPreviewLine:
    return BrandBulkPricingPreviewLine(
        product_id=product_id,
        sku=sku,
        old_base_price=decimal_to_api_string(old_base),
        new_base_price=decimal_to_api_string(new_base),
        original_price=decimal_to_api_string(original),
        line_status=line_status,
        conflict_reason=conflict_reason,
    )
