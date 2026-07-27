# PMO / Product Changelog (living)

## 2026-07-27
- [x] **UX-001** PLP filter + hub IA polish — mobile quick chips ≤3 taps; Persian empty states; hub child nav
- [x] **CAT-003** L1 category image coverage — helicoil roots 186–188 curated assets + seed URLs; all live L1 mapped
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
