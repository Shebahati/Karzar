# Sprint 04 — Freeze

**Focus:** Defer KB, REL-001 checkpoint
**Target week index:** 7

## Goals
- [x] Defer KB, REL-001 checkpoint

## Tasks
- [ ] **KB-001** Knowledge platform phase-1 content graph seed — `todo` 10% | P2 | 30h | Sprint 04
  - Owner: unassigned | Week 7 Day 1 | Risk: high
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
  - Notes: Defer if hours overrun
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
  - Notes: Readiness documentation complete; GO remains conditional on SEC-001 closure or explicit risk acceptance with named owner.

## Sprint exit checklist
- [x] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [x] PROJECT_STATUS.md updated
- [x] CHANGELOG.md entry