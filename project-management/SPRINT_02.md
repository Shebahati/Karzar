# Sprint 02 — Content + CWV

**Focus:** Articles 1–12, performance
**Target week index:** 3

## Goals
- [ ] Articles 1–12, performance

## Tasks
- [ ] **SEO-003** Publish 24 buyer-intent articles (calendar) — `todo` 5% | P0 | 60h | Sprint 02
  - Owner: unassigned | Week 4 Day 1 | Risk: high
  - [ ] Description: One article per mid-tail cluster (کولیس دیجیتال, میکرومتر خارج‌سنج, …).
  - [x] Dependencies: SEO-002
  - [ ] Files: content/blog/**, frontend/Storefront/**
  - [ ] Modules: content, seo
  - [ ] Tags: content, seo
  - Acceptance Criteria:
    - [ ] 24 published
    - [ ] Each links ≥2 products
    - [ ] FAQ schema where fit
  - Definition of Done:
    - [ ] CONTENT_CALENDAR checked
    - [ ] Live
  - Notes: Quality > volume; AI-assisted draft + human QA
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
- [ ] **PERF-001** Core Web Vitals pass on home+PDP+PLP — `todo` 25% | P0 | 24h | Sprint 02
  - Owner: unassigned | Week 3 Day 3 | Risk: med
  - [ ] Description: LCP/INP/CLS budgets; image priority; font subsetting.
  - [ ] Dependencies: —
  - [ ] Files: frontend/Storefront/**
  - [ ] Modules: frontend, perf
  - [ ] Tags: perf, cwv
  - Acceptance Criteria:
    - [ ] LCP≤2.5s mobile field or lab p75
    - [ ] CLS≤0.1
  - Definition of Done:
    - [ ] CORE_WEB_VITALS_PROGRESS

## Sprint exit checklist
- [ ] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [ ] PROJECT_STATUS.md updated
- [ ] CHANGELOG.md entry