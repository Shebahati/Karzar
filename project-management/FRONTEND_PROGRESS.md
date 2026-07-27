# Frontend Progress

**Rollup:** 39%

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
- [ ] **PERF-001** Core Web Vitals pass on home+PDP+PLP — `todo` 25% | P0 | 24h | Sprint 02
  - Owner: unassigned | Week 3 Day 3 | Risk: med
  - [ ] Description: LCP/INP/CLS budgets; image priority; font subsetting.
  - [ ] Dependencies: —
  - [ ] Files: frontend/Storefront/**
  - [ ] Modules: frontend, perf
  - [ ] Tags: perf, cwv
  - Acceptance Criteria:
    - [ ] LCP≤2.5s mobile field or lab p75
    - [ ] CLS≤0.1
  - Definition of Done:
    - [ ] CORE_WEB_VITALS_PROGRESS
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

## Evidence log
- [ ] Add links to PRs / GSC / Lighthouse here as you go
