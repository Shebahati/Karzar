"""Admin endpoints for Hesabfa (حسابفا) integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.hesabfa import (
    HesabfaItemPushResponse,
    HesabfaMappingSyncResponse,
    HesabfaSalesSummaryResponse,
    HesabfaStatusResponse,
    HesabfaStockSyncResponse,
)
from app.services.hesabfa.client import get_hesabfa_client
from app.services.hesabfa.exceptions import HesabfaError, HesabfaNotConfiguredError
from app.services.hesabfa.item_push import push_all_site_products_to_hesabfa
from app.services.hesabfa.mapping import sync_item_mappings_by_sku
from app.services.hesabfa.sales import get_sales_summary

router = APIRouter()


def _require_hesabfa_ready() -> None:
    if not settings.HESABFA_ENABLED:
        raise api_error(
            503,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Hesabfa integration is disabled (set HESABFA_ENABLED=true)",
        )
    if not get_hesabfa_client().is_configured():
        raise api_error(
            503,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Hesabfa credentials are not configured on this server",
        )


@router.get("/status", response_model=HesabfaStatusResponse, summary="Hesabfa integration status")
async def hesabfa_status(
    _: User = Depends(get_current_super_admin),
) -> HesabfaStatusResponse:
    client = get_hesabfa_client()
    return HesabfaStatusResponse(
        enabled=settings.HESABFA_ENABLED,
        configured=client.is_configured(),
        test_mode=settings.HESABFA_TEST_MODE,
        base_url=settings.HESABFA_BASE_URL,
        warehouse_code=settings.HESABFA_WAREHOUSE_CODE,
        currency_unit=settings.HESABFA_CURRENCY_UNIT,
        stock_sync_interval_seconds=settings.HESABFA_STOCK_SYNC_INTERVAL_SECONDS,
        stock_pull_enabled=False,
        item_push_enabled=True,
        admin_reads_enabled=settings.HESABFA_ADMIN_READS_ENABLED,
    )


@router.post(
    "/mappings/sync",
    response_model=HesabfaMappingSyncResponse,
    summary="Match site products to Hesabfa items by SKU",
)
async def sync_mappings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> HesabfaMappingSyncResponse:
    _require_hesabfa_ready()
    try:
        result = await sync_item_mappings_by_sku(db)
        await db.commit()
    except HesabfaNotConfiguredError as exc:
        raise api_error(503, error_code=ErrorCode.INTERNAL_ERROR, message=str(exc)) from exc
    except HesabfaError as exc:
        raise api_error(502, error_code=ErrorCode.INTERNAL_ERROR, message=str(exc)) from exc
    return HesabfaMappingSyncResponse(
        matched=result.matched,
        created=result.created,
        updated=result.updated,
        scanned_hesabfa=result.scanned_hesabfa,
        unmatched_site_skus=result.unmatched_site_skus,
    )


@router.post(
    "/items/push",
    response_model=HesabfaItemPushResponse,
    summary="Push site products into Hesabfa as item shells (qty 0)",
)
async def push_items(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    limit: int | None = Query(default=None, ge=1, le=5000),
) -> HesabfaItemPushResponse:
    _require_hesabfa_ready()
    try:
        result = await push_all_site_products_to_hesabfa(db, limit=limit)
        await db.commit()
    except HesabfaNotConfiguredError as exc:
        raise api_error(503, error_code=ErrorCode.INTERNAL_ERROR, message=str(exc)) from exc
    except HesabfaError as exc:
        raise api_error(502, error_code=ErrorCode.INTERNAL_ERROR, message=str(exc)) from exc
    return HesabfaItemPushResponse(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
        error_samples=list(result.error_samples),
    )


@router.post(
    "/stock/sync",
    response_model=HesabfaStockSyncResponse,
    summary="Deprecated: Hesabfa→site quantity pull is disabled",
    deprecated=True,
)
async def sync_stock(
    _: User = Depends(get_current_super_admin),
) -> HesabfaStockSyncResponse:
    return HesabfaStockSyncResponse(
        checked=0,
        updated=0,
        unchanged=0,
        missing_in_hesabfa=0,
        disabled=True,
        message="Hesabfa→site quantity sync is disabled; manage stock only in Hesabfa",
    )


@router.get(
    "/sales-summary",
    response_model=HesabfaSalesSummaryResponse,
    summary="Website-only paid sales (Hesabfa admin reads disabled)",
)
async def sales_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> HesabfaSalesSummaryResponse:
    """Website paid totals only — never returns Hesabfa invoice/sales figures."""
    summary = await get_sales_summary(db)
    return HesabfaSalesSummaryResponse(
        website_paid_total_toman=str(summary.website_paid_total_toman),
        website_paid_order_count=summary.website_paid_order_count,
        hesabfa_sales_total=None,
        hesabfa_sales_total_toman=None,
        hesabfa_invoice_count=None,
        hesabfa_currency_unit=summary.hesabfa_currency_unit,
        hesabfa_available=False,
        hesabfa_error=summary.hesabfa_error or "hesabfa_admin_reads_disabled",
    )
