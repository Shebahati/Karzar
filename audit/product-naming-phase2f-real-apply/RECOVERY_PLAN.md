# Phase 2F Product.name recovery plan

## Status
NOT EXECUTED. Separate owner authorization required.

## Scope
- Rows: 47
- Cohort SHA256: `25d586e371431cc371b6ce6432abba6c2da5b1f15102cac9ed187f78ef0052ff`

## Recovery semantics (if later authorized)
1. For each row in `RECOVERY_TARGETS.csv`, restore `products.name` to `pre_apply_name`
   only if current name still equals `applied_name`.
2. Revalidate SKU, manufacturer_code, brand_id, product_type_id before any write.
3. Write compensating `product_change_logs` rows; never delete original Phase 2F logs.
4. Use SERIALIZABLE transaction with advisory lock.

## Forbidden without new authorization
- SKU / slug / taxonomy / price / availability mutation
- Automatic full-database restore (disaster recovery dump only)
