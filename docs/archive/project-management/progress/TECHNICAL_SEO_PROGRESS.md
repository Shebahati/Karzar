# Technical SEO Progress

**Rollup:** 100%

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
  - Notes: #94 → main @a119b38; Deploy Staging green. Empty hubs hard-404; facet/private noindex; SITE_URL env; sitemap 6007 urls; hreflang N/A (fa-only). 2026-08-14: GSC root-canonical inheritance fix on `seo/gsc-remediation-2026-08` (local validated; not merged).

## Evidence log
- [ ] SEO-004 GSC canonical inheritance follow-up — branch `seo/gsc-remediation-2026-08` (2026-08-14); root layout no longer sets homepage canonical; local vitest/lint/typecheck/build green; merge/deploy pending
- [x] SEO-004 PR https://github.com/Shebahati/Karzar/pull/94 → `main` @a119b38; Deploy Staging https://github.com/Shebahati/Karzar/actions/runs/30247570716
- [x] Staging verify: `/robots.txt` allow+disallow; sitemap 6007 `<50k`; `/login` noindex; `/catalog?brand=1` noindex,follow + canonical `/catalog`; `/product/7115` 200
