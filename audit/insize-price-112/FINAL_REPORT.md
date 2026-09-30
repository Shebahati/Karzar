# INSIZE +12% Price APPLY — APPLIED

Generated: 2026-09-30T08:42:19Z
Abort reason: 

## RUNTIME
- DB: karzar_staging
- Host proof: srv5944957438
- Git SHA: ac481587c5823543d97a533ac19a84eede06335a

## PRE
{
  "live_insize": 872,
  "priced_insize": 487,
  "unpriced_insize": 385,
  "active_priced": 385,
  "inactive_priced": 102,
  "available_priced": 159,
  "unavailable_priced": 328,
  "min_base_price": "220000.00",
  "max_base_price": "197640000.00",
  "sum_base_price": "10266573300.00",
  "validation": {
    "ok": true,
    "errors": [],
    "priced_count": 487,
    "live_count": 872
  },
  "row_count": 487,
  "current_min": "220000.00",
  "current_max": "197640000.00",
  "current_sum": "10266573300.00",
  "proposed_min": "246400.00",
  "proposed_max": "221356800.00",
  "proposed_sum": "11498562096.00"
}

## REHEARSAL
{
  "commit": false,
  "target_rows": 487,
  "updated_rows": 487,
  "change_log_rows": 487,
  "status": "GATES_PASSED",
  "transaction_status": "ROLLED_BACK_REHEARSAL",
  "live_unchanged_proven": true,
  "fingerprints_unchanged": true
}

## APPLY
{
  "manifest_rows": 487,
  "manifest_sha256_csv": "c861269595ca8b5a7cd6a5fd3bc34812852ec91d53dcdc46b1d356c37937d9c5",
  "manifest_sha256_json": "d4839a2ec1fe42c712a99ba3e0b02be1e35d741b5f177f36cadd64b3b07535f7",
  "updated_rows": 487,
  "change_log_rows": 487,
  "formula": "base_price = quantize(old * 1.12, 0.01, ROUND_HALF_UP)",
  "transaction_status": "COMMITTED",
  "reason": "INSIZE +12% owner-authorized price update 2026-09-30"
}

## POST
{
  "target_rows": 487,
  "changed_products": 487,
  "price_exact_match": 487,
  "formula_matches": 487,
  "still_at_old_price": 0,
  "doubled_multiplier_count": 0,
  "current_price_matches_logged_new": 487,
  "change_log_rows_with_reason": 487,
  "distinct_changed_product_ids": 487,
  "duplicate_mutations": 0,
  "min": "246400.00",
  "max": "221356800.00",
  "sum": "11498562096.00",
  "delta_pct_min": "12.00",
  "delta_pct_max": "12.00",
  "null_price": 385,
  "isolation": {
    "non_insize_price_mutations": 0,
    "insize_nonprice_mutations": 0,
    "products_count_delta": 0,
    "product_images_count_delta": 0,
    "pre_fingerprints": {
      "non_insize_live_count": 5664,
      "non_insize_base_price_null_count": 1599,
      "non_insize_id_price_sha256": "808b9f9808d71869a22e3b353a66a333632b1c7d1c470a43abffb2764b33f22a",
      "insize_nonprice_sha256": "7a5d7d0d9d12dea274b69565740fc50e3dbe17647ea279581ac96883df4da969",
      "products_count": 6537,
      "product_images_count": 1492
    },
    "post_fingerprints": {
      "non_insize_live_count": 5664,
      "non_insize_base_price_null_count": 1599,
      "non_insize_id_price_sha256": "808b9f9808d71869a22e3b353a66a333632b1c7d1c470a43abffb2764b33f22a",
      "insize_nonprice_sha256": "7a5d7d0d9d12dea274b69565740fc50e3dbe17647ea279581ac96883df4da969",
      "products_count": 6537,
      "product_images_count": 1492
    }
  },
  "samples": [
    {
      "sku": "0110-1125",
      "product_id": 1771,
      "old_base_price": "23800000.00",
      "new_base_price": "26656000.00"
    },
    {
      "sku": "1103-150",
      "product_id": 1772,
      "old_base_price": "8175000.00",
      "new_base_price": "9156000.00"
    },
    {
      "sku": "1103-200",
      "product_id": 1773,
      "old_base_price": "11500000.00",
      "new_base_price": "12880000.00"
    },
    {
      "sku": "1103-300",
      "product_id": 1774,
      "old_base_price": "20225000.00",
      "new_base_price": "22652000.00"
    },
    {
      "sku": "1106-301",
      "product_id": 1775,
      "old_base_price": "23560000.00",
      "new_base_price": "26387200.00"
    }
  ],
  "ok": true
}

## RECOVERY
{
  "recovery_csv": "/tmp/karzar-insize-price-112-out/INSIZE_PRICE_112_RECOVERY_PREWRITE_20260930T084219Z.csv",
  "recovery_csv_sha256": "944ae58e27c730f5621fb2a0839c8c200664694e75dee96ec2f12bd3999f391a",
  "rollback_sql": "/tmp/karzar-insize-price-112-out/INSIZE_PRICE_112_ROLLBACK_20260930T084219Z.sql",
  "rollback_sql_sha256": "896a0af529eb73127651d12cc5af29826514cdff489d25831469afa2531e13cf"
}

INSIZE_PRICE_112_APPLY_OK
