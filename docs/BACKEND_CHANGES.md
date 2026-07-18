# Backend Changes Report

This document is the communication bridge between the backend and frontend Cursor sessions.

## Summary Table

| Priority | Contract | Modified Files | Summary of Change | Needs Frontend Change |
|----------|----------|----------------|-------------------|----------------------|
| URGENT-1 | C1 | `app/core/errors.py`, `app/services/payment_service.py`, `app/api/endpoints/payment.py`, `tests/test_payments.py` | Payment init/verify idempotency; gateway-specific ErrorCodes; rate limiting on init; authority mismatch validation | Yes — handle new payment error codes |
| URGENT-2 | C3 | `app/core/constants.py`, `app/api/endpoints/payment.py`, `tests/test_payments.py` | `TOMAN_TO_RIAL = 10`; gateway amounts multiply Tomans × 10 | No — frontend already sends/receives Tomans |
| URGENT-3 | C2 | `app/api/endpoints/payment.py`, `app/core/errors.py`, `tests/test_payments.py` (in URGENT-1 commit) | `GUEST_ORDER_NOT_PAYABLE` when `order.user_id is None` | Yes — show Persian login prompt for this code |
| URGENT-4 | C4 | `tests/test_brand_endpoints.py` | Regression test: brand delete requires `X-Step-Up-Token` | No (backend verification only) |
| URGENT-5 | C15 | `app/core/startup.py`, `docs/LOCAL_DEV_FRONTEND.md` | Bootstrap seed product `DEV-CHECKOUT-001`; local dev guide for `NEXT_PUBLIC_USE_MOCK=false` | No |
| IMPORTANT-6 | — | `tests/test_product_endpoints.py` | Verified `description` and `original_price` serialize in `ProductDetailResponse` | No |
| IMPORTANT-7 | — | `app/utils/image_validation.py`, `app/api/endpoints/product.py`, `app/crud/product.py`, `app/db/models/product.py`, `app/utils/product_presenter.py`, `alembic/versions/k7l8m9n0o1p2_product_image_display_order.py` | Image URL validation, max 10 images, `PATCH /products/{id}/images/reorder` | Yes — use reorder endpoint if needed |
| IMPORTANT-8 | — | `app/schemas/common.py`, `app/api/endpoints/order.py`, `app/api/endpoints/users.py`, `app/crud/commerce.py`, `app/schemas/user_admin.py`, `tests/test_product_endpoints.py` | Admin orders/users: `page`/`page_size`, `sort`, user `search` | Yes — wire admin tables to new params |
| IMPORTANT-9 | — | `app/schemas/order.py`, `app/api/endpoints/order.py`, `tests/test_orders.py` | Tracking returns `items` (product_id, quantity, unit_price); no PII (phone, address, name) | Yes — display line items on tracking page |
| IMPORTANT-10 | C6 | `app/schemas/storefront.py`, `app/services/checkout_service.py`, `tests/test_storefront.py` | Checkout returns separate `status` (code) and `status_label` (Persian) | Yes — use both fields |
| MEDIUM-11 | — | `app/services/spec_template_service.py`, `app/services/category_service.py`, `app/api/endpoints/category.py`, `app/schemas/category.py` | Documented spec filters below; added `GET /categories/{id}/spec-filter-options` | Yes — build filter UI from new endpoint |
| MEDIUM-12 | C7 | `app/api/endpoints/category.py`, `app/services/spec_template_service.py`, `app/schemas/category.py` | `GET /categories/spec-labels` public Persian feature labels | Yes — cache and map storefront spec keys |
| MEDIUM-13 | C9, C8, C10 | `app/schemas/product.py` (C9/C8 in IMPORTANT-7 commit), `app/schemas/auth.py` | `DEFAULT_TAX_PERCENT = 9`; `category_id` Optional comment (C8); PIN 6–12 digits (C10) | Yes — align tax default; PIN UI min length 6 |
| 14 | C5 | — | No backend work (frontend only) | — |
| 15 | — | — | Token key inconsistency is frontend-only | — |

## New ErrorCodes

| ErrorCode | HTTP Status | When |
|-----------|-------------|------|
| `GUEST_ORDER_NOT_PAYABLE` | 403 | Payment init/verify on guest order (`user_id` is null) |
| `PAYMENT_GATEWAY_TIMEOUT` | 504 | Zarinpal/mock gateway timeout |
| `PAYMENT_GATEWAY_ERROR` | 502 | Gateway request/response failure |
| `PAYMENT_VERIFY_FAILED` | 400 | Invalid authority, signature, or rejected verification |

## New Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/v1/categories/spec-labels` | Public | Feature key → Persian label map (cacheable) |
| `GET` | `/api/v1/categories/{category_id}/spec-filter-options` | Public | Available technical spec values per category for PLP filters |
| `PATCH` | `/api/v1/products/{product_id}/images/reorder` | Super admin | Reorder images via `{ "image_ids": [3,1,2] }` |

## Spec Filter Parameters (Item 11)

Two mechanisms merge in `GET /api/v1/products/`:

1. **JSON param** `filters` — e.g. `?filters={"technical_specs.range":"0-150mm"}`
2. **Prefixed params** `spec_*` — double underscore becomes dot path:
   - `?spec_technical_specs__range=0-150mm` → `technical_specs.range`
   - Suffix `__icontains` for case-insensitive match: `?spec_technical_specs__range__icontains=150`

Boolean values accept `"true"` / `"false"` strings.

**Filter options endpoint:** `GET /api/v1/categories/{category_id}/spec-filter-options` returns `technical_specs: { "range": ["0-150mm", ...], ... }` from the category's spec template.

## Contract Discrepancies Resolved

| Contract assumption | Actual codebase | Resolution |
|---------------------|-----------------|------------|
| Image file upload + storage deletion | Images are **URL-based** only (no blob storage) | Validated URL type/extension, count limit, reorder via `display_order`; no orphan file deletion (N/A) |
| Order tracking includes status history | No status history table exists | Tracking returns current `status` + `status_label` and `items`; history not added (would need migration) |
| `page`/`page_size` pagination | Backend used `skip`/`limit` | Added `page`/`page_size` as preferred aliases; `skip`/`limit` still work |
| Checkout `status` was Persian label | `checkout_service` put label in `status` | Fixed: `status` = enum code, `status_label` = Persian |
| Product images reorder | No `display_order` column | Added migration `k7l8m9n0o1p2` + reorder endpoint |

## Local Backend for Frontend Testing

See [docs/LOCAL_DEV_FRONTEND.md](docs/LOCAL_DEV_FRONTEND.md).

Quick checklist:
- `DEBUG=true`, `OTP_DEV_ECHO=true`, `PAYMENT_PROVIDER=mock`
- `CORS_ORIGINS=http://localhost:3000,http://localhost:3001`
- Run `alembic upgrade head` then `uvicorn app.main:app --reload --port 8000`
- Sample product SKU: `DEV-CHECKOUT-001` (seeded on empty DB)

## Manual Test Commands

```bash
# Spec labels (storefront)
curl -s http://localhost:8000/api/v1/categories/spec-labels | jq

# Spec filter options for category 3
curl -s http://localhost:8000/api/v1/categories/3/spec-filter-options | jq

# Admin users with search + pagination
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/users?page=1&page_size=20&search=0912&sort=phone_asc" | jq

# Checkout status fields
curl -s -X POST http://localhost:8000/api/v1/checkout -H "Content-Type: application/json" \
  -d '{"mode":"purchase","customer":{"full_name":"Test","phone":"09121112222"},"items":[{"product_id":1,"quantity":1}],"shipping":{"province":"تهران","city":"تهران","postal_code":"1234567890","address_line":"خیابان تست پلاک ۱"}}' | jq '.status, .status_label'
```

## Test Results

```
160 passed, 2 skipped (pytest; coverage ≥ 62%)
```

See [docs/TESTING.md](docs/TESTING.md) for markers, CI, and Postgres/Redis integration setup.

## Tracking response (clarification)

Public `GET /orders/track/{tracking_code}` returns `items` (product_id, quantity, unit_price) **without PII** (no phone, address, or customer name). Status history is exposed as `timeline` (current implementation). This matches IMPORTANT-9 above and `tests/test_orders.py`.

## Acceptance Checklist

- [x] All 15 items implemented or marked not needed
- [x] Relevant pytest tests green
- [x] No files outside `Karzar/` modified
- [x] `BACKEND_CHANGES.md` created
