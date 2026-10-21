# Final release gate — `INSIZE-PRICE-110-20261021`

**Gate status:** `READY_FOR_EXPLICIT_PRODUCTION_AUTHORIZATION`  
**Production APPLY:** **not executed**

## Manifest preservation

| Artifact | SHA256 (CSV) |
|----------|----------------|
| v1 immutable | `cc1003dd41d5a87ddfb4c98724992ffad897585a46203ad780992ec46cae2d15` |
| v2 frozen | `bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540` |

## Production read-only verification (2026-10-21)

- `--verify-frozen-manifest` v2: **ok=true**, drift **0**, cohort membership **ok**
- Priced INSIZE cohort: **206**; sum **3413658600.00** Toman
- Idempotency logs: base 2026-10-21 **0**; original clear **0**; Oct 19 **206**
- Live `original_price`: id **1944** → 47100000.00; **3639** → 53400000.00 (pre-APPLY)

## Rehearsal contract (in-transaction; ROLLBACK)

Apply SQL enforces: **206** `base_price` updates, **2** `original_price` NULL clears (1944, 3639), **208** `product_change_logs` rows (separate reasons). Live rehearsal: **REHEARSAL_OK** / **ROLLED_BACK**.

## Financial reconciliation (Toman, v2 manifest)

- Current sum: **3,413,658,600.00**
- Proposed sum: **3,755,024,460.00**
- Delta: **341,365,860.00**

## Tests

**31/31** pass (`test_insize_price_110_20261021_*`).

## Backup / identity

- Production identity gates: **pass** (`identity_errors=[]`)
- Health: **all_pass**
- `create_live_backup` runs on `--apply` only (ready path documented in operator)
