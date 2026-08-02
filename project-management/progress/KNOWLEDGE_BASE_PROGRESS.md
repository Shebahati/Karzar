# Knowledge Base Progress

**Rollup:** 40%

- [x] **KB-001** Knowledge platform phase-1 content graph seed — `done` 100% | P2 | 30h | Sprint 04 — Day-3 CLOSED (#176)
- [x] **KB-REMEDIATION-00 / 00A / 00B / 00C** — Master KB remediation architecture contract **v0.3.0** Proposed (PR #192); owner implementation approval 2026-08-02 for Prompts 01–14 (**not** Board-Accepted); amended to **v0.4.0** by KB-PT-00 (Product Type gate §12.1)
- [x] **KB-PT-00** — Canonical Product Type architecture contract (SPEC v0.1.0→**v0.1.1** + ADR-015 Hybrid + Master KB **v0.4.1**). No runtime. Board Hybrid clarification completed by **KB-PT-00B**.
- [x] **KB-PT-00A** — Final owner-review corrections: Prompt 11A before PT-W2 membership; templates out of 11A; Board clarification mandatory; PT-W1 no readout/seed/backfill; non-duplicative hierarchy.
- [x] **KB-PT-00B** — Board Option A Hybrid clarification Accepted (`AB-ADR-015-2026-08-02`); ADR-015 Canon; KB-PT-01 may start after merge
- [x] **KB-PT-01** — PT-W1 runtime core: `product_types` + nullable `products.product_type_id` (`e6f7a8b9c0d1`). No seed/backfill/API. Awaiting human commit/PR.
- [x] **KB-PT-01A** — Integrity gaps closed: `passive_deletes="all"`; loaded-collection delete regression; populated migration Product+JSONB evidence.
- [x] **KB-REMEDIATION-11A** — Property Dictionary runtime A3: units + definitions + aliases (`f7a8b9c0d1e2`); CLI import; admin GET. No templates. Awaiting human commit/PR.
- [x] **Property Dictionary v0 (metrology)** — Git seed landed Day-4; dual-write still gated
- [x] **Taxonomy v0 (metrology)** — Git seed + commerce L1 bridge; no second Category DAG
- [x] **Classification map INSIZE v0** — Git MAPPING-TABLE for brand_id=3; closed taxonomy labels; no CLASSIFIED_AS edges yet
- [x] **Admin read-only Knowledge views** — `/knowledge` + product neighborhood; Facts publish still gated
  - Owner: PMO | Week 7 Day 1 | Risk: high
  - [ ] Description: Link articles↔products↔categories; avoid second taxonomy.
  - [x] Dependencies: SEO-003
  - [ ] Files: docs/KNOWLEDGE_PLATFORM*.md, app/**
  - [ ] Modules: knowledge
  - [ ] Tags: knowledge
  - Acceptance Criteria:
    - [ ] Graph links queryable
    - [ ] No DAG categories
  - Definition of Done:
    - [ ] KNOWLEDGE_BASE_PROGRESS
  - Notes: Foundation SPECs Proposed (#167). **Architecture completion pack** Proposed (audit + domain + property dictionary + taxonomy seed + KG registry + transform + target + readiness). Graph IMPL not started; Board Accept UD-06 open. “No second taxonomy” = no second *commerce* Category DAG.

## Evidence log
- [ ] Add links to PRs / GSC / Lighthouse here as you go
- [x] 2026-07-30 foundation SPECs (Proposed) — [#167](https://github.com/Shebahati/Karzar/pull/167)
- [x] 2026-07-30 architecture completion pack (Proposed) — [#168](https://github.com/Shebahati/Karzar/pull/168)
- [x] 2026-08-01 Day-5 INSIZE classification map (Git MAPPING-TABLE) — [#181](https://github.com/Shebahati/Karzar/pull/181)
- [x] 2026-08-01 Day-5 Admin read-only Knowledge views — [#183](https://github.com/Shebahati/Karzar/pull/183)
- [x] 2026-08-01 KB-001 local alembic+full-catalog sync proof (1064 products → 2132 edges) — report GOV-2026-08-01-operator-kb001-local-sync / #184
- [x] 2026-08-02 KB remediation contract v0.3.0 + owner implementation approval (00–00C) — PR #192 to main; Board Accept not granted
- [x] 2026-08-02 KB-PT-00 Canonical Product Type contract (SPEC + ADR-015 Proposed + Master KB v0.4.x) — branch `docs/kb-pt-00-canonical-product-type-contract`; no runtime; Board Accept not granted
- [x] 2026-08-02 KB-PT-00A final owner-review corrections (SPEC v0.1.1 / Master KB v0.4.1; Board clarification mandatory before KB-PT-01) — same branch; runtime still blocked
- [x] 2026-08-02 KB-PT-00B Board Option A Hybrid clarification Accepted (`AB-ADR-015-2026-08-02`); ADR-015 + Canon Lock; KB-PT-01 unblocked after merge
- [x] 2026-08-02 KB-PT-01 PT-W1 Product Type runtime core (`product_types` + nullable FK; migration `e6f7a8b9c0d1`) — branch `feat/kb-pt-01-runtime-core`; awaiting human commit/PR
- [x] 2026-08-02 KB-PT-01A integrity gaps closed (`passive_deletes="all"` + populated migration evidence) — same branch
- [x] 2026-08-02 KB-REMEDIATION-11A Property Dictionary runtime (`f7a8b9c0d1e2`; 2/9/36 import; admin GET) — branch `feat/kb-remediation-11a-property-dictionary`; awaiting human commit/PR
