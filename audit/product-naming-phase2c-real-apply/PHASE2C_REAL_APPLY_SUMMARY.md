# Phase 2C REAL APPLY summary

## STATUS
`APPLIED_VERIFIED`

## Authorization
- Owner-authorized real APPLY: YES
- Cohort rows: 1350
- Cohort SHA256: `43620d24842b946652f8e2a0256aa75e45fbdf1b591b0374dcb84dea21417b03`

## Git
- Apply logic SHA: `bd817801ad9cd172b418a59f1302ff2768c40e69`

## Transaction
- Isolation: SERIALIZABLE
- Advisory lock: `karzar:phase2c:manufacturer_code:apply`
- Locked / updated / exact / logs: 1350 / 1350 / 1350 / 1350
- Protected drift: 0
- New collisions: 0
- Non-target manufacturer_code changes: 0
- COMMIT: YES
- Commit timestamp UTC: `2026-10-03T15:11:36.445036+00:00`
- TXID: not captured in psql stdout (COMMIT succeeded; post-commit verification passed)

## Post-apply
- Target non-null: 1350
- Target null: 0
- Exact frozen matches: 1350
- Global populated: 1350
- Change logs: 1350
- Protected drift: 0
- Collisions: 0
- DB identity smoke INSIZE/DASQUA/TERMA: PASS

## Backup / recovery
- Backup: `/home/shebahati/karzar-backups/phase2c/karzar_staging_phase2c_20261003T151115Z.dump`
- Backup SHA256: `08ff81c32a8ce02a1ba9c89e0cb5dc7fbcc3fcae79f47711dfd86134bfed7760`
- pg_restore --list: PASS
- Recovery package present (not executed)

## Second-run safety
- Re-apply blocked because manufacturer_code already populated = 1350
- New writes: 0
- New logs: 0

## Safety
- NO rename / NO deploy / NO Phase 2D / NO Phase 2E
