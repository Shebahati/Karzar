# Rollback plan (evidence only)

Pre-apply state captured in `expected_current_hash` per dry-run row.
Rollback restores `is_available` and `base_price` from pre-apply journal — not executed.
