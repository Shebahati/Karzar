# Phase 2C APPLY — future design (NOT IMPLEMENTED)

This document is planning only. No executable apply path exists in this PR.

## Preconditions

1. Owner-approved `BACKFILL_EXACT.csv` artifact  
2. Artifact SHA256 recorded and verified  
3. Exact expected row count  
4. Live DB baseline fingerprints (name/sku/slug/manufacturer_code)  
5. Read-only rehearsal against staging  
6. Transactional dry-run with before/after diffs  
7. `record_product_change(...)` for every mutation  
8. Rollback proof on a canary cohort  
9. Post-apply reconciliation (counts + collision scan)

## Hard refusals

- No bulk `SKU → manufacturer_code`  
- No title-heuristic auto-govern  
- No ProductCreate/ProductUpdate OEM writer exposure as part of APPLY tooling  
- No taxonomy / synonym / Fact / price / availability mutation  
- No production write without Category B + explicit allow flags  

## Discovery script contract

`scripts/audit_manufacturer_identity_phase2c_discovery.py` rejects `--apply`
(exit 2). Discovery remains fail-closed.
