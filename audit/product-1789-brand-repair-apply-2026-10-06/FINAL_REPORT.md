# Product 1789 Brand Repair APPLY — FINAL REPORT

## A. Status

`APPLIED_VERIFIED`

## B. Authorization

Owner-authorized YES — scope: product 1789 / brand_id NULL→3 only.

## C. Entry

- origin/main at apply: `30c6baf3f23aa0e7a38172ca1732fdd81cd97ecb` (PR #437 merge)
- execution UTC: 2026-10-06 12:48:07.607913

## D. Production identity

- host: srv5944957438
- database: karzar_staging
- container: lathe_postgres
- volume: karzar_postgres_data
- APP_ENV: staging
- Alembic: u4v5w6x7y8z9

## E. Preconditions

- product_id/sku/mfg: 1789 / 1114-150 / 1114-150
- brand_id before: NULL
- expected brand: 3 / INSIZE
- manifest SHA: `c5c572b3aadc65ec13f0692e019c645a60cd4f09e87691ddf27da20b952821d8`
- CURRENT_HASH_MATCH: True

## F. Apply

- Product rows affected: 1
- field: brand_id NULL → 3
- audit rows: 1 (`owner_authorized_brand_integrity_repair`)
- commit: YES @ 2026-10-06 12:48:07.607913

## G. Post-commit

- brand_id: 3
- brand: INSIZE | اینسایز
- is_available: True (unchanged from True)
- is_active: True
- base_price: 7980000.00
- manufacturer_code: 1114-150

## H. Blast radius / sellability

- other Products changed: 0
- availability/price/activation changes: 0
- sellable before/after/delta: 717 / 717 / 0

## I. Hardening deploy

- #437 audit-hardening code on lathe_api image: **NO** (image `karzar-app:staging` created 2026-10-01; live `product_service` lacks brand_id tracked_fields)
- Data repair complete; recurrence prevention requires normal deploy of #437

## J. Safety

```text
Hesabfa mutation: NO
deployment performed: NO
Wave 1B mutation: NO
PRODUCT_1789_BRAND_REPAIR = VERIFIED
```
