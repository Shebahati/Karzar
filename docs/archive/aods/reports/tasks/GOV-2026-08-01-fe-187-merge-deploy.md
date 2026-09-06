# GOV — FE #187 merge + Deploy Staging gate

**Date:** 2026-08-01  
**Result:** #188 MERGED · #187 MERGED · Deploy Staging **not** dispatched (integration 403)

## Merges
| PR | SHA | Notes |
|----|-----|-------|
| #188 | `0d422ec` | aods `on_main: true` for FE collaborator docs + frontend README link (required Frontend CI) |
| #187 | `18eac71` | Storefront redesign; branch updated with main then CI green (aods/storefront/admin-panel) |

## Pre-deploy smoke (live VPS, pre-#187 bundle)
- `www` HTTP 200
- `admin` HTTP 307 → `/login`
- `api/ready` HTTP 200 database/redis ok

## Owner action
Actions → Deploy Staging → Run workflow on `main`  
https://github.com/Shebahati/Karzar/actions/workflows/deploy-staging.yml  
Do not Deploy Production.
