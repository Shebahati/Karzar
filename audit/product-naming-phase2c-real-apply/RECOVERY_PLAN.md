# Phase 2C manufacturer_code recovery plan

## Status
NOT EXECUTED. Owner confirmation required before any recovery.

## Scope
- Rows: 1350
- Cohort SHA256: `43620d24842b946652f8e2a0256aa75e45fbdf1b591b0374dcb84dea21417b03`
- Pre-apply manufacturer_code: NULL for all targets

## Recovery semantics (if later authorized)
1. For each row in `RECOVERY_TARGETS.csv`, set `products.manufacturer_code`
   back to the pre-apply value (NULL).
2. Write compensating `product_change_logs` rows
   (`field_name=manufacturer_code`, old=applied, new=NULL).
3. Do **not** delete original Phase 2C audit logs.
4. Require explicit owner confirmation SHA matching the cohort.

## Forbidden without new authorization
- Product.name / SKU / slug / taxonomy / price / availability mutation
- Automatic post-commit reversal
