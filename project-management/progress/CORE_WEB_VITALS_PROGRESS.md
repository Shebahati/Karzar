# Core Web Vitals Progress

**Rollup:** 100%

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

## Evidence log
- [x] PERF-001 PR https://github.com/Shebahati/Karzar/pull/99 → main @d169831; Deploy Staging green (30251144532)
- [ ] Field p75 / GSC CWV monitor ongoing after foundations land
