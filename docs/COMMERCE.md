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

## Shipping (active storefront methods)

Public checkout offers **server-defined method codes** (client sends `shipping_method_code` only). All methods below are **`receiver_due`** (`price_label` = پس‌کرایه; `shipping_customer_cost` **NULL** at checkout; SEP = merchandise + tax only).

**Tehran province** (استان تهران — province normalization; **not** Tehran city only):

| Order | Method code | Label | Provider | Service |
|------|-------------|-------|----------|---------|
| 1 | `tipax_standard` | تیپاکس | `tipax` | `standard` |
| 2 | `chapar_standard` | چاپار | `chapar` | `standard` |
| 3 | `post_pishtaz` | پست پیشتاز | `iran_post` | `pishtaz` |
| 4 | `tehran_motorcycle_48h` | پیک موتوری حداکثر تا ۴۸ ساعت | `local_delivery` | `motorcycle_48h` |
| 5 | `tehran_express_3h` | ارسال فوری ۳ ساعته | `local_delivery` | `express_3h` |

**Other provinces:** `tipax_standard`, `chapar_standard`, `post_pishtaz` only (same order).

- Discovery: `POST /api/v1/shipping/options` (province + city; local methods use **province** = Tehran).
- `post_pishtaz` is manual receiver-due fulfillment (`iran_post`); it does **not** use Postex quote checkout and does **not** require `POSTEX_ENABLED`.
- Fulfillment: manual register → handoff → deliver (`/orders/{id}/shipments/{id}/manual/*`). External carriers (`tipax`, `chapar`, `iran_post`) require tracking/provider reference before handoff; `local_delivery` uses courier fields.
- Feature flags (default **false**): `SHIPPING_TIPAX_ENABLED`, `SHIPPING_CHAPAR_ENABLED`, `SHIPPING_POST_PISHTAZ_ENABLED`, `SHIPPING_TEHRAN_MOTORCYCLE_48H_ENABLED`, `SHIPPING_TEHRAN_EXPRESS_3H_ENABLED`. Legacy Postex quote checkout: **`SHIPPING_POSTEX_CHECKOUT_ENABLED=true`** plus `POSTEX_ENABLED`; never implied automatically.

**Intended production activation (ops — not applied by deploy alone):**

```text
POSTEX_ENABLED=false
SHIPPING_TIPAX_ENABLED=true
SHIPPING_CHAPAR_ENABLED=true
SHIPPING_POST_PISHTAZ_ENABLED=true
SHIPPING_TEHRAN_MOTORCYCLE_48H_ENABLED=true
SHIPPING_TEHRAN_EXPRESS_3H_ENABLED=true
SHIPPING_POSTEX_CHECKOUT_ENABLED=false
```

**Postex** remains in code and history for legacy orders but is **not** returned as a storefront option. `POSTEX_ENABLED` does not gate the receiver-due matrix above.

## Shipping (Postex — legacy provider)

Parcel shipping is a provider-neutral Karzar logistics domain. Postex is the v1 API provider, gated by `POSTEX_ENABLED` (safe default **false**). Parcel **create / mark-ready / cancel / edit** also require `POSTEX_BOOKING_ENABLED` (safe default **false**). See [`integrations/postex/README.md`](integrations/postex/README.md).

Provider-neutral shipping payment mode (persisted on order/shipment; **server-owned** — checkout clients cannot set it):

| Mode | Postex `payment_type` | SEP / `estimated_total` | Checkout quote |
|------|----------------------|-------------------------|----------------|
| `sender_prepaid` (default) | `SENDER` | items + tax + shipping | Required |
| `receiver_due` | `RECEIVER` (پس‌کرایه) | items + tax **only** | Not used |

- Mode authority: `POSTEX_SHIPPING_PAYMENT_MODE` / legacy `POSTEX_DEFAULT_PAYMENT_TYPE`. Storefront may **read** `GET /shipping/status.shipping_payment_mode` for UX only.
- `receiver_due` fulfillment (`POSTEX_FULFILLMENT_MODE=api`, default): `awaiting_packaging` → measure → packed quote → select service → `ready_to_book` → **explicit** admin `/book`. Enabling `POSTEX_BOOKING_ENABLED` alone must not create prepared receiver parcels.
- `receiver_due` fulfillment (`POSTEX_FULFILLMENT_MODE=manual_portal`): staff create parcels in the external Postex panel; Karzar admin records tracking/parcel refs via `/manual-portal/*` (**no Postex HTTP**). Booking/tracking workers skip these shipments. **`manual_portal` requires `receiver_due`.** Generic Postex admin paths and generic order `shipped`/`delivered` status changes are rejected (409) for active manual-portal shipments.

**Rollback (manual_portal):**

1. While this compatible release is still running, set `POSTEX_FULFILLMENT_MODE=api` so **new** paid orders resume API fulfillment snapshots.
2. Recreate only the approved API container (`lathe_api`) after the Owner-authorized env change (requires temporary removal of `KARZAR_DEPLOY_FREEZE`, deploy from `main`, then immediate restoration of the freeze).
3. Allow existing manual-portal shipments to retain their snapshotted workflow and complete handoff/delivery.
4. Confirm no non-terminal manual-portal shipments remain.
5. Only then may the previous pre-feature image be deployed.

Post-deploy smoke (after any production rollout): `GET /ready`, `GET /shipping/status`, and a sacrificial checkout — not part of this PR.

Manual-portal **local abandon/cancel** is **deferred** in this MVP (no admin API route); generic Postex cancel and provider-side cancellation reconciliation do not apply to manual-portal or corrupt fulfillment snapshots. **Invalid `fulfillment_mode` snapshot values cannot be repaired via `/manual-portal/correct`** (correction does not change `fulfillment_mode`); fix corrupt snapshots only through a separate Owner-authorized operational/data-repair workflow.

**Worker eligibility (Postex automation batches):** manual-portal and corrupt non-empty fulfillment snapshots are excluded in SQL **before** the worker `LIMIT`; they never fall back to API automation. Generic Postex admin routes fail closed for those snapshots. Rows excluded by eligibility are not logged per row (they never enter the worker loop). **Proactive alerting** for dormant corrupt snapshots is a deferred operational follow-up, not part of this MVP.

- **`RECEIVER` ≠ COD.** Merchandise remains SEP-paid. Only the carrier shipping fee is collected from the recipient.
- Do **not** treat `shipping_customer_cost = NULL` or amount `0` as free shipping. Free shipping is a separate Postex value (`FREE_SHIPPING`) and is **rejected**.
- Postex `receiver_due` checkout still requires a normalized destination `location_code` when using quote checkout. Tipax/Chapar/Tehran Express checkout does **not** require `location_code`, quotes, or catalog dimensions.
- **`POSTEX_FULFILLMENT_MODE=api`:** sealed-parcel length/width/height, weight, and hazards are entered in Karzar admin (`awaiting_packaging` → final-package → packed quote → select service → schedule booking → book) and drive Postex quote/booking.
- **`POSTEX_FULFILLMENT_MODE=manual_portal`:** product package master data is not required in the Karzar catalog; dimensions and weight do not block checkout. When Postex requires them, the operator enters the actual sealed-parcel dimensions, weight, and required hazards in the **external Postex portal**. Karzar admin records parcel/tracking references, correction before handoff, handoff, and delivery — with **no** Postex quote or provider HTTP from Karzar. This does not remove Postex’s need for parcel data; it is deferred from catalog/checkout and captured manually during external portal fulfillment.
- Creating a Postex label/barcode is **not** order `shipped`. `SHIPPED` requires tracking evidence of physical handoff. `DELIVERED` only when all required shipments are delivered.

Config authority: prefer `POSTEX_SHIPPING_PAYMENT_MODE` (`sender_prepaid` \| `receiver_due`). Legacy `POSTEX_DEFAULT_PAYMENT_TYPE` (`SENDER` \| `RECEIVER`) is normalized once into that mode when the neutral setting is blank. COD / `FREE_SHIPPING` fail closed.

**API fulfillment path** — unresolved until Owner enablement: origin city code, catalog package-dimension coverage (`sender_prepaid`), live RECEIVER quote, API sacrificial parcel canary, and staging verification. These are **not** blockers for the `manual_portal` MVP.

**Manual portal MVP** — after this release is deployed with `POSTEX_FULFILLMENT_MODE=manual_portal`, the combined production flow (paid order → external portal parcel → Karzar registration/handoff) still requires an Owner-approved post-deploy canary; it is not production-proven until that runs.

## Payments

| Provider | Status |
|----------|--------|
| SEP (`PAYMENT_PROVIDER=sep`) | **Implemented** in API + callback + verify worker. **Production-proven (2026-09-13):** real SEP payment succeeded for **4,800,000 IRR**; callback received with successful state/status; automatic verify returned result code `0`; provider amount matched expected; provider reference persisted; order/payment reached **paid**. Core callback/verify pipeline is proven. **`report.sep.ir` financial reconciliation** remains an operational follow-up. The combined **`manual_portal` post-payment fulfillment flow** is not production-proven until PR #315 is deployed and the Owner-approved canary runs. Postex API booking is **not** claimed proven here. |
| Mock | Local/dev only. **Production cannot boot** with `PAYMENT_PROVIDER=mock`. |
| Zarinpal | Env-selectable; not the live default. |
| Blu Pay | Out of scope until a separate Owner/Board node. |

Production rollback is **revert the previous working SEP/env/image** (or disable checkout). Never set production to mock — the app refuses to start.

Operational follow-up: `report.sep.ir` financial reconciliation (callback/verify already proven as above).

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
