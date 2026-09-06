# RELEASE-RECORD — PR #241 Local Change Batch V1

**Artifact:** `RELEASE-RECORD` (`R-REL`)  
**Path:** `aods/reports/releases/2026-09-01-pr-241-local-change-batch-v1.md`  
**Related PR:** [#241](https://github.com/Shebahati/Karzar/pull/241) — `feat(site): Local Change Batch V1`  
**Related Issue (stabilization):** [#245](https://github.com/Shebahati/Karzar/issues/245) — Stabilize main after merged PR #241  
**Merge SHA:** `d839bab75908811e9fa8b9e7002ad7c967bf1c32`  
**Merged at:** 2026-09-01T11:46:03Z  
**Deploy run URL:** not established  
**Record written:** 2026-09-06 (stabilization / release-note completion under #245)

---

## Storefront

Independent concerns shipped in #241:

- Hero v2 (desktop/mobile image pairs)
- About / contact / navigation updates
- Public catalog image filtering
- Category slug redirect infrastructure

## Backend

Independent concerns shipped in #241:

- Abandoned carts API
- Open-order filters
- Hesabfa category mapping migration + metadata
- Website paid-sales behavior excluding mock gateway

## Admin

Independent concerns shipped in #241:

- Abandoned carts page
- Sales report correction
- Hesabfa mapping fields
- Design-system token usage on affected routes

## Tooling / Data

Independent concerns shipped in #241:

- Taxonomy migration dry-run tooling
- Regression tests for the batch
- Taxonomy CSV **not committed** (`work/reports/`); dry-run must be run on the operator machine/server when needed — operational consequence: no in-repo CSV authority for taxonomy apply

## Deferred / residual items

Preserved from PR #241 notes (still residual unless separately closed):

- Enamad official snippet deferred (placeholder only)
- Taxonomy CSV not committed
- `STOREFRONT_REQUIRE_MATERIALIZED_IMAGES` defaults to DEBUG; production uses CDN URLs / materialized-image behavior must be understood in that context

## Validation / stabilization

### Validation originally associated with #241

- Targeted pytest / admin typecheck / storefront redirect unit tests / `aods_validate.py` were claimed on the PR
- PR test plan still listed unchecked items at merge time (CI green on PR, Deploy Staging, live smoke, Alembic on VPS)

### Failures discovered after merge

- Merge commit `d839bab75908811e9fa8b9e7002ad7c967bf1c32` did **not** land with a fully green Frontend CI
- Storefront E2E (`storefront-e2e` / checkout-smoke) **failed** on that merge commit (GitHub Actions run `33504158977`)
- Deployment freeze blocked staging sync while Frontend CI was red (Deploy Staging run `33504194739` failed / skipped sync)

**Do not claim that #241 originally merged green.**

### Stabilization evidence under #245

- Issue [#245](https://github.com/Shebahati/Karzar/issues/245) opened as the P0 release gate: no new feature merge until main is a green, deployable, rollback-capable baseline
- Backend CI on subsequent main tip `f20ccb09cb994651340ce250df9908997c346cd3` (ops healthcheck #265): **success** (run `33727584558`) including lint/test/Alembic on isolated CI Postgres `karzar_ci`
- Live smoke (read-only, 2026-09-06T08:59:33Z UTC): storefront `www` HTTP 200; API `/health` and `/ready` HTTP 200; `GET /api/v1/products/` HTTP 200; admin login shell HTTP 200 — no paid checkout, no Production writes
- This maintenance change adds Frontend CI `workflow_dispatch` so the exact releaseable main tip can obtain GitHub-hosted Frontend/E2E evidence without a no-op product commit
- Post-merge tip Backend + Frontend + storefront-e2e must be green on the maintenance merge SHA before #245 is closed

## Smoke result

| Check | Result | Notes |
|-------|--------|-------|
| Storefront home | PASS (2026-09-06T08:59:33Z) | `karzartools.com` → `www` 200 |
| API `/health` | PASS | HTTP 200 |
| API `/ready` | PASS | database ok; redis ok |
| Public products | PASS | `GET /api/v1/products/` 200 |
| Admin shell | PASS | `/login` 200; login not performed |
| Paid checkout / SEP | not run | intentionally non-destructive |

Re-confirm smoke after the #245 maintenance merge lands; record final timestamp on Issue #245 closure.

## Rollback

- **Application rollback for #241 content:** revert merge commit `d839bab75908811e9fa8b9e7002ad7c967bf1c32` (or the equivalent squash/revert PR) via normal git revert on `main`; redeploy only after human `HC-11` authorization.
- **This release-governance maintenance PR:** revert its merge commit on `main` (restores Frontend CI without `workflow_dispatch` and removes this record).
- **Deploy run to roll back to:** not established (no authoritative Deploy Staging/Production run URL recorded for #241).

## Residual risks

- Multi-concern batch increases blast radius; prefer smaller PRs going forward
- Taxonomy CSV remains out of tree
- Enamad snippet still deferred
- Materialized-image / CDN defaults differ between DEBUG and production
- Historical E2E flake/timeout on merge commit must not be forgotten if Frontend CI regresses again
