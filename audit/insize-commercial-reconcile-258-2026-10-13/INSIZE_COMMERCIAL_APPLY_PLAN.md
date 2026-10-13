# INSIZE commercial APPLY plan (NOT AUTHORIZED)

- Source SHA256: `8324b2c175a703ab0ff7364da4a33f82c440d592cdc10d990c133bed39ac2989`
- Plan CSV: `INSIZE_COMMERCIAL_RECONCILE_PLAN.csv`
- Rollback: `INSIZE_COMMERCIAL_ROLLBACK_MANIFEST.csv` (explicit pre/post values)
- CLI: `scripts/apply_insize_commercial_reconcile_258.py` (dry-run default)
- Future APPLY journal must record exact before/after, batch id, timestamp, success/failure
- **No `--apply` in this PR**
