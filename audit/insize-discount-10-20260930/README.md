# INSIZE 10% Storefront Discount — 2026-09-30

## Authorization

Owner-authorized exact **10% storefront discount** on all currently priced
INSIZE products. This was a Category B catalog mutation scoped to one brand
and two mutable fields (`base_price`, `original_price`). It is **complete**.
Do not rerun any historical APPLY for this event.

This campaign was calculated from the **current live** `base_price` values
that already include the earlier Owner-authorized INSIZE **+12%** update
(`audit/insize-price-112/`). That +12% event was **not** rerun or reverted.

## Discount semantics (existing storefront model)

No new discount engine. Existing fields:

| Field | Meaning after APPLY |
|-------|---------------------|
| `original_price` | Pre-discount customer list price (= pre-mutation `base_price`) |
| `base_price` | Customer-payable sale price = `quantize(pre_base × 0.90, 0.01, ROUND_HALF_UP)` |
| `discount_percent` | Derived: `round((1 − base/original) × 100)` → **10** |

Cart/checkout/payment use `base_price` only; `tax_percent` never surcharges
payable. Hesabfa catalog prices were **not** rewritten. Emalls
`current_price`/`old_price` map to `base_price`/`original_price`.

## Scope

| Item | Value |
|------|-------|
| Brand | `INSIZE \| اینسایز` |
| `brand_id` | `3` |
| Live INSIZE products | `872` |
| Priced target rows | `487` |
| Unpriced (unchanged) | `385` |
| Pre-existing `original_price` non-null | `0` |
| Mutable fields | `base_price` **and** `original_price` only |

Not in scope: availability, active flags, stock, SKU/slug/name, images,
Hesabfa catalog rewrite, Postex, deploy, or any other brand.

Change-log reason string (exact):

```text
INSIZE 10% storefront discount owner-authorized 2026-09-30
```

## Execution result

**STATUS:** `APPLIED`

| Check | Result |
|-------|--------|
| Target priced rows | **487** |
| Updated `base_price` (COMMITTED) | **487** |
| Updated `original_price` (COMMITTED) | **487** |
| `product_change_logs` `base_price` | **487** |
| `product_change_logs` `original_price` | **487** |
| Distinct product IDs | **487** |
| Formula matches | **487 / 487** |
| `original_price == pre_base` | **487 / 487** |
| `discount_percent == 10` | **487 / 487** |
| Duplicate mutations | **0** |
| Delta % min/max | **-10.00 / -10.00** |
| Non-INSIZE mutations | **0** |
| INSIZE other-field mutations | **0** |
| Products / images count delta | **0 / 0** |

Pre aggregates (`base_price`):

| Metric | Value |
|--------|-------|
| min | `246400.00` |
| max | `221356800.00` |
| sum | `11498562096.00` |

Post aggregates (`base_price`):

| Metric | Value |
|--------|-------|
| min | `221760.00` |
| max | `199221120.00` |
| sum | `10348705886.40` |
| discount amount | `1149856209.60` |

## Production identity (CR-011 live)

| Probe | Value |
|-------|-------|
| Host | `srv5944957438` |
| DB container | `lathe_postgres` |
| Database | `karzar_staging` |
| Volume | `karzar_postgres_data` |
| `APP_ENV` | `staging` (process label; live plane) |
| Alembic | `u4v5w6x7y8z9` |
| Git SHA (APPLY) | `637240754f5c618316b7d9daedd3bd238bcbba1c` |
| Workflow run | [`36725752688`](https://github.com/Shebahati/Karzar/actions/runs/36725752688) |

## Site verification

Public API samples: `base_price` / `original_price` / `discount_percent=10` matched.
PDP HTML: strike-through + 10% badge present; discounted digits present.
JSON-LD Offer: `priceCurrency=IRR` with Toman ×10 (exact Rial) matching discounted sale.
Guest cart `PUT /cart/items`: line `base_price` = discounted value.
Emalls mapping: `current_price=base_price`, `old_price=original_price` (no Emalls mutation).

Homepage deals (informational): active INSIZE list shows `discount_percent=10`
for priced active rows (385 of 643 active listed); deals rail filters
`discount_percent > 0` client-side — no homepage redesign.

## Safety

- Do **not** rerun this APPLY (idempotency refuses same reason).
- Do **not** reintroduce a push-triggered one-shot production APPLY workflow.
- Rollback must restore **exact** pre-write `base_price` and `original_price`
  from `INSIZE_DISCOUNT_10_ROLLBACK_*.sql` (never divide by 0.90).
- Do **not** rerun or revert `audit/insize-price-112/`.

## Final status

```text
INSIZE_DISCOUNT_10_APPLY_OK
```
