# INSIZE +10% Price Update — 2026-10-19 (Issue #541)

## Authorization

Owner-authorized increase of current INSIZE `base_price` by exactly **10%** (verbatim 2026-10-19).

Category B controlled production mutation. **Separate** from the completed 2026-09-30 +12% event (`audit/insize-price-112/`).

## Scope

| Item | Value (live preflight 2026-10-19T12:27:36Z) |
|------|---------------------------------------------|
| Brand | `INSIZE \| اینسایز` |
| `brand_id` | `3` (verified live) |
| Live INSIZE (non-deleted) | `870` |
| Priced target rows (`base_price > 0`) | `206` |
| Unpriced (unchanged) | `664` |
| Mutable field | `base_price` only |

Formula:

```text
new_base_price = quantize(old_base_price × 1.10, 0.01, ROUND_HALF_UP)
```

Change-log reason (exact):

```text
INSIZE +10% owner-authorized price update 2026-10-19
```

## Operator

- Logic: `app/domain/insize_price_110.py`
- Runner: `scripts/ops/insize_price_110_apply_once.py` (dry-run default)

### Preflight (completed)

```bash
PYTHONPATH=. python3 scripts/ops/insize_price_110_apply_once.py --out-dir audit/insize-price-110
```

- `STATUS`: `PREFLIGHT_OK`
- Manifest CSV SHA256: `edd614107db14d9ae96e6a5d5c2b04043f95c413e6902d45fc3de7d8228feee1`
- Rehearsal: `INSERT 0 206` then `ROLLBACK` (transaction gates passed)

### Production APPLY (human runner — not executed in Cursor Agent)

Cursor **production-write hook** blocked automated `--apply`. Run from an authorized shell on the operator workstation:

```bash
export KARZAR_ALLOW_PRODUCTION_WRITE=1
export KARZAR_INGESTION_CATEGORY=B
MANIFEST=audit/insize-price-110/INSIZE_PRICE_110_MANIFEST_20261019T122730Z.csv
SHA=edd614107db14d9ae96e6a5d5c2b04043f95c413e6902d45fc3de7d8228feee1
PYTHONPATH=. python3 scripts/ops/insize_price_110_apply_once.py \
  --out-dir audit/insize-price-110 \
  --manifest-csv "$MANIFEST" \
  --apply \
  --confirm-manifest-sha "$SHA"
```

Re-verify live priced count matches manifest row count immediately before APPLY. **If census or manifest drift is detected: DRIFT → STOP → INVESTIGATE → OWNER REVIEW.** Never silently regenerate the frozen owner-reviewed cohort or change `--confirm-manifest-sha` without owner review.

## Production identity (preflight)

| Probe | Value |
|-------|-------|
| VPS host | `srv5944957438` (`karzar-vps`) |
| DB | `karzar_staging` |
| Postgres container | `lathe_postgres` |
| Alembic | `c1d2e3f4a5b6` |
| API readiness | PASS |

## Artifacts

- `INSIZE_PRICE_110_MANIFEST_20261019T122730Z.{csv,json}`
- `INSIZE_PRICE_110_RECOVERY_PREWRITE_20261019T122730Z.csv`
- `INSIZE_PRICE_110_ROLLBACK_20261019T122730Z.sql`
- `APPLY_REPORT.json` (preflight; post-apply section filled after successful APPLY)
- `DISCOUNT_IMPACT_*.json` (0 rows at preflight — no compare-at display changes)

## Safety

- Idempotency: abort if any `product_change_logs` row exists with the event reason (MD5 match).
- Rollback: use exact `INSIZE_PRICE_110_ROLLBACK_*.sql` values — never divide by 1.10.
- Do not rerun after successful APPLY.
