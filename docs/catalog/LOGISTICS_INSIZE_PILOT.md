# INSIZE Logistics Pilot — Specification Only

**Status:** PLAN ONLY — do not execute measurement, backfill, or APPLY.  
**Authority:** [`LOGISTICS_AUTHORITY.md`](LOGISTICS_AUTHORITY.md)  
**Brand:** INSIZE (`brand_id = 3`)  
**Cohort:** production purchasable INSIZE SKUs (~158 as of 2026-09-10 readiness audit)

---

## Goal

Produce a reviewed logistics authority file for INSIZE purchasable SKUs so a
**future** Owner-authorized Category B APPLY can populate PR #311 product fields.

Out of scope for this pilot plan:

- Alembic apply / deploy
- `POSTEX_ENABLED=true`
- Product UPDATE
- Availability / price changes
- Shrinking the public catalog to manufacture readiness

---

## Required authority columns

| Column | Notes |
|--------|--------|
| `product_id` | Live production id |
| `sku` | Canonical SKU |
| `weight_grams` | Positive integer grams (packaged unit) |
| `package_length_cm` | Positive; intake may start as mm → convert |
| `package_width_cm` | Positive |
| `package_height_cm` | Positive |
| `shipping_is_fragile` | Explicit boolean |
| `shipping_is_liquid` | Explicit boolean |
| `shipping_class` | `parcel` or `freight_only` |
| `source` | Hierarchy class from LOGISTICS_AUTHORITY |
| `source_date` | ISO date of authority |
| `validation_status` | Output of `validate_logistics_package.py` |

---

## Process (when Owner later authorizes execution)

1. Export purchasable INSIZE snapshot (SELECT-only).
2. Fill intake worksheet (prefer manufacturer package data; else measure).
3. Run:

```bash
python3 scripts/catalog_target/logistics_backfill.py INTAKE.csv \
  --out-dir .local-scratch/insize-logistics-pilot/
python3 scripts/validate_logistics_package.py \
  .local-scratch/insize-logistics-pilot/logistics_authority.csv
```

4. Human review: all rows `READY` or intentional `BLOCKED`/`freight_only`.
5. Stop. APPLY is a separate ticket.

---

## Exit criteria (for a later APPLY ticket)

- 158/158 purchasable INSIZE rows classified
- `READY` count reported; residual blockers listed by SKU
- No availability mutation used to improve percentages
- Provenance (`source`, `source_date`) present on every READY row
