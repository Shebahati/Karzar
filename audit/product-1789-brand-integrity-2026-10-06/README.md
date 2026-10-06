# Product 1789 brand integrity — 2026-10-06

Rehearsal + writer audit for restoring `brand_id` NULL→3 on product 1789.

- **REAL_REPAIR_AUTHORIZED = NO**
- **PERSISTENT_PRODUCT_MUTATION = 0**
- Production plane: `srv5944957438` / `lathe_postgres` / `karzar_staging` / `karzar_postgres_data`
- Rehearsal tooling: `scripts/ops/product_1789_brand_repair_rehearsal.py` (ROLLBACK only; rejects APPLY flags)

See `FINAL_REPORT.md` and `ROOT_CAUSE_REPORT.md`.
