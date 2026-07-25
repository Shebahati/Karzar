# Phase — Documentation / Technical Writing Audit (v2)

**Date:** 2026-07-25 · **Auditors:** Documentation/Technical-Writing audit team (strict v2)
**Scope:** Entire documentation corpus of the `Shebahati/Karzar` monorepo — root `README.md`, `SECURITY.md`, all of `docs/`, `openapi/v1.json`, `frontend/` root docs, `frontend/docs/**`, per-app READMEs/AGENTS files, `.env.example` files, workflow YAMLs as documentation, and the v1 audit reports themselves.
**Posture:** Hostile due-diligence. Every significant doc claim verified against code (`app/`, `alembic/`, `scripts/`, `deploy/`, `.github/workflows/`, both frontends). Unverifiable marketing claims contradicted by evidence are treated as documentation defects.

---

## 1. Scope & method

- **Ground truth built first, docs judged second.** The live route table was reconstructed from every `@router.*` decorator in `app/api/endpoints/*` plus `app/api/v1/__init__.py`; the settings surface from `app/core/config.py` (≈70 settings); test count from `pytest --collect-only -q` → **242 tests collected** (36 files incl. `conftest.py`); coverage gate from `.github/workflows/backend-ci.yml:170` (`--cov-fail-under=62`).
- **Endpoint-by-endpoint spot check:** 20+ documented endpoints traced to code (products stock/availability, cart, orders, payments, hesabfa, cms nav-groups, auth OTP/refresh, categories tree/image, brands logo).
- **Snapshot diffing:** `openapi/v1.json` (71 paths, last committed 2026-07-18, `335a1cb`) diffed against the live router set.
- **Staleness evidence:** `git log -1` per doc file (backend repo at `backend/.git`, branch `docs/engineering-audit-2026-07`).
- **Spot-checks of claim-heavy docs:** 8 items of `frontend/BACKEND_NON_COMPLIANCE.md` re-tested against current code; the cookie contract verified against `app/core/auth_cookies.py`, `frontend/Storefront/src/lib/api-client.ts`, `frontend/admin-panel/src/middleware.ts`.
- **Read-only:** no file modified except this report.

Notation: line references are to the files as of commit `66e9ae9` (+ untracked `docs/audits/v2/`).

---

## 2. Drift matrix (one row per doc file)

Verdicts: **accurate** · **minor drift** · **major drift** · **aspirational-mislabeled** (plan/spec presented as, or readable as, current state) · **obsolete** (superseded snapshot not marked as such).

| # | File | Verdict | Worst drift found | Last-updated evidence |
|---|------|---------|-------------------|----------------------|
| 1 | `README.md` (559 ln) | **major drift** | Documents `POST /cart/items` + `PATCH /cart/items/{id}` — neither exists (real: `PUT /items`, `DELETE /items/{id}`, `cart.py:75,100`); "Real-time inventory tracking" contradicts binary-availability decision; stock example `"stock_quantity": "50"` vs hardwired `"0"`; category tree shape wrong; env-table defaults wrong; fictional project tree | git 2026-07-24 (`741ebd9`); footer self-claims "Last Updated 2026-07-12" — footer not maintained |
| 2 | `SECURITY.md` | **accurate** | None material — policy-only, no code claims; "acknowledge within 7 days" is an unverifiable aspiration for a 2-person team | 2026-07-24 `741ebd9` |
| 3 | `docs/API_CONTRACT.md` | **minor drift** | Endpoint map omits Hesabfa module entirely (`/api/v1/hesabfa/*`, 5 routes live since `app/api/v1/__init__.py:36`); links stale `openapi/v1.json` as typegen source; row "Products … CRUD, stock" doesn't flag stock as deprecated | 2026-07-18 `335a1cb` |
| 4 | `docs/API_CHANGELOG.md` | **accurate** (minor) | "160+ tests" (P5 era) now 242 — historical entry, acceptable; missing entries for post-18-Jul additions (nav-groups #51, availability endpoint, hesabfa admin-reads clear #55) — the changelog's own rule "new endpoint = record here" was not followed | 2026-07-19 `85ee42d` |
| 5 | `openapi/v1.json` | **major drift** (stale snapshot) | 71 paths; missing all 5 `/hesabfa/*` routes, `/cms/nav-groups` (GET/PUT), public `/nav-groups/`, `PUT /products/{id}/availability`, `POST /categories/{id}/image`, `POST /brands/{id}/logo` | 2026-07-18 `335a1cb` |
| 6 | `docs/ARCHITECTURE.md` | **accurate** | Self-dated 2026-07-18, honestly labels shims and refactor state (R0–R2 + partial R3); layout matches `app/` census | 2026-07-18 `8eebd79` |
| 7 | `docs/OPERATIONS.md` | **minor drift** | Dead link: restore-drill results to `docs/roadmap/phase-0-execution-log.md` (`OPERATIONS.md:159`) — `docs/roadmap/` does not exist; rest verified (backup scripts, compose files, coverage gate, Hesabfa policy all match) | 2026-07-25 `6999ae9` |
| 8 | `docs/GO_LIVE_EXECUTION_PLAN.md` | **major drift** (frozen "living doc") | §3 readiness matrix still says Catalog 25% "import انبوه نشده", DevOps 40% "deploy نشده", Integrations 15%, "وضعیت فعلی: بین L0 و L1" — while the site is live at karzartools.com with ~5,900 imported products and CI/CD; doc's own footer (ln 528) demands updates per phase | 2026-07-24 `2e4ff0d` (content body still 2026-07-14) |
| 9 | `docs/HESABFA.md` | **accurate** | Fully matches post-#55 code: admin-reads disabled (`config.py:80`), `/stock/sync` no-op (`hesabfa.py:115-131`), sales-summary website-only (`hesabfa.py:134-154`), item push qty 0 | 2026-07-25 `6999ae9` |
| 10 | `docs/TESTING.md` | **minor drift** | "Test layout" table lists 8 of 33 test files (P5-era snapshot); 62% gate, markers, Postgres/Redis CI setup all verified against `backend-ci.yml` | 2026-07-12 `1a5557c` |
| 11 | `docs/SEED_IMPORT.md` | **minor drift** | "Product images are **URL-based** (no multipart upload storage)" (ln 47) — multipart upload implemented (`products_images.py:60`, `category.py:154`, `brand.py:148`) with uploads volume documented in OPERATIONS; scripts table lists 8 of ~35 scripts (crawlers/import pipeline undocumented) | 2026-07-12 `437cb8c` |
| 12 | `docs/BACKEND_CHANGES.md` | **obsolete** (unmarked snapshot) | "Images are URL-based only (no blob storage)" (ln 59); "160 passed, 2 skipped" (ln 96) vs 242 collected; README still indexes it as "Recent backend deltas" | 2026-07-18 `8eebd79` |
| 13 | `docs/LOCAL_DEV_FRONTEND.md` | **minor drift** | `NEXT_PUBLIC_API_URL` (ln 63) — the frontends read **`NEXT_PUBLIC_API_BASE_URL`** (`Storefront/src/config/env.ts:11`, `admin-panel/src/config/env.ts:10`); seed product "stock 100" vs `startup.py:101` seeding `stock_quantity=0`; ships the same literal PIN as `.env.example` | 2026-07-10 `5527d8d` |
| 14 | `docs/COLLABORATOR_DEPLOY.md` | **accurate** | Honest about "staging = live VPS (karzartools.com)", production not split, manual-only production dispatch — all match workflow YAMLs | 2026-07-24 `741ebd9` |
| 15 | `docs/CATALOG_IMAGES_PLAN.md` | **accurate** (current plan) | Live-DB numbers dated 2026-07-25; matching scripts exist (`materialize_product_images.py`, crawlers) | 2026-07-25 `a328fae` |
| 16 | `docs/FRONTEND_HANDOVER.md` | **minor drift** | PDP field list still advertises `low_stock` semantics (always `false` in presenter, `product_presenter.py:151`); tree-shape guidance correct | 2026-07-18 era |
| 17 | `docs/FRONTEND_IMPLEMENTATION_GUIDE.md` | **major drift** (self-declared SoT, stale) | Declares itself "منبع اصلی کار فرانت" with precedence over other docs, yet readiness matrix frozen at 2026-07-13 (Storefront↔API 55%, OTP bug open — fixed 2026-07-17 per `INTEGRATION_RUNTIME_NOTES.md`); "1–2 هفته تا demo" timelines long overtaken | 2026-07-13 era |
| 18 | `docs/FRONTEND_INTEGRATION.md` | **minor drift** | `low_stock`: "true when quantity < 10" and `availability` = "is_active && stock_quantity > 0" (ln 95–96) — actual: `low_stock=False` always, availability from `is_available` flag (`crud/product.py:332-341`); tree raw-array guidance correct | 2026-07-18 era |
| 19 | `docs/BACKEND_STRUCTURE_REFACTOR_MAP.md` | **accurate** (status labeled) | Header states R0–R2 done, R3 partial, R4 deferred — matches ARCHITECTURE.md and `app/` layout | 2026-07-18 |
| 20 | `docs/BACKEND_COMPREHENSIVE_AUDIT_PLAYBOOK.md` | **accurate** (process doc) | Self-labeled status tracker (A–H PASS, B PARTIAL); no code-contradicting claims found | 2026-07-18 |
| 21–23 | `docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` | **aspirational — correctly labeled** | Explicit "Design only. No production code"; one cross-doc tension: declares image import "paused… reopen only after you say so" while `CATALOG_IMAGES_PLAN.md` (2026-07-25) is actively executing image import | 2026-07-22 |
| 24 | `frontend/AI_CONTEXT.md` (1,044 ln) | **major drift / partially obsolete** | Claims fresh update (۱۴۰۵/۰۵/۰۲ ≈ 2026-07-24) yet body asserts: SQLAdmin at `/admin` (removed — zero references in `requirements.txt`/`app/main.py`), "بدون refresh token" (refresh rotation live, `auth.py:230`), checkout/OTP/blog/hero/contact/comments/related "❌ ندارد" (all exist), brand delete "بدون step-up" (requires step-up, `brand.py:176`), 5 migrations head `f1a2b3c4d5e6` (24 revisions), admin orders/customers/reports "ComingSoon" (implemented), references nonexistent `RUN_GUIDE_FA.md` + PowerShell scripts + `V1/` root | Only §21 (remediation log) is current |
| 25 | `frontend/BACKEND_HANDOFF.md` | **obsolete** (requests since fulfilled) | §2 timeline/logistics, §3 is_deleted+restore, §6 multipart — all implemented; kept without a "resolved" banner | 2026-07-11 era |
| 26 | `frontend/BACKEND_NON_COMPLIANCE.md` (647 ln) | **major drift / obsolete** | Spot-check of 8 headline gaps: 7 now implemented (quote endpoint `order.py:329`; PATCH status logistics `schemas/order.py:61-69`; tracking `timeline` `schemas/order.py:53`; `is_deleted` filter `products_catalog.py:75`; customer note/category/tags `user_admin.py:33-35`; `mode`/`customer_phone` filters `order.py:169-183`; multipart images `products_images.py:60`). Doc's own closing rule "هر تغییر API باید در این فایل به‌روز شود" never honored. Still-open items (settings/store, reports/summary, invoice PDF) indistinguishable from resolved ones | 2026-07-11 (header) |
| 27 | `frontend/FRONTEND_CHANGES.md` | **accurate** (dated changelog) | Honest, including "backend unreachable — E2E blocked" caveat | 2026-07-17 |
| 28 | `frontend/INTEGRATION_RUNTIME_NOTES.md` | **accurate** (dated log) | §4 "known gaps" partially stale (slug/reports still open — true; documents page still mock — true) | 2026-07-17 |
| 29 | `frontend/LOCAL_STACK_ACCESS.md` | **accurate** | No credential leaks — points to local `.env` instead of embedding secrets; correct env var name | — |
| 30 | `frontend/README.md` | **accurate** | Doc index links all resolve; remediation phases match `frontend/docs/audits` + app READMEs | post-remediation |
| 31 | `frontend/docs/auth-cookie-httponly-contract.md` | **accurate** | Cookie names/paths match `auth_cookies.py:15-16`; localStorage-mock-only matches `api-client.ts:7-8`; HMAC admin session matches `middleware.ts:42` | current |
| 32 | `frontend/docs/audits/01-api-gaps-{en,fa}.md` | **accurate** (dated 17 Jul) | Superseded in part by `gaps/02` which explicitly corrects it ("Those are now wired… This document is the post-remediation truth") — good practice | 2026-07-17/18 |
| 33 | `frontend/docs/audits/02-uiux-audit-{en,fa}.md` | **accurate** (dated) | Static-analysis caveat declared | 2026-07-17 |
| 34 | `frontend/docs/gaps/01-fe-ahead-be-needed-{en,fa}.md` | **accurate** | Matches code: `/settings/store`, `/reports/*`, invoice PDF, documents library genuinely absent (grep of `app/api` confirms) | 2026-07-18 |
| 35 | `frontend/docs/gaps/02-be-exists-fe-should-use-{en,fa}.md` | **accurate** | Self-corrects predecessor; claims verified (register gated by `ALLOW_PUBLIC_REGISTER=False`, `config.py:93`) | 2026-07-18 |
| 36 | `frontend/docs/deploy/DEPLOYMENT_{en,fa}.md` | **minor drift** | Describes target split-host topology as guide while actual deploy is single-VPS via Actions (covered honestly in COLLABORATOR_DEPLOY.md); FA version is a simplified summary, not a translation (declared) | 2026-07-18 |
| 37 | `frontend/Storefront/README.md`, `frontend/admin-panel/README.md` | **accurate** | Env tables match `config/env.ts`; mock credentials clearly mock-scoped (mock PIN `84729101` is on the backend weak-PIN blocklist, `config.py:194` — good) | post-remediation |
| 38 | `frontend/admin-panel/AGENTS.md` / `CLAUDE.md` | **accurate** | Vendor-generated Next.js agent notice + pointer; no claims to verify | — |
| 39 | `.env.example` (root) | **minor drift + unsafe example** | Coverage of `config.py` is good (~90% of settings) but ships literal `ADMIN_STEP_UP_PIN=8472916350` that **passes** the weak-PIN validator; missing `OTP_EXPIRE_SECONDS`, `STEP_UP_MAX_ATTEMPTS`, `AUTH_MAX_ATTEMPTS`, `PENDING_PAYMENT_EXPIRE_MINUTES`, `IDEMPOTENCY_TTL_HOURS`, `TRUSTED_PROXIES`, `PUBLIC_ASSET_BASE` | current |
| 40 | `frontend/Storefront/.env.example` | **minor issue** | Real GA4 ID `G-7LLQJ74Y4F` active by default (+ commented GTM ID) — every fork/local build fires production analytics | current |
| 41 | `frontend/admin-panel/.env.example` | **accurate** | Placeholder secret clearly marked | current |
| 42 | `.github/workflows/*.yml` (as documentation) | **accurate — exemplary** | Names could mislead ("Deploy Staging" deploys the live customer site) but header comments state it explicitly (`deploy-staging.yml:3`, `deploy-production.yml:3-5`); CI comments explain the path-filter/required-checks trick truthfully | 2026-07-24 |
| 43 | `docs/audits/*.md` (v1, 9 files) | **minor drift** (see §4) | Documentation score 7.0 not traceable to any phase subscore; corpus-level doc drift missed | 2026-07-25 `66e9ae9` |

**Corpus summary:** 43 assessed units → 17 accurate · 12 minor drift · 7 major drift · 3 obsolete-unmarked · 3 aspirational (correctly labeled) · 1 accurate-with-unsafe-example. The **actively maintained operational core (HESABFA, OPERATIONS, ARCHITECTURE, COLLABORATOR_DEPLOY, workflows, cookie contract, frontend/docs set) is accurate**; the **entry-point and contract documents (README, AI_CONTEXT, openapi snapshot, non-compliance ledger, go-live plan) are the ones that mislead**.

---

## 3. Findings register

### DOC-01 — README documents API endpoints and shapes that do not exist
- **Severity:** High · **Category:** Accuracy / API contract drift · **Location:** `README.md:271,284-289,336-348`
- **Evidence (doc):** "`POST /api/v1/cart/items`", "`PATCH /api/v1/cart/items/{product_id}`" (ln 286–288); category tree response "`{ "data": [ … ] }`" (ln 271); stock response "`{ …, "stock_quantity": "50", "stock_status": "in_stock" }`" (ln 343); "`POST /api/v1/products/{product_id}/stock/adjust?quantity_delta=10`" presented as a working inventory operation (ln 347).
- **Evidence (code):** Cart router exposes only `GET ""`, `PUT "/items"`, `DELETE "/items/{product_id}"`, `DELETE ""`, `POST "/merge"` (`app/api/endpoints/cart.py:59-129`) — no POST, no PATCH. Tree returns `response_model=list[CategoryTreeResponse]` — a **raw array** (`app/api/endpoints/category.py:216-221`), which `docs/API_CONTRACT.md:57` and `docs/API_CHANGELOG.md:63` both state was *specifically fixed* in docs after audit A. `get_stock_status` hardwires `"stock_quantity": Decimal("0")`, `"low_stock": False` (`app/crud/product.py:332-341`). `/stock/adjust` is `deprecated=True`, summary "Deprecated: maps quantity delta to availability toggle" (`app/api/endpoints/products_admin.py:263-269`).
- **Why problematic:** The README is the repository front door and the only doc guaranteed to be read; an integrator following it writes four broken calls before reading anything else. The tree-shape error re-introduces the exact bug the changelog says was fixed.
- **Root cause:** README endpoint sections copy an early-era API and were never re-audited after the cart rewrite, tree-shape fix, and binary-availability pivot.
- **Risk:** Broken integrations; erosion of trust in all other docs. · **Business impact:** wasted collaborator time; onboarding cost for a 2-person team that can't afford it. · **Technical impact:** contract confusion propagates into mocks/clients.
- **Recommendation:** Regenerate the README endpoint section from the live OpenAPI (script exists in `API_CONTRACT.md:48`), or delete the endpoint catalog and link to `docs/API_CONTRACT.md` + `/api/docs` as the single source.
- **Alternative:** Keep prose but add a CI check diffing README-listed paths against `openapi/v1.json`.
- **Effort:** S · **Priority:** P1 · **Dependencies:** DOC-03 (regenerate snapshot first)

### DOC-02 — AI_CONTEXT.md: obsolete 1,000-line handover carrying a fresh "last updated" stamp
- **Severity:** Critical · **Category:** Currency / actively misleading · **Location:** `frontend/AI_CONTEXT.md:4,76,109-119,209,244,272,313-319,541-571,588-590,725-745`
- **Evidence (doc):** Header claims "آخرین به‌روزرسانی: ۱۴۰۵/۰۵/۰۲" (≈2026-07-24). Body asserts: SQLAdmin as the admin UI incl. "SQLAdmin در `/admin`" (ln 115, 209, 274-276); "بدون refresh token" (ln 590); integration matrix marks checkout, OTP request/verify, blog, hero-slides, contact, comments, related products all "❌ **ندارد**" (ln 561-569); "Brand delete step-up نمی‌خواهد" (ln 272, 752); migrations list of 5 with head `f1a2b3c4d5e6` (ln 313-319); admin `/orders`, `/customers`, `/reports` "ComingSoon" (ln 390, 727-734); references `RUN_GUIDE_FA.md`, `scripts/*.ps1`, root `V1/` (ln 85-99) — none exist.
- **Evidence (code):** No `sqladmin` in `requirements.txt` or `app/main.py` (grep: zero hits). `POST /auth/refresh` with rotation (`app/api/endpoints/auth.py:230`). All "missing" endpoints live (`checkout.py:23`, `auth.py:374-395`, `storefront_content.py:28-120`, `products_reviews.py:22-46`, `products_catalog.py:309`). Brand delete requires step-up (`brand.py:176` + regression test noted in `BACKEND_CHANGES.md` URGENT-4). 24 files in `alembic/versions/`. Admin orders/customers/CMS pages implemented (`frontend/docs/gaps/02-be-exists-fe-should-use-en.md` confirms wired).
- **Why problematic:** The document's stated purpose is to let a new AI/developer continue work "**بدون نیاز به کاوش اولیه**" (without initial exploration). Combined with a fresh timestamp, it is a trap: an agent trusting it would re-implement existing endpoints, use SQLAdmin instructions that fail, and skip refresh-token handling. Only §21 was updated; §1–§20 describe a codebase 3+ months old.
- **Root cause:** Append-only maintenance — new phase log added, stale body never revalidated; the timestamp was bumped for the append.
- **Risk:** Highest-leverage misinformation in the repo (explicitly targeted at automated consumers). · **Business impact:** wasted agent/developer cycles, wrong technical decisions. · **Technical impact:** duplicate implementations, contract regressions.
- **Recommendation:** Either rewrite §1–§20 against current code, or truncate to §21 + a pointer to `README.md`/`docs/API_CONTRACT.md`/`frontend/README.md`, with a banner marking the old body as historical.
- **Alternative:** Add a prominent "HISTORICAL — sections 1–20 describe the pre-commerce codebase (May 2026)" banner as an S-effort stopgap.
- **Effort:** M (rewrite) / S (banner) · **Priority:** P1 · **Dependencies:** none

### DOC-03 — Committed OpenAPI snapshot is stale while advertised as the offline source of truth
- **Severity:** High · **Category:** Contract currency · **Location:** `openapi/v1.json` (last commit 2026-07-18 `335a1cb`); advertised at `docs/API_CONTRACT.md:45-49`, `docs/API_CHANGELOG.md:117-126`
- **Evidence:** Snapshot contains 71 paths. Missing vs live router: `/api/v1/hesabfa/{status,mappings/sync,items/push,stock/sync,sales-summary}` (`hesabfa.py`), `/api/v1/cms/nav-groups` GET+PUT (`cms.py:265,274`), public `/api/v1/nav-groups/` (`storefront_content.py:101`), `PUT /api/v1/products/{id}/availability` (`products_admin.py:218`), `POST /api/v1/categories/{id}/image` (`category.py:132`), `POST /api/v1/brands/{id}/logo` (`brand.py:126`). `API_CONTRACT.md:3` instructs clients to treat these docs as "the **source of truth**" because prod Swagger is off; `API_CONTRACT.md:77` mandates "Regenerate and commit `openapi/v1.json`" per change — not done for ≥3 merged PRs (#51 nav-groups, availability work, category images).
- **Why problematic:** Typegen from the snapshot silently omits ~10 live operations; admin panel features (nav-groups, availability toggle) have no offline contract at all.
- **Root cause:** Regeneration is a manual step with no CI enforcement.
- **Risk:** Frontend types drift from reality precisely when prod docs are disabled. · **Business impact:** admin features built against guessed contracts. · **Technical impact:** type mismatches at runtime.
- **Recommendation:** CI job: boot app with dummy env, dump `app.openapi()`, fail if it differs from the committed snapshot.
- **Alternative:** Pre-commit hook doing the same locally.
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

### DOC-04 — BACKEND_NON_COMPLIANCE.md presents mostly-resolved gaps as open non-compliance
- **Severity:** High · **Category:** Currency / misleading ledger · **Location:** `frontend/BACKEND_NON_COMPLIANCE.md` (header 2026-07-11; closing rule ln 647)
- **Evidence:** Spot-check of 8 headline items against current code — **7 resolved, 0 marked**: quote endpoint "وجود ندارد/P0" → exists (`order.py:329`); PATCH status logistics contract → implemented verbatim (`schemas/order.py:61-69`); tracking `timeline` "لازم است" → shipped (`schemas/order.py:53,107`); `is_deleted` filter "الان فیلتر ندارد" → exists (`products_catalog.py:75`); customer `note/category/tags` → accepted (`schemas/user_admin.py:33-35`); `mode`/`customer_phone` list filters → exist (`order.py:169-183`); multipart image upload "آینده" → implemented (`products_images.py:60`). Still genuinely open: `/settings/store`, `/reports/summary`, invoice PDF (grep of `app/api`: absent). The doc's own footer commits: "هر تغییر API باید در این فایل به‌روز شود" — never honored. §2.1 also demands OTP bodies use `phone_number`, while the adopted backend contract is `phone` (`schemas/auth.py:34-35`) — the requirement was superseded, not just unimplemented.
- **Why problematic:** A 647-line "current non-compliance" document where ~70% of items are silently done inverts its meaning: a backend engineer triaging from it would re-do shipped work; a stakeholder would conclude the backend is far less complete than it is.
- **Root cause:** Requirements doc used as a one-shot handoff, never reconciled after the 2026-07-17 integration wave.
- **Risk:** Misallocated engineering effort; conflicting contract guidance (`phone` vs `phone_number`). · **Effort to fix:** S–M.
- **Recommendation:** Add a status column (✅ done / ❌ open / superseded) per item, or archive the file with a banner pointing to `frontend/docs/gaps/01-fe-ahead-be-needed-*` (which is the accurate, current version of the same content).
- **Alternative:** Delete; the `gaps/` pair fully supersedes it.
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

### DOC-05 — Go-live plan is a frozen "living document" describing a pre-launch project after launch
- **Severity:** High · **Category:** Currency · **Location:** `docs/GO_LIVE_EXECUTION_PLAN.md:25,45-57,528`
- **Evidence (doc):** "وضعیت فعلی: بین L0 و L1" (ln 25); readiness matrix: "Catalog/Data 25 — import انبوه نشده", "DevOps 40 — deploy نشده", "Integrations 15" (ln 47-57); footer: "این سند برنامه اجرایی زنده است — پس از هر فاز… به‌روز کنید" (ln 528).
- **Evidence (reality):** Live site at karzartools.com behind CI/CD (`deploy-staging.yml:3` — "Staging = live VPS serving karzartools.com"); ~5,900 products live (`docs/audits/master-engineering-report.md:5`; `CATALOG_IMAGES_PLAN.md` counts 3,471+ actionable products across 7 brands from the live DB); HTTPS/staging compose deployed (`deploy/staging/STAGING_DEPLOY.md`); backup cron installer shipped.
- **Why problematic:** Any stakeholder or new contributor reading the launch program concludes the platform is weeks from a first deploy. Checklists (F1–F4 gates) are useless for tracking what actually remains (Zarinpal live, Kavenegar/Faraz live, prod host split).
- **Root cause:** The plan achieved its purpose and was abandoned without a closing status pass; git shows only link-fix touches since 2026-07-14.
- **Recommendation:** One editing pass: update §3 matrix, tick completed gates, and re-scope §9 (F4) to the genuinely open items (live payment, live SMS, host split, restore drill).
- **Alternative:** Stamp "SNAPSHOT 2026-07-14 — superseded by OPERATIONS.md + COLLABORATOR_DEPLOY.md" and freeze.
- **Effort:** S–M · **Priority:** P2 · **Dependencies:** none

### DOC-06 — README "Project Structure" tree is fictional
- **Severity:** Medium · **Category:** Accuracy · **Location:** `README.md:41-111`
- **Evidence:** Tree lists 10 endpoint files — actual is 19 (missing `checkout.py`, `hesabfa.py`, `product_common.py`, `products_admin.py`, `products_catalog.py`, `products_images.py`, `products_reviews.py`, `storefront_content.py`); `crud/` shown as one file (`product.py`) vs ~10 modules; `services/` shown as one file vs 22 modules + `hesabfa/` package; `db/models/` shown with 2 files; `core/` missing 11 of 14 modules (middleware, rate_limit, health, auth_cookies…); `scripts/` shown with 1 file vs ~35; `tests/` shown with 3 files vs 33; `docs/` subtree lists 6 of 21 docs. `docs/ARCHITECTURE.md:8-44` contains the correct map.
- **Why problematic:** Understates the system by roughly 5× and contradicts the sibling ARCHITECTURE.md; newcomers form a wrong mental model on line 41 of the first file they read.
- **Recommendation:** Delete the tree and link to `docs/ARCHITECTURE.md` (already accurate).
- **Effort:** S · **Priority:** P2

### DOC-07 — README environment-variable table: wrong defaults, 55+ settings undocumented, Redis mischaracterized
- **Severity:** Medium · **Category:** Accuracy / completeness · **Location:** `README.md:113-118,471-486`
- **Evidence (doc):** Table claims `POSTGRES_SERVER` default `db`, `POSTGRES_DB` default `karzar_db`, `REDIS_HOST` default `redis`; prerequisites say "Redis 7+ (optional, for caching)".
- **Evidence (code):** `POSTGRES_SERVER`, `POSTGRES_DB` are **required with no default** (`config.py:20,22`); `REDIS_HOST` defaults to `None` (`config.py:24`); Redis is **mandatory whenever `DEBUG=False`** — boot fails without it (`config.py:228-232`) — and is used for rate limiting/locks, not caching. Table documents 12 of ~70 settings: nothing on `APP_ENV`, `ENFORCE_HTTPS`, `TRUSTED_HOSTS`, `CORS_ORIGINS`, `PAYMENT_*`, `SMS_*`, `HESABFA_*`, `ALLOW_PUBLIC_REGISTER`, throttles, cookies.
- **Why problematic:** Three of twelve documented defaults are wrong; the "optional Redis" claim directly contradicts a boot validator — a fresh operator following the README gets an unbootable non-debug instance.
- **Recommendation:** Replace the table with a pointer to `.env.example` (which is ~90% complete and annotated) and one paragraph on the production-required set.
- **Effort:** S · **Priority:** P2

### DOC-08 — README markets abandoned inventory semantics ("Real-time inventory tracking", "production-ready", "Stock Management")
- **Severity:** High · **Category:** Marketing claim contradicted by evidence · **Location:** `README.md:22,34,336-348,558-559`
- **Evidence (doc):** "A modern, **production-ready** FastAPI application… with comprehensive product management, **stock control**" (ln 22); "✅ **Stock Management**: Real-time inventory tracking" (ln 34); stock endpoints presented un-deprecated (ln 336-348); footer "Last Updated 2026-07-12, Version 1.0.0" (ln 558-559) while git shows edits through 2026-07-24 (`741ebd9`).
- **Evidence (code/business):** Inventory is binary by decision; counts live only in Hesabfa (`docs/HESABFA.md:8,64-68`); `stock_quantity` schema comment "count of is_available products (legacy field name)" (`schemas/product.py:236`); adjust endpoint deprecated toggle (`products_admin.py:267`). "Production-ready" coexists with the v1 audit's own P0 (same-disk backups) and mock-only payment gating production boot.
- **Why problematic:** This is the exact drift v1 flagged as ARCH-03/P1 on 2026-07-25 — and the README was edited *after* the pivot (2026-07-24) without touching these sections; the drift now has a documented, ignored warning.
- **Recommendation:** Rewrite Features/Stock sections around `is_available` (موجود/ناموجود), mark quantity endpoints deprecated, drop or qualify "production-ready", and make the footer date CI-maintained or delete it.
- **Effort:** S · **Priority:** P1 · **Dependencies:** duplicates v1 ARCH-03 (still open)

### DOC-09 — Integration guides teach dead field semantics (`low_stock`, `availability`)
- **Severity:** Medium · **Category:** Accuracy · **Location:** `docs/FRONTEND_INTEGRATION.md:92-96`, `docs/FRONTEND_HANDOVER.md:33`
- **Evidence (doc):** "`low_stock` boolean — `true` when quantity < 10"; "`availability` — `is_active && stock_quantity > 0`".
- **Evidence (code):** `low_stock=False` unconditionally (`app/utils/product_presenter.py:151`, `app/crud/product.py:340`); availability derives from the `is_available` flag via `product_is_available` (`crud/product.py:332`), never from quantity (quantity is pinned to 0).
- **Why problematic:** A storefront developer building "low stock, hurry!" UX from this guide ships a feature that can never trigger; the availability formula misleads about what admins control.
- **Recommendation:** One-paragraph correction in both files: availability is a manual admin flag; `low_stock`/`stock_quantity` are frozen legacy fields.
- **Effort:** S · **Priority:** P2

### DOC-10 — SEED_IMPORT.md asserts "no multipart upload storage" — contradicted by code and by OPERATIONS.md
- **Severity:** Medium · **Category:** Internal contradiction · **Location:** `docs/SEED_IMPORT.md:47` vs `docs/OPERATIONS.md:133-155`
- **Evidence:** SEED_IMPORT: "Product images are **URL-based** (no multipart upload storage)". Code: multipart accepted on product images (`products_images.py:32,60`), category card image (`category.py:136,154`), brand logo (`brand.py:130,148`); uploads persist in `karzar_uploads` volume with dedicated backup/restore scripts documented in OPERATIONS (`backup_uploads.sh` exists in `scripts/`). The active image pipeline (`CATALOG_IMAGES_PLAN.md:38`) materializes files to `data/uploads/products/{id}/`.
- **Why problematic:** Two backend docs give opposite answers to "where do images live?" — the one covering imports (where it matters most) is wrong, and its safety-rule framing ("validate URLs…") no longer covers the real attack/ops surface (file uploads).
- **Recommendation:** Update SEED_IMPORT §Safety rules for the dual URL+upload model and reference the uploads backup requirement.
- **Effort:** S · **Priority:** P2

### DOC-11 — OPERATIONS.md dead link to nonexistent roadmap log
- **Severity:** Low · **Category:** Broken reference · **Location:** `docs/OPERATIONS.md:159`
- **Evidence:** "Document results under `docs/roadmap/phase-0-execution-log.md`" — `docs/roadmap/` does not exist (`ls: cannot access`). The restore-drill checklist therefore has no recording target, consistent with v1 OPS-02's "no restore drills".
- **Recommendation:** Create the file (even empty with headers) or point to an existing location.
- **Effort:** S · **Priority:** P3

### DOC-12 — Example/env docs ship a copy-paste-able admin PIN that defeats the weak-PIN validator
- **Severity:** Medium · **Category:** Unsafe example-as-default · **Location:** `.env.example` (ADMIN_STEP_UP_PIN line), `docs/LOCAL_DEV_FRONTEND.md:39`, plus `INITIAL_SUPER_ADMIN_PASSWORD=change-me-admin-password` and `frontend/Storefront/.env.example` GA4 ID
- **Evidence:** Both files ship the literal `ADMIN_STEP_UP_PIN=8472916350`. The blocklist rejects `84729101` and other knowns (`config.py:188-196`) but **not** `8472916350` — so the documented example boots fine in production hardening mode, making "the PIN from the docs" a plausible live credential. The initial-admin password placeholder passes too (only the SECRET_KEY placeholder set is enforced, `config.py:143-147`). Storefront example enables a real GA4 property (`NEXT_PUBLIC_GA_MEASUREMENT_ID=G-7LLQJ74Y4F`) by default — every fork/dev build pollutes production analytics.
- **Why problematic:** Docs and examples are part of the security posture; a validator-bypassing example PIN repeated in two files is exactly how shared "temporary" credentials calcify (cross-ref v1 SEC-03/SEC-09 shared-PIN findings).
- **Recommendation:** Change examples to obviously-invalid placeholders (`ADMIN_STEP_UP_PIN=change-me-6-12-digits` fails length/charset naturally) **and** add the current example values to the weak-PIN blocklist; comment out the GA4 ID.
- **Effort:** S · **Priority:** P2 · **Dependencies:** coordinate with VPS check that `8472916350` is not the live PIN

### DOC-13 — Four documents claim contract precedence; two of them are stale
- **Severity:** High · **Category:** Structural / multiple sources of truth · **Location:** `docs/API_CONTRACT.md:3`, `docs/FRONTEND_IMPLEMENTATION_GUIDE.md:8`, `README.md:193`, `frontend/README.md:123`
- **Evidence:** API_CONTRACT: "Use the documents below as the **source of truth**" (listing 8 docs, headed by the go-live plan). FRONTEND_IMPLEMENTATION_GUIDE (frozen 2026-07-13): "این سند **منبع اصلی کار فرانت** است… این فایل + OpenAPI اولویت دارند". README: "Full interactive documentation: `/api/docs` (OpenAPI is always up to date)" — untrue for the committed snapshot and unavailable in prod (`ENABLE_API_DOCS=False` enforced, `config.py:211-212`). frontend/README: "API contract is owned by `backend` OpenAPI". Meanwhile the guide's §1 readiness numbers and open-bug list (OTP `phone_number`) are 12 days stale and contradicted by `INTEGRATION_RUNTIME_NOTES.md`.
- **Why problematic:** A developer resolving a contract question gets four different "authoritative" pointers, two of which lead to stale artifacts. The precedence chain itself is documented inconsistently.
- **Recommendation:** Declare exactly one machine artifact (regenerated `openapi/v1.json`, DOC-03) as contract SoT; demote FRONTEND_IMPLEMENTATION_GUIDE and the go-live plan to dated snapshots with banners; fix README's "always up to date" claim.
- **Effort:** S–M · **Priority:** P1 · **Dependencies:** DOC-03

### DOC-14 — BACKEND_CHANGES.md / BACKEND_HANDOFF.md: unmarked historical snapshots indexed as current
- **Severity:** Low · **Category:** Currency labeling · **Location:** `docs/BACKEND_CHANGES.md:59,96`; `frontend/BACKEND_HANDOFF.md` (whole); indexed at `README.md:464`
- **Evidence:** BACKEND_CHANGES states "Images are URL-based only (no blob storage)" and "160 passed, 2 skipped" — both superseded (multipart exists; 242 tests). README's doc table sells it as "Recent backend deltas for frontend". BACKEND_HANDOFF requests features (timeline, restore, multipart) that shipped.
- **Recommendation:** Date-stamp both headers ("snapshot of the 15-item July integration batch") or archive under `docs/archive/`.
- **Effort:** S · **Priority:** P3

### DOC-15 — LOCAL_DEV_FRONTEND.md names a nonexistent env var (`NEXT_PUBLIC_API_URL`)
- **Severity:** Medium · **Category:** Accuracy · **Location:** `docs/LOCAL_DEV_FRONTEND.md:63`
- **Evidence (doc):** "API base URL for frontends: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`".
- **Evidence (code):** Both apps read only `NEXT_PUBLIC_API_BASE_URL` (`frontend/Storefront/src/config/env.ts:11`, `frontend/admin-panel/src/config/env.ts:10`); every other doc (GO_LIVE, LOCAL_STACK_ACCESS, READMEs, HANDOFF) uses the correct name.
- **Why problematic:** The variable is silently ignored; locally it happens to coincide with the fallback default, so the error only bites when someone points at staging and can't understand why requests still hit localhost.
- **Recommendation:** One-word fix.
- **Effort:** S · **Priority:** P2

### DOC-16 — LOCAL_DEV_FRONTEND.md seed description contradicts startup code
- **Severity:** Low · **Category:** Accuracy · **Location:** `docs/LOCAL_DEV_FRONTEND.md:48`
- **Evidence:** "One active product: SKU `DEV-CHECKOUT-001`, price 250,000 Toman, **stock 100**" vs `app/core/startup.py:101` seeding `stock_quantity=Decimal("0")` (availability-flag model).
- **Recommendation:** Say "available (موجود)" instead of a quantity.
- **Effort:** S · **Priority:** P3

### DOC-17 — README footer metadata is stale and hand-maintained
- **Severity:** Low · **Category:** Currency · **Location:** `README.md:558-559`
- **Evidence:** "Last Updated: 2026-07-12" while the file's last commit is 2026-07-24 (`741ebd9`); "Version 1.0.0" mirrors the decorative `config.py:14` constant (cross-ref v1 ARCH-08).
- **Recommendation:** Delete the footer or derive from git.
- **Effort:** S · **Priority:** P3

### DOC-18 — TESTING.md file census is a P5-era subset
- **Severity:** Low · **Category:** Completeness · **Location:** `docs/TESTING.md:34-46`
- **Evidence:** "Test layout" lists 8 files; `tests/` has 33 test modules including the entire audit-series (`test_c_…` through `test_g_…`), payments, orders, storefront, hesabfa, nav-groups. Gate/markers/CI content verified accurate.
- **Recommendation:** Replace the table with a naming-convention paragraph (also mitigates v1 QA-04).
- **Effort:** S · **Priority:** P3

### DOC-19 — Knowledge-platform docs vs active image work: contradictory "paused" status
- **Severity:** Low · **Category:** Internal consistency · **Location:** `docs/KNOWLEDGE_PLATFORM_PHASE1_ARCHITECTURE_AUDIT.md:9`, `PHASE3_…:13` vs `docs/CATALOG_IMAGES_PLAN.md` (2026-07-25)
- **Evidence:** Phase docs state product-image import is "paused… resume after Knowledge Platform phases"; three days later a full Phase-A image plan is executing against the live DB. The KP docs are otherwise exemplary in labeling themselves design-only.
- **Recommendation:** One-line status update in the Phase 3 header.
- **Effort:** S · **Priority:** P3

### DOC-20 — API_CHANGELOG stopped recording endpoint additions after 2026-07-19
- **Severity:** Medium · **Category:** Update discipline · **Location:** `docs/API_CHANGELOG.md` (last substantive entry: staging deploy kit)
- **Evidence:** Changelog policy: "New endpoint | Minor | record here" (ln 14). Added since without entries: `PUT /products/{id}/availability`, `POST /categories/{id}/image`, `POST /brands/{id}/logo`, `GET/PUT /cms/nav-groups`, `GET /nav-groups/`, all `/hesabfa/*`, plus the behavioral change "Hesabfa admin reads disabled" (PR #55) which alters `GET /hesabfa/sales-summary` responses (fields now always null — `hesabfa.py:148-153`).
- **Why problematic:** The changelog is the designated mechanism for clients to track the contract when Swagger is off; a two-week silent gap during active endpoint work breaks that promise.
- **Recommendation:** Backfill one "2026-07 — nav groups, category/brand media, Hesabfa admin surface" entry; add changelog check to PR template.
- **Effort:** S · **Priority:** P2

### DOC-21 — v1 audit reports: untraceable Documentation score and missed corpus drift (see §4)
- **Severity:** Medium · **Category:** Audit quality · **Location:** `docs/audits/master-engineering-report.md:57`; `docs/audits/architecture-audit.md` (scores), `docs/audits/testing-quality-audit.md:§1.4`
- **Evidence/Why/Recommendation:** detailed in §4 below.
- **Effort:** S (errata note) · **Priority:** P3

**Counts:** 1 Critical · 6 High (DOC-01, 03, 04, 05, 08, 13) · 8 Medium (DOC-06, 07, 09, 10, 12, 15, 20, 21) · 6 Low (DOC-11, 14, 16, 17, 18, 19).

---

## 4. v1-audit-report critique (required)

The 9 v1 reports (`docs/audits/*.md`, committed 2026-07-25 `66e9ae9`) are, as engineering audits, **substantially reliable**: file:line citations are dense, self-challenge sections genuinely reverse findings (e.g. the admin localStorage false-positive disproved in `frontend-admin-audit.md §3`), and unverified areas are explicitly fenced (devops: four VPS facts; storefront: no live axe run; testing: suite not executed). Numeric claims re-verified here: **242 tests** ✓ (collected), 62% gate ✓ (`backend-ci.yml:170`), 24 alembic revisions ✓, pool 20+10 ✓ (`database.py:17-18`), staging-is-live ✓. Minor factual slips only: "36 files" for the test suite (33 test modules + conftest + `__init__` — defensible but imprecise), "18 services" (22 service modules + hesabfa package).

**Where v1 fails under strict grading — Documentation specifically:**

1. **The 7.0 Documentation score is not traceable to any evidence.** Master line 57 sources it to "Phases 1/8". Phase 1's own subscore is "Documentation accuracy **6/10** … README/API drift on inventory semantics is misleading today" (`architecture-audit.md §5`). Phase 8 assigns **no documentation score at all** — its §1.4 offers only the richness observation "Documentation for developers is unusually rich" (a volume claim, not an accuracy claim). Synthesizing 6/10-with-known-drift plus an unscored richness remark into 7.0 inflated the grade above its only measured input. Under the audit plan's own rule ("Every claim must cite… scores with justification", `00-audit-plan.md §4-5`), this cell is unsupported.
2. **No phase audited the documentation corpus.** The plan (§2) assigns docs to Phase 1 ("docs" in scope title) and Phase 8 ("documentation" in scope title), but Phase 1's method statement reads only `docs/ARCHITECTURE.md` + README, and Phase 8 lists doc names without verification. Consequently v1 **missed**: the README's nonexistent cart endpoints and wrong tree shape (DOC-01), the wrong env-table defaults (DOC-07), the stale `openapi/v1.json` contract snapshot (DOC-03), the obsolete 1,044-line `AI_CONTEXT.md` with fresh timestamp (DOC-02 — arguably the single most misleading file in the repo), the inverted `BACKEND_NON_COMPLIANCE.md` ledger (DOC-04), the frozen go-live readiness matrix (DOC-05), the dead OPERATIONS link (DOC-11), and the SEED_IMPORT/OPERATIONS images contradiction (DOC-10). Eight corpus-level defects, zero detected.
3. **What v1 got right on docs** (credit where due): ARCH-03 correctly identified the README inventory-semantics drift with correct severity logic ("every doc reader mis-learning inventory semantics" appears again in the master debt register), ARCH-08 caught the stale version/date footer, and master P1 item 12 escalated README drift to the top-12 list. The direction was right; the depth was one file deep.
4. **Master-report consistency gap:** master §19 lists "Documentation culture (architecture, contracts, operations, refactor maps — and honest comments)" as strength 7 while item 12 of P1 says the README misleads — both true, but the score cell reconciles them upward (7.0) rather than downward, contradicting the master's own stated method of weighting toward risk (§2: "deliberately pulled below the code-quality average" — applied to DevOps but not to Documentation).

**Verdict on v1 reliability:** Trust the v1 code/infra findings — spot-checks corroborate them. Treat the v1 **Documentation 7.0 as unsupported**; the evidence-backed number available inside v1 itself was 6/10, and a corpus-wide check (this report) lands materially lower.

---

## 5. Score (strict, 0–10)

### Documentation: **4.5 / 10** (v1: 7.0 → **−2.5**)

**Rubric placement:** "3–4 material risk (docs actively mislead)" ↔ "5–6 systemic weaknesses". This corpus straddles the boundary: the two documents a newcomer reads first (`README.md`, `frontend/AI_CONTEXT.md`) both actively mislead — fabricated endpoints, abandoned inventory semantics marketed as features, an obsolete handover wearing a fresh timestamp — and the designated offline contract (`openapi/v1.json`) is stale. That is material-risk territory. What pulls the score up to 4.5 rather than lower:

- **The operationally-load-bearing docs are accurate and current:** `HESABFA.md` (updated same-day as the code change it describes — the "clear admin reads" merge), `OPERATIONS.md`, `ARCHITECTURE.md`, `COLLABORATOR_DEPLOY.md`, the workflow YAMLs (whose comments honestly document the staging-is-live reality), the cookie contract (verified against code on both sides), root `.env.example` (~90% of settings, annotated), and the post-remediation `frontend/docs/` set — which even **explicitly corrects its own predecessor** (`gaps/02`: "The earlier audit listed… Those are now wired… This document is the post-remediation truth"), the single best documentation-discipline artifact in the repo.
- **Aspirational docs are mostly labeled** (Knowledge Platform trilogy, refactor map, audit playbook all carry explicit status headers).
- **Volume and coverage are genuinely unusual** for a two-person team: 40+ substantive documents, bilingual where audience demands it (FA files are declared simplified summaries, not sloppy translations — acceptable).

**Why the −2.5 delta is justified:** v1's 7.0 was produced without a documentation phase and above its only measured input (6/10). A strict pass verified ~200 individual claims and found a **systemic currency failure mode**: documents are written well once, then abandoned while carrying "living document", "source of truth", or fresh-timestamp markers — README (edited 2026-07-24, endpoint sections years-stale in API terms), NON_COMPLIANCE (own update rule violated), GO_LIVE (own update rule violated), API_CHANGELOG (own recording rule violated for 6+ endpoints), openapi snapshot (own regeneration rule violated). Five documents each broke their own stated maintenance contract. Accuracy problems concentrate exactly where reader trust is highest.

**Path back to 7:** fix DOC-01/02/03/04/08/13 (all S–M effort, mostly deletion/banner/regeneration) and add the one CI check (openapi diff). The corpus's problem is discipline, not ability — the same team demonstrably writes accurate docs when the doc sits next to the code it describes.

### Sub-scores (informational)

| Dimension | Score | Note |
|---|---|---|
| Accuracy vs code | 4/10 | Front-door and contract docs contradict code; ops core accurate |
| Completeness | 6/10 | Impressive breadth; env/scripts/test surfaces under-documented in the docs that claim them |
| Currency / update discipline | 3/10 | Five self-imposed maintenance rules broken; snapshots unmarked |
| Audience fit | 6.5/10 | Clear audience headers, FA/EN split sensible; AI-audience doc is the most dangerous |
| Internal consistency | 4.5/10 | Tree shape ×2, images ×2, env-var name ×1, contract precedence ×4 |
| Discoverability / structure | 6/10 | Good doc indexes in README/API_CONTRACT/frontend README; no archive convention, so stale and live docs are indistinguishable |

---

## 6. Self-review (unverified items & limitations)

1. **Live VPS state not inspected** — whether `8472916350` (DOC-12) is the actual production PIN, whether the GA4 property is production's, and whether backup cron is installed were not verifiable from the repo (same limitation v1 declared).
2. **`pytest` was collected, not executed** — "242 tests" is collection truth; pass/fail state relies on CI history (consistent with v1's approach).
3. **PDF artifact** `docs/FRONTEND_INTEGRATION.pdf` was not diffed against its markdown sibling (binary; assumed export of same content — if it predates the tree-shape fix it silently preserves the old error).
4. **FA/EN semantic equivalence** was spot-checked (deploy pair, gaps pair headers, ~20 claims), not line-by-line; FA files are intentionally abridged, so drift *between* language versions of the same doc cannot be fully excluded.
5. **`frontend/docs/audits/01-api-gaps-en.md` route census ("~87 routes")** was not independently recounted route-by-route; my decorator census (~95 operations across 19 modules) is consistent within counting-method differences.
6. **Out-of-repo duplicate tree**: `/home/moahmmad/Projects/Karzar/Website/frontend/` and `Website/docs` (root-owned, dated Jul 18) duplicate repo docs outside the repo; flagged as a discoverability hazard for local agents but not audited (outside repo scope).
7. **Admin-panel `src/lib/mock-credentials.ts`** referenced by v1 FE-A-05 was not re-read this pass; the README-documented mock credentials were verified against the backend weak-PIN blocklist instead.
8. **Severity judgment calls:** DOC-02 Critical vs High is contestable — I graded on the doc's explicit promise ("no exploration needed") to automated consumers who cannot smell staleness; readers who disagree should still treat DOC-01/03/04 as the P1 cluster.
