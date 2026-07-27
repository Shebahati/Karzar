# Sprint 00 — Foundation & triage

**Focus:** PMO, PR triage, images, selectable FE drift
**Target week index:** 1

## Goals
- [ ] PMO, PR triage, images, selectable FE drift

## Tasks
- [x] **PMO-001** Bootstrap living PMO workspace — `done` 100% | P0 | 8h | Sprint 00
  - Owner: agent | Week 1 Day 1 | Risk: low
  - [x] Description: Create project-management SoT, exports, Cursor rule, printable boards.
  - [x] Dependencies: —
  - [x] Files: project-management/**, .cursor/rules/pmo-living-system.mdc
  - [x] Modules: docs, ops
  - [x] Tags: pmo, meta
  - Acceptance Criteria:
    - [x] All required PMO files exist
    - [x] Cursor rule alwaysApply
    - [x] Exports importable
  - Definition of Done:
    - [x] Merged to main
    - [x] Linked from README
  - Notes: #86 → main; living PMO in active use (SEO-001/002/004)
- [x] **CAT-001** Close enrichment PR triage (Dasqua/Mitutoyo/etc.) — `done` 100% | P1 | 8h | Sprint 00
  - Owner: unassigned | Week 1 Day 2 | Risk: low
  - [x] Description: Merge or close remaining enrichment PRs with content-only guarantees.
  - [x] Dependencies: —
  - [x] Files: scripts/**, data/imports/**
  - [x] Modules: catalog
  - [x] Tags: catalog, ops
  - Acceptance Criteria:
    - [x] Each open enrichment PR decided
    - [x] No price writes
  - Definition of Done:
    - [x] PROJECT_STATUS updated
  - Notes: #67 → main @f51c9fd; #69 → main @0829571 (Deploy Staging 30274744553); #70–#73 prior; #74 closed; #90 deferred w/ CAT-002.

- [x] **CAT-003** Category image coverage for all L1+key L2 — `done` 100% | P1 | 10h | Sprint 00
  - Owner: unassigned | Week 1 Day 3 | Risk: low
  - [x] Description: Ensure every homepage/megamenu root has full-bleed quality image.
  - [x] Dependencies: —
  - [x] Files: scripts/seed_category_images.py, frontend/Storefront/public/images/**
  - [x] Modules: frontend, catalog
  - [x] Tags: ui, images
  - Acceptance Criteria:
    - [x] 0 L1 without image
    - [x] Visual QA mobile
  - Definition of Done:
    - [x] UI_PROGRESS
  - Notes: Helicoil L1 186–188 curated; prior L1 map via #85; seed script ready for API image_url on metrology+helicoil; key L2 optional.

- [x] **BE-001** Catalog API readiness for SEO fields — `done` 100% | P1 | 10h | Sprint 00
  - Owner: unassigned | Week 1 Day 4 | Risk: low
  - [x] Description: Ensure short_description, meta, specs exposed consistently to storefront.
  - [x] Dependencies: —
  - [x] Files: app/api/**, app/schemas/**, openapi/v1.json
  - [x] Modules: backend
  - [x] Tags: backend, seo
  - Acceptance Criteria:
    - [x] Contract tests green
    - [x] OpenAPI updated
  - Definition of Done:
    - [x] BACKEND_PROGRESS
  - Notes: Regenerated `openapi/v1.json` (SEO fields on product schemas); #66/#68 plumbing; pytest SEO/audit 16 passed.

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
- [x] **OPS-001** Merge promote-measurement workflow fix #81 — `done` 100% | P2 | 2h | Sprint 00
  - Owner: unassigned | Week 1 Day 2 | Risk: low
  - [x] Description: Land no-checkout workflow for taxonomy promote on VPS.
  - [x] Dependencies: —
  - [x] Files: .github/workflows/**
  - [x] Modules: ops
  - [x] Tags: ops, ci
  - Acceptance Criteria:
    - [x] Workflow green
  - Definition of Done:
    - [x] DONE.md
  - Notes: #81 → main @e1981b6; workflow/script-only (no Deploy Staging)

## Sprint exit checklist
- [ ] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [ ] PROJECT_STATUS.md updated
- [ ] CHANGELOG.md entry