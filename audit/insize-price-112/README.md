# INSIZE +12% Price Update — 2026-09-30

## Authorization

Owner-authorized increase of current INSIZE `base_price` by exactly **12%**.

This was a Category B catalog mutation scoped to one brand and one mutable
field. It is **complete**. Do not rerun any historical APPLY for this event.

## Scope

| Item | Value |
|------|-------|
| Brand | `INSIZE \| اینسایز` |
| `brand_id` | `3` |
| Live INSIZE products | `872` |
| Priced target rows | `487` |
| Unpriced (unchanged) | `385` |
| Mutable field | `base_price` **only** |

Not in scope: `original_price`, availability, active flags, stock, SKU/slug/name,
images, Hesabfa, Postex, deploy, or any other brand.

Formula:

```text
new_base_price = quantize(old_base_price × 1.12, 0.01, ROUND_HALF_UP)
```

Change-log reason string (exact):

```text
INSIZE +12% owner-authorized price update 2026-09-30
```

## Execution result

**STATUS:** `APPLIED`

| Check | Result |
|-------|--------|
| Target priced rows | **487** |
| Updated rows (COMMITTED) | **487** |
| `product_change_logs` rows (`field_name=base_price`, reason above) | **487** |
| Distinct product IDs | **487** |
| Formula matches (`new = round(old×1.12, 2)`) | **487 / 487** |
| Current DB `base_price` = logged `new_value` | **487 / 487** |
| Duplicate product mutations | **0** |
| Delta % min/max | **12.00 / 12.00** |
| Non-INSIZE price mutations | **0** |
| INSIZE non-price mutations | **0** |
| Products count delta | **0** |
| Product images count delta | **0** |

Pre aggregates (old prices):

| Metric | Value |
|--------|-------|
| min | `220000.00` |
| max | `197640000.00` |
| sum | `10266573300.00` |

Post aggregates (new prices):

| Metric | Value |
|--------|-------|
| min | `246400.00` |
| max | `221356800.00` |
| sum | `11498562096.00` |

## Production identity (CR-011 live)

| Probe | Value |
|-------|-------|
| Host | `srv5944957438` |
| DB container | `lathe_postgres` |
| Database | `karzar_staging` |
| Volume | `karzar_postgres_data` |
| Git SHA (APPLY) | `ac481587c5823543d97a533ac19a84eede06335a` |
| Workflow run | [`36691354159`](https://github.com/Shebahati/Karzar/actions/runs/36691354159) |

Evidence:

- [`APPLY_REPORT.json`](./APPLY_REPORT.json)
- [`VERIFY_REPORT.json`](./VERIFY_REPORT.json)
- [`VERIFY_IDENTITY_PROBE.json`](./VERIFY_IDENTITY_PROBE.json)
- [`SITE_VERIFY.json`](./SITE_VERIFY.json)
- Manifest / recovery / exact-value rollback SQL in this directory

## Site verification

Read-only checks against `https://api.karzartools.com` and storefront PDPs
confirmed the new prices for sampled active/available products, unavailable
products, and low/high price samples. Inactive product `1114-200` correctly
returned API 404 (not publicly listed) while remaining updated in DB via
change logs.

## Safety

- Do **not** rerun the historical INSIZE +12% APPLY.
- Do **not** reintroduce a push-triggered one-shot production APPLY workflow for this event.
- Rollback, if ever needed, must restore **exact** pre-write prices from
  `INSIZE_PRICE_112_ROLLBACK_*.sql` (never divide by 1.12).
- Idempotency: any future attempt with the same change reason must stop.

## Final status

```text
INSIZE_PRICE_112_APPLY_OK
```
