# Structured Data Progress

**Rollup:** 100%

- [x] **SEO-001** Ship Product/Offer/Breadcrumb JSON-LD on PDP+PLP — `done` 100% | P0 | 16h | Sprint 01
  - Owner: unassigned | Week 2 Day 1 | Risk: med
  - [x] Description: Complete structured data for products, offers, breadcrumbs, organization.
  - [x] Dependencies: PMO-001
  - [x] Files: frontend/Storefront/src/** (FE schema emission; no enrichment API price writes)
  - [x] Modules: seo, frontend
  - [x] Tags: seo, schema
  - Acceptance Criteria:
    - [x] Rich Results-ready schema verified on staging sample PDP (/product/7115 Offer+IRR)
    - [x] No invalid Offer without price (Offer gated on present `base_price`; inquiry → Product+Breadcrumb only)
  - Definition of Done:
    - [x] Deployed staging
    - [x] Documented in STRUCTURED_DATA_PROGRESS
  - Notes: Ship Product (url + gallery images) + gated Offer (IRR / catalog `base_price`) + BreadcrumbList on PDP; CollectionPage+ItemList+Breadcrumb on `/categories/[slug]`; Organization+WebSite+SearchAction in root layout. Vitest `json-ld.test.ts`. No aggregateRating/reviews invented.

## Evidence log
- [x] PR https://github.com/Shebahati/Karzar/pull/88
- [x] Staging sample PDP (priced): /product/7115 Product+Offer IRR
- [ ] Staging sample PDP (inquiry / null price) — Product without Offer (gate covered by vitest; null-price SKU scarce in first API page)
- [x] Category hub CollectionPage/ItemList shipped (SSR on /categories/[slug])
