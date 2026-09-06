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
  - Notes: Ship Product (url + gallery images) + gated Offer (IRR / catalog `base_price`) + BreadcrumbList on PDP; CollectionPage+ItemList+Breadcrumb on `/categories/[slug]`; Organization+WebSite+SearchAction in root layout. Vitest `json-ld.test.ts`. No aggregateRating/reviews invented. LocalBusiness geo/hasMap follow-up tracked as **SEO-010**.

- [x] **SEO-010** Store LocalBusiness geo + Maps place on contact/footer/JSON-LD — `done` 100% | P0 | 4h | Sprint 01
  - Owner: unassigned | Week 2 Day 2 | Risk: low
  - [x] Description: Extend layout Organization with LocalBusiness + PostalAddress + GeoCoordinates + hasMap; align contact/footer store identity. (Was orphan «SEO-001 follow-up»; registered CR-013.)
  - [x] Dependencies: SEO-001
  - [x] Files: frontend/Storefront/src/lib/json-ld.ts, frontend/Storefront/src/lib/store-location.ts
  - [x] Modules: seo, frontend
  - [x] Tags: seo, schema, localbusiness
  - Acceptance Criteria:
    - [x] Organization JSON-LD includes LocalBusiness + geo + hasMap
    - [x] Contact/footer store identity SoT aligned (no invented hours)
  - Definition of Done:
    - [x] STRUCTURED_DATA_PROGRESS
    - [x] UX_PROGRESS evidence
  - Notes: #101 → main @1e8cd9b; `buildOrganizationNode` emits LocalBusiness + geo (35.6873, 51.40428) + hasMap. Later FE-003 redirected customer-facing map href to internal `/contact#store-address`.

## Evidence log
- [x] PR https://github.com/Shebahati/Karzar/pull/88
- [x] Staging sample PDP (priced): /product/7115 Product+Offer IRR
- [ ] Staging sample PDP (inquiry / null price) — Product without Offer (gate covered by vitest; null-price SKU scarce in first API page)
- [x] Category hub CollectionPage/ItemList shipped (SSR on /categories/[slug])
- [x] SEO-010 LocalBusiness geo/hasMap — PR https://github.com/Shebahati/Karzar/pull/101 → main @1e8cd9b
