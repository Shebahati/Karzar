"""Brand bulk base_price adjustment — preview, confirm, apply with drift guards."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.crud import platform as crud_platform
from app.crud import product as crud_product
from app.db.models.brand_bulk_pricing import (
    BrandPriceAdjustmentDirection,
    BrandPriceAdjustmentMode,
    BrandPriceLineStatus,
    BrandPriceOperation,
    BrandPriceOperationLine,
    BrandPriceOperationStatus,
)
from app.db.models.product import Brand, Product
from app.db.models.user import User
from app.schemas.brand_bulk_pricing import (
    BrandBulkPricingApplyResponse,
    BrandBulkPricingConfirmRequest,
    BrandBulkPricingOperationDetail,
    BrandBulkPricingOperationListResponse,
    BrandBulkPricingOperationSummary,
    BrandBulkPricingPreviewResponse,
    BrandBulkPricingAdjustRequest,
    line_from_values,
)
from app.services.audit_service import record_audit
from app.utils.decimal_utils import to_decimal
from app.utils.storefront_catalog import decimal_to_api_string

MANIFEST_SCHEMA = "brand.bulk_price.manifest.v1"
MONEY_QUANT = Decimal("0.01")
IDEMPOTENCY_SCOPE_PREFIX = "brand_bulk_pricing:apply"


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def compute_adjusted_base_price(
    *,
    old_base: Decimal,
    mode: BrandPriceAdjustmentMode,
    direction: BrandPriceAdjustmentDirection,
    amount: Decimal,
) -> Decimal:
    if mode == BrandPriceAdjustmentMode.PERCENT:
        factor = amount / Decimal("100")
        if direction == BrandPriceAdjustmentDirection.INCREASE:
            result = old_base * (Decimal("1") + factor)
        else:
            result = old_base * (Decimal("1") - factor)
    else:
        if direction == BrandPriceAdjustmentDirection.INCREASE:
            result = old_base + amount
        else:
            result = old_base - amount
    return _quantize_money(result)


def _discount_conflict(new_base: Decimal, original: Decimal | None) -> str | None:
    if original is None:
        return None
    orig = to_decimal(original)
    if orig <= Decimal("0"):
        return None
    if new_base >= orig:
        return "new_base_price_invalidates_discount"
    return None


def _catalog_fingerprint_rows(products: list[Product]) -> list[dict[str, str]]:
    rows = []
    for product in sorted(products, key=lambda p: p.id):
        base = product.base_price
        rows.append(
            {
                "product_id": str(product.id),
                "base_price": decimal_to_api_string(base) if base is not None else None,
            }
        )
    return rows


def compute_catalog_fingerprint_sha256(products: list[Product]) -> str:
    payload = {"schema": "brand.bulk_price.catalog_fingerprint.v1", "rows": _catalog_fingerprint_rows(products)}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_manifest_payload(
    *,
    brand_id: int,
    mode: BrandPriceAdjustmentMode,
    direction: BrandPriceAdjustmentDirection,
    amount: Decimal,
    lines: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_lines = sorted(lines, key=lambda row: (row["product_id"], row["sku"]))
    return {
        "schema": MANIFEST_SCHEMA,
        "brand_id": brand_id,
        "adjustment": {
            "mode": mode.value,
            "direction": direction.value,
            "amount": decimal_to_api_string(amount),
        },
        "lines": normalized_lines,
    }


def compute_manifest_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _fetch_brand_or_404(db: AsyncSession, brand_id: int) -> Brand:
    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Brand not found",
            details=[{"field": "brand_id", "message": "not found"}],
        )
    return brand


async def _fetch_brand_products(db: AsyncSession, brand_id: int) -> list[Product]:
    stmt = (
        select(Product)
        .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
        .order_by(Product.id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _build_preview_lines(
    products: list[Product],
    *,
    mode: BrandPriceAdjustmentMode,
    direction: BrandPriceAdjustmentDirection,
    amount: Decimal,
) -> tuple[list[dict[str, Any]], list[Any]]:
    manifest_lines: list[dict[str, Any]] = []
    response_lines = []
    for product in products:
        old_base = product.base_price
        original = product.original_price
        if old_base is None:
            line_status = BrandPriceLineStatus.SKIPPED.value
            conflict_reason = "missing_base_price"
            new_base = None
        else:
            old_dec = to_decimal(old_base)
            new_base = compute_adjusted_base_price(
                old_base=old_dec,
                mode=mode,
                direction=direction,
                amount=amount,
            )
            if new_base <= Decimal("0"):
                line_status = BrandPriceLineStatus.CONFLICT.value
                conflict_reason = "non_positive_result"
            else:
                conflict_reason = _discount_conflict(new_base, original)
                if conflict_reason:
                    line_status = BrandPriceLineStatus.CONFLICT.value
                else:
                    line_status = BrandPriceLineStatus.PENDING.value
                    conflict_reason = None
        manifest_lines.append(
            {
                "product_id": product.id,
                "sku": product.sku,
                "old_base_price": decimal_to_api_string(old_base),
                "new_base_price": decimal_to_api_string(new_base),
                "original_price": decimal_to_api_string(original),
                "line_status": line_status,
                "conflict_reason": conflict_reason,
            }
        )
        response_lines.append(
            line_from_values(
                product_id=product.id,
                sku=product.sku,
                old_base=to_decimal(old_base) if old_base is not None else None,
                new_base=new_base,
                original=to_decimal(original) if original is not None else None,
                line_status=line_status,
                conflict_reason=conflict_reason,
            )
        )
    return manifest_lines, response_lines


class BrandBulkPricingService:
    @staticmethod
    async def preview(
        db: AsyncSession, payload: BrandBulkPricingAdjustRequest
    ) -> BrandBulkPricingPreviewResponse:
        await _fetch_brand_or_404(db, payload.brand_id)
        mode = BrandPriceAdjustmentMode(payload.mode)
        direction = BrandPriceAdjustmentDirection(payload.direction)
        amount = to_decimal(payload.amount)
        products = await _fetch_brand_products(db, payload.brand_id)
        manifest_lines, response_lines = _build_preview_lines(
            products, mode=mode, direction=direction, amount=amount
        )
        manifest = build_manifest_payload(
            brand_id=payload.brand_id,
            mode=mode,
            direction=direction,
            amount=amount,
            lines=manifest_lines,
        )
        manifest_sha = compute_manifest_sha256(manifest)
        fingerprint = compute_catalog_fingerprint_sha256(products)
        eligible = sum(1 for line in response_lines if line.line_status == BrandPriceLineStatus.PENDING.value)
        conflicts = sum(1 for line in response_lines if line.line_status == BrandPriceLineStatus.CONFLICT.value)
        skipped = sum(1 for line in response_lines if line.line_status == BrandPriceLineStatus.SKIPPED.value)
        return BrandBulkPricingPreviewResponse(
            brand_id=payload.brand_id,
            mode=payload.mode,
            direction=payload.direction,
            amount=decimal_to_api_string(amount) or "0",
            manifest_sha256=manifest_sha,
            catalog_fingerprint_sha256=fingerprint,
            total_products=len(response_lines),
            eligible_count=eligible,
            conflict_count=conflicts,
            skipped_count=skipped,
            lines=response_lines,
        )

    @staticmethod
    async def confirm(
        db: AsyncSession,
        payload: BrandBulkPricingConfirmRequest,
        *,
        actor: User,
    ) -> BrandBulkPricingOperationDetail:
        preview = await BrandBulkPricingService.preview(db, payload)
        if preview.manifest_sha256 != payload.manifest_sha256.strip().lower():
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message="Preview manifest hash mismatch — re-run preview",
                details=[{"field": "manifest_sha256", "message": "stale or mismatched"}],
            )
        mode = BrandPriceAdjustmentMode(payload.mode)
        direction = BrandPriceAdjustmentDirection(payload.direction)
        amount = to_decimal(payload.amount)
        manifest_lines = [
            {
                "product_id": line.product_id,
                "sku": line.sku,
                "old_base_price": line.old_base_price,
                "new_base_price": line.new_base_price,
                "original_price": line.original_price,
                "line_status": line.line_status,
                "conflict_reason": line.conflict_reason,
            }
            for line in preview.lines
        ]
        manifest = build_manifest_payload(
            brand_id=payload.brand_id,
            mode=mode,
            direction=direction,
            amount=amount,
            lines=manifest_lines,
        )
        operation = BrandPriceOperation(
            brand_id=payload.brand_id,
            status=BrandPriceOperationStatus.CONFIRMED,
            adjustment_mode=mode,
            adjustment_direction=direction,
            adjustment_amount=amount,
            manifest=manifest,
            manifest_sha256=preview.manifest_sha256,
            catalog_fingerprint_sha256=preview.catalog_fingerprint_sha256,
            actor_user_id=actor.id,
            confirmed_at=datetime.now(UTC),
        )
        db.add(operation)
        await db.flush()
        for line in preview.lines:
            db.add(
                BrandPriceOperationLine(
                    operation_id=operation.id,
                    product_id=line.product_id,
                    sku_snapshot=line.sku,
                    old_base_price=to_decimal(line.old_base_price) if line.old_base_price else None,
                    new_base_price=to_decimal(line.new_base_price) if line.new_base_price else None,
                    original_price_snapshot=to_decimal(line.original_price) if line.original_price else None,
                    line_status=BrandPriceLineStatus(line.line_status),
                    conflict_reason=line.conflict_reason,
                )
            )
        await record_audit(
            db,
            actor_user_id=actor.id,
            action="brand_bulk_pricing.confirm",
            entity_type="brand_price_operation",
            entity_id=operation.id,
            details={"brand_id": payload.brand_id, "manifest_sha256": preview.manifest_sha256},
        )
        await db.commit()
        await db.refresh(operation)
        return await BrandBulkPricingService.get_operation(db, operation.id)

    @staticmethod
    async def get_operation(db: AsyncSession, operation_id: int) -> BrandBulkPricingOperationDetail:
        operation = (
            await db.execute(
                select(BrandPriceOperation)
                .options(selectinload(BrandPriceOperation.lines))
                .where(BrandPriceOperation.id == operation_id)
            )
        ).scalar_one_or_none()
        if operation is None:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message="Operation not found",
            )
        lines = [
            line_from_values(
                product_id=line.product_id,
                sku=line.sku_snapshot,
                old_base=line.old_base_price,
                new_base=line.new_base_price,
                original=line.original_price_snapshot,
                line_status=line.line_status.value,
                conflict_reason=line.conflict_reason,
            )
            for line in sorted(operation.lines, key=lambda row: row.product_id)
        ]
        eligible = sum(1 for line in lines if line.line_status == BrandPriceLineStatus.PENDING.value)
        conflicts = sum(1 for line in lines if line.line_status == BrandPriceLineStatus.CONFLICT.value)
        return BrandBulkPricingOperationDetail(
            id=operation.id,
            brand_id=operation.brand_id,
            status=operation.status.value,
            mode=operation.adjustment_mode.value,
            direction=operation.adjustment_direction.value,
            amount=decimal_to_api_string(operation.adjustment_amount) or "0",
            manifest_sha256=operation.manifest_sha256,
            catalog_fingerprint_sha256=operation.catalog_fingerprint_sha256,
            actor_user_id=operation.actor_user_id,
            confirmed_at=operation.confirmed_at,
            applied_at=operation.applied_at,
            eligible_count=eligible,
            conflict_count=conflicts,
            lines=lines,
            apply_error=operation.apply_error,
        )

    @staticmethod
    async def list_operations(
        db: AsyncSession, *, skip: int = 0, limit: int = 50, brand_id: int | None = None
    ) -> BrandBulkPricingOperationListResponse:
        filters = []
        if brand_id is not None:
            filters.append(BrandPriceOperation.brand_id == brand_id)
        total = (
            await db.execute(select(func.count()).select_from(BrandPriceOperation).where(*filters))
        ).scalar_one()
        rows = (
            await db.execute(
                select(BrandPriceOperation)
                .options(selectinload(BrandPriceOperation.lines))
                .where(*filters)
                .order_by(BrandPriceOperation.id.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()
        data = []
        for operation in rows:
            eligible = sum(
                1 for line in operation.lines if line.line_status == BrandPriceLineStatus.PENDING
            )
            conflicts = sum(
                1 for line in operation.lines if line.line_status == BrandPriceLineStatus.CONFLICT
            )
            data.append(
                BrandBulkPricingOperationSummary(
                    id=operation.id,
                    brand_id=operation.brand_id,
                    status=operation.status.value,
                    mode=operation.adjustment_mode.value,
                    direction=operation.adjustment_direction.value,
                    amount=decimal_to_api_string(operation.adjustment_amount) or "0",
                    manifest_sha256=operation.manifest_sha256,
                    catalog_fingerprint_sha256=operation.catalog_fingerprint_sha256,
                    actor_user_id=operation.actor_user_id,
                    confirmed_at=operation.confirmed_at,
                    applied_at=operation.applied_at,
                    eligible_count=eligible,
                    conflict_count=conflicts,
                )
            )
        return BrandBulkPricingOperationListResponse(data=data, total=total)

    @staticmethod
    async def apply_operation(
        db: AsyncSession,
        operation_id: int,
        *,
        actor: User,
        idempotency_key: str | None,
    ) -> BrandBulkPricingApplyResponse:
        if not settings.BRAND_BULK_PRICE_APPLY_ENABLED:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.FORBIDDEN,
                message="Brand bulk price apply is disabled",
            )

        scope = f"{IDEMPOTENCY_SCOPE_PREFIX}:{operation_id}"
        expires_at = datetime.now(UTC) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS)
        if idempotency_key:
            existing = await crud_platform.get_idempotency_record(
                db, scope=scope, key=idempotency_key
            )
            if existing and existing.status_code:
                body = existing.response_body or {}
                return BrandBulkPricingApplyResponse(**body)
            reserved = await crud_platform.reserve_idempotency_record(
                db, scope=scope, key=idempotency_key, expires_at=expires_at
            )
            if not reserved:
                existing = await crud_platform.get_idempotency_record(
                    db, scope=scope, key=idempotency_key
                )
                if existing and existing.response_body:
                    return BrandBulkPricingApplyResponse(**existing.response_body)

        operation = (
            await db.execute(
                select(BrandPriceOperation)
                .options(selectinload(BrandPriceOperation.lines))
                .where(BrandPriceOperation.id == operation_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if operation is None:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message="Operation not found",
            )
        if operation.status == BrandPriceOperationStatus.APPLIED:
            response = BrandBulkPricingApplyResponse(
                operation_id=operation.id,
                status=operation.status.value,
                applied_count=sum(
                    1 for line in operation.lines if line.line_status == BrandPriceLineStatus.APPLIED
                ),
                skipped_count=sum(
                    1 for line in operation.lines if line.line_status == BrandPriceLineStatus.SKIPPED
                ),
                conflict_count=sum(
                    1 for line in operation.lines if line.line_status == BrandPriceLineStatus.CONFLICT
                ),
                drift_detected=False,
            )
            return response
        if operation.status != BrandPriceOperationStatus.CONFIRMED:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=f"Operation status {operation.status.value} cannot be applied",
            )

        pending_lines = [
            line for line in operation.lines if line.line_status == BrandPriceLineStatus.PENDING
        ]
        product_ids = [line.product_id for line in pending_lines]
        locked = await crud_product.get_products_for_update(db, product_ids)
        live_products = list(locked.values())
        live_fingerprint = compute_catalog_fingerprint_sha256(live_products)
        drift_detected = live_fingerprint != operation.catalog_fingerprint_sha256
        if drift_detected:
            operation.status = BrandPriceOperationStatus.FAILED
            operation.apply_error = "catalog_fingerprint_drift"
            await db.commit()
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message="Catalog drift detected since confirm — re-run preview",
                details=[{"field": "catalog_fingerprint_sha256", "message": "drift"}],
            )

        applied_count = 0
        for line in pending_lines:
            product = locked.get(line.product_id)
            if product is None:
                line.line_status = BrandPriceLineStatus.SKIPPED
                line.conflict_reason = "product_missing"
                continue
            if line.new_base_price is None:
                line.line_status = BrandPriceLineStatus.SKIPPED
                continue
            new_base = to_decimal(line.new_base_price)
            conflict = _discount_conflict(new_base, product.original_price)
            if conflict:
                line.line_status = BrandPriceLineStatus.CONFLICT
                line.conflict_reason = conflict
                continue
            old_str = decimal_to_api_string(product.base_price)
            product.base_price = new_base
            line.line_status = BrandPriceLineStatus.APPLIED
            applied_count += 1
            await crud_platform.record_product_change(
                db,
                product_id=product.id,
                field_name="base_price",
                old_value=old_str,
                new_value=decimal_to_api_string(new_base),
                reason=f"brand_bulk_pricing:{operation.id}",
                actor_user_id=actor.id,
            )

        operation.status = BrandPriceOperationStatus.APPLIED
        operation.applied_at = datetime.now(UTC)
        operation.audit_details = {
            "applied_count": applied_count,
            "actor_user_id": actor.id,
        }
        await record_audit(
            db,
            actor_user_id=actor.id,
            action="brand_bulk_pricing.apply",
            entity_type="brand_price_operation",
            entity_id=operation.id,
            details={"applied_count": applied_count},
        )
        await db.commit()

        response = BrandBulkPricingApplyResponse(
            operation_id=operation.id,
            status=operation.status.value,
            applied_count=applied_count,
            skipped_count=sum(
                1 for line in operation.lines if line.line_status == BrandPriceLineStatus.SKIPPED
            ),
            conflict_count=sum(
                1 for line in operation.lines if line.line_status == BrandPriceLineStatus.CONFLICT
            ),
            drift_detected=False,
        )
        if idempotency_key:
            await crud_platform.finalize_idempotency_record(
                db,
                scope=scope,
                key=idempotency_key,
                status_code=200,
                response_body=response.model_dump(),
                expires_at=expires_at,
            )
            await db.commit()
        return response
