# Phase 2 (v2) — Database & Data Model Audit — STRICT MODE

**Date:** 2026-07-25 · **Team:** Database Architect (v2 hostile due-diligence re-audit)
**Baseline:** v1 report `docs/audits/database-audit.md` (scores: Database 7.0, Performance 6.0, Scalability 6.0)
**Repo state:** branch `docs/engineering-audit-2026-07`, HEAD `66e9ae9`. Migration head: `y0z1a2b3c4d5`.

---

## 1. Scope & method

- **Read in full:** all 7 model modules (`app/db/models/{base,product,commerce,user,content,platform,hesabfa}.py`), all **23** Alembic revisions in `alembic/versions/` (v1 claimed 24 — miscount), `alembic/env.py`, `app/db/database.py`, `gunicorn_conf.py`, `docker-entrypoint.sh`, all 4 compose files, `requirements.txt`.
- **Query layer:** `app/crud/{product,commerce,category,content,platform,cart_persistence,idempotency,otp,refresh_tokens}.py`, `app/utils/{jsonb_filters,storefront_catalog,specifications}.py`, `app/services/{checkout_service,cart_service,order_expiry_service,payment_flow_service,stock_ledger_service,idempotency_service}.py`, `app/api/endpoints/checkout.py`, `app/main.py` lifespan worker.
- **Redis:** `app/core/{rate_limit,distributed_lock,request_throttle}.py` + compose Redis service definition.
- **Docs:** `docs/SEED_IMPORT.md`, `docs/OPERATIONS.md`, CI workflow `backend-ci.yml`, `tests/conftest.py`.
- **Not done (constraint):** no live-DB connection; no `EXPLAIN`, no `alembic check` against a running instance. All drift/performance findings are structural, derived from code + migration DDL comparison. Marked "unverifiable" where relevant.

Every v1 finding was re-verified against current `file:line`. New findings are numbered from DB-20.

---

## 2. v1 critique

**What v1 got right (re-verified, citations updated in §4):** DB-01 through DB-09 and DB-11 all still hold. The "genuinely good" list also re-verified: Numeric money everywhere (`product.py:153,168,170`, `commerce.py:65,93,136`), partial unique `uq_products_sku_active` (`product.py:130–135`), single-primary-image partial unique (`product.py:222–227`), tz-aware timestamps + DB triggers (`base.py:18–30`, migrations `g3h4`, `i5j6`), append-only ledgers, hashed OTP/refresh secrets, disciplined `selectinload`.

**What v1 got wrong or graded generously:**

1. **DB-10 is factually stale.** `requirements.txt:2` pins `alembic==1.13.1`; `compare_type=True` has been the **default since Alembic 1.12**. Only `compare_server_default` remains off. v1 presented type-drift blindness as a live gap; it is not. Downgraded to Info.
2. **Migration count wrong:** 23 revision files, not 24. Cosmetic, but "we counted the chain" claims must be exact in an audit.
3. **"Migration chain is clean … done right" (8/10) was generous.** v2 found: a migration that imports application service code at replay time (DB-24), a data migration that silently mis-categorizes products (DB-26), zero `CREATE INDEX CONCURRENTLY` usage plus auto-`upgrade head` on every container boot (DB-25), and residual model↔DDL drift the chain never reconciled (DB-20). None is fatal, but 8/10 does not survive them.
4. **DB-09's arithmetic was worst-case without checking deploy topology.** Production compose never sets `APP_SERVER`, so `docker-entrypoint.sh:7,14` runs **single-process uvicorn** → real budget 30 ≤ 100. Staging pins `GUNICORN_WORKERS: 2` → 60. The genuine hazard is the *latent* gunicorn default `cpu*2+1` (`gunicorn_conf.py:7`), which v1 did not pinpoint. Kept Low, re-evidenced.
5. **v1 missed the entire data-retention axis** (DB-21): no cleanup path exists for expired `otp_codes` sweeps, expired/revoked `refresh_tokens`, `idempotency_keys`, `step_up_token_uses`, or abandoned guest `carts` — and expired idempotency rows permanently 409-block key reuse due to the expiry-blind unique constraint. This is a functional bug, not just hygiene.
6. **v1 missed all concurrency findings outside checkout** (DB-22): `get_or_create_cart` is check-then-insert against a unique constraint with no IntegrityError handling → 500s under concurrent first-add; guest→user cart merge is unlocked.
7. **v1 praised `escape_ilike_pattern` without noticing it is applied inconsistently** (DB-23): admin order search and JSONB `__icontains` interpolate raw user input into LIKE patterns.

---

## 3. Schema inventory (26 tables)

| Table | PK | FKs (ondelete) | UNIQUE | CHECK | Soft-delete | Notes |
|---|---|---|---|---|---|---|
| categories | id | parent_id→categories (none) | slug; (parent_id,name) NULLS NOT DISTINCT | — | no | no cycle/self-loop guard (DB-07) |
| brands | id | — | name; slug | — | no | |
| products | id | category_id→categories (none), brand_id→brands (none) | slug; sku partial (deleted_at IS NULL) | stock_quantity≥0 | `deleted_at` | GIN on specifications (unused by filters, DB-03); no priced⇔available CHECK (DB-05) |
| product_images | id | product_id→products (CASCADE) | (product_id) partial WHERE is_primary | — | no | `is_primary` has no server_default |
| stock_movements | id | product_id→products (CASCADE), user_id→users (none) | — | — | no | movement_type free text (DB-02) |
| users | id | — | phone_number | — | `deleted_at` | email free-form, non-unique (DB-11); note type drift (DB-20) |
| otp_codes | id | — | — | — | no | code = SHA-256 hex; expires_at unindexed (DB-06); no sweep (DB-21) |
| refresh_tokens | id | user_id→users (CASCADE) | token_hash | — | no | expires_at unindexed; rows never purged (DB-21) |
| step_up_token_uses | id | — | jti | — | no | expires_at indexed; never purged (DB-21) |
| carts | id | user_id→users (CASCADE) | (user_id,lane); (guest_token,lane) | — | no | no XOR(user_id,guest_token); guest carts immortal (DB-21/22) |
| cart_items | id | cart_id→carts (CASCADE), product_id→products (none) | (cart_id,product_id) | — | no | quantity unchecked >0 (DB-27) |
| orders | id | user_id→users (none) | tracking_code; payment_authority | — | `deleted_at` | status/payment_status free text (DB-02); invoice_number non-unique (DB-30) |
| order_items | id | order_id→orders (CASCADE), product_id→products (**RESTRICT default**) | — | — | no | no snapshot columns (DB-01); product_id unindexed (DB-06) |
| order_status_events | id | order_id→orders (CASCADE) | — | — | no | status/actor free text |
| payment_transactions | id | order_id→orders (CASCADE) | — | — | no | status/gateway free text |
| idempotency_keys | id | — | (scope,key) | — | no | expiry-blind unique (DB-21) |
| admin_audit_logs | id | actor_user_id→users (SET NULL) | — | — | no | append-only, unbounded |
| product_change_logs | id | product_id→products (CASCADE), actor_user_id→users (SET NULL) | — | — | no | |
| articles | id | — | slug | — | no | related_product_ids JSONB, no RI (DB-28) |
| hero_slides | id | — | — | — | no | |
| megamenu_nav_groups | id | — | slug | — | no | root_category_ids JSONB, no RI (DB-28) |
| contact_submissions | id | — | ticket_code | — | no | |
| product_comments | id | product_id→products (CASCADE) | — | rating 1–5 | no | |
| hesabfa_item_mappings | id | product_id→products (CASCADE) | product_id; hesabfa_code | — | no | |
| hesabfa_contact_mappings | id | user_id→users (SET NULL) | customer_phone; hesabfa_code | — | no | |
| hesabfa_invoice_records | id | order_id→orders (CASCADE) | order_id | — | no | status free text, Python-side default only |

Native PG enums: `stockunitenum`, `userrole`, `otppurpose`, `ordermode`, `cartlane`. Lifecycle columns (`orders.status`, `orders.payment_status`, `payment_transactions.status`, `stock_movements.movement_type`, `order_status_events.actor`, `hesabfa_invoice_records.status`) are all unconstrained VARCHAR — the enum policy is split-brain (DB-02).

---

## 4. Findings register

### Re-verified v1 findings

#### DB-01 — Order lines are not immutable snapshots — **CONFIRMED**
- **Severity:** High · **Category:** Data integrity / Accounting · **Location:** `app/db/models/commerce.py:129–138`; write path `app/crud/commerce.py:50–58`
- **Evidence:** `OrderItem` = `order_id, product_id (FK, no ondelete → RESTRICT), quantity, unit_price` only. Checkout writes exactly these (`commerce.py:52–57`). Product rename/re-SKU rewrites what historical orders display; tax at time of sale is not captured even though checkout computes it (`checkout_service.py:93–94` folds `tax_percent` into `estimated_total` and then discards the rate).
- **Why problematic:** orders feed Hesabfa invoices (`hesabfa_invoice_records` keyed by order); line evidence must be stable for accounting/disputes. v2 adds: because `tax_percent` is only in the total, a later product tax change makes historical order math unreproducible from its own rows.
- **Root cause:** model built for display. · **Risk:** silent history rewrite; blocked catalog cleanup (RESTRICT FK).
- **Business impact:** wrong historical invoices/quotes, audit friction. **Technical impact:** cannot hard-delete products ever.
- **Recommendation:** add `product_name`, `product_sku`, `tax_percent` to `order_items`, written at checkout; backfill from products. · **Alternative:** `product_snapshot JSONB` per line.
- **Effort:** S · **Priority:** P1 · **Dependencies:** none

#### DB-02 — Lifecycle states stored as unconstrained text — **CONFIRMED, WIDER THAN v1**
- **Severity:** Medium · **Category:** Integrity · **Location:** `commerce.py:89` (`status String(100)`), `commerce.py:90–92` (`payment_status String(20)`), `commerce.py:69` (`PaymentTransaction.status`), `commerce.py:147,149` (`OrderStatusEvent.status/actor`), `product.py:212` (`movement_type`), `hesabfa.py:65` (`HesabfaInvoiceRecord.status`, Python-side default `"pending"` only — raw SQL insert without status fails or diverges)
- **Evidence:** Python enums exist (`OrderStatus` `commerce.py:21–34`, etc.) but no CHECK/native enum on any of the six columns, while `ordermode`/`cartlane`/`userrole`/`otppurpose`/`stockunitenum` are native PG enums. Migration `s4t5u6v7w8x9:33–43` shows the team knows how to add CHECKs — it added one for stock and a unique for payment_authority, but skipped statuses.
- **Why problematic / Risk:** 35 scripts write to this DB; the state machine in `order_service.py:35–63` is bypassable by any raw UPDATE; queries filtering `status='paid'` silently miss typos.
- **Root cause:** enum policy split between "native enum" and "text + Python enum" eras, never reconciled.
- **Business impact:** invalid order states invisible to admins. **Technical impact:** state machine unenforceable at the storage layer.
- **Recommendation:** one migration adding `CHECK (status IN (...))` on all six columns (CHECKs, not native enums — cheaper to extend). · **Alternative:** native enums with `ALTER TYPE ... ADD VALUE` playbook.
- **Effort:** S · **Priority:** P2 · **Dependencies:** confirm no legacy rows violate (Persian labels were remapped in `j6k7l8m9n0o1:20–48`).

#### DB-03 — Spec filters bypass the GIN index they sit next to — **CONFIRMED**
- **Severity:** Medium · **Category:** Performance · **Location:** `app/utils/jsonb_filters.py:80–86` vs index at `product.py:136–140`
- **Evidence:** builder emits `accessor.astext == ...` / `accessor.astext.ilike(...)`. SQLAlchemy renders this as `(specifications -> 'technical_specs' ->> 'range') = '0-150mm'` and `... ->> 'range' ILIKE '%0-150%'`. `ix_products_specifications_gin` is default `jsonb_ops` (migration `g3h4i5j6k7l8:45–51`), which accelerates `@>`, `?`, `?&`, `?|` — **not** `->>` expression equality. Every spec-filtered PLP is a sequential scan, twice (count query + page query, `crud/product.py:220–232`).
- **Why problematic:** index pays write cost, delivers zero read benefit for the only queries that touch the column. Fine at 5,900 rows; linear degradation to 50k.
- **Root cause:** filter DSL written for SQLite test parity (`jsonb_filters.py:69–78`), Postgres path never optimized.
- **Recommendation:** rewrite exact matches as containment `specifications @> '{"technical_specs":{"range":"0-150mm"}}'::jsonb`; keep `__icontains` documented as slow path; add expression B-tree indexes for the 2–3 hottest keys per category. · **Alternative:** promote hot spec keys to columns at import.
- **Effort:** M · **Priority:** P2 · **Dependencies:** DB-23 (escape the icontains value while touching this file).

#### DB-04 — Search is leading-wildcard ILIKE with no trigram index, no Persian normalization — **CONFIRMED**
- **Severity:** Medium · **Category:** Performance / Correctness · **Location:** `app/crud/product.py:198–205`
- **Evidence:** `Product.name/sku ILIKE '%…%'` + correlated `EXISTS` on `Brand.name ILIKE`. `rg "pg_trgm|to_tsvector|unaccent|CREATE EXTENSION"` across `app/`, `alembic/`, `scripts/` → **zero hits**. No ی/ي or ک/ك normalization exists anywhere in the write path (`app/utils/specifications.py`, `slugify.py` checked — nothing).
- **Why problematic:** every storefront search runs two sequential scans (count + page). Persian text entered with Arabic yeh/kaf simply won't match — a *correctness* bug for an Iranian market site, not just performance.
- **Root cause:** search built on ORM primitives only. · **Risk:** "product not found" for products that exist.
- **Recommendation:** `CREATE EXTENSION pg_trgm` + GIN trigram indexes on `products.name`, `products.sku`, `brands.name`; normalize ی/ک variants at write time (one column-rewrite script) and at query time (2-line helper).
- **Effort:** S (indexes) / M (normalization + backfill) · **Priority:** P2 · **Dependencies:** superuser for extension.

#### DB-05 — "priced ⇔ purchasable-available" invariant not in the DB — **CONFIRMED**
- **Severity:** Medium · **Category:** Integrity · **Location:** `products.is_available` (migration `x9y0z1a2b3c4:22–37`); guards only in `cart_service.py:67–68` and `checkout_service.py:84–88`; reconciliation via `scripts/reconcile_prices_availability.py`
- **Evidence:** DB accepts `is_available=true, base_price=NULL` freely; migration backfilled from `stock_quantity>0` once; app guards cover cart-upsert and checkout, but admin edits / import scripts / raw SQL can still strand rows, silently pushing priced-lane products into a state the storefront presents as sellable-but-unpriceable.
- **Recommendation:** `CHECK (NOT is_available OR base_price IS NOT NULL)` — verify current data first (cannot be done in this audit; no live DB). · **Alternative:** nightly reconcile job + alert.
- **Effort:** S · **Priority:** P2 · **Dependencies:** one-time data validation.

#### DB-06 — Missing housekeeping/support indexes — **CONFIRMED + 2 NEW GAPS**
- **Severity:** Low · **Category:** Performance/Operations
- **Evidence (all verified absent in models and all 23 migrations):** no index on `otp_codes.expires_at` (`content.py:105`), `idempotency_keys.expires_at` (`platform.py:111`), `refresh_tokens.expires_at` (`platform.py:70`), `orders.payment_status` (`commerce.py:90`). **New in v2:** `order_items.product_id` unindexed while `has_user_purchased_product` filters on it (`crud/commerce.py:242`) and the RESTRICT FK check on product delete scans it; `orders.customer_phone` unindexed while `list_orders` filters equality on it (`crud/commerce.py:169–171`). `step_up_token_uses.expires_at` IS indexed — pattern known, unevenly applied.
- **Recommendation:** add the six indexes (partial where appropriate). · **Effort:** S · **Priority:** P3 · **Dependencies:** DB-21 (sweeps make expiry indexes actually earn their keep).

#### DB-07 — Category tree integrity app-enforced only — **CONFIRMED**
- **Severity:** Low · **Category:** Integrity · **Location:** `product.py:91`; services `app/utils/category_depth.py`, `category_validation.py`; raw setter `crud/category.py:147–150` writes `parent_id` with no cycle re-check at the CRUD layer
- **Evidence:** self-FK without even `CHECK (parent_id <> id)`; depth-3 rule and reassignment live in services with tests; concurrent parent updates can still cycle (no advisory lock).
- **Recommendation:** add the self-loop CHECK now (free); accept residual concurrent-cycle risk at current team size, documented. · **Effort:** S · **Priority:** P3

#### DB-08 — Spec template ↔ stored JSONB has no versioning — **CONFIRMED**
- **Severity:** Medium · **Category:** Maintainability · **Location:** `get_default_specifications()` `product.py:49–69` (measurement-tool skeleton: `battery_type`, `waterproof` written for every product incl. cutting tools); `categories.spec_template_key` `product.py:92`; `spec_template_service.py:145–152` resolves templates by ancestor walk
- **Evidence:** `rg "spec_version"` → zero hits. `specifications_for_storage` (`specifications.py:100–122`) normalizes shape but stamps no version; template evolution silently diverges old rows from filter-UI expectations.
- **Recommendation:** stamp `spec_version` in JSONB; write per-category defaults from the resolved template instead of the global skeleton; per-change backfill playbook. · **Effort:** M · **Priority:** P2

#### DB-09 — Connection budget — **CONFIRMED, NUMBERS CORRECTED**
- **Severity:** Low · **Category:** Operations · **Location:** `app/db/database.py:17–18` (`pool_size=20, max_overflow=10` → 30/process); `gunicorn_conf.py:7`; `docker-entrypoint.sh:7,14`; `docker-compose.staging.yml:16,19`
- **Real budget (v2 computation):** production compose sets no `APP_SERVER` → uvicorn **single process** → 30 conns. Staging: gunicorn with `GUNICORN_WORKERS:-2` → 60. Postgres is `postgres:15-alpine` with **no `max_connections` tuning anywhere** (grep of compose + `deploy/`) → default 100. Both fine today. **Foot-gun:** setting `APP_SERVER=gunicorn` without `GUNICORN_WORKERS` triggers `cpu_count()*2+1` (`gunicorn_conf.py:7`) — a 4-vCPU VPS gives 9 workers × 30 = **270 > 100** and connection-refused storms under load. v1's "4 workers ≈ 120" was the right instinct with the wrong path.
- **Recommendation:** cap pool per worker (e.g. `pool_size=5, max_overflow=5`) and hard-code a sane worker count for this box; PgBouncer only if worker count must grow. · **Effort:** S · **Priority:** P2 (one env-var away from an outage)

#### DB-10 — Autogenerate compare flags — **v1 PARTIALLY WRONG, DOWNGRADED**
- **Severity:** Info (was Low) · **Category:** DX · **Location:** `alembic/env.py:41–44`
- **Evidence:** `context.configure(connection=..., target_metadata=...)` with no flags — but `alembic==1.13.1` (`requirements.txt:2`) defaults `compare_type=True` since 1.12. Only `compare_server_default=False` remains, which matters here because real server-default drift exists (DB-20: `users.tags`).
- **Recommendation:** add `compare_server_default=True`; expect noise on the first autogenerate. · **Effort:** S · **Priority:** P3

#### DB-11 — `users.email` free-form — **CONFIRMED**
- **Severity:** Low · **Location:** `app/db/models/user.py:34`; created in `l8m9n0o1p2q3:28`
- **Evidence:** nullable, no unique, no partial unique, no format check; grep shows no login/notification flow reads it today (dormant column).
- **Recommendation:** partial unique `WHERE email IS NOT NULL` *before* any feature starts using it. · **Effort:** S · **Priority:** P3

### New findings (v2)

#### DB-20 — Residual model ↔ migration drift (4 items)
- **Severity:** Low · **Category:** Migrations/DX
- **Location & Evidence:**
  1. `users.note`: model `String(500)` (`user.py:35`) vs DDL `sa.Text()` (`l8m9n0o1p2q3:29`) — live column is TEXT; length limit is fiction.
  2. `orders.payment_authority`: model `unique=True, index=True` (`commerce.py:108`) vs DB reality = non-unique index `ix_orders_payment_authority` (`o0p1q2r3s4t5:23`) **plus** separate unique constraint `uq_orders_payment_authority` (`s4t5u6v7w8x9:39–43`) — redundant double index on the same column.
  3. `users.tags`: DDL has `server_default="[]"` (`l8m9n0o1p2q3:33`); model has none (`user.py:37`) — invisible to autogenerate while `compare_server_default` is off (DB-10).
  4. `megamenu_nav_groups.slug`: model `unique=True, index=True` (`content.py:68`) vs DDL unique constraint + separate non-unique index (`y0z1a2b3c4d5:50–52`) — same redundancy pattern as (2).
- **Why problematic:** the next `alembic revision --autogenerate` will emit spurious DDL (or in case 3, miss real drift); redundant indexes cost writes; TEXT vs VARCHAR(500) means app-level assumptions are unenforced.
- **Root cause:** hand-written migrations diverging from models with no `alembic check` in CI.
- **Business impact:** none direct. **Technical impact:** migration noise, wasted write amplification.
- **Recommendation:** one reconciliation migration (drop redundant non-unique indexes, align note type, add tags server_default to model); add `alembic check` (or autogenerate-diff assertion) to CI. · **Alternative:** document known drift and freeze.
- **Effort:** S · **Priority:** P3 · **Dependencies:** DB-10 flag first.

#### DB-21 — No retention path for expirable rows; expired idempotency keys permanently block reuse
- **Severity:** Medium · **Category:** Operations / Correctness
- **Location:** `crud/otp.py` (delete only per-phone on re-issue, lines 20–24), `crud/refresh_tokens.py` (revoke sets timestamp, nothing deletes, lines 39–53), `crud/idempotency.py:50–70`, `app/api/endpoints/checkout.py:57–73`, `carts` (no TTL concept at all); `rg "cleanup|sweep|purge"` across `scripts/` and `app/main.py` → only the order-expiry sweep exists.
- **Evidence (the functional bug):** `reserve_idempotency_record` does a raw INSERT against `uq_idempotency_scope_key`; an **expired** row still occupies the key. Reserve fails → `checkout.py:64–68` re-reads via `get_idempotency_record`, which filters `expires_at > now` → returns `None` → **409 "in progress" forever** for that (scope, key). TTL (`IDEMPOTENCY_TTL_HOURS`, default 24h) is advisory fiction: nothing deletes expired rows and the unique constraint ignores expiry.
- **Why problematic:** correctness edge (client retrying with a deliberately stable key after 24h is hard-locked out) plus unbounded growth of `otp_codes` (rows for phones that never re-request), `refresh_tokens`, `step_up_token_uses`, `idempotency_keys`, and guest `carts`/`cart_items` (every anonymous bot visit that adds to cart persists forever).
- **Root cause:** expiry modeled as a query filter, never as a lifecycle.
- **Business impact:** stuck checkout retries (rare); table bloat on a small VPS. **Technical impact:** cleanup later requires care because expiry columns are unindexed (DB-06).
- **Recommendation:** in `reserve_idempotency_record`, treat conflict-with-expired-row as reclaim (`DELETE ... WHERE scope=.. AND key=.. AND expires_at <= now()` then retry insert, or upsert `ON CONFLICT ... WHERE expires_at <= now()`); add a daily sweep (extend the existing lifespan worker in `app/main.py:32–47`) deleting expired otp/idempotency/step-up rows, expired+revoked refresh tokens, and guest carts idle > N days. · **Alternative:** `pg_cron`.
- **Effort:** M · **Priority:** P2 · **Dependencies:** DB-06 expiry indexes first.

#### DB-22 — Cart creation and guest-merge race conditions
- **Severity:** Low · **Category:** Concurrency
- **Location:** `app/crud/cart_persistence.py:10–33` (`get_or_create_cart`), `:99–131` (`merge_guest_cart_into_user`)
- **Evidence:** `get_or_create_cart` is SELECT-then-INSERT against `uq_carts_user_lane` / `uq_carts_guest_lane` with **no IntegrityError handling** — contrast with `reserve_idempotency_record` (`crud/idempotency.py:57–70`) which does it correctly with `begin_nested()`. Two concurrent first-add-to-cart requests → one gets an unhandled unique violation → HTTP 500. `merge_guest_cart_into_user` takes no locks; double login-merge (two tabs) can double quantities (`user_item.quantity += guest_item.quantity`, line 118) because neither cart row is locked.
- **Root cause:** happy-path CRUD; the team's own savepoint pattern not reused.
- **Business impact:** sporadic 500 on add-to-cart under double-click; inflated quantities after login. **Technical impact:** flaky errors that won't reproduce in tests.
- **Recommendation:** wrap cart insert in `begin_nested()` + retry-select on IntegrityError; in merge, lock both carts `WITH FOR UPDATE` ordered by id. · **Alternative:** Postgres `INSERT ... ON CONFLICT DO NOTHING RETURNING`.
- **Effort:** S · **Priority:** P3 · **Dependencies:** none.

#### DB-23 — Inconsistent LIKE-pattern escaping (wildcard injection)
- **Severity:** Low · **Category:** Correctness / minor DoS
- **Location:** `app/crud/commerce.py:173–181` (admin order search: `pattern = f"%{search.strip()}%"` — raw); `app/utils/jsonb_filters.py:73,82` (`ilike(f"%{value}%")` — raw); correct counter-example `crud/product.py:199` uses `escape_ilike_pattern`.
- **Evidence:** quoted above. User-supplied `%`/`_`/`\` reach the LIKE pattern verbatim on two endpoints.
- **Why problematic:** not SQL injection (bound params), but pattern injection: `%` returns everything, crafted `%a%b%c%...` patterns are quadratic on long text; filter results silently wrong for legitimate underscores in SKUs/spec values.
- **Root cause:** helper exists but adoption is per-file.
- **Recommendation:** route every ILIKE through `escape_ilike_pattern`; add a lint/test. · **Effort:** S · **Priority:** P3 · **Dependencies:** touch together with DB-03.

#### DB-24 — Migration `y0z1a2b3c4d5` imports live application code
- **Severity:** Medium · **Category:** Migrations
- **Location:** `alembic/versions/y0z1a2b3c4d5_megamenu_nav_groups.py:54–58`
- **Evidence:** `from app.services.nav_groups_seed import DEFAULT_NAV_GROUP_SEEDS, resolve_root_ids_for_matchers` executed inside `upgrade()`.
- **Why problematic:** migrations must replay identically forever; this one's behavior changes whenever `nav_groups_seed.py` changes, and a future rename/removal of that module **breaks fresh-database builds** (`alembic upgrade head` runs on every container boot — `docker-entrypoint.sh:5` — so a broken replay blocks deployment of a new VPS or a disaster-recovery restore-from-scratch).
- **Root cause:** seeding conflated with schema migration.
- **Business impact:** DR/rebuild fragility. **Technical impact:** hidden coupling invisible to tests that run on an already-migrated DB.
- **Recommendation:** freeze: copy the seed constants + matcher logic into the migration file itself (it's historical data now). Move future seeding to idempotent startup/scripts. · **Alternative:** guard the import with try/except and skip seeding when module missing (accepting divergent fresh DBs) — worse.
- **Effort:** S · **Priority:** P2 · **Dependencies:** none.

#### DB-25 — Auto-migrate-on-boot with no backup gate; zero `CONCURRENTLY`
- **Severity:** Low (at current data size) · **Category:** Operations/Migrations
- **Location:** `docker-entrypoint.sh:4–5`; all `op.create_index` calls (e.g. `g3h4i5j6k7l8:30–51` incl. the GIN build) are transactional/locking
- **Evidence:** every container start runs `alembic upgrade head` unconditionally; no dump precedes it (backup cron exists separately, `docs/OPERATIONS.md:145`, but is not sequenced with deploys). No migration in the chain uses `postgresql_concurrently`.
- **Why problematic:** index builds take `SHARE` locks blocking writes; at 5,900 products this is milliseconds, but the habit scales badly, and a data-migration bug executes on prod boot with no snapshot to roll back to. Downgrades exist but several are effectively destructive-by-design (`o0p1q2r3s4t5:26` deleted all OTP rows on upgrade — acceptable for ephemeral data, correctly documented).
- **Recommendation:** deploy script: backup → `alembic upgrade head` → start app (remove auto-upgrade from entrypoint, or gate behind `RUN_MIGRATIONS=1`); adopt `CONCURRENTLY` for future index-on-large-table migrations. · **Effort:** S · **Priority:** P3
- **Dependencies:** deploy pipeline touch.

#### DB-26 — Historical data migration silently mis-categorized products
- **Severity:** Low (historical, one-shot) · **Category:** Data quality
- **Location:** `alembic/versions/p1q2r3s4t5u6:55–74`
- **Evidence:** to enforce NOT NULL, the migration assigned **every** uncategorized product to "the first depth-3 leaf category" (`ORDER BY c3.id LIMIT 1`) — an arbitrary bucket, with no marker/log of which rows were touched.
- **Why problematic:** any products that went through this path are silently filed under an unrelated leaf; nothing distinguishes them from correctly-categorized rows. The subsequent RuntimeError guard (lines 76–83) was good; the arbitrary assignment was not.
- **Recommendation:** one-time forensic query (products whose category equals that first-leaf and whose spec/brand pattern doesn't match siblings) if catalog accuracy matters; going forward, use an explicit "Uncategorized" quarantine category for such backfills. · **Effort:** S (forensics) · **Priority:** P3 · **Dependencies:** needs live DB (unverifiable here whether any rows were actually affected).

#### DB-27 — No sign/positivity constraints on commercial quantities
- **Severity:** Low · **Category:** Integrity
- **Location:** `commerce.py:135–136` (`OrderItem.quantity`, `unit_price`), `platform.py:58` (`CartItem.quantity`), `product.py:153` (`base_price`), `commerce.py:93` (`estimated_total`)
- **Evidence:** none of these carry a CHECK; only `products.stock_quantity >= 0` exists (`s4t5u6v7w8x9:33–37`). App validates cart quantity > 0 (`cart_persistence.py:71–72`) but the DB accepts `quantity = -5`, `unit_price = -100`, `base_price < 0` from any script.
- **Why problematic:** a negative-quantity order line flows into `estimated_total` and Hesabfa invoicing; ledger tables would faithfully record garbage.
- **Recommendation:** `CHECK (quantity > 0)` on order_items/cart_items, `CHECK (unit_price >= 0)`, `CHECK (base_price >= 0)`. · **Effort:** S · **Priority:** P3 · **Dependencies:** data validation pass first.

#### DB-28 — JSONB ID lists without referential integrity
- **Severity:** Low · **Category:** Integrity
- **Location:** `content.py:43` (`Article.related_product_ids`), `content.py:74` (`MegamenuNavGroup.root_category_ids`)
- **Evidence:** plain JSONB int arrays; deleting a product/category leaves dangling IDs — no FK, no cleanup hook in `delete_category_row` (`crud/category.py:193–195`) or product delete paths.
- **Why problematic:** megamenu groups reference category roots; a deleted root leaves a phantom entry that presenters must defensively filter (and whether they do is a per-consumer gamble).
- **Recommendation:** either association tables (correct) or a periodic integrity sweep + defensive filtering documented as the contract. · **Effort:** M (tables) / S (sweep) · **Priority:** P3

#### DB-29 — Order-expiry sweep runs inside the user checkout transaction
- **Severity:** Low · **Category:** Concurrency/Latency
- **Location:** `app/services/checkout_service.py:59–60` calling `order_expiry_service.py:23–65`; duplicate mechanism in `app/main.py:32–47` (background worker + Redis lock)
- **Evidence:** every purchase checkout first loads **all** expired pending-payment orders with items (`selectinload`, no `FOR UPDATE SKIP LOCKED`, no LIMIT) and transitions them one-by-one, in the same session/transaction as the customer's own order.
- **Why problematic:** a backlog of stale orders (e.g. after gateway downtime) makes some unlucky customer's checkout do the janitorial work — extra latency and enlarged lock/transaction scope; concurrent checkouts race on the same stale rows (ValueError races are caught, but the work is duplicated). A dedicated worker already exists — the inline call is redundant belt-and-braces with a user-facing cost.
- **Recommendation:** delete the inline sweep from `submit_checkout`; keep the background worker, add `LIMIT` + `FOR UPDATE SKIP LOCKED` to the sweep query. · **Effort:** S · **Priority:** P3

#### DB-30 — `orders.invoice_number` has no uniqueness
- **Severity:** Low · **Category:** Integrity/Accounting
- **Location:** `commerce.py:104`; created in `m9n0o1p2q3r4:31` with no constraint
- **Evidence:** `invoice_number String(32)` nullable, non-unique; also duplicated inside `orders.invoice` JSONB (`order_service.py:92–107` reads both).
- **Why problematic:** duplicate invoice numbers are an accounting defect by definition; dual storage (column + JSONB) can silently diverge.
- **Recommendation:** partial unique index `WHERE invoice_number IS NOT NULL`; treat the JSONB copy as denormalized display data only. · **Effort:** S · **Priority:** P3

### Redis as a datastore (task §5 — assessment, no numbered finding)

Redis stores exactly three things (verified by exhaustive grep): fixed-window **rate-limit failure counters** (`rate_limit.py:79–128`, keys `ratelimit:*` with window TTLs), **public-endpoint throttle counters** (`request_throttle.py`), and **single-leader locks** (`distributed_lock.py:27–37`, `lock:*`, NX+EX). No carts, sessions, or cache-of-record. **If Redis is flushed:** brute-force counters and throttle state reset (an attacker window of one TTL), and the order-expiry leader lock vanishes (worst case two workers sweep concurrently — the transition state-machine tolerates it). Nothing durable is lost; `redis:7-alpine` runs with default RDB snapshotting and no AOF, which is *appropriate* for this payload. Two deliberate asymmetries worth keeping documented: rate limiter **fails closed** (Redis outage throttles all auth attempts for a full window — security over availability, `rate_limit.py:109–111`) while the distributed lock **fails open** (`distributed_lock.py:35–37`). Both defensible; the pairing is correct.

---

## 5. Doc-drift table

| Doc claim | Reality | Verdict |
|---|---|---|
| v1 audit: "24 linear revisions" | 23 revision files, linear chain verified via down_revision walk | **Wrong (minor)** |
| v1 audit DB-10: type drift can pass unnoticed | alembic 1.13.1 → `compare_type=True` by default | **Stale/wrong** |
| `SEED_IMPORT.md:48`: "category_id is required on every product" | Model `product.py:150` NOT NULL; enforced by migration `p1q2r3s4t5u6:85–90` | Accurate |
| `SEED_IMPORT.md:48`: "tree depth must not exceed 3 levels" | App-enforced only (`category_depth.py`); no DB constraint | Accurate but unstated caveat |
| `SEED_IMPORT.md:57–58`: local SQLite / CI Postgres `USE_POSTGRES_TESTS=1` | `tests/conftest.py:18,105`; `.github/workflows/backend-ci.yml:146,165` | Accurate |
| `SEED_IMPORT.md:46`: seed_categories may delete products on reseed | Consistent with script behavior; backup rule stated | Accurate |
| `OPERATIONS.md:112`: "entrypoint does this on boot" (alembic) | `docker-entrypoint.sh:5` | Accurate (see DB-25 for why it's risky anyway) |
| `product.py:154` comment: "warehouse counts live in Hesabfa only" | `stock_quantity` column + CHECK still live; `cart_service.py:44` still serializes `stock_quantity` into cart responses | **Code-internal drift** — deprecated field still on the wire |
| `IDEMPOTENCY_TTL_HOURS` implies keys expire | No deletion path; expired keys still block reuse (DB-21) | **Misleading** |

---

## 6. Scores (0–10, strict)

| Category | v2 | v1 | Δ | Justification |
|---|---|---|---|---|
| **Database** | **6.5** | 7.0 | −0.5 | Fundamentals are genuinely good (Numeric money, partial uniques, tz triggers, ledgers, hashed secrets) and v1 was right to credit them. But strict mode cannot hold 7 with: an unpatched High accounting gap (DB-01), six unconstrained lifecycle columns (DB-02), a functional idempotency bug + zero retention story (DB-21), a migration that can't replay without app code (DB-24), and four unreconciled drift items (DB-20). v1's 8/10 migrations sub-score was generous. |
| **Data-layer Performance** | **5.5** | 6.0 | −0.5 | Eager loading is disciplined and hot paths are clean — real credit. But *both* discovery paths (text search DB-04, spec filters DB-03) are sequential scans executed **twice per request** (count + page, `crud/product.py:220–232`), the GIN index is dead weight for the emitted SQL, sorts on `base_price`/`created_at` have no supporting composite indexes, and Persian yeh/kaf mismatch is a correctness hole inside the search path. At 5,900 rows this is invisible, which is exactly why it must be scored structurally. |
| **Data-layer Scalability** | **5.5** | 6.0 | −0.5 | Connection budget is actually safer than v1 implied (single uvicorn in prod = 30/100) but one env var (`APP_SERVER=gunicorn` without worker count) flips it to 270/100 (DB-09). Search/filter cost grows linearly with catalog (→50k), OFFSET pagination degrades on deep pages, and five tables grow unboundedly with no retention (DB-21). Nothing here needs partitioning or sharding — the deductions are for growth paths that have no plan, not for missing big-company machinery. |

---

## 7. Self-review

- **Did we verify every v1 finding against current code?** Yes — all 11, each with re-checked file:line; one (DB-10) downgraded as factually stale, one (DB-09) re-computed with actual deploy topology.
- **Could DB-03 be wrong (containment used somewhere)?** Re-searched: only `astext` accessors in `jsonb_filters.py`; no `@>`, `contains()`, `has_key` anywhere in `app/`. Stands.
- **Could DB-21's 409-lock be wrong?** Traced the exact path: `reserve` → IntegrityError → `get_idempotency_record` filters `expires_at > now` → None → `api_error(409)` (`checkout.py:63–73`). Only escape is manual row deletion. Stands. Practical severity tempered because clients typically send fresh UUID keys.
- **Is DB-24 overblown given tests pass?** Tests run against migrated DBs and CI runs `alembic upgrade head` from scratch — so CI *would* catch a hard break of the import, but only after the breaking change lands; the coupling still violates migration immutability and would fail exactly at deploy time. Kept Medium.
- **What we could not verify (no live DB):** actual row counts/violations for DB-05 (v1 claimed 0 as of 2026-07-25 — plausible, unverified), whether DB-26's backfill touched any rows, actual `max_connections`, index bloat, and any `EXPLAIN` plans. All performance findings are structural.
- **Bias check:** we deducted for structural risks that don't hurt at today's scale (5,900 products, low order volume). That is intentional under strict mode; the operational reality is that this database will run fine this quarter. The P1/P2 list (DB-01, DB-02, DB-05, DB-09, DB-21, DB-24, then DB-03/DB-04 before catalog 10×) is the honest priority order.

**Finding counts:** High 1 · Medium 7 (DB-02, DB-03, DB-04, DB-05, DB-08, DB-21, DB-24) · Low 13 · Info 1 (DB-10) — total 22.
