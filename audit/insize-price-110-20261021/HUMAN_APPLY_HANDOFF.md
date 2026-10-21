# Human APPLY handoff — `INSIZE-PRICE-110-20261021` (manifest v2)

**Use manifest v2 only.** v1 is immutable evidence (`immutable-v1/`, SHA `cc1003dd…`).

## Frozen manifest v2

- CSV: `INSIZE_PRICE_110_20261021_MANIFEST_20261021T133454Z.csv`
- SHA256: `bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540`

## Verify (read-only)

```bash
python3 scripts/ops/insize_price_110_20261021_apply_once.py \
  --verify-frozen-manifest audit/insize-price-110-20261021/INSIZE_PRICE_110_20261021_MANIFEST_20261021T133454Z.csv
```

## APPLY (Category B — human only; not executed in preparation)

```bash
export KARZAR_ALLOW_PRODUCTION_WRITE=1
export KARZAR_INGESTION_CATEGORY=B
python3 scripts/ops/insize_price_110_20261021_apply_once.py \
  --apply \
  --manifest-csv audit/insize-price-110-20261021/INSIZE_PRICE_110_20261021_MANIFEST_20261021T133454Z.csv \
  --confirm-manifest-sha bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540
```

Expect **206** `base_price` logs + **2** `original_price` NULL clears (product_id 1944, 3639). Post-commit DB + API verification required; no automatic rollback.
