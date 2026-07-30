# PMO / Product Changelog (living)

## 2026-07-30
- [x] **CR-004 residual B+C CLOSED** — `scripts/ingestion_boundary.py` fail-closed guard; deploy-staging sets Category B env for `publish_seo003_articles.py`; policy/SCRIPTS docs updated.
- [x] **Phase 4 / OI-GOV-05** — Backend CI job `aods` runs `aods_validate.py` (incl. openapi); `CR-012` CLOSED; minute `BOARD-MINUTE-AODS-PHASE4-CI.md`.
- [x] **CR-015 CLOSED** — quarantined `frontend/AI_CONTEXT.md` (Option A: stub + archive under `docs/archive/`).
- [x] **CR-007 CLOSED** — Option A: `progress/` + `sprints/` canonical; deleted 19 root twin files; living-PMO rule + GOV prompt updated.
- [x] **CR-004 CLOSED** — 18 scripts default to local API/asset base (ADR-012 Option A); `--gate ingestion-boundary` PASS; residual fail-closed/Category-B classify tracked as tech debt.
- [x] **CR-001 CLOSED** — Canon Lock on `main` via #125; registry `on_main` reconciled (53 docs); baseline CR-001 link findings removed.
- [x] **CR-012** Regenerated `openapi/v1.json` (81→82 paths; adds `/api/v1/products/slug/{slug}`); `--gate openapi` PASS; baseline entry removed; CI wiring still Phase-4.
- [x] **Skill** Added Cursor skill `karzar-aods-operator` (`.cursor/skills/karzar-aods-operator/SKILL.md`) — operating pack for Accepted AODS 1.0.0 + Canon Lock on main; refreshed `aods-auto-mode.mdc` CR-001 citation note.
- [x] **D9 / HC-14** Architecture Board **Accepted AODS in full** — ۸ مرداد ۱۴۰۵; signed **Mohammad Shebahati / محمد شباهتی**. Minute: `aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`. Pack headers + registry → **Accepted / 1.0.0**.
- [x] **AODS-001 → `done`** — PR [#128](https://github.com/Shebahati/Karzar/pull/128). Remaining: merge #125 (Canon Lock row / `CR-001`), then #128 to `main`.

## 2026-07-29
- [x] **AODS-001** AI-Orchestrated Development System designed and delivered under `aods/` — 19 required sections, 23 documents, 11 instantiated prompts, 3 machine-readable registries, and stdlib-only runnable validators. Initially shipped as **Proposed**; Board acceptance recorded 2026-07-30 (see above). Process-only: no application behaviour changed.
- [x] **Validation gates now exist and run** — `python3 aods/tools/aods_validate.py` (8 automatic gates: registry, links, pmo, prompts, graph, naming, openapi, ingestion-boundary; 2 contextual: citation, allowlist). Previously the repository had no validator of any kind.
- [x] **23 governance conflicts registered** in `aods/10-repository-intelligence/CONFLICT-REGISTER.md`, none silently resolved. 5 are BLOCKERs and are now mirrored in `BLOCKERS.md`; the rest feed `RISKS.md` (R9–R11) and `TECH_DEBT.md`.
- [x] **Three conflicts independently confirmed by tooling rather than by reading:** `CR-004` (18 scripts default to the production API, violating Accepted ADR-012), `CR-007` (6 divergent PMO ledger pairs), and `CR-012` — `openapi/v1.json` is missing `/api/v1/products/slug/{slug}`, live since #126 while the snapshot was last regenerated in #111. Two EPIC-1 PRs merged against a stale machine contract with nothing reporting it.
- [x] **`CR-023` opened** — two root-relative links in `docs/BACKEND_CHANGES.md` do not resolve; surfaced because the baseline writer refuses to record an unattributed suppression.
- [x] **31 findings baselined** as visible, owned, dated debt in `aods/registry/validation-baseline.json`. The file may only shrink without approval.
- [x] **Two Cursor rules added** — `aods-auto-mode.mdc` (always-on safety floor: forbidden context, no push/merge/deploy, cite-don't-infer, halt instead of guess) and `aods-node-execution.mdc` (rules for editing AODS itself). `pmo-living-system.mdc` left untouched.
- [x] **Independent accuracy pass on the pack itself** — every numeric and line-number claim re-verified against the repository. Corrected: 55→41 scripts, 58→62 unmerged branches, 78→79 PMO files, ~150→~140 markdown documents, two wrong line citations inside the `RESTATE` example, a gate name (`--gate ingestion`) that did not exist, and a missing prompt-lint rule. Logged in `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` §10 rather than fixed silently.
- [x] **`D9` opened in `DECISIONS.md`** — adopting AODS is a Board decision, not an agent decision.

## 2026-07-28
- [x] **PMO close pass** validated checkpoint-final PMO state against current SoT: only CAT-002 and KB-001 remain open and intentionally deferred
- [x] **Deferred governance hardened** for CAT-002/KB-001 across `tasks.json`, `PROJECT_STATUS.md`, `RELEASE_PLAN.md`, `DECISIONS.md`, `KANBAN_BOARD.md`, `BACKEND_PROGRESS.md`, and `KNOWLEDGE_BASE_PROGRESS.md` with explicit owner `PMO` + revisit date `2026-09-23`
- [x] **Portfolio status corrected** weighted progress updated to 85% (hours-weighted from `exports/tasks.json` progress values)

## 2026-07-27
- [x] **FE-001 follow-up** Separate page footer padding from section tokens — #117 → `main` @174718f (Deploy Staging 30282336447)
- [x] **FE-001** Design system tokens + homepage consistency — #115 → `main` @daa8abd; shared section spacing/type tokens + home-stack; steel/red (closes remaining after #93)
- [x] **TD-001** Pay down category depth/selectable FE drift — #114 → `main` @8cd01bd; depth 2|3 helpers + docs; no depth===3-only filters
- [x] **UX-001** PLP filter + hub IA polish — #113 → `main` @f4ec40b; mobile quick chips ≤3 taps; Persian empty states; hub child nav
- [x] **CAT-003** L1 category image coverage — #112 → `main` @fb7d628; helicoil roots 186–188 curated assets + seed URLs; all live L1 mapped
- [x] **BE-001** Catalog API SEO fields readiness — regenerated `openapi/v1.json` (short_description/meta_*/slug); contract tests green
- [x] **CAT-001** Close enrichment PR triage — #67 phase-A image docs → `main` @f51c9fd; #69 Dohre tooling → `main` @0829571 (Deploy Staging 30274744553); #70–#73 prior; #74 closed; **#90 INSIZE deferred with CAT-002**
- [x] **CAT-002** / **KB-001** explicitly deferred (post-31-Shahrivar / launch-bar) per RELEASE_PLAN + EXECUTIVE_SUMMARY; D7 recorded
- [x] **SEC-001** Security hygiene pass for go-live bar — admin `X-Robots-Tag` + layout noindex; secrets hygiene script green; FE key-material scan 0 hits; step-up PIN coverage inventoried; Pillow→12.3.0; residual ecdsa/Next advisories → RISKS R8
- [x] **REL-001** Release readiness for 31 Shahrivar checkpoint — scope freeze documented (P0 completed/deferred), explicit go/no-go gates, rollback plan, launch-window verification checklist, and residual risk ownership added across PMO artifacts.
- [x] **SEO-003** Publish 24 buyer-intent articles (calendar A01–D06) — #102 → `main` @aa159b0; publish fixes #103/#104; Deploy Staging green (30255672560); CMS `ok=24`; verified `/blog/digital-caliper-workshop-accuracy`
- [x] **SEO-001 follow-up** Store LocalBusiness geo + official Google Maps place on contact/footer/JSON-LD — (PR pending)
- [x] **PERF-001** Core Web Vitals foundations (fonts/LCP/image pipeline) — #99 → `main` @d169831; Deploy Staging green (30251144532)
- [x] **UX-002** PDP trust strip + specs SoT presentation — #96 → `main` @e8ea7bf; Deploy Staging green; verified `/product/2000` (trust+RTL specs) + `/product/7115` (trust+JSON-LD)
- [x] **OPS-001** Measurement promote workflow marked done in PMO — #81 → `main` @e1981b6 (merged 2026-07-26; Kanban sync)
- [x] **SEO-004** Technical crawl hygiene — #94 → `main` @a119b38; Deploy Staging green; robots/sitemap/SITE_URL; empty-hub 404; facet+private noindex; sitemap 6007 urls
- [x] **PMO-001** Living PMO bootstrap marked done (in active use since #86)
- [x] **FE-001** (partial) Floating transparent home header over full-bleed hero — #93 → `main` @53f0100; Deploy Staging green
- [x] Taxonomy «عمومی» padding leaves — #87 apply on staging: **23 categories deleted / 1970 products** remapped to L2 parents

## 2026-07-26
- [x] **SEO-002** Category hub intros + internal links (15 metrology/cutting hubs) — #91 → `main` @d92722a; Deploy Staging green; verified `/categories/انواع-کولیس`
- [x] **SEO-001** Storefront JSON-LD: Product + gated Offer + Breadcrumb (PDP); CollectionPage/ItemList (category hubs); Organization + WebSite + SearchAction (layout) — #88 → `main` @89a4cf5; Deploy Staging green; verified `/product/7115`
- [x] Merged to `main`: Measurement promote CI (#81); SAN OU (#73), Mitutoyo leaflets (#72), Dasqua 2025 (#71), Chumpower (#70) enrichment; Hesabfa stock clear asyncpg (#56); CI lint/test unlock for frontend-only PRs (#26); Living PMO (#86)
- [x] Staging deployed for the enrichment PRs above (#70–#73)
- [x] Skipped (not merged): phase-A images continue (#67, open), Dohre enrichment (#69, open), Insize 108A (#74, closed) — **superseded 2026-07-27:** #67/#69 merged; #90 deferred w/ CAT-002
- [x] Created living PMO under `project-management/`
- [x] Seeded tasks.json + import CSVs
- [x] Documented 31 Shahrivar realism assessment

## Prior (repo history — selected)
- [x] Homepage megamenu hero / categories / why-karzar waves
- [x] Metrology taxonomy promote + admin megamenu display flags
- [x] SEO short_description plumbing (#66/#68)
