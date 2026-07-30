# Project Status

**Updated:** 2026-07-30  
**Weighted progress:** 86%  
**Checkpoint:** 2026-09-22

## Overall
- [x] Site live on karzartools.com (staging≈prod VPS)
- [x] Homepage hero + categories + why-karzar polish waves
- [x] Metrology L1 reshape (56/81/87) + megamenu-only label
- [x] Admin categories/megamenu unified (#85)
- [x] Remove padding «عمومی» L3 leaves — #87; staging apply **23 cats / 1970 products**
- [x] Catalog enrichment tooling on `main` + staging: #70 Chumpower, #71 Dasqua, #72 Mitutoyo, #73 SAN OU, #69 Dohre (0-SKU tooling)
- [x] Ops/CI on `main`: **OPS-001** #81 Measurement promote workflow, #56 Hesabfa stock clear asyncpg, #26 frontend-only CI unlock
- [x] Living PMO (#86 → main; PMO-001 done)
- [x] SEO-001 Product/Offer/Breadcrumb JSON-LD (#88 → main, staging deployed)
- [x] SEO-002 Hub intros + internal links (#91 → main @d92722a, staging deployed)
- [x] SEO-004 Technical crawl hygiene (#94 → main @a119b38, staging deployed)
- [x] UX-002 PDP trust + specs presentation (#96 → main @e8ea7bf, staging deployed)
- [x] PERF-001 Core Web Vitals foundations home+PDP+PLP (#99 → main @d169831, staging deployed)
- [x] SEO-003 24 buyer-intent articles (#102 → main @aa159b0; publish #103/#104; staging deployed)
- [x] FE-001 Design system tokens + homepage consistency (#115 @daa8abd + #117 @174718f; builds on #93 header)
- [x] 24 mid-tail articles
- [x] CWV budgets green (PERF-001 foundations; field p75 monitor ongoing)
- [x] 31 Shahrivar release freeze package documented (REL-001)
- [x] SEC-001 Security hygiene pass (admin X-Robots-Tag, secrets audit, step-up inventory, dep scan)
- [x] CAT-001 enrichment PR triage closed (#67/#69 decided+merged; #90 deferred w/ CAT-002)
- [x] BE-001 Catalog API SEO fields readiness (openapi snapshot + contract tests)
- [x] UX-001 PLP filter + hub IA polish (#113 → main @f4ec40b)
- [x] TD-001 Category depth/selectable FE drift (#114 → main @8cd01bd)
- [x] CAT-003 L1 category image coverage (#112 → main @fb7d628)
- [x] FE-001 follow-up homepage padding (#117 → main @174718f)
- [x] **AODS-001** AI-Orchestrated Development System **Accepted** ۱.۰.۰ — Board minute ۸ مرداد ۱۴۰۵ (Mohammad Shebahati); PR #128
- [x] **CR-008 / D14** EPIC-1 ↔ PMO join (Option C) — tasks `SEO-005`…`SEO-009`, `BE-002`, `FE-002`; see `sprints/SPRINT_05.md`

## By stream
- [x] PMO bootstrap (#86 → main)
- [x] SEO — see `SEO_PROGRESS.md` (001–004 checkpoint done; EPIC-1 SEO-005…009 in Sprint 05)
- [x] Content — see `CONTENT_PROGRESS.md` (SEO-002/003 done)
- [x] UX/UI — see `UX_PROGRESS.md` / `UI_PROGRESS.md` (UX-001/002 + FE-001 done; FE-002 open)
- [x] Performance — see `CORE_WEB_VITALS_PROGRESS.md` (PERF-001 done)
- [x] Security — see `SECURITY_PROGRESS.md` (SEC-001 done; residual dep advisories R8)
- [x] Catalog enrichment triage (CAT-001) closed; CAT-002 INSIZE deferred — see `BACKEND_PROGRESS.md`
- [x] Explicitly deferred: CAT-002 (#90 open), KB-001 (post-31-Shahrivar); #74 Insize 108A closed
- [x] Deferred ownership locked at checkpoint close (2026-07-28): CAT-002/KB-001 owner = PMO, revisit date = 2026-09-23
- [x] Process governance — AODS Accepted (D9); see `aods/`
- [x] Backend EPIC-1 brand meta — **BE-002** done (#126); see `BACKEND_PROGRESS.md`

## Active sprint
See `sprints/SPRINT_04.md` (checkpoint freeze) and `sprints/SPRINT_05.md` (EPIC-1 Board wave post-checkpoint). Checkpoint PMO: **operationally complete**. Open Board-wave: **SEO-008**, **FE-002**. Checkpoint deferrals: CAT-002 / KB-001 (revisit 2026-09-23).

## Process governance (AODS-001)
Repository process is governed by `aods/` — **Accepted 1.0.0** (۸ مرداد ۱۴۰۵ / 2026-07-30, Mohammad Shebahati).
Minute: `aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`. Decision **D9** closed.
Phase 4 CI: Backend CI job `aods` (**D12** / `OI-GOV-05`); minute `BOARD-MINUTE-AODS-PHASE4-CI.md`.
Protect main requires `lint`+`test`+`aods` (**D13** / `OI-GOV-02` CLOSED).
Runnable gates: `python3 aods/tools/aods_validate.py`. Conflicts: `aods/10-repository-intelligence/CONFLICT-REGISTER.md`
(CR-001/002/003/004/007/008/009/010/011/012/015/021/023 closed among others; open BLOCKERs: 0).

## Blockers
See `BLOCKERS.md`

## Risks
See `RISKS.md`
