# Sprint 01 — SEO foundation & PDP

**Focus:** Schema, hubs, tech SEO, PDP trust
**Target week index:** 2

## Goals
- [ ] Schema, hubs, tech SEO, PDP trust

## Tasks
- [ ] **SEO-001** Ship Product/Offer/Breadcrumb JSON-LD on PDP+PLP — `in_progress` 90% | P0 | 16h | Sprint 01
  - Owner: unassigned | Week 2 Day 1 | Risk: med
  - [x] Description: Complete structured data for products, offers, breadcrumbs, organization.
  - [x] Dependencies: PMO-001
  - [x] Files: frontend/Storefront/src/**
  - [x] Modules: seo, frontend
  - [x] Tags: seo, schema
  - Acceptance Criteria:
    - [ ] Rich Results test passes for sample PDPs (pending staging)
    - [x] No invalid Offer without price
  - Definition of Done:
    - [ ] Deployed staging
    - [x] Documented in STRUCTURED_DATA_PROGRESS
  - Notes: PDP Product+gated Offer+Breadcrumb; category CollectionPage/ItemList; root Org+WebSite; vitest.
- [ ] **SEO-002** Category hub content + internal linking for mid-tail — `todo` 0% | P0 | 24h | Sprint 01
  - Owner: unassigned | Week 2 Day 3 | Risk: med
  - [ ] Description: Write hub intros for L1/L2 metrology+cutting; link to leaves and guides.
  - [ ] Dependencies: SEO-001
  - [ ] Files: frontend/Storefront/src/components/category/**, content/**
  - [ ] Modules: seo, content
  - [ ] Tags: seo, content
  - Acceptance Criteria:
    - [ ] Top 15 hubs have unique 150–300w intro
    - [ ] Internal links ≥3 per hub
  - Definition of Done:
    - [ ] Live
    - [ ] CONTENT_PROGRESS updated
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
- [ ] **UX-001** PLP filter + hub IA polish — `todo` 35% | P1 | 20h | Sprint 01
  - Owner: unassigned | Week 2 Day 4 | Risk: low
  - [ ] Description: Improve category PLP filters, empty states, mobile sheet clarity.
  - [ ] Dependencies: —
  - [ ] Files: frontend/Storefront/src/components/**
  - [ ] Modules: frontend, ux
  - [ ] Tags: ux
  - Acceptance Criteria:
    - [ ] Mobile filter usable in <3 taps
    - [ ] Empty states Persian
  - Definition of Done:
    - [ ] UX_PROGRESS
- [ ] **UX-002** PDP trust + specs presentation — `todo` 40% | P0 | 16h | Sprint 01
  - Owner: unassigned | Week 2 Day 5 | Risk: low
  - [ ] Description: Clarify short vs long description; specs SoT; no duplicate bullets.
  - [ ] Dependencies: SEO-001
  - [ ] Files: frontend/Storefront/src/components/product/**
  - [ ] Modules: frontend, seo
  - [ ] Tags: ux, pdp
  - Acceptance Criteria:
    - [ ] Specs not duplicated in long desc
    - [ ] Trust strip visible
  - Definition of Done:
    - [ ] UX_PROGRESS
  - Notes: Policy locked earlier
- [ ] **FE-001** Design system tokens + homepage consistency — `todo` 55% | P2 | 12h | Sprint 01
  - Owner: unassigned | Week 2 Day 6 | Risk: low
  - [ ] Description: Align home sections after hero/categories/why-karzar polish.
  - [ ] Dependencies: CAT-003
  - [ ] Files: frontend/Storefront/src/**
  - [ ] Modules: frontend, design
  - [ ] Tags: design
  - Acceptance Criteria:
    - [ ] Shared tokens for spacing/type
    - [ ] No purple-default AI look
  - Definition of Done:
    - [ ] DESIGN_SYSTEM_PROGRESS
  - Notes: #85 why-karzar/categories

## Sprint exit checklist
- [ ] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [ ] PROJECT_STATUS.md updated
- [ ] CHANGELOG.md entry