# Architecture Audit — v2 (Strict / Hostile Due-Diligence Mode)

**Date:** 2026-07-25 · **Auditors:** Principal Architect team (v2 re-audit)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9` · **Repo:** `Shebahati/Karzar` (monorepo root = `backend/`)
**Posture:** Every v1 finding re-verified against current code; v1 generosity called out explicitly; new findings numbered ≥ ARCH-20.

---

## 1. Scope & method

Read in full or in targeted depth: `app/main.py`, `app/core/config.py`, `app/core/startup.py`, `app/api/v1/__init__.py`, all of `app/api/endpoints/` (census + targeted reads of `order.py`, `checkout.py`, `hesabfa.py`, aggregators), `app/services/` (census + `payment_flow_service.py`, `product_service.py`, `hesabfa/invoices.py`, `hesabfa/item_push.py`), `app/crud/` (`platform.py`, `content.py`, `product.py` excerpts), all `app/db/models/*`, `docker-compose*.yml`, `gunicorn_conf.py`, `docker-entrypoint.sh`, `.github/workflows/*`, `scripts/` census + `reconcile_prices_availability.py`, and the four mandated architecture docs. Import graph mapped with ripgrep over `from app.*` edges (endpoints→crud, endpoints→services, services→crud, reverse-direction checks, lazy-import sites). Outer workspace layout inspected above the repo root. Read-only; the only write is this report.

Verification limits are listed in §6.

---

## 2. Critique of the v1 report

### 2.1 v1 findings verified (still true today)

| v1 ID | Status | Current evidence |
|---|---|---|
| ARCH-01 in-process background worker | **Confirmed, understated** | `app/main.py:32–68` (`_order_expiry_worker` started in `lifespan`, line 61). v1 missed that the same process also runs startup **seed writes** (`app/main.py:58–59` → `app/core/startup.py:57–120`) and that gunicorn defaults to `cpu_count*2+1` workers (`gunicorn_conf.py:7`) each running the loop and each racing the seed. |
| ARCH-02 scripts/ unmanaged business logic | **Confirmed, understated** | 36 entries in `scripts/`; pricing rules at `scripts/reconcile_prices_availability.py:131–132` (rial÷10), `:324–327` (markup10/markup20 CSVs). v1 missed the hardcoded developer-home data dependency (see ARCH-21) and the churn rate (27 commits touching `scripts/` in 30 days). |
| ARCH-03 README inventory-semantics drift | **Confirmed, unfixed** | `README.md:34` still says "**Stock Management**: Real-time inventory tracking"; `README.md:347` still documents `POST .../stock/adjust`; model says the opposite at `app/db/models/product.py:154` ("Deprecated for sellable UX: warehouse counts live in Hesabfa only"). v1 rated P1 "cheap fix" — not done. |
| ARCH-04 dual blog content sources | **Confirmed** | `frontend/Storefront/src/data/articles/how-to-read-vernier-caliper.ts` exists alongside CMS `Article` model (`app/db/models/content.py:31`) and admin CMS routes (`app/api/endpoints/cms.py`). Also `mock-data.ts`, `mock-catalog-generator.ts` in the same folder. |
| ARCH-05 free-text status columns | **Confirmed** | `app/db/models/commerce.py:89` `status: String(100)`, `:90–92` `payment_status: String(20)`, `app/db/models/product.py:212` `movement_type: String(20)`; no CHECK constraints; native PG enums used for `OrderMode`/`CartLane`/`StockUnitEnum` (`commerce.py:85–88`, `product.py:161–165`) — inconsistent policy stands. |
| ARCH-06 no order-item snapshot | **Confirmed, worse than v1 said** | `app/db/models/commerce.py:129–138`: `OrderItem` = `product_id, quantity, unit_price` only — and `unit_price` is **nullable** (`:136`). Hesabfa invoicing already has to fall back: `app/services/hesabfa/invoices.py:159` `item.unit_price or product.base_price or 0` — i.e., invoices for historical orders can be priced from **today's** product price. v1 severity High is correct; the nullable price and the live fallback make it a P1 accounting-integrity defect. |
| ARCH-07 repo-root hygiene | **Confirmed** | `.venv/`, `.venv312/`, `venv/` all present; `.coverage`, `.logo_audit/`, `logs/`, `backups/`, `data/` at root (untracked — verified via `git ls-files`). Naming still `frontend/Storefront` vs `frontend/admin-panel`. v1 severity Low was **too generous** given what sits *above* the root (see ARCH-20). |
| ARCH-08 version identity stale | **Confirmed** | `app/core/config.py:14` `VERSION = "1.0.0"`; git tag `v1.0.0` dated **2026-06-16**, with **148 commits** since and no new tag. `/health` (`app/main.py:176–187`) reports the decorative constant; no git SHA anywhere. |

### 2.2 What v1 got WRONG

- **"Compat shims … risk is bounded because tests import both paths" (v1 §4).** False. No test imports `app.crud.platform`, `app.crud.cart_persistence`, or `app.crud.idempotency` (ripgrep over `tests/`: zero hits; only `crud.payment_transaction` and `crud.stock_movement` are imported directly, in `tests/test_f_payment_audit.py:8`, `tests/test_orders.py:7`, `tests/test_p0_payment.py:6`). The shim is exercised only transitively through API tests. Worse, the shim is not a compat layer at all — see ARCH-24.
- **"The layered architecture is real, not aspirational" (v1 §2.1) — half-true, stated too strongly.** 14 of 19 endpoint modules import `app.crud` directly (ripgrep census), `app/api/endpoints/users.py` and `auth.py` execute ORM `select()` statements inline (e.g. `auth.py:120–121`, `users.py` 9 query sites), and step-up-token verification/consumption — security-critical business logic — lives inside the endpoint handler at `app/api/endpoints/order.py:260–290`. The repo's own refactor map defines Done-R3 as "`rg "from app.crud" app/api/endpoints` → zero" (`docs/BACKEND_STRUCTURE_REFACTOR_MAP.md` §6.4); the codebase fails its own bar in 14 files.
- **"Ledger tables are append-only" (v1 §2.5) — schema does not enforce it.** `PaymentTransaction.order_id` has `ondelete="CASCADE"` (`commerce.py:62–64`) plus `cascade="all, delete-orphan"` on the relationship (`commerce.py:121–126`); `StockMovement` likewise (`product.py:208–209`, `:192–194`). Hard-deleting an order or product silently destroys its financial/stock audit trail. Soft-delete conventions mitigate in practice, but the "append-only" property is convention, not architecture.

### 2.3 What v1 MISSED (now filed as ARCH-20…ARCH-28)

Outer-workspace chaos including a second full clone and a parent git repo that owns the business's price lists (ARCH-20, ARCH-21); Hesabfa failed-invoice dead end with no retry (ARCH-22); synchronous external SaaS calls inside the payment-verify and product-create request paths with commit-splitting (ARCH-23); shims adopted as the canonical import path (ARCH-24); unconditional dev catalog seeding at startup (ARCH-25); the knowledge-platform doc suite describing a large architecture with zero code behind it (ARCH-26, doc-drift); a bulk external-sync endpoint doing up to 5,000 sequential SaaS calls in one HTTP request (ARCH-27); duplicated payment identity fields on `Order` vs the ledger (ARCH-28).

### 2.4 Where v1 was generous

- **Architecture 7.5** rested on "layering is real" and "shims documented" — both weaker than claimed (§2.2). The strongest genuine positives (config fail-fast validation `config.py:185–233`, centralized error envelope, distributed lock, OpenAPI-preserving refactor discipline) survive scrutiny; the score does not.
- v1 sampled `auth.py` (432 lines) and called it "within reason" without noting the repo's own Done criterion is ~350 lines (`BACKEND_STRUCTURE_REFACTOR_MAP.md` §4 "معیار Done R1") and **four** endpoint files exceed it (auth 432, payment 429, order 391, products_admin 364).
- v1's doc-accuracy score (6/10) never examined the four mandated architecture docs' biggest claim — an entire knowledge platform — nor checked the refactor map's Done criteria against code.

---

## 3. Findings register

Reused IDs = same finding as v1, re-verified. New findings start at ARCH-20.

---

### ARCH-01 — API process is also the job runner and the seeder (multi-worker)
- **Severity:** High (raised from v1 Medium) · **Category:** Architecture/Scalability · **Location:** `app/main.py:32–68`, `app/core/startup.py:57–120`, `gunicorn_conf.py:7`
- **Evidence:** `expiry_task = asyncio.create_task(_order_expiry_worker(stop_event))` in `lifespan` (`main.py:61`); `await bootstrap_super_admin(); await bootstrap_catalog_seed()` (`main.py:58–59`); `workers = int(os.getenv("GUNICORN_WORKERS", max(2, multiprocessing.cpu_count() * 2 + 1)))` (`gunicorn_conf.py:7`).
- **Why problematic:** Every gunicorn worker runs the sweeper loop (Redis lock dedups work, not wakeups) and every worker races the SELECT-then-INSERT seed path (`startup.py:60–62` check is not atomic); on a fresh DB, concurrent workers can collide on unique slug constraints and crash their lifespans. No heartbeat/metric exists for the sweeper; if it dies inside a live process, `pending_payment` orders stop expiring silently. The Hesabfa integration is already accruing more job-shaped work (invoice retries — ARCH-22 — have nowhere to run).
- **Root cause:** No job-runner process in the stack; single-VPS pragmatism.
- **Risk:** Stuck orders; silent job death; startup crash-loop on fresh DB under gunicorn. **Business impact:** abandoned-order cleanup and (future) invoice retries are revenue/accounting-relevant. **Technical impact:** every new periodic need (image sync, price reconciliation, invoice retry) piles onto a pattern with no supervision.
- **Recommendation:** Dedicated job entrypoint (`python -m app.jobs`, same image, compose service with `restart: always`), move seeds into it or into the migration/entrypoint step, add per-job last-run heartbeat exposed via `/ready`.
- **Alternative:** Keep in-process but gate the worker to one designated worker (env flag) and add heartbeat + alert.
- **Effort:** M · **Priority:** P1 · **Dependencies:** none

### ARCH-02 — `scripts/` is an unmanaged business-logic layer
- **Severity:** High (raised from v1 Medium) · **Category:** Maintainability · **Location:** `scripts/` (36 entries)
- **Evidence:** Pricing policy in `scripts/reconcile_prices_availability.py:131–132` (`rial_to_toman`), `:324–327` (per-family markup CSV wiring), `:687` ("PDF rial÷10; Asal toman as-is; markup CSV stored_price as-is"); crawlers (`mitutoyo_crawl.py`, `shopmill_insize_crawl.py`), seeders, backup shell scripts all co-located; 27 commits touched `scripts/` in the last 30 days; zero test coverage (no `tests/` file imports any script).
- **Why problematic:** The company's *entire pricing policy* — the thing that determines revenue per unit — lives in untested one-off scripts with no authoritative-vs-deprecated designation. See also ARCH-21: the data these scripts consume isn't even in the repo.
- **Root cause:** Rapid catalog-import iteration with no import framework.
- **Risk:** Silent mispricing at import; unrepeatable catalog state. **Business impact:** direct margin errors across ~5,900 products. **Technical impact:** duplicated DB boilerplate (13 scripts import `app.*` each with their own session handling).
- **Recommendation:** Promote price conversion/markup into `app/imports/` with unit tests (currency conversion, rounding, markup math); freeze one-offs under `scripts/oneoff/` with dates; add `scripts/README.md` status table.
- **Alternative:** Minimum: tests for `rial_to_toman` + markup application, and a status table.
- **Effort:** M · **Priority:** P1 · **Dependencies:** ARCH-21 (data location)

### ARCH-03 — README still documents abandoned inventory semantics
- **Severity:** Medium · **Category:** Documentation/Correctness · **Location:** `README.md:34`, `README.md:336–347` vs `app/db/models/product.py:154–160`
- **Evidence:** README: "✅ **Stock Management**: Real-time inventory tracking" and `POST /api/v1/products/{product_id}/stock/adjust?quantity_delta=10`; model comment: "Deprecated for sellable UX: warehouse counts live in Hesabfa only"; binary `is_available` at `product.py:158–160`.
- **Why problematic / risk:** Unchanged since v1 flagged it as P1 "cheap fix, prevents recurring bugs" — the fact that a one-hour P1 doc fix survived an audit cycle is itself a due-diligence signal about remediation follow-through. Admin-panel availability regressions (PR #53/#54 area) show the drift's track record.
- **Recommendation:** Rewrite README stock sections around `is_available`; mark quantity endpoints `deprecated=True` in OpenAPI (the Hesabfa stock-pull endpoint already models this correctly — `app/api/endpoints/hesabfa.py:115–131`).
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

### ARCH-04 — Dual content sources for articles + mock data shipped in storefront
- **Severity:** Low · **Category:** Architecture/Coupling · **Location:** `frontend/Storefront/src/data/articles/`, `frontend/Storefront/src/data/mock-data.ts`, `mock-catalog-generator.ts` vs `app/db/models/content.py:31` (`Article`)
- **Evidence:** Static article `how-to-read-vernier-caliper.ts` compiled into the bundle while the backend CMS has publish flags and admin routes; a script `scripts/publish_vernier_article.py` exists to push the same article into the CMS — both paths alive simultaneously.
- **Recommendation:** Pick CMS as the single source; delete `src/data/articles` after migration; scope mock-data files to test builds only.
- **Effort:** S–M · **Priority:** P3 · **Dependencies:** none

### ARCH-05 — Enum values as unconstrained strings at the DB boundary
- **Severity:** Medium · **Category:** Domain-model integrity · **Location:** `app/db/models/commerce.py:89–92`, `:147` (`OrderStatusEvent.status String(100)`), `:69` (`PaymentTransaction.status String(20)`), `app/db/models/product.py:212`
- **Evidence:** as cited; contrast native enums at `commerce.py:85–88` and `product.py:161–165`. No CHECK constraints in any of the 24 alembic revisions (grep).
- **Why problematic:** Policy inconsistency; a script (and `scripts/` writes to the DB constantly — ARCH-02) can persist `status='shiped'` unimpeded; state machine exists only in `app/services/order_service.py`.
- **Recommendation:** CHECK constraints enumerating allowed values; document the "text + CHECK" policy for high-churn enums.
- **Effort:** S · **Priority:** P2 · **Dependencies:** none

### ARCH-06 — Order items carry no product snapshot; nullable price with live-price fallback
- **Severity:** High · **Category:** Domain model / Accounting integrity · **Location:** `app/db/models/commerce.py:129–138`; `app/services/hesabfa/invoices.py:159`
- **Evidence:** `OrderItem` = `order_id, product_id, quantity, unit_price (nullable)`. Invoice push: `unit_toman = Decimal(str(item.unit_price or product.base_price or 0))` — a paid order whose item price is missing gets invoiced at the *current* catalog price.
- **Why problematic:** Historical orders mutate when products are renamed/re-SKUed/re-priced; the fallback in the accounting integration converts a data gap into a wrong legal document. FK on `product_id` has no `ondelete` (RESTRICT), so product hard-deletes are blocked — good — but the snapshot gap remains.
- **Recommendation:** Add `product_name`, `product_sku`, `tax_percent` (or JSONB `product_snapshot`) to `order_items`, populate at checkout, backfill; make `unit_price` NOT NULL for purchase-lane orders; remove the `base_price` fallback in `invoices.py`.
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

### ARCH-07 — Repo-root hygiene (three venvs, artifacts, backups beside code)
- **Severity:** Low (within the repo; the *outer* layout is ARCH-20) · **Category:** Repo structure/DX · **Location:** repo root
- **Evidence:** `.venv/`, `.venv312/`, `venv/`, `.coverage`, `.logo_audit/`, `logs/`, `backups/`, `data/` at root (all untracked); `frontend/Storefront` vs `frontend/admin-panel` casing. Refactor-map items R0.2/R0.3 (`BACKEND_STRUCTURE_REFACTOR_MAP.md` §3) marked as executed 2026-07-18 but the venvs and `.coverage` are present today.
- **Recommendation / Effort / Priority:** as v1: single documented venv, backups off-tree; S · P3.

### ARCH-08 — Version identity is decorative
- **Severity:** Low · **Category:** Release engineering · **Location:** `app/core/config.py:14`; tag `v1.0.0` (2026-06-16); `app/main.py:176–187`
- **Evidence:** 148 commits since the only tag; `/health` and `/` report `"1.0.0"` forever; no `GIT_SHA` injection in `Dockerfile`/workflows.
- **Why problematic:** During an incident nobody can tell which code is live; rollback verification is guesswork on a single VPS where staging and production share the host (see ARCH-20 evidence from `deploy-production.yml:3–5`).
- **Recommendation:** Inject `GIT_SHA` at build (`ARG`→env), expose in `/health`; tag releases or drop the semver pretense.
- **Effort:** S · **Priority:** P2 · **Dependencies:** none

---

### ARCH-20 — Outer workspace chaos: monorepo nested inside a personal git repo, plus a second full clone and unsynced tree copies *(NEW)*
- **Severity:** High · **Category:** Repo structure / Data-loss & leak risk · **Location:** `/home/moahmmad/Projects` (outer), `Website/backend-stat-fix/`, `Website/frontend/`, `Website/.audit_staging/`
- **Evidence:** (a) `/home/moahmmad/Projects/.git` exists and **tracks business files** (`git ls-files` → `Karzar/DOCS/Price/*.pdf` etc.), so the deployable monorepo is nested inside an unrelated personal repo; (b) `Website/backend-stat-fix/` is a **second complete clone** of `Shebahati/Karzar` sitting on `main` @ `e5e89eb` (verified `git remote -v`, `git log`); (c) `Website/frontend/` is a **byte-identical but git-less copy** of `backend/frontend/` (diff of `AI_CONTEXT.md` → SAME, mtime today) — a shadow tree someone edits or syncs manually; (d) `Website/docs/`, `Website/data/`, `Website/logs/`, `Website/tmp/`, `Website/.audit_staging/` are further loose trees.
- **Why problematic:** Work performed in the wrong tree is silently lost or diverges (the shadow `frontend/` copy was touched *today*); the outer repo can accidentally commit secrets/DB dumps that live beside the inner repo; two clones on different branches on the same disk invite deploying or editing the stale one. This is the "confusing outer folder layout" made concrete: **four** copies of frontend docs exist under `Website/`.
- **Root cause:** Ad-hoc working-copy management by a two-person team; hotfix clone (`backend-stat-fix` name matches PR #43's stat-card fix) never deleted.
- **Risk:** Lost edits, stale deploys, secret leakage into the personal outer repo. **Business impact:** unrecoverable confusion during incident response. **Technical impact:** every tool (IDE, agents, scripts) must guess which tree is authoritative.
- **Recommended solution:** Delete `backend-stat-fix` (use branches/worktrees instead); delete or archive the shadow `Website/frontend`, `Website/docs` copies; move `Karzar/DOCS` business files into a proper store (see ARCH-21); remove the `Projects`-level git repo or add ignore rules so it cannot track the nested repos.
- **Alternative:** `git worktree` for parallel branches; a single `WORKSPACE.md` naming the authoritative tree.
- **Effort:** S · **Priority:** P1 · **Dependencies:** ARCH-21

### ARCH-21 — Authoritative pricing data lives on one developer's machine, hardcoded by absolute path *(NEW)*
- **Severity:** Critical · **Category:** Business-continuity / Architecture · **Location:** `scripts/reconcile_prices_availability.py:42–44`
- **Evidence:** `PRICE_DIR = Path(os.getenv("KARZAR_PRICE_DIR", "/home/moahmmad/Projects/Karzar/DOCS/Price"))` and `EXPORT_DATE = "2026-07-25"` (hardcoded, edited per run). The referenced PDFs/CSVs are tracked only by the **personal outer repo** at `/home/moahmmad/Projects` (`git ls-files` shows `Karzar/DOCS/Price/2026-07-25_AST-Power_*.pdf`), which has no verified remote relationship to `Shebahati/Karzar`.
- **Why problematic:** The inputs that set prices for ~5,900 products are outside the deployable repo, outside CI, on a single laptop/VPS home directory, referenced by absolute path and a date constant that must be hand-edited. If that machine or directory is lost, the price-reconciliation pipeline cannot be re-run; nobody else can run it at all. For an acquisition, the revenue-determining data pipeline is effectively *personal property of one engineer*.
- **Root cause:** Import tooling grew out of local experimentation and was never productized.
- **Risk:** Unrepeatable pricing; bus-factor 1; silent divergence between the last import and supplier lists. **Business impact:** direct revenue/margin risk and a due-diligence red flag. **Technical impact:** scripts cannot run on the VPS/CI as written.
- **Recommended solution:** Move price-list source files into versioned object storage or a `data/price-lists/` area with provenance metadata; make `KARZAR_PRICE_DIR` and export date required CLI args; record each import run (file hashes, row counts) in a DB table.
- **Alternative:** Minimum: commit the current price CSVs to the monorepo (they are already derived/markup files) and delete the home-dir default.
- **Effort:** M · **Priority:** P0 · **Dependencies:** ARCH-02, ARCH-20

### ARCH-22 — Failed Hesabfa invoices are dead-ended: recorded, never retried, never surfaced *(NEW)*
- **Severity:** High · **Category:** Domain model / Accounting integrity · **Location:** `app/services/hesabfa/invoices.py:207–214`; `app/db/models/hesabfa.py:51–67`; absence in `app/api/endpoints/hesabfa.py`
- **Evidence:** On any exception the record is set to `status="failed"` with `error_message` (`invoices.py:208–210`) and the result is swallowed ("Best-effort hook … never raises", `:221`). Ripgrep confirms `HesabfaInvoiceRecord` is referenced **only** in `models/hesabfa.py`, `models/__init__.py`, and `invoices.py` — no retry job, no admin list endpoint, no metric. The only periodic worker in the process is order expiry (`main.py:61`).
- **Why problematic:** A transient Hesabfa outage during payment verification permanently loses the accounting invoice for a *paid* order unless a human greps logs. The schema was clearly designed for reconciliation (status column, unique order_id) but the loop was never closed — architecture half-implemented at exactly the money boundary.
- **Root cause:** No job runner (ARCH-01) to host a retry sweep; feature shipped to the "record intent" stage only.
- **Risk:** Books diverge from the site silently. **Business impact:** unbooked revenue in the accounting system; manual reconciliation burden. **Technical impact:** every future best-effort integration will copy this dead-end pattern.
- **Recommended solution:** Periodic retry sweep over `status IN ('pending','failed')` with backoff + max attempts, and an admin endpoint/metric exposing failed count (currently zero visibility).
- **Alternative:** Admin-triggered "retry failed invoices" endpoint as a stopgap.
- **Effort:** S–M · **Priority:** P1 · **Dependencies:** ARCH-01 (job home)

### ARCH-23 — Synchronous external SaaS calls inside payment-verify and product-create request paths, with split commits *(NEW)*
- **Severity:** Medium · **Category:** Hidden coupling / Scalability · **Location:** `app/services/payment_flow_service.py:161–162`; `app/services/product_service.py:34–48` (and `:156` for update); `app/api/endpoints/hesabfa.py:94–112`
- **Evidence:** Payment verify awaits `maybe_create_invoice_after_payment(db, order)` inline — that function performs up to three sequential Hesabfa HTTP calls (contact ensure, item lookups, `save_invoice`; `invoices.py:121–194`) inside the gateway-callback request, bounded only by `HESABFA_TIMEOUT_SECONDS=15` each. Product create commits, then calls Hesabfa, then commits again (`product_service.py:34, 41`) — a failure between commits leaves the push unrecorded with no retry (see ARCH-22 pattern).
- **Why problematic:** The customer-facing payment callback latency is coupled to a third-party accounting SaaS; a slow Hesabfa adds up to ~45s to the verify request (worker slot held; gunicorn `timeout=60`). Commit-splitting in services makes transaction boundaries a per-method surprise rather than a layer property.
- **Root cause:** No async job/outbox mechanism; "best-effort inline" chosen as the cheapest integration.
- **Risk:** Slow/timed-out payment callbacks at the worst possible UX moment; worker-pool exhaustion under Hesabfa degradation. **Business impact:** checkout abandonment/perceived payment failure. **Technical impact:** transaction semantics differ per service method.
- **Recommended solution:** Transactional-outbox row written in the payment-verify transaction; a worker (ARCH-01) performs the Hesabfa calls. Same for item push on product create/update.
- **Alternative:** `asyncio.create_task` fire-and-forget with the invoice record as the durable intent — weaker but zero-infra.
- **Effort:** M · **Priority:** P2 · **Dependencies:** ARCH-01, ARCH-22

### ARCH-24 — The "temporary" crud shims became the canonical import path; refactor R3 abandoned mid-flight *(NEW; supersedes v1's benign framing)*
- **Severity:** Medium · **Category:** Layering / Maintainability · **Location:** `app/crud/platform.py:1–33`; consumers: `app/api/deps.py:14`, `checkout.py:14`, `order.py:19`, `payment.py:19`, `auth.py:237`, `users.py:115`, `products_admin.py:349`, `app/services/auth_token_service.py:9`, `audit_service.py:7`, `idempotency_service.py:14`; `app/crud/content.py:8` (OTP re-export)
- **Evidence:** The refactor map prescribes "سپس در PR بعدی shim حذف شود" (*delete the shim in the next PR*, `BACKEND_STRUCTURE_REFACTOR_MAP.md` §5.1) and Done-R3 = zero `from app.crud` in endpoints (§6.4). Instead, ten modules — including **new** code — import through `crud.platform`; almost nothing imports the split modules directly. Four endpoint files exceed the map's own 350-line R1 bar (auth 432, payment 429, order 391, products_admin 364). `OtpCode`/`OtpPurpose` still live in `app/db/models/content.py:88–100` — the map's "biggest domain smell" (§5.2) was fixed at the crud layer only.
- **Why problematic:** A shim used as the primary API is an inverted dependency: the indirection outlives its purpose and hides the real module boundaries; the documented plan and the code have diverged in a way `docs/ARCHITECTURE.md` ("compat", "temporary") actively misrepresents.
- **Root cause:** Refactor stopped after R2; no lint rule was ever added (map §6.4 planned one).
- **Risk:** Boundary erosion compounds; newcomers cargo-cult the shim. **Technical impact:** module graph illegible; the planned `crud/` domain packages can no longer be introduced mechanically.
- **Recommended solution:** Decide: either finish R3 (repoint imports to split modules, delete shims, add the ruff import-ban) or officially bless `crud.platform` as a façade and update the docs to stop calling it temporary.
- **Alternative:** Freeze with a lint rule preventing *new* `crud.platform` imports.
- **Effort:** M · **Priority:** P2 · **Dependencies:** none

### ARCH-25 — Dev sample catalog seeds unconditionally on any empty database *(NEW)*
- **Severity:** Medium · **Category:** Startup composition / Environment hygiene · **Location:** `app/core/startup.py:57–120`, wired at `app/main.py:59`
- **Evidence:** `bootstrap_catalog_seed()` — docstring "for local E2E testing" — runs in `lifespan` in every environment; if `categories` is empty it inserts three categories, three brands, and a **purchasable** product `DEV-CHECKOUT-001` with `is_available=True`, price 250,000 (`startup.py:94–115`). No `APP_ENV` gate; the check-then-insert is racy across gunicorn workers (unique-slug collision ⇒ lifespan crash on some workers).
- **Why problematic:** A production disaster-recovery restore that briefly starts the API against an empty DB puts a fake sellable product live on karzartools.com. Startup-time data mutation from the API process also blocks read-only replicas or multi-instance rollout by design.
- **Root cause:** Local-E2E convenience placed in the production composition path.
- **Recommendation:** Gate on `APP_ENV != "production"` (one line), or move seeding to `scripts/`/entrypoint behind an explicit flag; make insert idempotent via `ON CONFLICT DO NOTHING`.
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

### ARCH-26 — Knowledge platform: 1,337 lines of architecture docs, zero lines of code *(NEW; doc-drift, see §4)*
- **Severity:** Medium (as a due-diligence/asset-valuation matter; the docs are honest about status) · **Category:** Documentation / Roadmap risk · **Location:** `docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` vs `app/`, `alembic/`
- **Evidence:** Phase 2 (632 lines) specifies module catalog M0–M8, knowledge routers `/api/v1/knowledge/*`, jobs tables; Phase 3 (368 lines) is an I0–I15 roadmap estimated **18–32 engineering days**, status "awaiting approval to start Implementation Slice I0". Ripgrep for `knowledge` across `app/` and `alembic/`: **zero hits**. No feature flags from the I0 spec exist in `config.py`.
- **Why problematic:** Not deceptive — the docs state design-only — but any valuation that counts "knowledge platform" as an asset must be corrected: it is a plan whose prerequisite (a jobs/worker foundation, I6) is precisely the gap called out in ARCH-01/22. A three-phase, 4–7-week program for a two-person team also competes with the unfinished R3 refactor and the payments go-live.
- **Recommendation:** Either fund I0–I5 with dates or mark the suite `STATUS: PARKED` prominently; do not present it externally as in-progress capability.
- **Effort:** S (doc), XL (implementation) · **Priority:** P3 · **Dependencies:** ARCH-01

### ARCH-27 — Bulk external sync endpoints run unbounded sequential SaaS calls in one HTTP request *(NEW)*
- **Severity:** Medium · **Category:** Scalability-by-design · **Location:** `app/api/endpoints/hesabfa.py:89–112` (`POST /hesabfa/items/push`, `limit ≤ 5000`), `:63–86` (`/mappings/sync` scans all Hesabfa items)
- **Evidence:** `push_all_site_products_to_hesabfa(db, limit=limit)` executes inside the request; with ~5,900 products and per-call latency this exceeds gunicorn `timeout=60` (`gunicorn_conf.py:10`) by an order of magnitude, killing the worker mid-push. No progress persistence beyond per-item mapping rows; no idempotency key; admin retries re-scan everything.
- **Why problematic:** The design guarantees admin-visible failures on realistic data volume; the "solution" (repeated invocation with `limit`) is manual pagination of a batch job through HTTP.
- **Recommendation:** Move to the job runner (ARCH-01) with a progress row; endpoint becomes "enqueue + status".
- **Alternative:** Chunked endpoint with cursor + `Retry-After`, keeping each request < 30 s.
- **Effort:** M · **Priority:** P2 · **Dependencies:** ARCH-01

### ARCH-28 — Payment identity duplicated between `Order` columns and the transaction ledger *(NEW)*
- **Severity:** Low · **Category:** Domain-model coherence · **Location:** `app/db/models/commerce.py:108–110` vs `:51–72`
- **Evidence:** `Order.payment_authority` (unique), `payment_ref_id`, `payment_refund_id` coexist with the `payment_transactions` ledger that stores `authority`/`ref_id`/`status` per attempt; verify logic reads/writes the Order columns (`payment_flow_service.py:94, 124, 152–153`).
- **Why problematic:** Two sources of truth for gateway identity. The unique constraint on `Order.payment_authority` also structurally forbids a **second payment attempt with a new authority** after a failed one — retrying a failed payment requires overwriting the column, orphaning the ledger linkage (`existing` short-circuit at `payment_flow_service.py:80–85` returns the old authority even after failure).
- **Risk:** A customer whose first gateway attempt failed may be unable to pay again without support intervention (state must be inspected to confirm exact behavior — see §6).
- **Recommendation:** Treat `payment_transactions` as the source of truth; derive "current authority" from the latest initiated transaction; drop or demote the Order columns to a cache.
- **Effort:** M · **Priority:** P2 · **Dependencies:** none

---

## 4. Architecture-doc drift table (mandated docs vs code)

| Doc | Claim | Reality in code | Verdict |
|---|---|---|---|
| `docs/ARCHITECTURE.md:3` | "structure refactor R0–R2 (+ partial R3)" executed | R0 partially false: `.venv/.venv312/venv`, `.coverage` still at root (untracked but present); R1 done as described (aggregators `product.py`/`storefront.py` exist and match); R2 done (`crud/otp.py`, `cart_persistence.py`, etc. exist) | **Mostly accurate**, overstates R0 |
| `docs/ARCHITECTURE.md:55–59` | shims are "compat", implying transitional | Shims are the *primary* import path for 10 modules incl. new code (ARCH-24) | **Drift** — framing no longer true |
| `docs/ARCHITECTURE.md:8–44` root-layout tree | Tree matches (`endpoints/` files all exist; `utils/category` package exists as facade over still-present loose `category_*.py` files — both coexist) | **Accurate with omissions** (no mention of `openapi/`, `deploy/`, dual category-utils paths) |
| `BACKEND_STRUCTURE_REFACTOR_MAP.md` §4 Done-R1 "no endpoint file > ~350 lines" | auth 432, payment 429, order 391, products_admin 364 | **Failed own criterion** |
| `BACKEND_STRUCTURE_REFACTOR_MAP.md` §6 Done-R3 "zero `from app.crud` in endpoints" + ruff lint rule | 14 endpoint files import crud; no lint rule in `pyproject.toml` | **Not executed** (map itself says R3 "جزئی" — honest) |
| `BACKEND_STRUCTURE_REFACTOR_MAP.md` §5.2 "OTP separation — biggest domain smell" | `crud/otp.py` exists, but `OtpCode`/`OtpPurpose` models remain in `db/models/content.py:88–100`; `crud/content.py:8` still re-exports OTP | **Half-executed** |
| `BACKEND_COMPREHENSIVE_AUDIT_PLAYBOOK.md:4` | "وضعیت: A–H PASS (B PARTIAL)" — self-audit passed all phases | Playbook is a checklist doc; its PASS statuses are self-graded with no linked evidence artifacts in the repo. B-PARTIAL matches our findings (layering); but F "پرداخت و یکپارچگی مالی PASS" coexists with ARCH-06/22/28 | **Self-graded PASS overstated** for F |
| `KNOWLEDGE_PLATFORM_PHASE1..3` | Phase 1 audit "Complete", Phase 2 design "Complete", Phase 3 "awaiting approval to start I0" | Zero knowledge-platform code, tables, flags, or routes in `app/`, `alembic/`, `config.py` | **Consistent — design-only. Vaporware if presented as capability** (ARCH-26) |

---

## 5. Scores (strict rubric)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| **Architecture** | 7.5 | **6.0** | v1's two strongest pillars partially collapse under verification: layering is violated in 14/19 endpoint modules against the repo's own written rule, and "append-only ledgers" are cascade-deletable conventions. Genuine strengths remain (fail-fast config `config.py:185–233`, error envelope, request-ID context, dual-lane domain model, contract-preserving refactor discipline) and keep this at the top of the 5–6 band, but money-path architecture (no outbox, no retry, inline SaaS calls, no snapshot) is a systemic weakness a due-diligence team prices in. |
| **Maintainability** | 6.5 | **5.5** | Refactor R3 abandoned with shims canonized (ARCH-24); four endpoint god-files exceed the team's own bar; `scripts/` is 36 untested files churning 27 commits/month with pricing policy inside (ARCH-02/21); README P1 fix from v1 not executed (ARCH-03). Counterweights: real test suite (36 files), consistent service naming, honest refactor map. |
| **Scalability-by-design** | 6.0 | **5.0** | Single process is API + sweeper + seeder + bulk-sync executor (ARCH-01/25/27); payment callback latency coupled to a third-party SaaS (ARCH-23); production shares a VPS with staging (`deploy-production.yml:3–5`); startup-time DB writes block multi-instance rollout by design. Redis-backed locks/throttles and stateless JWT auth are the mitigating design choices that keep it at 5. |

---

## 6. Self-review — what remains unverified

1. **Runtime behavior not executed.** We did not boot the app, run the test suite, or hit endpoints; all findings are static-analysis based. In particular the multi-worker seed race (ARCH-01/25) and the failed-payment retry lockout (ARCH-28) are schema/code-path deductions, not reproduced incidents.
2. **`backend-stat-fix` purpose** inferred from its branch/PR contents (`e5e89eb`, stat-card fix); it may be a deliberate deploy checkout — either way the risk stands, but intent is unconfirmed.
3. **Hesabfa production configuration** (`HESABFA_ENABLED`, `HESABFA_TEST_MODE` values on the VPS) is unknown; ARCH-22/23 severity assumes the integration is or will be live, consistent with `docs/HESABFA.md` and recent commit activity.
4. **Outer repo remote** — whether `/home/moahmmad/Projects/.git` pushes anywhere (and thus whether price PDFs have any off-machine backup) was not verifiable from here.
5. **Frontend import graph** (Storefront/admin-panel internals) was sampled only for the static-articles and mock-data findings; a full frontend architecture pass is out of this report's scope.
6. **Circular imports:** no hard cycles found (lazy imports at `crud/product.py:428`, `product_service.py:38` are one-directional precautions), but this was verified by grep, not by an import-time execution trace.
