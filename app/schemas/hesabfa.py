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
    stock_pull_enabled: bool = False
    item_push_enabled: bool = True
    admin_reads_enabled: bool = False


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
    disabled: bool = True
    message: str | None = None


class HesabfaItemPushResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: int
    error_samples: list[str] = Field(default_factory=list)


class HesabfaSalesSummaryResponse(BaseModel):
    website_paid_total_toman: str = Field(description="Sum of paid purchase orders on the site (Tomans)")
    website_paid_order_count: int
    # Always null — Hesabfa metrics must not be exposed to admin.
    hesabfa_sales_total: str | None = Field(
        default=None,
        description="Deprecated: always null (admin Hesabfa reads disabled)",
    )
    hesabfa_sales_total_toman: str | None = Field(
        default=None,
        description="Deprecated: always null (admin Hesabfa reads disabled)",
    )
    hesabfa_invoice_count: int | None = None
    hesabfa_currency_unit: str
    hesabfa_available: bool = False
    hesabfa_error: str | None = "hesabfa_admin_reads_disabled"
