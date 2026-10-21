# Hero real photos hotfix (2026-10-21)

## Root cause
PR #545 shipped `pack-20261021` graphic placeholders (yellow/grey rectangles), not Owner photographic masters.

## Corrected source
- ZIP: `karzar_hero_photos_corrected_20261021.zip`
- ZIP SHA-256: `f2cba559338debbad06aff82aa75f535aa116d70589fea71b56e48670e86826d`
- Asset dir: `photo-20261021-v2/`
- Byte integrity: `src/config/hero-photo-20261021-v2-manifest.json` + `hero-photo-20261021-v2-integrity.test.ts`

## Local validation
- Storefront: 456 tests pass, typecheck, build OK
- Screenshots: `screenshots/` (H01 direct WebP at 390/1023 mobile, 1440 desktop; `nextImage=false`)

## Deploy / rollback
- Deploy via **Deploy Staging** on merged `main` (freeze currently **true**).
- Rollback: redeploy previous `ba9ebda` images or frontend-only `6a9ee839` / keep `pack-20261021` paths on prior commit — do not delete `pack-20261021/` on disk.
