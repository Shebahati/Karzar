# INSIZE second +10% — revised owner review (`INSIZE-PRICE-110-20261021`)

**Status:** `READY_FOR_OWNER_REVIEW`  
**Production APPLY:** **not executed**

## Currency correction

All totals are **`products.base_price` / `original_price` as stored in the database — TOMAN**. No unit conversion is applied in reports or the operator.

## Cohort (206 priced INSIZE SKUs — unchanged)

| | Count |
|--|--:|
| INSIZE non-deleted | 870 |
| Eligible (`base_price > 0`) | **206** |
| Excluded (unpriced) | 664 |

## Financial summary (TOMAN)

| | Toman |
|--|--:|
| Current total `base_price` | 3,413,658,600.00 |
| Proposed total `base_price` | 3,755,024,460.00 |
| **Delta** | **341,365,860.00** |

## Merchandising exceptions (owner-approved pattern — 2 SKUs)

Authorized: `AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS = {1944, 3639}`.

| product_id | SKU | Current base | Current original | Proposed base | Proposed original | Current discount % | Proposed discount % | Current display | Proposed display |
|-----------|-----|-------------:|-----------------:|--------------:|------------------:|-------------------:|--------------------:|-----------------|------------------|
| 1944 | 3203-1506 | 44,038,500 | 47,100,000 | 48,442,350 | **NULL** | 6.50% | — | discounted (compare-at) | **no_compare_at** (promo removed) |
| 3639 | S3-2824 | 49,929,000 | 53,400,000 | 54,921,900 | **NULL** | 6.50% | — | discounted | **no_compare_at** |

No replacement compare-at prices. All other attributes unchanged; cohort remains **206** rows.

## Manifest versioning

| Version | Role | SHA256 (CSV) |
|---------|------|----------------|
| **v1** | Immutable historical (blocked on semantics) | `cc1003dd41d5a87ddfb4c98724992ffad897585a46203ad780992ec46cae2d15` |
| **v2** | **Owner-frozen proposal (exceptions)** | `bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540` |

- v1 archive: worktree `audit/insize-price-110-20261021/immutable-v1/`
- v2 CSV: `INSIZE_PRICE_110_20261021_MANIFEST_20261021T133454Z.csv`

## Operator (revised)

- `app/domain/insize_price_110_20261021.py` — dual-field CAS, separate `product_change_logs` for `base_price` (206) and `original_price` (2 exceptions)
- `scripts/ops/insize_price_110_20261021_apply_once.py`
- Recovery CSV includes `base_price` + `original_price` prewrite; guarded rollback restores both where applicable

## Verification

| Step | Result |
|------|--------|
| Unit tests | **31/31** pass |
| Read-only preflight (v2 snapshot) | **PREFLIGHT_OK** (0 blockers) |
| SERIALIZABLE rehearsal + ROLLBACK | **REHEARSAL_OK** (206 rows) |
| Oct 19 prior event | **verified** (206 logs, sum 3413658600.00 Toman) |

## Before APPLY

1. Owner sign-off on two-product exception table above.
2. `--verify-frozen-manifest` on v2 CSV + SHA immediately before COMMIT.
3. Category B controls + backup; no Hesabfa / deploy / Admin Publish.

Worktree: `/home/shebahati/Projects/Karzar-insize-price-110-20261021` (`feat/insize-price-110-20261021`).
