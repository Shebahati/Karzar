# Frontend Progress

**Rollup:** 55%

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
- [x] **PERF-001** Core Web Vitals pass on home+PDP+PLP — `done` 100% | P0 | 24h | Sprint 02
  - Owner: unassigned | Week 3 Day 3 | Risk: med
  - [x] Description: LCP/INP/CLS budgets; image priority; font subsetting.
  - [x] Dependencies: —
  - [x] Files: frontend/Storefront/**
  - [x] Modules: frontend, perf
  - [x] Tags: perf, cwv
  - Acceptance Criteria:
    - [x] LCP≤2.5s mobile field or lab p75
    - [x] CLS≤0.1
  - Definition of Done:
    - [x] CORE_WEB_VITALS_PROGRESS
  - Notes: #99 → main @d169831; Deploy Staging green (30251144532). next/font IRANYekanX 400/500/700 subset+preload; LCP image props on hero#0, PDP gallery, first PLP/home cards; AVIF/WebP; vitest cwv.
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

## Evidence log
- [x] PERF-001 PR https://github.com/Shebahati/Karzar/pull/99 → main @d169831; Deploy Staging green (30251144532)
- [ ] Add links to PRs / GSC / Lighthouse here as you go
