# 09 — Implementation report

**Commit branch:** `fix/hero-calibrated-delivery-quality-20261019`  
**HEAD:** `ae77eb9b6f392b2391aa977256763cd533e0745a` (pre-commit attestation — re-run `git rev-parse` after commit)

## Files changed

| File | Change |
|------|--------|
| `frontend/Storefront/src/lib/hero-background-image.tsx` | `isCalibratedCampaignHeroArt()`; `unoptimized: true` for calibrated `<picture>` + `SafeImage` fallback |
| `frontend/Storefront/src/lib/__tests__/hero-background-image.test.tsx` | Expect direct WebP URLs (no `/_next/image`) for calibrated assets |
| `frontend/Storefront/e2e/hero-image-quality-audit.spec.ts` | Forensic capture harness (optional CI) |
| `audit/hero-image-quality-20261019/*` | Evidence bundle |

## Rationale

Smallest complete delivery fix: stop width cap + double lossy re-encode for **already-exported** full-resolution WebP masters.

## Tests run

- `npm test -- src/lib/__tests__/hero-background-image.test.tsx` — pass
- `npm run build` — pass
- `npm run typecheck` / `lint` — see CI/local log

## Rollback

Revert commit or set `unoptimized` guard to false; calibrated URLs return to `/_next/image` behavior. Original assets unchanged under `calibrated-20261018/`.

## Admin / publication

Published hero paths remain the same URLs; admin overrides pointing at calibrated directory inherit fix automatically. Legacy PNG overrides still optimized.
