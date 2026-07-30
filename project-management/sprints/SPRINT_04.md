# Sprint 04 — Freeze

**Focus:** Defer KB, REL-001 checkpoint
**Target week index:** 7

## Goals
- [x] Defer KB, REL-001 checkpoint

## Tasks
- [ ] **KB-001** Knowledge platform phase-1 content graph seed — `todo` 20% | P2 | 30h | Sprint 04 — **eligible to start** (foundation SPECs Proposed 2026-07-30)
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
  - Notes: Historical deferral at checkpoint close (2026-07-28) per D7/RELEASE_PLAN. Schedule unblock 2026-07-30: 2026-09-23 date gate lifted — eligible to start. Phase-1 graph slice still needs SPEC before IMPL.
- [x] **REL-001** Release readiness for 31 Shahrivar checkpoint — `done` 100% | P0 | 10h | Sprint 04
  - Owner: Mohammad Shebahati | Week 8 Day 5 | Risk: med
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
  - Notes: Readiness documentation complete; SEC-001 hygiene ACs closed; residual dep advisories as R8; release/rollback owners named 2026-07-30 (S1 / `CR-021` CLOSED).

- [x] **FE-003** Remove non-Karzar website references from storefront content/images — `done` 100% | P0 | 6h | Sprint 04
  - Owner: unassigned | Week 4 Day 2 | Risk: med
  - [x] Description: Purge external website mentions; local assets; remove external footer/contact website links. (CR-013; was CONTENT-URL-001.)
  - [x] Dependencies: SEO-003
  - [x] Files: frontend/Storefront/content/**, frontend/Storefront/src/**
  - [x] Modules: content, ui
  - [x] Tags: content, ux, compliance
  - Acceptance Criteria:
    - [x] No non-Karzar website references in storefront content payloads
    - [x] Customer-visible images from local assets
    - [x] Contact/footer external website links removed
  - Definition of Done:
    - [x] CONTENT_PROGRESS
  - Notes: #109 → main @f100ffa.

- [x] **AODS-001** Design the AI-Orchestrated Development System (AODS) — `done` 100% | P1 | 24h | Sprint 04
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
    - [x] Board acceptance (HC-14) — **Accepted** ۸ مرداد ۱۴۰۵; signed Mohammad Shebahati / محمد شباهتی; pack `1.0.0`; minute `aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`; PR #128
  - Notes: Process-only; no application behaviour changed. D9 closed. Canon Lock row still needs PR #125 merge (`CR-001`).

## Sprint exit checklist
- [x] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [x] PROJECT_STATUS.md updated
- [x] CHANGELOG.md entry