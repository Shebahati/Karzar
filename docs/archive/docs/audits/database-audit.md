# Phase 2 — Database & Data Model Audit

**Date:** 2026-07-25 · **Auditors:** Database Architect, Staff Backend Engineer, Principal Reviewer
**Scope:** All ORM models (`app/db/models/*`), engine/session config, 24 Alembic migrations, index strategy vs. actual query patterns (`app/crud/*`, `app/utils/jsonb_filters.py`, `app/utils/storefront_catalog.py`).
**Live context:** ~5,900 products, 40 brands, 159 categories, low order volume (<1000/month target).

---

## 1. What is genuinely good (verified)

1. **Money is `Numeric`, never float** (`Numeric(15,2)` prices, `Numeric(12,2)` quantities) with Toman as the site unit and explicit rial conversion for Hesabfa.
2. **Soft-delete-aware uniqueness** — `uq_products_sku_active` is a partial unique index `WHERE deleted_at IS NULL` (`product.py:130–135`): the correct pattern, allowing SKU reuse after deletion without breaking history.
3. **Single-primary-image invariant enforced in the DB** — partial unique index `uq_product_images_one_primary WHERE is_primary IS TRUE`.
4. **Timestamps are timezone-aware and double-enforced**: `Base` sets `server_default=func.now()` + ORM `onupdate`, and migration `g3h4i5j6k7l8` adds DB triggers `set_updated_at()` so even raw SQL writes maintain `updated_at`.
5. **Append-only ledgers**: `stock_movements`, `payment_transactions`, `order_status_events` give auditability; `idempotency_keys (scope,key)` unique and `step_up_token_uses.jti` unique give replay protection at the storage layer.
6. **Secrets-at-rest hygiene**: OTP codes stored as SHA-256 (`otp_codes.code` 64 chars), refresh tokens stored as hash (`refresh_tokens.token_hash`).
7. **Eager loading is disciplined** — order/cart/product reads use `selectinload` consistently (`crud/commerce.py`, `crud/product.py:30–32`); we found no obvious N+1 on hot paths.
8. **Migration chain is clean**: 24 linear revisions, integrity migration added FKs/indexes/triggers deliberately; a data-repair migration (`t5u6v7w8x9y0`) fixed OTP column length properly rather than patching in prod.

## 2. Findings

### DB-01 — Order lines are not immutable snapshots
- **Severity:** High · **Category:** Data integrity / Accounting · **Location:** `app/db/models/commerce.py:129–138`
- **Evidence:** `OrderItem(product_id, quantity, unit_price)` only. Product rename/re-SKU rewrites what historical orders appear to contain; `order_items.product_id` FK has no `ondelete` (RESTRICT), so a future hard-delete path either fails or forces cascade decisions ad hoc.
- **Why problematic:** Orders feed Hesabfa invoices; line-item evidence must be stable for accounting and dispute handling.
- **Root cause:** Model built for display, not for bookkeeping.
- **Business impact:** Wrong historical invoices/quotes; audit friction. **Technical impact:** Cannot safely clean catalog.
- **Recommendation:** Add `product_name`, `product_sku`, `tax_percent` to `order_items` written at checkout; backfill. · **Alternative:** `product_snapshot JSONB`.
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

### DB-02 — Lifecycle states stored as unconstrained text
- **Severity:** Medium · **Category:** Integrity · **Location:** `commerce.py:89` (`Order.status String(100)`), `:90` (`payment_status String(20)`), `product.py:212` (`movement_type String(20)`)
- **Evidence:** Python enums exist (`OrderStatus`, `PaymentStatus`, `StockMovementType`) but no CHECK constraint or native enum on these columns, unlike `ordermode`/`cartlane`/`userrole` which are native PG enums. Migration `s4t5u6v7w8x9` added CHECKs elsewhere, so the tooling pattern exists.
- **Risk:** Scripts (35 of them touch this DB) or future bugs can write invalid states; queries filtering `status='paid'` silently miss typo'd rows.
- **Recommendation:** `CHECK (status IN (...))` constraints — cheaper to evolve than native enums, closes the hole.
- **Effort:** S · **Priority:** P2

### DB-03 — Spec filters cannot use the GIN index they sit next to
- **Severity:** Medium · **Category:** Performance/Scalability · **Location:** `app/utils/jsonb_filters.py:80–86` vs `product.py:136–140`
- **Evidence:** `ix_products_specifications_gin` (default `jsonb_ops`) accelerates `@>`, `?`, `?&` operators. The filter builder emits `specifications->'a'->>'b' = 'x'` and `...->>'b' ILIKE '%x%'` — expression comparisons that **bypass GIN** entirely → sequential scans.
- **Why problematic:** Works at 6k products; degrades linearly as catalog grows toward 50k+. The index costs write overhead while delivering nothing for these queries.
- **Recommendation:** For exact matches, rewrite to containment: `specifications @> '{"technical_specs":{"range":"0-150mm"}}'::jsonb` (GIN-eligible). Keep `__icontains` as-is but document it as slow path; add expression B-tree indexes for the 2–3 hottest spec keys per major category.
- **Alternative:** Promote hot spec keys to real columns during import.
- **Effort:** M · **Priority:** P2

### DB-04 — Catalog search is `ILIKE '%term%'` with no trigram index
- **Severity:** Medium · **Category:** Performance · **Location:** `app/crud/product.py:199–203`
- **Evidence:** Search ORs `name/sku/brand.name ILIKE '%…%'` (properly escaped via `escape_ilike_pattern` — good), but no `pg_trgm` GIN/GiST index exists in any migration; leading-wildcard ILIKE cannot use B-tree indexes.
- **Impact:** Full scans on every storefront search keystroke path; also no Persian-aware ranking (no FTS at all).
- **Recommendation:** `CREATE EXTENSION pg_trgm` + GIN trigram indexes on `products.name`, `products.sku`, `brands.name`. Consider simple unaccent/normalization for Persian variants (ی/ي، ک/ك) at write time — normalization matters more than FTS here.
- **Effort:** S (indexes) / M (normalization) · **Priority:** P2

### DB-05 — Business invariant "priced ⇔ available" exists only in scripts
- **Severity:** Medium · **Category:** Integrity · **Location:** `products.is_available` (migration `x9y0z1a2b3c4`), enforcement in `scripts/reconcile_prices_availability.py`
- **Evidence:** The business rule (no price → unavailable) was applied by a one-off script; nothing prevents `is_available=true, base_price=NULL` from admin edits or imports. Current data is consistent (verified 2026-07-25: 0 violations) but only by discipline.
- **Recommendation:** `CHECK (NOT is_available OR base_price IS NOT NULL)` after confirming admin flows can't strand rows; plus service-layer guard with a clear Persian error.
- **Effort:** S · **Priority:** P2

### DB-06 — Housekeeping columns lack supporting indexes
- **Severity:** Low · **Category:** Performance/Operations
- **Evidence:** No index on `otp_codes.expires_at`, `idempotency_keys.expires_at`, `refresh_tokens.expires_at` (cleanup sweeps / revocation checks scan), none on `orders.payment_status` (admin filtering). `step_up_token_uses.expires_at` **is** indexed — the pattern is known but unevenly applied.
- **Recommendation:** Add the three expiry indexes and a partial index `orders(payment_status) WHERE deleted_at IS NULL` if admin filters on it.
- **Effort:** S · **Priority:** P3

### DB-07 — Category tree integrity is app-enforced only
- **Severity:** Low · **Category:** Integrity · **Location:** `product.py:91`, `app/utils/category_depth.py`, `category_validation.py`
- **Evidence:** `parent_id` self-FK without cycle protection; depth limits and delete-reassignment live in services (tests exist: `test_category_delete_reassignment.py`, `test_category_depth.py`). A concurrent pair of updates could still create a cycle (no DB guard, no advisory lock).
- **Recommendation:** Accept risk at current team size but add a `CHECK (parent_id != id)` (self-loop) now; document the tree-mutation lock strategy.
- **Effort:** S · **Priority:** P3

### DB-08 — Spec templates vs stored JSONB have no schema versioning
- **Severity:** Medium · **Category:** Maintainability · **Location:** `get_default_specifications()` (`product.py:49–69`), `categories.spec_template_key`, `app/services/spec_template_service.py`
- **Evidence:** Every product stores a full nested skeleton (measurement-tool oriented: `battery_type`, `waterproof`) even for cutting tools; template evolution has no version marker, so old rows silently diverge from new template expectations.
- **Risk:** Filter UIs built on template keys return incomplete results for legacy rows; imports write divergent shapes.
- **Recommendation:** Add `spec_version` inside the JSONB, write per-category defaults from the template (not a global skeleton), and a backfill/migration playbook per template change.
- **Effort:** M · **Priority:** P2

### DB-09 — Connection budget vs. single-VPS Postgres
- **Severity:** Low · **Category:** Operations · **Location:** `app/db/database.py:13–21`
- **Evidence:** `pool_size=20, max_overflow=10` **per process**. With N Gunicorn workers, worst case N×30 connections against default `max_connections=100` — 4 workers ≈ 120 > 100.
- **Recommendation:** Size pool per worker count (e.g. 5+5 with 4 workers) or add PgBouncer; verify `gunicorn_conf.py` worker count against this budget.
- **Effort:** S · **Priority:** P2 (cheap outage prevention)

### DB-10 — Autogenerate compares are not strict
- **Severity:** Low · **Category:** DX/Migrations · **Location:** `alembic/env.py`
- **Evidence:** `context.configure(...)` without `compare_type=True` / `compare_server_default=True` — type drift between models and DB can pass unnoticed in autogenerated revisions.
- **Recommendation:** Enable both flags; review next autogenerate diff carefully.
- **Effort:** S · **Priority:** P3

### DB-11 — `users.email` is free-form
- **Severity:** Low · **Location:** `user.py:34`
- **Evidence:** Nullable, no unique constraint, no format validation at DB level (schema-level unknown until backend phase).
- **Recommendation:** Partial unique index `WHERE email IS NOT NULL` if email is ever used for login/notifications.
- **Effort:** S · **Priority:** P3

## 3. Self-challenge

- Checked whether the GIN finding is wrong (maybe filters use `@>` somewhere): searched — only `astext` comparisons exist; finding stands.
- Checked whether status CHECKs exist in later migrations (`s4t5u6v7w8x9` hardening): it constrains other fields; statuses remain unconstrained.
- Checked N+1 accusations: `selectinload` usage disproves the default accusation on hot paths; PLP thumbnail resolution should be re-verified in backend phase (presenter reads `images` relationship — eager-loaded in `crud/product.py:30`).
- We did **not** run `EXPLAIN` against the live DB (audit is code-first); performance findings are structural, not measured.

## 4. Scores

| Category | Score | Justification |
|---|---|---|
| Schema design | **7.5/10** | Ledgers, partial unique indexes, tz-aware triggers, hashed secrets — strong; loses points for order-snapshot gap and text statuses. |
| Data integrity | **6.5/10** | Key invariants (SKU, primary image, rating range) DB-enforced; lifecycle states and price↔availability are not. |
| Index & query strategy | **6/10** | Sensible B-trees and eager loading; GIN mismatch and missing trigram/expiry indexes are structural gaps. |
| Migrations | **8/10** | Clean 24-revision chain, integrity/trigger migrations done right; minor env strictness gap. |
| Scalability posture | **6/10** | Fine at 6k products/low orders; search+spec filtering and connection budget need work before 10× growth. |
