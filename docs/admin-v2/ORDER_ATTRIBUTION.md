# Order source attribution (Admin V2-B)

Storefront captures first-party attribution in cookie `karzar_attribution_v1` (30 days).
Checkout sends `acquisition` snapshot; server validates and persists immutable order columns.

Admin: filter/list `acquisition_source`, detail section, `GET /orders/reports/acquisition`.
