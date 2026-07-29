# Sprint 04 — Freeze

**Focus:** Defer KB, REL-001 checkpoint
**Target week index:** 7

## Goals
- [x] Defer KB, REL-001 checkpoint

## Tasks
- [ ] **KB-001** Knowledge platform phase-1 content graph seed — `todo` 10% | P2 | 30h | Sprint 04 — **DEFERRED** (post-31-Shahrivar)
  - Owner: PMO | Week 7 Day 1 | Risk: high
  - [ ] Description: Link articles↔products↔categories; avoid second taxonomy.
  - [ ] Dependencies: SEO-003
  - [ ] Files: docs/KNOWLEDGE_PLATFORM*.md, app/**
  - [ ] Modules: knowledge
  - [ ] Tags: knowledge
  - Acceptance Criteria:
    - [ ] Graph links queryable
    - [ ] No DAG categories
  - Definition of Done:
    - [ ] KNOWLEDGE_BASE_PROGRESS
  - Notes: DEFERRED at checkpoint close (2026-07-28) post-31-Shahrivar (EXEC/RELEASE/D7); not checkpoint KPI; revisit 2026-09-23
- [x] **REL-001** Release readiness for 31 Shahrivar checkpoint — `done` 100% | P0 | 10h | Sprint 04
  - Owner: unassigned | Week 8 Day 5 | Risk: med
  - [x] Description: Freeze P0s, changelog, rollback plan, monitoring checklist.
  - [x] Dependencies: SEO-003, PERF-001, SEC-001
  - [x] Files: project-management/RELEASE_PLAN.md
  - [x] Modules: ops
  - [x] Tags: release
  - Acceptance Criteria:
    - [x] All P0 done or explicitly deferred
    - [x] Rollback noted
  - Definition of Done:
    - [x] RELEASE_PLAN signed
  - Notes: Readiness documentation complete; SEC-001 hygiene ACs closed; residual dep advisories as R8; GO still needs named release/rollback owners.

- [ ] **AODS-001** Design the AI-Orchestrated Development System (AODS) — `in_progress` 90% | P1 | 24h | Sprint 04
  - Owner: agent | Week 1 Day 3 | Risk: med
  - [x] Description: Repository audit, then the governing process system for AI-assisted development.
  - [x] Dependencies: none
  - [x] Files: aods/**, .cursor/rules/aods-*.mdc
  - [x] Modules: docs, ops
  - [x] Tags: aods, governance, meta, process
  - Acceptance Criteria:
    - [x] All 19 required sections delivered as documentation
    - [x] Validators run on python3 with no third-party imports
    - [x] Every tracked markdown file is classified in the document registry
    - [x] Conflicts reported with owners, never silently resolved
    - [x] Prompt library follows one mandatory template and passes the prompt lint
  - Definition of Done:
    - [x] aods_validate.py exits 0 against the recorded baseline
    - [x] CHANGELOG.md + PROJECT_STATUS.md updated
    - [ ] Board acceptance (HC-14) — pack ships as **Proposed**; not done until a Board minute accepts it
  - Notes: Process-only; no application behaviour changed. Validators independently confirmed CR-004 (18 scripts default to the production API), CR-007 (6 divergent PMO ledger pairs) and CR-012 (`openapi/v1.json` is missing `/api/v1/products/slug/{slug}`, live since #126). 23 conflicts registered; 31 findings baselined as visible debt. Deliberately **not** marked done: only the Architecture Board can accept the pack.

## Sprint exit checklist
- [x] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [x] PROJECT_STATUS.md updated
- [x] CHANGELOG.md entry