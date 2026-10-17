# INSIZE Wave D APPLY plan (guarded — NOT EXECUTED)

**Authorization phase:** dry-run only. Owner must separately issue `AUTHORIZE_WAVE_D_APPLY`.

## Entry point

```bash
python3 scripts/apply_insize_wave_d_391_availability.py \
  --evidence-dir audit/sellability-391-wave-d-insize-2026-10-13 \
  # --apply  # NOT RUN in this phase
```

## Preconditions (fail-closed)

1. Immutable allowlist: exactly **10** product IDs in `ALLOWLIST.csv`
2. Source SHA256: `beb549109165a1fd0d156af8d9b8a9622eb3a04e7fc92b07c548993ee98669cf`
3. Freshness ∈ {CURRENT_ENOUGH, AGING_BUT_USABLE} at execution
4. Each row `expected_current_hash` in `INSIZE_WAVE_D_EXPECTED_STATE.csv` matches live DB
5. `UPDATE` scope: `is_available` only; rowcount must equal 10
6. Category B: `KARZAR_ALLOW_PRODUCTION_WRITE=1` and `KARZAR_INGESTION_CATEGORY=B` when `--apply`

## Rollback

Use `ROLLBACK_MANIFEST.csv` — set `is_available=false` only for rows successfully updated.

## Audit journal

Post-apply read-only reconciliation required; journal path TBD at APPLY authorization.
