# INSIZE 10% Storefront Discount APPLY — APPLIED

Generated: 2026-10-03T13:52:01Z
Abort reason: 

## RUNTIME
- DB: karzar_staging
- Host proof: srv5944957438
- Git SHA: 601b346548d1fc68f007d97a4d2af0abafad5e16

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
  "original_price_null": 385,
  "original_price_nonnull": 487,
  "original_price_gt_base_price": 487,
  "original_price_le_base_price": 0,
  "priced_with_existing_original_price": 487,
  "min_base_price": "221760.00",
  "max_base_price": "199221120.00",
  "sum_base_price": "10348705886.40",
  "validation": {
    "ok": true,
    "errors": [],
    "cohort_count": 487,
    "live_count": 872,
    "discovery": {
      "live_insize": 872,
      "priced_insize": 487,
      "discounted_cohort": 487,
      "undiscounted_priced": 0,
      "wrong_discount_percent_ids": [],
      "discount_apply_log_products": 487
    }
  },
  "discovery": {
    "live_insize": 872,
    "priced_insize": 487,
    "discounted_cohort": 487,
    "undiscounted_priced": 0,
    "wrong_discount_percent_ids": [],
    "discount_apply_log_products": 487
  },
  "row_count": 487,
  "current_min": "221760.00",
  "current_max": "199221120.00",
  "current_sum": "10348705886.40",
  "proposed_min": "246400.00",
  "proposed_max": "221356800.00",
  "proposed_sum": "11498562096.00",
  "absolute_discount_total": "-1149856209.60",
  "pre_existing_original_price_nonnull": 487
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
  "manifest_sha256_csv": "41f2f1939c68ed23355b8b88e63659b068458e7ec5f8f73ab2f6562bfe8fa1d0",
  "manifest_sha256_json": "b170a4cf21288bbb79db5d223269629a30b3ae14bd75e76d72623131351f15c6",
  "updated_rows": 487,
  "updated_base_price": 487,
  "updated_original_price": 487,
  "base_price_change_log_rows": 487,
  "original_price_change_log_rows": 487,
  "change_log_rows": 974,
  "formula": "base_price = pre_original_price; original_price = NULL",
  "transaction_status": "COMMITTED",
  "reason": "INSIZE 10% storefront discount removal owner-authorized 2026-10-03"
}

## POST
{
  "target_rows": 487,
  "base_price_exact_match": 487,
  "original_price_null_match": 487,
  "formula_matches": 487,
  "still_discounted": 0,
  "accidental_re_discount_count": 0,
  "current_matches_logged_new": 487,
  "change_log_base_price_rows": 487,
  "change_log_original_price_rows": 487,
  "change_log_rows_total": 974,
  "distinct_changed_product_ids": 487,
  "duplicate_mutations": 0,
  "pre_min": "221760.00",
  "pre_max": "199221120.00",
  "pre_sum": "10348705886.40",
  "min": "246400.00",
  "max": "221356800.00",
  "sum": "11498562096.00",
  "discount_amount": "-1149856209.60",
  "delta_pct_min": "11.11",
  "delta_pct_max": "11.11",
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
  "recovery_csv": "/tmp/karzar-insize-discount-10-removal-out/INSIZE_DISCOUNT_10_REMOVAL_RECOVERY_PREWRITE_20261003T135201Z.csv",
  "recovery_csv_sha256": "09fdc5a26c463a3e47b0531050cdbc220b391f101a3ffb245f9225921f4c3660",
  "rollback_sql": "/tmp/karzar-insize-discount-10-removal-out/INSIZE_DISCOUNT_10_REMOVAL_ROLLBACK_20261003T135201Z.sql",
  "rollback_sql_sha256": "a046bb26d354b21c0e0e8b4546cc0ab9113d3c29afc6068bb4757d672e7f940e"
}

INSIZE_DISCOUNT_10_REMOVAL_APPLY_OK
