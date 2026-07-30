# Blockers

- [x] ~~Runner offline~~ — karzar-vps restored (historical)
- [ ] Search Console API access for weekly automation (optional)
- [x] ~~Editorial QA capacity for 24 articles~~ — SEO-003 24 articles published and verified
- [ ] Clear owner assignment for release command/rollback command (still `unassigned`)
- [x] ~~SEC-001 closure or explicit risk acceptance owner for GO decision~~ — SEC-001 closed 2026-07-27; residual dep advisories tracked as R8
- [x] ~~**Canon Lock is not on `main`** (AODS `CR-001`)~~ — **CLOSED** 2026-07-30: PR #125 merged (`8b63415`); Canon + standards resolve on `main`. Owner: Architecture Board
- [x] ~~**18 scripts default to the production API** (AODS `CR-004`)~~ — **CLOSED** 2026-07-30: defaults → `http://127.0.0.1:8000/api/v1` (ADR-012 Option A). Residual: fail-closed guard + Category B classify for deploy publishers.
- [ ] **Authoring source-of-record lives outside Git** (AODS `CR-009`) — `Website/docs/` is declared authoritative but unversioned. Owner: Owner
- [ ] **Staging and production are the same VPS** (AODS `CR-011`) — merge to `main` deploys live; there is no independent rehearsal. Owner: DevOps / Release Manager
- [x] ~~**`frontend/AI_CONTEXT.md` is an active hallucination source** (AODS `CR-015`)~~ — **CLOSED** 2026-07-30 Option A: stub + `docs/archive/AI_CONTEXT-2026-07-11.md`; forbidden_context retained.
