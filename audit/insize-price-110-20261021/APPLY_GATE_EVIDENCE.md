# Apply gate evidence — `INSIZE-PRICE-110-20261021`

**Gate status:** `READY_FOR_INDEPENDENT_RE_REVIEW`  
**Production APPLY:** **not executed** (blocked until explicit owner authorization after re-review)

## Critical review remediation (CSV boolean)

- **Defect:** `csv.DictReader` yields strings; `bool("False")` is true, so legacy SQL generation could mark all 206 rows as `original_price` exceptions.
- **Fix:** `parse_csv_bool`, `normalize_manifest_from_csv_rows`, and `validate_owner_frozen_commercial_contract` (exact IDs `{1944, 3639}`, 2 exceptions / 204 non-exceptions, proposed `original_price` whitelist).
- **SQL:** `_sql_exception_literal` + hard-coded contract constants (`exception_n=2`, `total logs=208`) independent of string truthiness; post-update stray `original_price` guards.
- **Frozen v2 CSV SHA256 unchanged:** `bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540`

## Manifest preservation

| Artifact | SHA256 (CSV) |
|----------|----------------|
| v1 immutable | `cc1003dd41d5a87ddfb4c98724992ffad897585a46203ad780992ec46cae2d15` |
| v2 frozen | `bb2d073b8adc037ccfc50122da845d9e4869658a0467c364264fbe7f0af80540` |

## Production read-only verification (fresh)

- `--verify-frozen-manifest` v2: **ok=true**, drift **0** (includes **old_original_price** NULL-safe compare for all 206)
- Idempotency: base 2026-10-21 **0**; original-clear **0**; Oct 19 base **206**

## Rehearsal (SERIALIZABLE + ROLLBACK)

| Contract item | Count |
|---------------|------:|
| `base_price` updates | 206 |
| `original_price` NULL clears (1944, 3639) | 2 |
| Base change logs | 206 |
| Original-clear change logs | 2 |
| **Total event logs** | **208** |

Status: **REHEARSAL_OK** / **ROLLED_BACK** (no persistent DB change).

## Post-commit verification (operator — required before `COMMITTED_VERIFIED`)

- All 206 `base_price` exact + sum **3,755,024,460.00** Toman
- `original_price` NULL only on **1944** and **3639**; 204 unchanged
- Both change-log reasons: **206** + **2**; no unexpected `original_price` logs
- Public API spot checks use **Decimal** equality; merchandising exception slugs included when public

## Tests

`test_insize_price_110_20261021_*` + frozen CSV boolean regression (DictReader round-trip).

## Guarded rollback

`build_rollback_sql` uses the same strict parsing/contract; restores both price fields; **no auto-rollback**.
