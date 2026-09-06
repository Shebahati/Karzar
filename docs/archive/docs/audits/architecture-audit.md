# Phase 1 — Architecture, Repository Structure & Domain Model Audit

**Date:** 2026-07-25 · **Auditors:** Principal Software Architect, Engineering Manager, Principal Reviewer
**Scope:** Monorepo layout, backend layering, domain model design, module boundaries, documentation accuracy.
**Method:** Full read of `app/main.py`, `app/core/config.py`, `app/api/v1`, `app/api/deps.py`, all `app/db/models/*`, `docs/ARCHITECTURE.md`, README, module size census.

---

## 1. Objectives & evaluation criteria

- Does the implemented architecture match the documented one?
- Are layer boundaries real or aspirational?
- Is the domain model coherent for an industrial-commerce business?
- Where is hidden coupling and hidden debt?

## 2. What is genuinely good (verified)

1. **The layered architecture is real, not aspirational.** Requests flow
   endpoints → `deps.py` (authn/z) → services → crud → models, and the module
   census confirms logic lives in `app/services/` (18 services incl. a
   `hesabfa/` package) rather than in route handlers. The largest endpoint file
   (`auth.py`, 432 lines) is within reason.
2. **Configuration is a strength.** `app/core/config.py` fail-fast validates:
   weak `SECRET_KEY` placeholders rejected, production mode forbids `DEBUG`,
   mock payments, console SMS, API docs, wildcard CORS, missing Redis, weak
   step-up PINs and OTP echo (`validate_production_security`, lines 185–233).
   This is above-average discipline for a project of this age.
3. **Cross-cutting concerns are centralized**: request-ID context, error
   envelope (`core/errors.py`), security headers middleware, body-size limit,
   proxy-header trust, distributed lock for the background sweeper.
4. **Refactor debt is documented, not hidden** — `docs/ARCHITECTURE.md`
   explicitly lists compat shims (`crud/platform.py`, `crud/content.py`
   re-exports) with the contract rule "file moves must not change `/api/v1`".
5. **Domain model covers the real business**: dual-lane commerce
   (purchase + B2B inquiry) is modeled first-class (`OrderMode`, `CartLane`),
   ledger tables are append-only (`StockMovement`, `PaymentTransaction`),
   idempotency and step-up-token single-use are DB-backed.

## 3. Findings

### ARCH-01 — Background worker lives inside the API process
- **Severity:** Medium · **Category:** Architecture/Scalability · **Location:** `app/main.py:32–68`
- **Evidence:** `_order_expiry_worker` is an `asyncio.Task` started in FastAPI `lifespan`, guarded by a Redis distributed lock.
- **Why problematic:** Ties job execution to web-worker lifecycle. With multiple Gunicorn workers every worker runs the loop (lock prevents double work but not wasted wakeups); worker restarts silently kill the task; there is no visibility (no metric/heartbeat) if the sweeper dies inside a live process. Hesabfa pushes and future jobs (stock/image sync) will pile onto this pattern.
- **Root cause:** No job runner in the stack; single-VPS pragmatism.
- **Risk / impact:** Orders stuck in `pending_payment` if the loop dies; future job classes multiply the pattern. Business impact: abandoned-order cleanup and invoice pushes are revenue/accounting-relevant.
- **Recommendation:** Extract periodic jobs into a dedicated process (same image, different entrypoint, e.g. `python -m app.jobs`) supervised by compose `restart: always`; add a heartbeat metric per job.
- **Alternative:** Keep in-process but add a `/health`-checked last-run timestamp and alerting.
- **Effort:** M · **Priority:** P2 · **Dependencies:** none

### ARCH-02 — `scripts/` mixes production business logic with one-off scrapers
- **Severity:** Medium · **Category:** Maintainability · **Location:** `scripts/` (~35 files)
- **Evidence:** `import_price_lists.py`, `reconcile_prices_availability.py` encode pricing rules (rial÷10 conversions, per-brand markups ×1.10/×1.20), alongside crawlers (`mitutoyo_crawl.py`, `shopmill_insize_crawl.py`) and seeders. None are covered by the test suite; several duplicate DB-access boilerplate instead of reusing `app/` services.
- **Why problematic:** Pricing/markup policy is business-critical yet lives in untested, unversioned-policy scripts. Two scripts already collided in an add/add merge conflict this week (`import_shopmill_brand_images.py`), evidence the area is churn-heavy.
- **Root cause:** Rapid catalog-import iteration without a designated import framework.
- **Risk:** Silent mispricing at import time; nobody can say which script is authoritative for a brand.
- **Recommendation:** Split `scripts/` into `scripts/oneoff/` (frozen, dated) and `app/imports/` (maintained, tested import pipelines with shared price-conversion helpers). Add unit tests for currency conversion and markup math.
- **Alternative:** Keep layout but add a `scripts/README.md` status table (authoritative / deprecated / one-off) and tests for the two pricing scripts.
- **Effort:** M · **Priority:** P2

### ARCH-03 — Documentation drift on inventory semantics
- **Severity:** Medium · **Category:** Documentation/Correctness · **Location:** `README.md` (Features, Stock Management sections) vs `app/db/models/product.py:154–160`
- **Evidence:** README advertises "Stock Management: Real-time inventory tracking" and documents `POST .../stock/adjust`, while the model comments `stock_quantity` as "Deprecated for sellable UX: warehouse counts live in Hesabfa only" and the business now runs binary `is_available`.
- **Why problematic:** New engineers and API consumers will build against quantity semantics the business has abandoned. The admin panel already had availability/mock-stock regressions this week (PRs #53/#54 area) — drift has a track record here.
- **Recommendation:** Rewrite README stock sections around `is_available`; mark quantity endpoints deprecated in OpenAPI (`deprecated=True`) and in `docs/API_CONTRACT.md`.
- **Effort:** S · **Priority:** P1 (cheap, prevents recurring bugs)

### ARCH-04 — Dual content sources for blog articles
- **Severity:** Low · **Category:** Architecture/Coupling · **Location:** `frontend/Storefront/src/data/articles/` vs backend `articles` table + `/api/v1/blog/`
- **Evidence:** The storefront ships static article data while the backend has a CMS `Article` model with publish flags and admin routes.
- **Why problematic:** Two sources of truth for the same surface; content editors cannot rely on the CMS if some articles are compiled into the bundle.
- **Recommendation:** Migrate static articles into the CMS and delete `src/data/articles`, or explicitly designate static content as "evergreen docs" distinct from blog.
- **Effort:** S–M · **Priority:** P3

### ARCH-05 — Enum values duplicated as raw strings at the DB boundary
- **Severity:** Medium · **Category:** Domain model integrity · **Location:** `app/db/models/commerce.py:89` (`Order.status: String(100)`), `:90–92` (`payment_status: String(20)`), `product.py:212` (`StockMovement.movement_type: String(20)`)
- **Evidence:** Python enums (`OrderStatus`, `PaymentStatus`, `StockMovementType`) exist, but the columns are free-text with no CHECK constraint, while other columns (`OrderMode`, `CartLane`, `UserRole`) use native PG enums.
- **Why problematic:** Inconsistent policy; nothing stops an invalid `status='shiped'` write from a script or future bug. State machines enforced only in service code.
- **Root cause:** Native-enum migration pain avoidance for high-churn enums (a defensible choice, but then a CHECK constraint should exist).
- **Recommendation:** Add CHECK constraints listing allowed values (cheap to alter later) or move to native enums; document the policy either way.
- **Effort:** S · **Priority:** P2

### ARCH-06 — Order items carry no product snapshot
- **Severity:** High · **Category:** Domain model / Accounting integrity · **Location:** `app/db/models/commerce.py:129–138`
- **Evidence:** `OrderItem` stores only `product_id`, `quantity`, `unit_price`. Name, SKU, tax, and spec at time of sale are not captured.
- **Why problematic:** Renaming or re-SKUing a product mutates the apparent content of historical orders and invoices; if a product row were ever hard-deleted the FK (no `ondelete`, default RESTRICT) blocks it or orphaned history follows. For a platform that must reconcile with Hesabfa accounting, order lines must be immutable evidence.
- **Recommendation:** Add `product_name`, `product_sku` (and optionally `tax_percent`) columns to `order_items`, populated at checkout; backfill from current products.
- **Alternative:** JSONB `product_snapshot` column.
- **Effort:** S · **Priority:** P1

### ARCH-07 — Monorepo hygiene: stray environments and artifacts in repo root
- **Severity:** Low · **Category:** Repo structure/DX · **Location:** repo root
- **Evidence:** Three virtualenvs (`.venv/`, `.venv312/`, `venv/`), `.coverage`, cache dirs, `logs/`, `backups/`, `data/` and a `.logo_audit/` scratch dir live beside source (untracked but present); naming is inconsistent (`frontend/Storefront` vs `frontend/admin-panel`).
- **Why problematic:** Onboarding confusion ("which venv?"), risk of accidental data commits, backup files co-located with code on the same disk.
- **Recommendation:** Keep exactly one venv path in docs; move backups/data outside the repo tree on the VPS; normalize casing to `frontend/storefront` at a low-churn moment (coordinate with CI paths).
- **Effort:** S · **Priority:** P3

### ARCH-08 — Version identity duplicated and stale
- **Severity:** Low · **Category:** Documentation · **Location:** `app/core/config.py:14` (`VERSION = "1.0.0"`), README footer ("Last Updated 2026-07-12")
- **Evidence:** Rapid daily changes ship (PR #40–#56 in one week) but the version string and README date never move; API changelog exists but version constant is decorative.
- **Recommendation:** Derive version from git tag/SHA at build (`GIT_SHA` env into `/health`), or maintain semver honestly.
- **Effort:** S · **Priority:** P3

## 4. Self-challenge (what we tried to disprove)

- *"Layering is cosmetic"* — disproved by module census; services carry the orchestration weight.
- *"Config validation is theater"* — checked validators execute at import (`settings = Settings()` at module load) so a bad prod config genuinely prevents boot.
- *"Compat shims are hidden debt"* — they are debt but documented; risk is bounded because tests import both paths.
- Remaining doubt: we did not measure how many route handlers bypass services and call `crud` directly; spot checks (`products_catalog.py`, `order.py`) show mostly service-mediated flows with some direct `crud` reads, acceptable for read paths.

## 5. Scores

| Category | Score | Justification |
|---|---|---|
| Architecture | **7.5/10** | Real layering, strong config discipline, documented shims; loses points for in-process jobs, scripts sprawl, enum policy inconsistency. |
| Domain model | **7/10** | Dual-lane commerce and ledgers well modeled; order-item snapshot gap and free-text statuses are real integrity risks. |
| Repository structure | **6.5/10** | Clear monorepo roles; hygiene and naming inconsistencies; scripts folder unmanaged. |
| Documentation accuracy | **6/10** | Unusually rich docs, but README/API drift on inventory semantics is misleading today. |
