# PRODUCT 1789 Integrity Investigation (read-only; NO repair)

## Current Production (staging plane) state

Snapshot via Category A SSH read-only (`transaction_read_only=on`):

| Field | Value |
| --- | --- |
| product_id | 1789 |
| sku | 1114-150 |
| manufacturer_code | 1114-150 |
| brand_id | **NULL** |
| is_active | true |
| is_available | **true** |
| base_price | 7980000.00 |
| updated_at | 2026-10-04 11:19:55+00 |

Wave 0 / historical audits consistently show `brand_id=3` (INSIZE).

## Availability mutation source (proven via `product_change_logs`)

| When (UTC) | field | old→new | reason | actor |
| --- | --- | --- | --- | ---: |
| 2026-10-04 11:11:45 | is_available | False→True | `mark_available` | 3 |
| 2026-10-04 11:11:48 | is_available | True→False | `mark_unavailable` | 3 |
| 2026-10-04 11:11:50 | is_available | False→True | `mark_available` | 3 |

Actor user_id `3` performed rapid admin toggle; final state `is_available=true`.
This explains Wave 1A sellable +1 and commercial class `IDENTITY_DRIFT` when
combined with brand loss.

Subsequent same-day `base_price` updates (`product_update`) to 7900000 then 7980000.

## brand_id mutation source

```text
product_change_logs rows with field_name matching brand*: 0
```

No audited `brand_id` 3→NULL transition was found. Pre-2026-10-04 ops manifests
(Phase 2C, INSIZE +12%, discount removal) all record `brand_id=3`. Null brand
appeared by Wave 1A census without a change-log row — likely an unlogged path
or a write that bypassed `product_change_logs` for `brand_id`.

## Root cause (best evidence)

1. **Availability:** intentional admin `mark_available` / `mark_unavailable`
   toggles by actor 3 on 2026-10-04 (logged).
2. **Brand NULL:** **unlogged identity integrity defect** — brand_id cleared
   without `product_change_logs` evidence; not attributable to Wave 1A (read-only)
   or this Wave 1A.1 pass.

## Trailing-A note (identity only)

Workbook control CODE `1114-150A` matches catalog SKU `1114-150` under the new
registered INSIZE trailing-A identity rule; workbook status `موجود`. This does
**not** authorize APPLY and does not repair brand_id.

## Recommended remediation (NOT performed)

1. Restore `brand_id=3` (INSIZE) under Category B + Owner authorization with
   recovery snapshot; write change-log.
2. Audit admin/product_update paths to ensure `brand_id` mutations always log.
3. Decide whether `is_available=true` should remain given IDENTITY_DRIFT until
   brand is restored (commerce safety).
4. Do **not** silent-fix in Wave 1A.1.

```text
mutation_performed: NO
```
