# Commerce

Domain rules for catalog sellability, checkout, and payment. Accounting detail: [`HESABFA.md`](HESABFA.md). Gateway protocol: [`SEP_PAYMENT_GATEWAY.md`](SEP_PAYMENT_GATEWAY.md). Ingestion: [`architecture/data-ingestion-policy.md`](architecture/data-ingestion-policy.md).

## Availability

Site inventory is **binary** `is_available` (موجود / ناموجود).

- Warehouse numeric stock lives **only in Hesabfa**. Do not treat `stock_quantity` or `low_stock` as sellable truth.
- `stock_quantity` is a legacy field typically `"0"`. `low_stock` is always `false` at runtime.
- `GET /products/{id}/stock` is compatibility-only. `POST /products/{id}/stock/adjust` raises — use `is_available`.
- Content enrichment **never writes** price, stock, or availability.

## Prices

The **site** is source of truth for catalog prices. Do not push site prices to Hesabfa as primary. Price jobs are a separate commercial path from spec enrichment.

## Dual-lane checkout

| Lane | Condition | Path |
|------|-----------|------|
| Purchase | Priced SKU | `/cart` → checkout → payment |
| Inquiry | `base_price == null` | `/quote` → inquiry checkout (no payment) |

Require `Idempotency-Key` on checkout and payment init.

### Temporary purchase kill switch

| Variable | Safe default | Effect |
|----------|--------------|--------|
| `PURCHASE_CHECKOUT_ENABLED` | `false` | When `false`, `mode=purchase` checkout returns **HTTP 503** with `PURCHASE_CHECKOUT_TEMPORARILY_DISABLED` **before** any order, stock, payment, or cart mutation. Inquiry checkout is unchanged. |

Set `PURCHASE_CHECKOUT_ENABLED=true` only after SEP merchant-domain / Referrer is confirmed. Keep `PAYMENT_PROVIDER=sep` — do not flip back to mock.

## Shipping (Postex)

Parcel shipping is a provider-neutral Karzar logistics domain. Postex is the v1 provider, gated by `POSTEX_ENABLED` (safe default **false**). Parcel **create / mark-ready / cancel / edit** also require `POSTEX_BOOKING_ENABLED` (safe default **false**). See [`integrations/postex/README.md`](integrations/postex/README.md).

Provider-neutral shipping payment mode (persisted on order/shipment; **server-owned** — checkout clients cannot set it):

| Mode | Postex `payment_type` | SEP / `estimated_total` | Checkout quote |
|------|----------------------|-------------------------|----------------|
| `sender_prepaid` (default) | `SENDER` | items + tax + shipping | Required |
| `receiver_due` | `RECEIVER` (پس‌کرایه) | items + tax **only** | Not used |

- Mode authority: `POSTEX_SHIPPING_PAYMENT_MODE` / legacy `POSTEX_DEFAULT_PAYMENT_TYPE`. Storefront may **read** `GET /shipping/status.shipping_payment_mode` for UX only.
- `receiver_due` fulfillment: `awaiting_packaging` → measure → packed quote → select service → `ready_to_book` → **explicit** admin `/book`. Enabling `POSTEX_BOOKING_ENABLED` alone must not create prepared receiver parcels.

- **`RECEIVER` ≠ COD.** Merchandise remains SEP-paid. Only the carrier shipping fee is collected from the recipient.
- Do **not** treat `shipping_customer_cost = NULL` or amount `0` as free shipping. Free shipping is a separate Postex value (`FREE_SHIPPING`) and is **rejected**.
- `receiver_due` checkout still requires a normalized destination `location_code`. Product package master data is **not** required at checkout; final sealed-parcel L/W/H/weight/hazards are entered during fulfillment (`awaiting_packaging` → admin final-package → packed quote → select service → schedule booking → book).
- Creating a Postex label/barcode is **not** order `shipped`. `SHIPPED` requires tracking evidence of physical handoff. `DELIVERED` only when all required shipments are delivered.

Config authority: prefer `POSTEX_SHIPPING_PAYMENT_MODE` (`sender_prepaid` \| `receiver_due`). Legacy `POSTEX_DEFAULT_PAYMENT_TYPE` (`SENDER` \| `RECEIVER`) is normalized once into that mode when the neutral setting is blank. COD / `FREE_SHIPPING` fail closed.

Unresolved until Owner enablement: origin city code, catalog package-dimension coverage (sender_prepaid), live RECEIVER quote then sacrificial parcel (separate authorizations), staging verification.

## Payments

| Provider | Status |
|----------|--------|
| SEP (`PAYMENT_PROVIDER=sep`) | **Implemented** in API + callback + verify worker. A successful real or test charge is **not yet proven**. |
| Mock | Local/dev only. **Production cannot boot** with `PAYMENT_PROVIDER=mock`. |
| Zarinpal | Env-selectable; not the live default. |
| Blu Pay | Out of scope until a separate Owner/Board node. |

Production rollback is **revert the previous working SEP/env/image** (or disable checkout). Never set production to mock — the app refuses to start.

Unresolved: first Owner-approved low-amount SEP charge + `report.sep.ir` reconciliation.

## Auth on commerce paths

- Storefront: OTP.
- Cart may use `X-Cart-Token` plus optional JWT.
- Admin order/payment mutations: session + role; destructive actions need step-up PIN.

## URLs (ADR-010)

- Canonical PDP: `/product/{slug}`
- `/product/{id}` → **301** to slug
- Brand hubs: `/brands/{slug}`
- Categories: `/categories/{slug}`
- Canonical, sitemap, breadcrumbs, and JSON-LD `@id` must agree

## Ingestion vs storefront

Routine catalog writes target `http://127.0.0.1:8000/api/v1` only. Production writes need Category B + backup + rollback (`ADR-012`). Admin UI bulk-click is not a substitute for a versioned pipeline.
