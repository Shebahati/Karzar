# INSIZE +10% — Human production APPLY handoff (Issue #541)

**STATUS:** READY_FOR_HUMAN_APPLY (operator verified; Cursor Agent production-write hook blocks automated `--apply`)

## Reviewed commit

Checkout branch `feat/issue-541-insize-price-110-apply-20261019` at the PR HEAD SHA (see GitHub PR for Issue #541).

## Environment (Category B)

```bash
export KARZAR_ALLOW_PRODUCTION_WRITE=1
export KARZAR_INGESTION_CATEGORY=B
```

SSH alias: `karzar-vps` → host `srv5944957438`, Postgres container `lathe_postgres`, database `karzar_staging` (CR-011 live plane).

## Frozen manifest (do not regenerate without owner review)

| Item | Value |
|------|-------|
| Path | `audit/insize-price-110/INSIZE_PRICE_110_MANIFEST_20261019T122730Z.csv` |
| SHA256 | `edd614107db14d9ae96e6a5d5c2b04043f95c413e6902d45fc3de7d8228feee1` |
| Rows | 206 priced INSIZE products |

## Mandatory pre-execution checks

1. **Idempotency:** `product_change_logs` must have **zero** rows with reason  
   `INSIZE +10% owner-authorized price update 2026-10-19`
2. **Brand:** `brands.id=3` name `INSIZE | اینسایز`
3. **Drift:** read-only manifest vs live (must exit 0):

```bash
PYTHONPATH=. python3 scripts/ops/insize_price_110_apply_once.py \
  --verify-frozen-manifest audit/insize-price-110/INSIZE_PRICE_110_MANIFEST_20261019T122730Z.csv
```

4. **Census:** live priced INSIZE count must still be **206** and match manifest row count.
5. **Rehearsal (optional):** `--rehearsal` performs INSERT/update gates then `ROLLBACK`.

## APPLY (human shell only)

```bash
MANIFEST=audit/insize-price-110/INSIZE_PRICE_110_MANIFEST_20261019T122730Z.csv
SHA=edd614107db14d9ae96e6a5d5c2b04043f95c413e6902d45fc3de7d8228feee1

PYTHONPATH=. python3 scripts/ops/insize_price_110_apply_once.py \
  --out-dir audit/insize-price-110 \
  --manifest-csv "$MANIFEST" \
  --apply \
  --confirm-manifest-sha "$SHA"
```

**Backup:** operator calls `create_live_backup` **before** COMMIT; artifact under `~/karzar-backups/insize-price-110/` plus `audit/insize-price-110/BACKUP_MANIFEST.json`.

## Expected results

- `APPLY_REPORT.json` → `STATUS: APPLIED`, `FINAL_LINE: INSIZE_PRICE_110_APPLY_OK`
- **206** `products.base_price` updates
- **206** `product_change_logs` (`field_name=base_price`, event reason above)
- `VERIFY_REPORT.json` API spot-checks on samples

## STOP conditions

- Drift report `ok: false` or manifest SHA mismatch
- Idempotency logs already present
- Backup failure or empty dump
- Post-COMMIT verification incomplete → **do not re-run APPLY**; reconcile read-only DB state first

## Recovery

- Exact rollback: `audit/insize-price-110/INSIZE_PRICE_110_ROLLBACK_20261019T122730Z.sql`
- Recovery CSV: `INSIZE_PRICE_110_RECOVERY_PREWRITE_20261019T122730Z.csv`
- Never divide prices by 1.10
