# INSIZE commercial rollback plan (evidence only)

Use `INSIZE_COMMERCIAL_ROLLBACK_MANIFEST.csv` for reversible pre-apply values
(`pre_is_available`, `pre_base_price`). Hashes are stale guards only — not rollback data.

Post-APPLY journal must capture exact before/after per row. Rollback not executed in this PR.
