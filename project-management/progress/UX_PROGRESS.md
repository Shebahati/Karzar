# UX Progress

**Rollup:** 70%

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

## Evidence log
- [x] UX-002 PR https://github.com/Shebahati/Karzar/pull/96 → main @e8ea7bf; Deploy Staging green; verified /product/2000 (trust+specs) + /product/7115 (trust+JSON-LD)
- [ ] Contact/footer official Google Maps place (KarZar Tools) — PR pending; address SoT unchanged (پاساژ فجر ۱۰۸)
- [ ] Add links to PRs / GSC / Lighthouse here as you go
