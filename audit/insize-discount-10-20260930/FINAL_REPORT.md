# INSIZE 10% Storefront Discount APPLY — APPLIED

Generated: 2026-09-30T14:00:00Z
Abort reason: 

## RUNTIME
- DB: karzar_staging
- Host proof: srv5944957438
- Git SHA: 637240754f5c618316b7d9daedd3bd238bcbba1c

## PRE
{
  "live_insize": 872,
  "priced_insize": 487,
  "unpriced_insize": 385,
  "active": 643,
  "available": 159,
  "storefront_visible": 643,
  "sellable": 159,
  "imaged": 643,
  "active_priced": 385,
  "inactive_priced": 102,
  "available_priced": 159,
  "unavailable_priced": 328,
  "original_price_null": 872,
  "original_price_nonnull": 0,
  "original_price_gt_base_price": 0,
  "original_price_le_base_price": 0,
  "priced_with_existing_original_price": 0,
  "min_base_price": "246400.00",
  "max_base_price": "221356800.00",
  "sum_base_price": "11498562096.00",
  "validation": {
    "ok": true,
    "errors": [],
    "priced_count": 487,
    "live_count": 872
  },
  "row_count": 487,
  "current_min": "246400.00",
  "current_max": "221356800.00",
  "current_sum": "11498562096.00",
  "proposed_min": "221760.00",
  "proposed_max": "199221120.00",
  "proposed_sum": "10348705886.40",
  "absolute_discount_total": "1149856209.60",
  "pre_existing_original_price_nonnull": 0
}

## REHEARSAL
{
  "commit": false,
  "target_rows": 487,
  "updated_rows": 487,
  "base_price_change_log_rows": 487,
  "original_price_change_log_rows": 487,
  "change_log_rows": 974,
  "status": "GATES_PASSED",
  "transaction_status": "ROLLED_BACK_REHEARSAL",
  "live_unchanged_proven": true,
  "fingerprints_unchanged": true,
  "field_restoration": "base_price+original_price exact",
  "scope_gates": "non_insize+other_fields unchanged"
}

## APPLY
{
  "manifest_rows": 487,
  "manifest_sha256_csv": "cd73ccc4c0d966c3ef6aee30f48427bad6b608f5da99df0414e7530aa3f2c460",
  "manifest_sha256_json": "6d60c94bd1575339afa75e4282d75dd45882c79aeee5919078ffadd887eec296",
  "updated_rows": 487,
  "updated_base_price": 487,
  "updated_original_price": 487,
  "base_price_change_log_rows": 487,
  "original_price_change_log_rows": 487,
  "change_log_rows": 974,
  "formula": "original_price = pre_base; base_price = quantize(pre_base * 0.90, 0.01, ROUND_HALF_UP)",
  "transaction_status": "COMMITTED",
  "reason": "INSIZE 10% storefront discount owner-authorized 2026-09-30"
}

## POST
{
  "target_rows": 487,
  "base_price_exact_match": 487,
  "original_price_exact_match": 487,
  "formula_matches": 487,
  "discount_percent_10": 487,
  "still_at_old_price": 0,
  "compounded_0_90_count": 0,
  "current_matches_logged_new": 487,
  "change_log_base_price_rows": 487,
  "change_log_original_price_rows": 487,
  "change_log_rows_total": 974,
  "distinct_changed_product_ids": 487,
  "duplicate_mutations": 0,
  "pre_min": "246400.00",
  "pre_max": "221356800.00",
  "pre_sum": "11498562096.00",
  "min": "221760.00",
  "max": "199221120.00",
  "sum": "10348705886.40",
  "discount_amount": "1149856209.60",
  "delta_pct_min": "-10.00",
  "delta_pct_max": "-10.00",
  "null_price": 385,
  "isolation": {
    "non_insize_mutations": 0,
    "insize_other_field_mutations": 0,
    "products_count_delta": 0,
    "product_images_count_delta": 0,
    "pre_fingerprints": {
      "non_insize_live_count": 5664,
      "non_insize_base_price_null_count": 1599,
      "non_insize_id_price_sha256": "9446ef5f8653432b3e648f35b751e6a097f12ee5491090e3efe432e7fe749fd6",
      "insize_other_fields_sha256": "b3aef02937da659e0da8af7f2295b7cdc705e768437ac788071d25625c7a5b64",
      "products_count": 6537,
      "product_images_count": 1492
    },
    "post_fingerprints": {
      "non_insize_live_count": 5664,
      "non_insize_base_price_null_count": 1599,
      "non_insize_id_price_sha256": "9446ef5f8653432b3e648f35b751e6a097f12ee5491090e3efe432e7fe749fd6",
      "insize_other_fields_sha256": "b3aef02937da659e0da8af7f2295b7cdc705e768437ac788071d25625c7a5b64",
      "products_count": 6537,
      "product_images_count": 1492
    }
  },
  "ok": true
}

## RECOVERY
{
  "recovery_csv": "/tmp/karzar-insize-discount-10-out/INSIZE_DISCOUNT_10_RECOVERY_PREWRITE_20260930T140000Z.csv",
  "recovery_csv_sha256": "d0510f39fa42ac8b9afdc06bd7cc659b8f8c54087f9292da18d36eb4e6535f1f",
  "rollback_sql": "/tmp/karzar-insize-discount-10-out/INSIZE_DISCOUNT_10_ROLLBACK_20260930T140000Z.sql",
  "rollback_sql_sha256": "15eb4db591c19a49c2841c2bb67b286b1b1f8587ef99de5c57ac85de54a3bea4"
}

INSIZE_DISCOUNT_10_APPLY_OK
