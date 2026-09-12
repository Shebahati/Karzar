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

v1 price policy: **pass-through**. Customer shipping equals the **total** provider logistics cost in Toman (service component + pickup when Postex returns `pickup_price`). No markup, subsidy, or COD.

Component storage on `shipping_quotes`:

| Field | Meaning |
|-------|---------|
| `provider_amount_toman` | Carrier **service** component only |
| `pickup_amount_toman` | Collection/pickup component (nullable) |
| `customer_amount_toman` | Karzar customer shipping price (policy) |

**Provider total** (what Karzar owes the provider for this quote) is computed centrally as:

```text
provider_total_toman = provider_amount_toman + COALESCE(pickup_amount_toman, 0)
```

Snapshots:

- `orders.shipping_provider_quoted_cost` / `shipments.provider_quoted_cost` → **provider total**
- `orders.shipping_customer_cost` / `shipments.customer_shipping_cost` → **customer policy price**

v1 pass-through: these two snapshot totals are equal. Compute them independently so a future markup/subsidy policy can diverge without rewriting accounting.

Live example (2026-09-10): service `1,298,000` IRR + pickup `1,200,000` IRR = `2,498,000` IRR = `249,800` Toman provider total.

Payable total (purchase):

- **`sender_prepaid`:** items + tax + customer shipping → `orders.estimated_total` → SEP.
- **`receiver_due` (پس‌کرایه):** items + tax only → `orders.estimated_total` → SEP. Shipping is collected by the carrier from the recipient. `shipping_customer_cost` stays **NULL** (not `0`; NULL ≠ free shipping). `shipping_provider_quoted_cost` stays NULL until a packed-parcel quote exists.

## Payment boundary

Checkout payment remains **SEP** for merchandise. Postex COD / wallet / top-up remain out of scope.

Parcel `payment_type` mapping (provider-neutral Karzar mode → Postex):

| Karzar mode | Postex | Meaning |
|-------------|--------|---------|
| `sender_prepaid` | `SENDER` | Karzar/customer prepaid shipping via SEP |
| `receiver_due` | `RECEIVER` | پس‌کرایه — carrier collects shipping from recipient |

**`RECEIVER` ≠ `COD`.** COD is rejected. Merchandise is never “پرداخت در محل” via Postex.

Authority: persist `shipping_payment_mode` on the order/shipment at create time. `build_parcel_create_request` must use that snapshot — not mutable `settings.POSTEX_DEFAULT_PAYMENT_TYPE` at booking time.

`POSTEX_SHIPPING_PAYMENT_MODE` is preferred. Legacy `POSTEX_DEFAULT_PAYMENT_TYPE` is normalized once into the neutral mode when the preferred setting is blank.

Write gate: `POSTEX_BOOKING_ENABLED` (default **false**) must be true for parcel create / mark-ready / cancel / edit. Quotes/reference may run under `POSTEX_ENABLED` alone.

SEP init/verify/callback still use `order.estimated_total` once. Shipping is not added again for `receiver_due`.

## Booking flow (after payment)

SEP verify **must not** wait on Postex.

On payment `VERIFIED`:

1. Create/ensure a `shipments` row in the same DB transaction as paid state.
   - `sender_prepaid` → `pending_booking` (quote package snapshot present).
   - `receiver_due` → `awaiting_packaging` (`booking_next_attempt_at` unset; worker must not claim).
2. Return the payment flow normally.
3. For `receiver_due`, admin enters **final sealed parcel** measurements, obtains a packed quote (`payment_type=RECEIVER`), selects carrier/service, then explicitly schedules `pending_booking`. Only then may the worker claim.
4. Background worker claims `pending_booking` only when `POSTEX_BOOKING_ENABLED`. **TX A** locks, marks `booking`, persists `create_attempted`, **commits**, then `POST /parcels/bulk` with **no** row lock held. **TX B** persists parcel/tracking (`booked`) or `creation_uncertain`. Admin manual book uses the same domain function.
5. Process death after Postex accepts create but before TX B leaves `booking` (never `pending_booking`). Restart looks up `custom_order_no` = `shipment.public_id` before any second create.

`custom_order_no` = shipment UUID (lookup key). `custom_reference_no` = Karzar order tracking code.

Final outbound parcel must still be weighed/measured before booking in `receiver_due` mode.

## Idempotency / uncertain create

Official spec has **no** idempotency key. A create attempt is **committed** as `booking` before `POST /parcels/bulk`. After a create **timeout** or process death, shipment status is `booking` or `creation_uncertain`. Worker reconciles with `GET /parcels/custom-order-no/{uuid}`. It does **not** POST bulk again until lookup proves no parcel (two empty lookups). Cancel of those states must not locally mark `cancelled` while a provider parcel may exist.

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

Operational rollback: `POSTEX_ENABLED=false`. Purchase checkout no longer requires a
quote token. Existing shipments remain for history.

**Not** an operational rollback: Alembic `downgrade` of `i2j3k4l5m6n7` after quote/shipment
rows exist — that drop is destructive. Prefer forward-only schema changes unless Owner
explicitly authorizes a destructive downgrade.
