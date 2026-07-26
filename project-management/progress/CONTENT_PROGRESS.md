# Content Progress

**Rollup:** 32%

- [x] **SEO-002** Category hub content + internal linking for mid-tail — `done` 100% | P0 | 24h | Sprint 01
  - Owner: unassigned | Week 2 Day 3 | Risk: med
  - [x] Description: Write hub intros for L1/L2 metrology+cutting; link to leaves and guides.
  - [x] Dependencies: SEO-001
  - [x] Files: frontend/Storefront/src/components/category/**, content/**
  - [x] Modules: seo, content
  - [x] Tags: seo, content
  - Acceptance Criteria:
    - [x] Top 15 hubs have unique 150–300w intro
    - [x] Internal links ≥3 per hub
  - Definition of Done:
    - [x] Live
    - [x] CONTENT_PROGRESS updated
  - Notes: #91 → main @d92722a; Deploy Staging green; `content/hubs/intros.json` + CategoryHubIntro; verified `/categories/انواع-کولیس`.

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

## Evidence log
- [x] SEO-002 PR https://github.com/Shebahati/Karzar/pull/91 — 15 hubs live
- [ ] Add links to PRs / GSC / Lighthouse here as you go
