# UI Progress

**Rollup:** 58%

- [x] **CAT-003** Category image coverage for all L1+key L2 — `done` 100% | P1 | 10h | Sprint 00
  - Owner: unassigned | Week 1 Day 3 | Risk: low
  - [x] Description: Ensure every homepage/megamenu root has full-bleed quality image.
  - [x] Dependencies: —
  - [x] Files: scripts/seed_category_images.py, frontend/Storefront/public/images/**
  - [x] Modules: frontend, catalog
  - [x] Tags: ui, images
  - Acceptance Criteria:
    - [x] 0 L1 without image
    - [x] Visual QA mobile
  - Definition of Done:
    - [x] UI_PROGRESS
  - Notes: Helicoil L1 186–188 curated; prior L1 map via #85; seed script ready for API image_url on metrology+helicoil; key L2 optional.

- [ ] **FE-001** Design system tokens + homepage consistency — `in_progress` 65% | P2 | 12h | Sprint 01
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
  - Notes: #85 why-karzar/categories; floating transparent home header over hero (#93 → main @53f0100)

## Evidence log
- [x] Floating home header / full-bleed hero polish — #93 → `main` @53f0100 (staging deployed)
- [ ] Add links to PRs / GSC / Lighthouse here as you go
