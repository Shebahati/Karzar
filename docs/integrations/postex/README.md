# Postex logistics (Karzar)

Karzar owns logistics. Postex is a **backend provider** behind a provider-neutral shipping domain. Customers never talk to Postex.

Architecture:

```
Storefront / Admin
    → Karzar Logistics API (`/api/v1/shipping/*`)
    → ShippingProvider protocol
    → PostexProvider
    → Postex HTTP (`x-api-key` server-side only)
```

Official contract extraction: [`API-CONTRACT.md`](API-CONTRACT.md). Commerce money/payment: [`docs/COMMERCE.md`](../../COMMERCE.md).

## Feature flag (safe default)

| Variable | Default | Meaning |
|----------|---------|---------|
| `POSTEX_ENABLED` | `false` | Entire dynamic-shipping path off. Purchase checkout stays product+tax only. Inquiry unchanged. |

Rollback: set `POSTEX_ENABLED=false` and restart. Existing orders keep `postal_tracking_code` and any `shipments` rows; no historical backfill.

Activation is a **separate Owner operation**. This code must ship disabled.

## Required env when enabled

See `.env.example`. Startup **fails** if `POSTEX_ENABLED=true` and any of these are missing:

- `POSTEX_API_KEY`
- `POSTEX_ORIGIN_CITY_CODE`
- `POSTEX_ORIGIN_CITY_NAME`
- `POSTEX_ORIGIN_POSTAL_CODE`
- `POSTEX_ORIGIN_ADDRESS`
- `POSTEX_ORIGIN_FIRST_NAME`
- `POSTEX_ORIGIN_LAST_NAME`
- `POSTEX_ORIGIN_MOBILE`
- `POSTEX_COLLECTION_TYPE` (`pick_up` \| `courier_drop_off` \| `postex_drop_off`)

`POSTEX_BASE_URL` must be `https://api.postex.ir/api/v1` in staging/production. Localhost only in development/tests.

Never commit a real API key. Never return it from any API. Logs redact `x-api-key`, `authorization`, `token`, and nested secret names.

## Quote flow

1. Customer enters destination (normalized **city/location code**, not free-text alone).
2. Storefront `POST /api/v1/shipping/quotes` with cart items + destination code.
3. Server loads products, rejects incomplete package data (`SHIPPING_DATA_INCOMPLETE`), rejects `freight_only` (`SHIPPING_FREIGHT_REQUIRED`), builds one conservative parcel, calls Postex quotes.
4. Server persists options (unguessable tokens, TTL ~10 minutes) and returns customer-facing prices in **Toman**.
5. Customer selects a service. Checkout sends `shipping_quote_token` (not an amount).
6. Checkout re-verifies user, TTL, cart fingerprint, destination fingerprint, then **binds** the quote. Client amounts are never trusted.

v1 price policy: **pass-through**. `customer_shipping_cost = provider quote` (Toman). No markup, subsidy, or COD. `provider_shipping_cost` and `customer_shipping_cost` are stored separately for a future policy.

Payable total (purchase): **items + tax + customer shipping**. That sum is `orders.estimated_total` and is what SEP charges (×10 → Rial).

## Payment boundary

Checkout payment remains **SEP**. Postex wallet/COD/top-up are out of scope. Parcel `payment_type` is official **`SENDER`** (sender/merchant pays the carrier). Karzar collects product+tax+shipping from the customer via SEP, then pays Postex from the merchant wallet.

SEP init/verify/callback still use `order.estimated_total` once. Shipping is not added again.

## Booking flow (after payment)

SEP verify **must not** wait on Postex.

On payment `VERIFIED`:

1. Create/ensure a `shipments` row (`pending_booking`) in the same DB transaction as paid state.
2. Return the payment flow normally.
3. Background worker (same lifespan style as order-expiry / SEP verify retry) claims the row and `POST /parcels/bulk`.

`custom_order_no` = shipment UUID (lookup key). `custom_reference_no` = Karzar order tracking code.

## Idempotency / uncertain create

Official spec has **no** idempotency key. After a create **timeout**, shipment status is `creation_uncertain`. Worker reconciles with `GET /parcels/custom-order-no/{uuid}`. It does **not** POST bulk again until lookup proves no parcel.

## Tracking

No official webhook. Worker polls `GET /tracking/events/{parcel-no}` for non-terminal shipments. Events are append-only. Unknown Postex statuses are stored verbatim and mapped conservatively (never auto-delivered).

## Order ↔ shipment mapping

Shipment state is **not** `OrderStatus`.

| Shipment | Order |
|----------|--------|
| Label / barcode from `/parcels/bulk` | Still `paid` / `processing`. **Not** shipped. |
| Tracking evidence of physical handoff (`picked_up` / in-network) | Eligible `processing` → `shipped`. Mirror primary barcode onto legacy `orders.postal_tracking_code`. |
| All required non-cancelled shipments `delivered` | `shipped` → `delivered` |
| Terminal `delivered` | Never regress to in-transit on replay |

Admin manual ship dialog remains for fallback when Postex is off or a shipment is unmanaged.

## Package requirements

Products already have `weight_grams`. Do **not** use `specifications.dimensions` (engineering). New fields:

- `package_length_cm` / `package_width_cm` / `package_height_cm` (null = unknown, not zero)
- `shipping_is_fragile` / `shipping_is_liquid`
- `shipping_class`: `parcel` \| `freight_only`

v1 packer: sort each item’s edges, keep the two largest bounding axes, stack on the third, weight = Σ(weight × qty). Fit into an official Postex box (`GET /common/boxes`). If none fits or data is missing → no fabricated dimensions.

## Production enablement checklist

1. Fill origin address + city code from Postex locality APIs.
2. Catalog: every sellable `parcel` SKU has weight + package L/W/H.
3. `POSTEX_ENABLED=false` until Owner says otherwise.
4. One Owner-authorized **read-only** live smoke: `POSTEX_LIVE_READONLY_TESTS=1` (whoami, cities, methods, boxes, quote). **No parcel create.**
5. Later, a separate explicit human authorization for a sacrificial parcel lifecycle test.
6. Staging verification with SEP totals including shipping.
7. Production env + image rollout. Do not deploy from this document.

## Live-test safety

```bash
POSTEX_LIVE_READONLY_TESTS=1 POSTEX_API_KEY=… python3 scripts/postex_readonly_smoke.py
```

Allowed: whoami, cities/reference, shipping methods, boxes, quote. Forbidden: create/edit/cancel/mark-ready/wallet mutations. The script never prints the key.

## Rollback

`POSTEX_ENABLED=false`. Purchase checkout no longer requires a quote token. Existing shipments remain for history.
