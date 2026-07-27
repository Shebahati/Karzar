# Sprint 02 — Content + CWV

**Focus:** Articles 1–12, performance
**Target week index:** 3

## Goals
- [x] Articles 1–12 (SEO-003 full calendar A–D = 24)
- [x] Performance (PERF-001)

## Tasks
- [x] **SEO-003** Publish 24 buyer-intent articles (calendar) — `done` 100% | P0 | 60h | Sprint 02
  - Owner: unassigned | Week 4 Day 1 | Risk: high
  - [x] Description: One article per mid-tail cluster (کولیس دیجیتال, میکرومتر خارج‌سنج, …).
  - [x] Dependencies: SEO-002
  - [x] Files: content/blog/**, frontend/Storefront/**
  - [x] Modules: content, seo
  - [x] Tags: content, seo
  - Acceptance Criteria:
    - [x] 24 published
    - [x] Each links ≥2 products
    - [x] FAQ schema where fit
  - Definition of Done:
    - [x] CONTENT_CALENDAR checked
    - [x] Live
  - Notes: #102 → main @aa159b0; publish fixes #103/#104; Deploy Staging green (30255672560); 24 CMS articles live.
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
- [x] **PERF-001** Core Web Vitals pass on home+PDP+PLP — `done` 100% | P0 | 24h | Sprint 02
  - Owner: unassigned | Week 3 Day 3 | Risk: med
  - [x] Description: LCP/INP/CLS budgets; image priority; font subsetting.
  - [x] Dependencies: —
  - [x] Files: frontend/Storefront/**
  - [x] Modules: frontend, perf
  - [x] Tags: perf, cwv
  - Acceptance Criteria:
    - [x] LCP≤2.5s mobile field or lab p75
    - [x] CLS≤0.1
  - Definition of Done:
    - [x] CORE_WEB_VITALS_PROGRESS
  - Notes: #99 → main @d169831; Deploy Staging green (30251144532). next/font IRANYekanX 400/500/700 subset+preload; LCP image props on hero#0, PDP gallery, first PLP/home cards; AVIF/WebP; vitest cwv.

## Sprint exit checklist
- [x] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [x] PROJECT_STATUS.md updated
- [x] CHANGELOG.md entry
