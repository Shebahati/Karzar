# Phase 2C post-apply evidence integrity closure

## STATUS
`PASS`

## Facts

1. Live APPLY itself was already **APPLIED_VERIFIED** (COMMIT at `2026-10-03T15:11:36.445036+00:00`).
2. No live DB changes occurred in this closure (read-only check: manufacturer_code populated = 1350).
3. Recovery manifest hash naming was clarified: embedded field is now `manifest_payload_sha256` (hash of JSON body before that field). Final on-disk file hash is recorded only externally in `APPLY_EVIDENCE_INTEGRITY_REPORT.json`.
4. Pre-apply baseline was reconstructed from the verified pre-apply backup `karzar_staging_phase2c_20261003T151115Z.dump` (`08ff81c32a8ce02a1ba9c89e0cb5dc7fbcc3fcae79f47711dfd86134bfed7760`). It is **not** claimed to be the original first-write file.
5. Tooling now prevents silent overwrite of successful-run evidence; later invocations isolate to `probes/<timestamp>/`.
6. Evidence chain is now merge-safe for PR #424.

## Safety
- NO DEPLOY
- NO RENAME
- NO PHASE 2D
- NO PHASE 2E
- NO live APPLY rerun
