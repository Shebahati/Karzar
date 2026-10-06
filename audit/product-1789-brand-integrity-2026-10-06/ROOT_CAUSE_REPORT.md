# Product 1789 brand_id loss — root cause

## Classification

```text
ADMIN_PATH_DEFECT
```

Exact writer of the historical 3→NULL mutation: **NOT proven** (no `product_change_logs` row for `brand_id`).

## Details

1. **Availability toggles (proven):** actor `3` on 2026-10-04 11:11:45/48/50 UTC via `mark_available` / `mark_unavailable`. These do not clear `brand_id`.
2. **Brand loss window:** after last proven `brand_id=3` (Wave 0 / Phase 2C / discount-removal 2026-10-03) and by Wave 1A census (2026-10-06), with `products.updated_at=2026-10-04 11:19:55+00` matching the last `product_update` price write. Exact clear timestamp is unknown.
3. **Code defect (proven on current main before this PR):** `ProductService.update_product_with_validation` tracked only `base_price`, `original_price`, `is_available` — **not** `brand_id`. Admin FE always sends `brand_id` (empty→`null`). Therefore an admin PUT could clear `brand_id` while logging only the price change — matching the observed evidence pattern.
4. **Secondary unaudited path (pre-fix):** `BrandService.delete_brand` → `clear_brand_on_products` bulk-nulls without per-product change logs. INSIZE brand id=3 still exists, so this is unlikely for 1789 specifically.
5. **Cannot exclude** direct SQL / unlogged script, but the admin update audit gap is sufficient to classify as `ADMIN_PATH_DEFECT` / code-path capable of the observed symptom.

## Hardening in this PR

- Log `brand_id` mutations via canonical `record_product_change` on product update.
- Pass `actor_user_id` from admin PUT.
- Log per-product clears on brand delete (`reason=brand_delete_clear`).
- Tests cover omit/preserve, set, explicit null, and unrelated-field non-log.

## Repair status

```text
REAL_REPAIR_AUTHORIZED = NO
PERSISTENT_PRODUCT_MUTATION = 0
```

Rehearsal restored `brand_id=3` transiently and ROLLED BACK.
