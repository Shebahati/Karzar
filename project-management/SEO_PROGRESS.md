# SEO Progress

**Rollup:** 42%

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
- [ ] **SEO-004** Technical SEO crawl hygiene — `todo` 30% | P0 | 12h | Sprint 01
  - Owner: unassigned | Week 2 Day 2 | Risk: low
  - [ ] Description: Canonicals, sitemap freshness, robots, hreflang if needed, indexation audit.
  - [ ] Dependencies: SEO-001
  - [ ] Files: frontend/Storefront/**, deploy/**
  - [ ] Modules: seo, ops
  - [ ] Tags: seo, tech
  - Acceptance Criteria:
    - [ ] 0 soft-404 hubs
    - [ ] Sitemap <50k urls valid
  - Definition of Done:
    - [ ] TECHNICAL_SEO_PROGRESS

## Evidence log
- [x] SEO-002 PR https://github.com/Shebahati/Karzar/pull/91 + staging hub `/categories/انواع-کولیس`
- [x] SEO-001 #88 + staging /product/7115
