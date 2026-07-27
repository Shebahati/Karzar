# Content Progress

**Rollup:** 100%

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
  - Notes: #102 → main @aa159b0; publish fixes #103/#104; Deploy Staging green (30255672560); 24 CMS articles; verified `/blog/digital-caliper-workshop-accuracy`.

- [x] **CONTENT-URL-001** Remove non-Karzar website references from storefront content/images — `done` 100% | P0 | 6h | Sprint 04
  - Owner: unassigned | Week 4 Day 2 | Risk: med
  - [x] Description: Purge external website mentions from customer-facing content, replace third-party image links with local assets, and remove external footer/contact website links.
  - [x] Dependencies: SEO-003
  - [x] Files: frontend/Storefront/content/**, frontend/Storefront/src/**, frontend/Storefront/public/images/placeholders/**
  - [x] Modules: content, ui
  - [x] Tags: content, ux, compliance
  - Acceptance Criteria:
    - [x] No non-Karzar website references in storefront content payloads
    - [x] All customer-visible article/about images served from local assets
    - [x] Contact/footer external website links removed
  - Definition of Done:
    - [x] CONTENT_PROGRESS updated
    - [x] CHANGELOG updated
  - Notes: Local placeholder assets added for article/about/map visuals; Google Maps and Enamad external links removed from customer-visible footer/contact surface; removed www.craftsman.com mark from categories/drills.jpg.

## Evidence log
- [x] SEO-002 PR https://github.com/Shebahati/Karzar/pull/91 — 15 hubs live
- [x] SEO-003 PR https://github.com/Shebahati/Karzar/pull/102 (+ #103/#104) — 24 articles live
- [x] CONTENT-URL-001 cleanup PR pending — non-Karzar website references removed from storefront content/UI surface
