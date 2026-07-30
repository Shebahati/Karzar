# SEO Progress

**Rollup:** 100%

- [x] **SEO-001** Ship Product/Offer/Breadcrumb JSON-LD on PDP+PLP — `done` 100% | P0 | 16h | Sprint 01
  - Owner: unassigned | Week 2 Day 1 | Risk: med
  - [x] Description: Complete structured data for products, offers, breadcrumbs, organization.
  - [x] Dependencies: PMO-001
  - [x] Files: frontend/Storefront/src/**
  - [x] Modules: seo, frontend
  - [x] Tags: seo, schema
  - Acceptance Criteria:
    - [x] Rich Results-ready schema verified on staging sample PDP (/product/7115 Offer+IRR)
    - [x] No invalid Offer without price
  - Definition of Done:
    - [x] Deployed staging
    - [x] Documented in STRUCTURED_DATA_PROGRESS
  - Notes: PDP Product+gated Offer+Breadcrumb; category CollectionPage/ItemList; root Organization+WebSite+SearchAction; vitest.
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
  - Notes: #102 → main @aa159b0; publish fixes #103/#104; Deploy Staging green (30255672560); `content/blog/articles.json` + CMS upsert; verified sample `/blog/digital-caliper-workshop-accuracy`.
- [x] **SEO-004** Technical SEO crawl hygiene — `done` 100% | P0 | 12h | Sprint 01
  - Owner: unassigned | Week 2 Day 2 | Risk: low
  - [x] Description: Canonicals, sitemap freshness, robots, hreflang if needed, indexation audit.
  - [x] Dependencies: SEO-001
  - [x] Files: frontend/Storefront/**, deploy/**
  - [x] Modules: seo, ops
  - [x] Tags: seo, tech
  - Acceptance Criteria:
    - [x] 0 soft-404 hubs
    - [x] Sitemap <50k urls valid
  - Definition of Done:
    - [x] TECHNICAL_SEO_PROGRESS
  - Notes: #94 → main @a119b38; Deploy Staging green; soft-404→404; facet/private noindex; sitemap 6007 urls; hreflang N/A.

## EPIC-1 Board wave (post-checkpoint — D14 / CR-008 C)

- [x] **SEO-005** EPIC-1.1–1.2 PDP slug + 301 — `done` 100% | P1 | Sprint 05 — #127
- [x] **SEO-006** EPIC-1.3 Cards/breadcrumbs/sitemap slug — `done` 100% | P1 | Sprint 05
- [x] **SEO-007** EPIC-1.4 JSON-LD slug `@id` — `done` 100% | P1 | Sprint 05
- [ ] **SEO-008** EPIC-1.5 Brand Hub `/brands/{slug}` — `todo` 15% | P1 | Sprint 05 — SPEC Proposed (`brand-hub-page-contract.md`); HC-01 Q1–Q5 open
- [x] **SEO-009** EPIC-1.8 Category Hub affirm — `done` 100% | P1 | Sprint 05

## Evidence log
- [x] SEO-004 PR https://github.com/Shebahati/Karzar/pull/94 + staging robots/sitemap/facet noindex
- [x] SEO-003 PR https://github.com/Shebahati/Karzar/pull/102 (+ #103/#104) + staging `/blog/digital-caliper-workshop-accuracy`
- [x] SEO-002 PR https://github.com/Shebahati/Karzar/pull/91 + staging hub `/categories/انواع-کولیس`
- [x] SEO-001 #88 + staging /product/7115
- [x] SEO-005 / SEO-006 / SEO-007 / SEO-009 registered 2026-07-30 (CR-008 C); Brand Hub open as SEO-008

- [x] CAT-002 INSIZE apply deferred (post-checkpoint); tooling candidate remains #90
