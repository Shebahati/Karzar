# Release Plan — REL-001 (31 Shahrivar Checkpoint)

**Last updated:** 2026-07-30  
**Checkpoint date:** 2026-09-22 (31 Shahrivar)  
**Decision type:** Readiness + explicit go/no-go gate

## 0) Named operators (AODS `CR-021` — CLOSED 2026-07-30)

| Role | Person | Notes |
|------|--------|-------|
| **Release owner** | Mohammad Shebahati / محمد شباهتی | Authorises merge/deploy for checkpoint releases |
| **Rollback owner** | Mohammad Shebahati / محمد شباهتی | Executes §4 rollback |

**Model:** single-operator release path **accepted** (HC-03 Option S1). Compensating control = this document §4
(`identify last known good` → redeploy prior revision → smoke + SEO quick checks → PMO incident note). Separation
of duties is not available with one human; bus-factor-1 and same-VPS staging (`CR-011`) remain residual ops risk.
## 1) Scope freeze (P0 baseline)

### Completed P0 scope
- [x] `PMO-001` Living PMO bootstrap
- [x] `SEO-001` Product/Offer/Breadcrumb JSON-LD
- [x] `SEO-002` Category hub intros + internal links
- [x] `SEO-003` 24 buyer-intent articles
- [x] `SEO-004` Technical crawl hygiene
- [x] `UX-002` PDP trust + specs presentation
- [x] `PERF-001` Core Web Vitals foundations
- [x] `REL-001` Release readiness pack (this update)

### Deferred / out-of-scope for checkpoint
- [x] `KB-001` deferred to post-checkpoint (P2, high effort, non-critical for current KPI)
- [x] `CAT-002` deferred as content-safe backlog (not required for launch bar)
- [x] `SEC-001` completed (admin noindex/X-Robots-Tag, secrets audit, step-up inventory, dep scan); residual transitive advisories tracked as R8
- [x] Deferred-task ownership/date recorded at close (2026-07-28): owner `PMO`, revisit `2026-09-23` for both `CAT-002` and `KB-001`

Rationale: checkpoint KPI is stable store + indexable mid-tail + CWV discipline, not head-term rank race or broad platform expansion.

## 2) Release gates (must pass for GO)

### Product/SEO gates
- [x] Schema baseline shipped (`SEO-001`) and staging-verified on representative PDPs
- [x] Mid-tail content baseline shipped (`SEO-002` + `SEO-003`)
- [x] Crawl hygiene baseline shipped (`SEO-004`)

### UX/performance gates
- [x] PDP trust/specs baseline shipped (`UX-002`)
- [x] CWV foundation shipped (`PERF-001`)
- [ ] Field p75 confirmation during launch window (monitoring gate, post-merge verification)

### Operations/security gates
- [x] Backup/rollback steps documented (see section 4)
- [x] `SEC-001` completion (ACs met; residual dep advisories accepted as R8 with named follow-up)
- [x] Clear owner assignment for launch command + rollback command — Mohammad Shebahati (both; S1 / `CR-021` CLOSED 2026-07-30)

## 3) Launch window verification checklist

Run immediately after merge to `main` and staging/prod deployment event:

- [ ] Verify home renders with expected hero/header behavior
- [ ] Verify one representative PLP/category hub page
- [ ] Verify one representative PDP with schema + trust strip + specs
- [ ] Verify one representative blog URL from the 24-article set
- [ ] Verify sitemap endpoint responds and includes recent `lastmod`
- [ ] Verify robots/noindex behavior for private/facet pages
- [ ] Verify no Sev1/Sev2 error spike in app logs for first 30 minutes
- [ ] Record CWV baseline observations for home/PDP/PLP in launch note

## 4) Rollback plan

### Trigger conditions
- Sev1 conversion/runtime breakage
- Major SEO regression (critical schema invalidation or widespread canonical/indexing misconfiguration)
- Sustained performance collapse beyond acceptable baseline

### Rollback execution
1. Identify last known good `main` commit before release.
2. Re-deploy previous good revision via standard deploy workflow.
3. Confirm smoke paths: home, PLP, PDP, blog article.
4. Validate sitemap/robots/schema quick checks.
5. Publish incident note in PMO changelog + blockers/risks if unresolved.

### Data/migration notes
- Current release-track changes are mostly content/frontend/metadata.
- Megamenu/category flag migrations previously noted as additive-safe.
- No price/stock/catalog mutation action is included in REL-001.

## 5) Explicit go/no-go criteria

### GO requires all of:
- P0 baseline above remains intact in `main`
- No open Sev1 blockers
- `SEC-001` completed (residual R8 dep advisories tracked, not blocking hygiene ACs)
- Rollback operator + release operator explicitly assigned
- Launch window checklist executed and logged

### NO-GO if any of:
- Sev1 blocker unresolved
- Release/rollback ownership unresolved *(resolved 2026-07-30 — see §0)*
- Rollback path cannot be executed quickly/clearly

## 6) Residual risks at freeze point

Residual risk items and owners are tracked in `RISKS.md`; unresolved execution blockers are tracked in `BLOCKERS.md`.
