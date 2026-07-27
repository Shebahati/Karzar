# Backend Progress

**Rollup:** 42%

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
- [ ] **CAT-002** INSIZE JSON-schema content fill (staging apply) — `todo` 15% | P1 | 20h | Sprint 02
  - Owner: unassigned | Week 3 Day 1 | Risk: med
  - [ ] Description: Resume content-only INSIZE enrichment with locked measurement schema; no inventing specs.
  - [ ] Dependencies: CAT-001
  - [ ] Files: scripts/enrich_insize*.py
  - [ ] Modules: catalog, seo
  - [ ] Tags: insize, content
  - Acceptance Criteria:
    - [ ] ≥200 SKUs content QA
    - [ ] price_fields_written=none
  - Definition of Done:
    - [ ] SEO_PROGRESS note
  - Notes: #74 closed intentionally
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

## Evidence log
- [ ] Add links to PRs / GSC / Lighthouse here as you go
