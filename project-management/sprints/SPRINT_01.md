# Sprint 01 — SEO foundation & PDP

**Focus:** Schema, hubs, tech SEO, PDP trust
**Target week index:** 2

## Goals
- [ ] Schema, hubs, tech SEO, PDP trust

## Tasks
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
  - Notes: PDP Product+gated Offer+Breadcrumb; category CollectionPage/ItemList; root Org+WebSite; vitest.
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
  - Notes: #94 → main @a119b38; Deploy Staging green; soft-404→404; facet/private noindex; sitemap 6007 urls
- [x] **UX-001** PLP filter + hub IA polish — `done` 100% | P1 | 20h | Sprint 01
  - Owner: unassigned | Week 2 Day 4 | Risk: low
  - [x] Description: Improve category PLP filters, empty states, mobile sheet clarity.
  - [x] Dependencies: —
  - [x] Files: frontend/Storefront/src/components/**
  - [x] Modules: frontend, ux
  - [x] Tags: ux
  - Acceptance Criteria:
    - [x] Mobile filter usable in <3 taps
    - [x] Empty states Persian
  - Definition of Done:
    - [x] UX_PROGRESS

- [x] **UX-002** PDP trust + specs presentation — `done` 100% | P0 | 16h | Sprint 01
  - Owner: unassigned | Week 2 Day 5 | Risk: low
  - [x] Description: Clarify short vs long description; specs SoT; no duplicate bullets.
  - [x] Dependencies: SEO-001
  - [x] Files: frontend/Storefront/src/components/product/**
  - [x] Modules: frontend, seo
  - [x] Tags: ux, pdp
  - Acceptance Criteria:
    - [x] Specs not duplicated in long desc
    - [x] Trust strip visible
  - Definition of Done:
    - [x] UX_PROGRESS
  - Notes: #96 → main @e8ea7bf; Deploy Staging green (30249086441). Trust strip (اصالت/گارانتی/بازگشت/ارسال); RTL specs table SoT; editorial dedup vs specs+short_description; JSON-LD preserved; vitest pdp-description+trust-strip.
- [x] **FE-001** Design system tokens + homepage consistency — `done` 100% | P2 | 12h | Sprint 01
  - Owner: unassigned | Week 2 Day 6 | Risk: low
  - [x] Description: Align home sections after hero/categories/why-karzar polish.
  - [x] Dependencies: CAT-003
  - [x] Files: frontend/Storefront/src/**
  - [x] Modules: frontend, design
  - [x] Tags: design
  - Acceptance Criteria:
    - [x] Shared tokens for spacing/type
    - [x] No purple-default AI look
  - Definition of Done:
    - [x] DESIGN_SYSTEM_PROGRESS
  - Notes: #85 why-karzar/categories; #93 floating header; FE-001 tokens home-stack

## Sprint exit checklist
- [ ] All P0 tasks in sprint done or explicitly moved with note in DECISIONS.md
- [ ] PROJECT_STATUS.md updated
- [ ] CHANGELOG.md entry