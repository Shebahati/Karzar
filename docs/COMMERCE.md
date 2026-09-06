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
