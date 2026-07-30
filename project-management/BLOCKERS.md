# Blockers

- [x] ~~Runner offline~~ — karzar-vps restored (historical)
- [ ] Search Console API access for weekly automation (optional)
- [x] ~~Editorial QA capacity for 24 articles~~ — SEO-003 24 articles published and verified
- [x] ~~Clear owner assignment for release command/rollback command~~ — **CLOSED** 2026-07-30 (AODS `CR-021` S1): release + rollback owner = **Mohammad Shebahati / محمد شباهتی** (single-operator model accepted; compensating control = `RELEASE_PLAN.md` §4)
- [x] ~~SEC-001 closure or explicit risk acceptance owner for GO decision~~ — SEC-001 closed 2026-07-27; residual dep advisories tracked as R8
- [x] ~~**Canon Lock is not on `main`** (AODS `CR-001`)~~ — **CLOSED** 2026-07-30: PR #125 merged (`8b63415`); Canon + standards resolve on `main`. Owner: Architecture Board
- [x] ~~**18 scripts default to the production API** (AODS `CR-004`)~~ — **CLOSED** 2026-07-30: defaults → local (Option A); fail-closed `KARZAR_ALLOW_PRODUCTION_WRITE` + Category B classify for deploy publishers (Options B+C).
- [x] ~~**Staging auto-deploy on push to `main`** (AODS `CR-011` auto-deploy half)~~ — **CLOSED** 2026-07-30 Option B: `deploy-staging.yml` is `workflow_dispatch` only.
- [ ] **Staging and production remain the same VPS** (AODS `CR-011` residual / future Option A) — no independent rehearsal host. Owner: DevOps / Release Manager
- [ ] **Authoring source-of-record lives outside Git** (AODS `CR-009`) — `Website/docs/` is declared authoritative but unversioned. Owner: Owner
- [x] ~~**`frontend/AI_CONTEXT.md` is an active hallucination source** (AODS `CR-015`)~~ — **CLOSED** 2026-07-30 Option A: stub + `docs/archive/AI_CONTEXT-2026-07-11.md`; forbidden_context retained.
