"""Pydantic schemas for Hesabfa admin endpoints."""

from pydantic import BaseModel, Field


class HesabfaStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    test_mode: bool
    base_url: str
    warehouse_code: int | None = None
    currency_unit: str
    stock_sync_interval_seconds: int


class HesabfaMappingSyncResponse(BaseModel):
    matched: int
    created: int
    updated: int
    scanned_hesabfa: int
    unmatched_site_skus: int


class HesabfaStockSyncResponse(BaseModel):
    checked: int
    updated: int
    unchanged: int
    missing_in_hesabfa: int


class HesabfaSalesSummaryResponse(BaseModel):
    website_paid_total_toman: str = Field(description="Sum of paid purchase orders on the site (Tomans)")
    website_paid_order_count: int
    hesabfa_sales_total: str | None = Field(
        default=None,
        description="Sum of Hesabfa sale invoices (all channels) in Hesabfa currency unit",
    )
    hesabfa_sales_total_toman: str | None = Field(
        default=None,
        description="Hesabfa sales converted to Tomans for display parity",
    )
    hesabfa_invoice_count: int | None = None
    hesabfa_currency_unit: str
    hesabfa_available: bool
    hesabfa_error: str | None = None
