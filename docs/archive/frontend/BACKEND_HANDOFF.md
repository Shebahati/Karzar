# Backend Handoff — KarZar Frontend Requirements

This document lists API gaps and contract extensions the **backend team** should implement so the frontend works with `NEXT_PUBLIC_USE_MOCK=false`. The frontend already handles these via mocks and mappers where possible.

---

## 1. Payment callback URL

Set in backend env:

```env
PAYMENT_CALLBACK_URL=http://localhost:3000/checkout/payment/callback
```

Production: use the live storefront URL + `/checkout/payment/callback`.

Frontend sends on verify:

```json
{ "order_id": 123, "authority": "...", "status": "OK" }
```

---

## 2. Order tracking timeline & logistics (decision 6-B)

**Current:** `GET /orders/track/{tracking_code}` returns status only.

**Needed:** extend `OrderTrackingResponse` (or admin order detail) with:

```json
{
  "postal_tracking_code": "1234567890123456",
  "delivery_eta": "2026-07-15T10:00:00Z",
  "timeline": [
    {
      "status": "paid",
      "status_label": "پرداخت شده",
      "occurred_at": "2026-07-09T12:00:00Z",
      "description": "پرداخت تأیید شد"
    }
  ]
}
```

Admin status update should accept optional:

```json
{
  "status": "shipped",
  "note": "...",
  "postal_tracking_code": "...",
  "delivery_eta": "..."
}
```

SMS hooks can use `postal_tracking_code` + customer phone later.

---

## 3. Deleted products list (decision 8-A)

**Needed:** `GET /products/?is_deleted=true` filter for admin deleted-products page.

**Needed:** `POST /products/{id}/restore` with `X-Step-Up-Token` (frontend already sends step-up).

---

## 4. Order line items enrichment (decision 4-B)

**Current:** Admin order items return `product_id`, `quantity`, `unit_price` only.

**Option A (preferred):** Include `product_name` and `sku` in `OrderItemResponse`.

**Option B:** Frontend batch-fetches `GET /products/?ids=1,2,3` (already implemented).

---

## 5. Customer admin fields (decision 9-A)

**Current:** PATCH `/users/{id}` requires step-up; accepts `full_name`, `is_active`.

**Not needed on backend:** `note`, `role`, `order_count`, `created_at` in PATCH (frontend read-only or mock-only extras).

Map `phone_number` in responses (frontend maps to `phone`).

---

## 6. Product images (decision 10-B)

**Current:** URL-only `POST /products/{id}/images` with `{ image_url, is_primary? }`.

**Optional future:** multipart upload endpoint. Frontend mock simulates file upload via blob URLs.

**Already exists:** primary, reorder, delete — frontend wired.

---

## 7. PLP spec filters (decision 11-B)

**Current:** `spec_*` query params on `GET /products/` (e.g. `spec_technical_specs__grade=GC4325`).

**Current:** `GET /categories/{id}/spec-filter-options` for filter UI values.

**Current:** `GET /categories/spec-labels` for Persian feature labels.

Ensure spec filter paths match admin product `specifications` JSONB shape.

---

## 8. Auth `/auth/me`

Return:

```json
{ "id": 1, "phone_number": "09121234567", "full_name": "..." }
```

Frontend maps `phone_number` → `phone`.

---

## 9. Stock adjust

**Current:** `POST /products/{id}/stock/adjust?quantity_delta=N&reason=...` (query params).

Frontend admin service uses query params when `USE_MOCK=false`.

---

## 10. Brands & categories envelopes

- `GET /brands/` → `{ "data": [...] }`
- `GET /categories/tree` → bare array `[...]` (not wrapped)

---

## Quick verification (backend dev)

```bash
curl -s http://localhost:8000/api/v1/categories/spec-labels | jq
curl -s "http://localhost:8000/api/v1/products/?spec_technical_specs__grade=GC4325" | jq
curl -s http://localhost:8000/api/v1/categories/11/spec-filter-options | jq
```

---

## Frontend env for live API

```env
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Storefront: port 3000 · Admin: port 3001 (run with `-p 3001`).
