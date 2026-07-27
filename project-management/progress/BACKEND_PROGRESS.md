# Backend Progress

**Rollup:** 42%

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
- [ ] **CAT-002** INSIZE JSON-schema content fill (staging apply) — `todo` 15% | P1 | 20h | Sprint 02 — **DEFERRED**
  - Owner: unassigned | Week 3 Day 1 | Risk: med
  - [ ] Description: Resume content-only INSIZE enrichment with locked measurement schema; no inventing specs.
  - [x] Dependencies: CAT-001
  - [ ] Files: scripts/enrich_insize*.py
  - [ ] Modules: catalog, seo
  - [ ] Tags: insize, content
  - Acceptance Criteria:
    - [ ] ≥200 SKUs content QA
    - [ ] price_fields_written=none
  - Definition of Done:
    - [ ] SEO_PROGRESS note
  - Notes: DEFERRED per RELEASE_PLAN/EXEC; #90 kept open; #74 closed intentionally

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


## Evidence log
- [ ] Add links to PRs / GSC / Lighthouse here as you go
