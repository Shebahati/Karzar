# Phase 2C APPLY Rehearsal Summary

> **REHEARSAL ONLY** — transaction rolled back; no persistent writes.

- Frozen cohort: **1350** rows (`43620d24842b946652f8e2a0256aa75e45fbdf1b591b0374dcb84dea21417b03`)
- Rehearsal logic git SHA: `a0b04291b02d583ee1981c579acb2b19646b6aae`
- Slug comparison: `NOT_AVAILABLE_IN_FROZEN_ARTIFACT` / drift `NOT_APPLICABLE`
- Name drift rows: **0**
- Preflight pass: **1350**
- Rehearsal OK: **True**
- Live health: API=PASS DB=PASS Redis=PASS
- Change-log path: `transactional SQL equivalent` (contract `app.crud.audit.record_product_change`)
- Rollback proof: **{'explicit_rollback': True, 'target_manufacturer_code_non_null': 0, 'target_manufacturer_code_null': 1350, 'persistent_rehearsal_change_logs': 0, 'fingerprints_equal': True, 'baseline_counts_equal': True}**
- Ready for owner APPLY: **True**

REHEARSAL REPRODUCED FROM IMMUTABLE LOGIC COMMIT
ROLLBACK VERIFIED
READY FOR OWNER APPLY

