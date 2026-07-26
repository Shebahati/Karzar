# Sprint 00 — Foundation & triage

**Focus:** PMO, PR triage, images, selectable FE drift
**Target week index:** 1

## Goals
- [ ] PMO, PR triage, images, selectable FE drift

## Tasks
- [ ] **PMO-001** Bootstrap living PMO workspace — `in_progress` 70% | P0 | 8h | Sprint 00
  - Owner: agent | Week 1 Day 1 | Risk: low
  - [ ] Description: Create project-management SoT, exports, Cursor rule, printable boards.
  - [ ] Dependencies: —
  - [ ] Files: project-management/**, .cursor/rules/pmo-living-system.mdc
  - [ ] Modules: docs, ops
  - [ ] Tags: pmo, meta
  - Acceptance Criteria:
    - [ ] All required PMO files exist
    - [ ] Cursor rule alwaysApply
    - [ ] Exports importable
  - Definition of Done:
    - [ ] Merged to main
    - [ ] Linked from README
  - Notes: This PR
- [ ] **CAT-001** Close enrichment PR triage (Dasqua/Mitutoyo/etc.) — `todo` 40% | P1 | 8h | Sprint 00
  - Owner: unassigned | Week 1 Day 2 | Risk: low
  - [ ] Description: Merge or close remaining enrichment PRs with content-only guarantees.
  - [ ] Dependencies: —
  - [ ] Files: scripts/**, data/imports/**
  - [ ] Modules: catalog
  - [ ] Tags: catalog, ops
  - Acceptance Criteria:
    - [ ] Each open enrichment PR decided
    - [ ] No price writes
  - Definition of Done:
    - [ ] PROJECT_STATUS updated
  - Notes: #71/#72 merged or open — verify
- [ ] **CAT-003** Category image coverage for all L1+key L2 — `todo` 60% | P1 | 10h | Sprint 00
  - Owner: unassigned | Week 1 Day 3 | Risk: low
  - [ ] Description: Ensure every homepage/megamenu root has full-bleed quality image.
  - [ ] Dependencies: —
  - [ ] Files: scripts/seed_category_images.py, frontend/Storefront/public/images/**
  - [ ] Modules: frontend, catalog
  - [ ] Tags: ui, images
  - Acceptance Criteria:
    - [ ] 0 L1 without image
    - [ ] Visual QA mobile
  - Definition of Done:
    - [ ] UI_PROGRESS
  - Notes: Partial via #85
- [ ] **BE-001** Catalog API readiness for SEO fields — `todo` 70% | P1 | 10h | Sprint 00
  - Owner: unassigned | Week 1 Day 4 | Risk: low
  - [ ] Description: Ensure short_description, meta, specs exposed consistently to storefront.
  - [ ] Dependencies: —
  - [ ] Files: app/api/**, app/schemas/**
  - [ ] Modules: backend
  - [ ] Tags: backend, seo
  - Acceptance Criteria:
    - [ ] Contract tests green
    - [ ] OpenAPI updated
  - Definition of Done:
    - [ ] BACKEND_PROGRESS
  - Notes: #66/#68
- [ ] **TD-001** Pay down category depth / selectable FE drift — `todo` 50% | P2 | 6h | Sprint 00
  - Owner: unassigned | Week 1 Day 5 | Risk: low
  - [ ] Description: Align admin FE helpers with depth-2|3 selectable rule everywhere.
  - [ ] Dependencies: —
  - [ ] Files: frontend/admin-panel/**
  - [ ] Modules: frontend, techdebt
  - [ ] Tags: techdebt
  - Acceptance Criteria:
    - [ ] No depth===3-only filters left
  - Definition of Done:
    - [ ] TECH_DEBT
- [ ] **OPS-001** Merge promote-measurement workflow fix #81 — `todo` 80% | P2 | 2h | Sprint 00
  - Owner: unassigned | Week 1 Day 2 | Risk: low
  - [ ] Description: Land no-checkout workflow for taxonomy promote on VPS.
  - [ ] Dependencies: —
  - [ ] Files: .github/workflows/**
  - [ ] Modules: ops
  - [ ] Tags: ops, ci
  - Acceptance Criteria:
    - [ ] Workflow green
  - Definition of Done:
    - [ ] DONE.md
  - Notes: Open PR #81

## Sprint exit checklist
- [ ] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [ ] PROJECT_STATUS.md updated
- [ ] CHANGELOG.md entry