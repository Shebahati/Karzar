# API changelog

Karzar uses **path versioning** (`/api/v1`). Breaking changes to request/response shapes require a new major path (`/api/v2`) or an explicit deprecation window documented here.

Non-breaking additions (new optional fields, new endpoints, new error codes) are recorded under the current minor line.

## Versioning rules

| Change type | Version bump | Example |
|-------------|--------------|---------|
| Remove/rename required field | Major (`v2`) | `checkout.status` renamed |
| Change field type | Major | `order_id` string → int |
| New optional response field | Minor (same `v1`) | `payment_url` on checkout |
| New endpoint | Minor | `GET /categories/spec-labels` |
| New `error_code` | Minor | `GUEST_ORDER_NOT_PAYABLE` |
| Stricter validation | Minor* | `category_id` required on create |

\* Document in this file; frontend should handle new validation errors.

## Current baseline: API v1.0

**Status:** Active  
**Contract references:** [API_CONTRACT.md](API_CONTRACT.md), [`../openapi/v1.json`](../openapi/v1.json)

### 2026-09-24 — Wave environment_pins.alembic lineage compatibility

- Behavioral clarification (no OpenAPI shape change): sealed `environment_pins.alembic` is a **minimum compatible Alembic lineage pin**. Runtime must equal the sealed revision or be a descendant of it in the Alembic revision graph (via `is_runtime_revision_compatible`). Plane and `freeze_required` remain exact. Shared SSOT: `assert_environment_gates` (execute, evidence validate, batch assert).

### 2026-09-24 — Knowledge Wave Registry PR3-B.2 (Evidence validation)

- `POST /api/v1/knowledge/waves/{wave_id}/validate-evidence` — Asserted → EvidenceValidated (super-admin); read-only Fact/Evidence/assert-run checks; SHA + env pins; deny-by-default via `knowledge_wave_lifecycle.assert_transition`.
- Audit: `wave.evidence_validate`, `wave.evidence_validate.fail`.
- No publish orchestration; no Fact/Evidence mutation on success path beyond wave status.

### 2026-09-23 — Knowledge Wave Registry PR3-B.1 (lifecycle foundation)

- Additive Alembic `s2t3u4v5w6x7`: wave `status` CHECK expands to include `EvidenceValidated|Publishing|Published|Superseded|Archived` (no new endpoints).
- Single-source transition map in `app/services/knowledge_wave_lifecycle.py` (deny-by-default); review/seal/execute call `assert_transition`.
- Response schema status Literal widened to `WaveStatusPR3B` (OpenAPI enum). No validate-evidence / publish APIs in this change.

### 2026-09-23 — Knowledge Wave Registry PR3-A (Execute)

- Additive status vocabulary (Alembic `q0r1s2t3u4v5`): wave `Executing|Asserted|Failed|Aborted`; run `created|running|completed|failed|aborted`; item `pending|running|success|failed|skipped` + ledger columns.
- `POST /api/v1/knowledge/waves/{wave_id}/execute` — Sealed only; freeze/plane/alembic/SHA gates; sync SKU loop via `kb-batch-assert`; Sealed→Executing→Asserted|Failed.
- `GET /api/v1/knowledge/wave-runs/{run_id}` — run ledger.
- `POST /api/v1/knowledge/wave-runs/{run_id}/resume` — failed runs only; new run_id; no Fact duplication.
- Audit: `wave.execute`, `wave.run.start|complete|fail|resume`, `wave.item.success|fail`.

### 2026-09-23 — Knowledge Wave Registry PR2 (Seal + validate)

- Additive CHECK: wave `status` may be `Draft|Reviewed|Sealed` (Alembic `p9q0r1s2t3u4`).
- `POST /api/v1/knowledge/waves/{id}/seal` — Reviewed → Sealed; stores deterministic `manifest_sha256` from canonical manifest payload; rejects Draft and mutation after seal.
- `POST /api/v1/knowledge/waves/{id}/validate` — tiered validation (`basic` / `pre_seal` / `execution_readiness`); no execution.
- Audit actions: `wave.seal`, `wave.validate`.

### 2026-09-23 — Knowledge Wave Registry PR1 (Draft/Review)

- Additive schema only: `knowledge_waves`, `knowledge_wave_products`, `knowledge_wave_runs`, `knowledge_wave_run_items` (Alembic `o8p9q0r1s2t3`). No Fact/Evidence/Product/JSONB mutation; no Sealed/execute/publish orchestration.
- Super-admin endpoints under `/api/v1/knowledge/waves`:
  - `POST /waves` — create Draft
  - `GET /waves`, `GET /waves/{id}`
  - `PATCH /waves/{id}` — Draft fields only
  - `POST /waves/{id}/review` — Draft↔Reviewed (`to_status` + `change_reason`)
- Audit actions: `knowledge_wave.create`, `knowledge_wave.update_draft`, `knowledge_wave.review`.

### 2026-09-13 — Manual Postex portal receiver-due MVP

- `POSTEX_FULFILLMENT_MODE`: `api` (default) | `manual_portal`. Snapshotted on new shipments as `provider_data.fulfillment_mode` (no migration).
- `GET /shipping/status` adds `fulfillment_mode`.
- Admin (super-admin, no Postex HTTP): `POST …/manual-portal/register`, `…/handoff`, `…/deliver`, `…/correct` (step-up on correct).
- Generic Postex admin paths (`book`, `ready`, `label`, `refresh-tracking`, `edit`, `cancel`) return **409** for `manual_portal` shipments and for **invalid** `provider_data.fulfillment_mode` snapshots (zero provider HTTP; workers exclude ineligible snapshots before batch `LIMIT`).
- `POST …/manual-portal/correct` uses partial-update semantics: omitted optional fields preserve stored registration; explicit JSON `null` clears a field.
- `POSTEX_FULFILLMENT_MODE=manual_portal` requires effective receiver-due payment mode at config validation (derived from `POSTEX_SHIPPING_PAYMENT_MODE` / legacy `POSTEX_DEFAULT_PAYMENT_TYPE` only — no module-global settings during bootstrap).
- Generic `PATCH /orders/{id}/status` rejects `shipped`/`delivered` when an active manual-portal shipment exists (409 `SHIPMENT_STATE_INVALID`).
- Manual-portal **local abandon/cancel** is **deferred** (no API route in this MVP); use operational handoff/deliver paths and support playbooks for edge cases.
- Definitive SEP verify failure after accepted callback moves the order to `reconciliation_required` (not silent `failed` limbo).
- Shipment admin view adds `fulfillment_mode`, `registration_source`.
- Order expiry sweep cancels expired `pending_payment` with `payment_status=failed` when authority expired, without cancelling verified/callback orders.

### 2026-09-12 — Postex receiver-paid shipping (پس‌کرایه)

- Provider-neutral `shipping_payment_mode`: `sender_prepaid` | `receiver_due` (persisted on order + shipment). Maps to Postex `SENDER` / `RECEIVER`. **COD unsupported.**
- `GET /shipping/status` adds `shipping_payment_mode`, `checkout_quote_required`, `booking_enabled`.
- Checkout: optional `shipping_payment_mode` from client is **forbidden**; server policy (`POSTEX_SHIPPING_PAYMENT_MODE` / default) is sole authority. `GET /shipping/status` exposes mode for presentation only.
- Receiver prepare action moves to `ready_to_book` (worker never claims). Explicit admin `/book` is required for Postex create.
- `POSTEX_BOOKING_ENABLED` (default false) gates parcel create / mark-ready / cancel / edit. Error `SHIPPING_BOOKING_DISABLED`.
- Additive Alembic `j3k4l5m6n7o8` (not applied in this change).

### 2026-09-10 — Postex logistics domain (safe-disabled)

- New provider-neutral shipping endpoints: `GET /shipping/status`, `GET /shipping/cities`, `POST /shipping/quotes`.
- Admin shipment actions under `/orders/{order_id}/shipments*` (book, ready, label PDF, refresh-tracking, edit, cancel).
- Admin `GET /admin/shipping/health` and optional read-only wallet.
- Checkout: optional `shipping.location_code` and `shipping_quote_token` (required when `POSTEX_ENABLED` and `sender_prepaid`).
- Order detail / public track: `shipments` plus shipping cost snapshots. `estimated_total` is SEP payable total (items + tax [+ shipping for sender_prepaid]).
- Product: optional `package_*_cm` (must be `> 0` when set); `shipping_is_fragile` / `shipping_is_liquid` / `shipping_class` nullable (**NULL = UNKNOWN**, not defaulted to false/parcel).
- New error codes: `SHIPPING_DATA_INCOMPLETE`, `SHIPPING_FREIGHT_REQUIRED`, `SHIPPING_UNAVAILABLE`, `SHIPPING_QUOTE_*`, `SHIPPING_QUOTE_STALE`, `SHIPMENT_*`, `SHIPPING_PROVIDER_CUTOFF`.
- Shipment statuses include `cancellation_pending` (Postex cancel-request is not a confirmed cancel) and event status `provider_unknown` (unknown provider text is persisted, never inferred as in-transit/delivered).
- Admin shipment view may include `cancellation_requested_at`.
- Default `POSTEX_ENABLED=false`. No live Postex mutation in this change.

### 2026-08-02 — KB-REMEDIATION-11A Property Dictionary admin read (CR-012)

- Regenerated committed `openapi/v1.json` from `app.openapi()` (paths → 90).
- Adds super-admin-only GETs under `/api/v1/knowledge/dictionary/{units,properties,aliases}` (Prompt 11A). No HTTP import/write routes.
- Import remains CLI: `scripts/seed_property_dictionary.py`.

### 2026-07-30 — CR-022 availability semantics (docs)

- **Binding model:** site inventory is **binary** (`is_available` / storefront `availability`). Warehouse counts live only in Hesabfa (`README.md`, `docs/HESABFA.md`, `app/crud/product.py`). Closes AODS `CR-022` Option A (**D19**).
- **`FRONTEND_INTEGRATION.md`:** corrected stale claims (`low_stock` when qty&lt;10; `availability` from `stock_quantity > 0`).
- **Deprecated / legacy (still returned for compatibility — do not use as inventory truth):**
  - `stock_quantity` on product/stock payloads — not a real count (typically `"0"`).
  - `low_stock` — always `false` at runtime; no site threshold.
  - `GET /api/v1/products/{id}/stock` — prefer product fields / availability updates via `is_available`.
  - `POST /api/v1/products/{id}/stock/adjust` — raises; use `is_available` / availability endpoint instead.
- **Follow-up (not this change):** migrate admin bulk path off deprecated stock adjust (advisory node 3).

### 2026-07-30 — CR-012 OpenAPI snapshot sync (EPIC-1 slug)

- Regenerated committed `openapi/v1.json` from `app.openapi()` (81 → 82 paths).
- Adds missing `GET /api/v1/products/slug/{slug}` (live since PR #126; snapshot had lagged since PR #111).
- `python3 aods/tools/aods_validate.py --gate openapi` now PASSes with zero findings for this drift.
- Durable CI wiring of the gate remains a Phase-4 follow-up (`OI-GOV-05`); this change closes the *current* contract drift only.

### 2026-07-27 — BE-001 OpenAPI snapshot sync

- Regenerated committed `openapi/v1.json` from `app.openapi()` so product schemas document `short_description`, `meta_title`, `meta_description`, and `slug` (detail/summary as applicable).
- Runtime contract unchanged vs #66/#68; snapshot drift fixed for offline typegen.

### 2026-07 — product SEO descriptions (P0)

- Added nullable `products.short_description` (separate from long `description`).
- Public product detail (+ list summary) now expose `slug`, `short_description`, `meta_title`, `meta_description` (detail); summary includes `slug` + `short_description`.
- Admin create/update accept the same SEO fields. No URL migrate to `/product/[slug]` in this change.

### 2026-07 — P0 payment & checkout

- Checkout (`POST /checkout`) returns `payment_url` for purchase mode (authenticated users).
- Payment fields moved to `payment_authority` / `payment_ref_id` on orders (no longer parsed from `note`).
- Public `GET /payments/callback` for gateway redirect; verify accepts authority without JWT on callback path.
- OTP codes stored hashed; guest purchase checkout requires authentication.

### 2026-07 — P1/P2 contracts & platform

- Standard error envelope on all endpoints (`error_code`, `message`, `details`).
- Cart merge on login; refresh token rotation; audit log for admin mutations.
- Idempotency keys on checkout and payment init.
- Order soft-delete; inquiry quote endpoint; refund via mock/Zarinpal provider.

### 2026-07 — P3 security

- Request throttles on contact, checkout, PLP search, and public tracking.
- SSRF guard on product image URLs; security middleware (body size, optional HTTPS, trusted hosts).
- Production config validators (Redis, CORS, OTP echo, weak PIN).

### 2026-07 — P4 data quality & ops

- `admin_note` separated from customer `note` on orders.
- `category_id` required on product create; category tree max depth **3** (strict).
- Docker bridge network; metrics (`/metrics`), structured logging, staging env template.

### 2026-07 — P5 testing & CI

- No API shape changes; coverage gate **68%** (enforced), ruff/mypy in CI, expanded test suite (160+ tests).

### 2026-07 — structure refactor + OTP hash column fix

- Internal only: split product/storefront endpoints and kitchen-sink CRUD modules; **no URL or payload changes**.
- Fix: `otp_codes.code` widened to `VARCHAR(64)` so SHA-256 hashed OTPs persist (restores `POST /auth/otp/request`).
- Docs moved: `BACKEND_CHANGES.md`, `ARCHITECTURE.md` under `docs/`.

### 2026-07 — contract drift fixes (post audit A)

- Docs: `GET /categories/tree` documented as **raw array** (was incorrectly `{data:[]}` in INTEGRATION/HANDOVER).
- OpenAPI: optional-auth routes use `HTTPBearer` with anonymous alternative `{}` in `security`.
- Snapshot: committed `openapi/v1.json` for offline typegen.
- Cart `base_price` serialized via `decimal_to_api_string` (aligned with PLP/order money strings).

### 2026-07 — security audit C hardening

- Production config: `APP_ENV=production` cannot be bypassed with `DEBUG=True`; requires `TRUSTED_HOSTS`, `ENFORCE_HTTPS`, non-mock payment, non-console SMS, docs off.
- Added regression tests: refresh-token reuse, step-up single-use, customer authz matrix (`tests/test_c_security_authz.py`).

### 2026-07 — catalog audit D

- Added `tests/test_d_catalog_audit.py` (inactive PDP, slug lookups, stock PUT guard, admin stats/change-log, SEO field exposure).
- Product detail/create responses now include `slug`, `short_description`, `meta_title`, `meta_description` (see product SEO P0).

### 2026-07 — commerce audit E

- Added `tests/test_e_commerce_audit.py` (cart lane isolation, short cart token, merge-on-login, inquiry_review status, purchase shipping required, paid-cancel blocked until refund).

### 2026-07 — payment audit F

- Added `tests/test_f_payment_audit.py` (payment init ownership, callback failure redirect, refund ledger + cancelled status, toman→rial ROUND_HALF_UP).

### 2026-07 — content audit G

- Added `tests/test_g_content_audit.py` (published-only blog, active/sorted heroes, unique contact tickets, comment auth/inactive guards, CMS auth, soft-fail order SMS, upload extension guards).

### 2026-07 — quality/ops audit H

- CI hygiene: ruff import fix (`test_g_content_audit.py`); mypy-safe Redis ping in `app/core/health.py`.
- Docker: create `appuser` before `chown` in `Dockerfile`.
- Dependencies: bump `python-dotenv` to `1.2.2` (pip-audit); note accepted `ecdsa` transitive advisory via `python-jose`.
- Confirmed ops surface: `/health`, `/ready`, `/metrics`, `X-Request-ID`, backup/restore scripts, env templates, performance smoke.

### 2026-07 — CI Postgres suite stabilization

- Test harness: `NullPool` + engine dispose across event loops; Postgres isolation via `TRUNCATE … CASCADE` (Alembic owns schema).
- Default suite clears `REDIS_HOST` (preserves `KARZAR_TEST_REDIS_HOST` for opt-in Redis tests) to avoid fail-closed 429s.
- Contact ticket placeholder shortened to fit `ticket_code` `String(32)` on Postgres.
- Readiness test mocks DB down instead of assuming unreachable production DSN.

### 2026-07 — staging VPS deploy kit

- Added `deploy/staging/` runbook + scripts (bootstrap, backend/frontend deploy, backup cron, restore, smoke).
- Staging compose binds API/DB/Redis to `127.0.0.1` (`!override` ports) for Nginx TLS termination.
- Provider swap later documented in `deploy/staging/PROVIDERS_LATER.md` (mock/console → Zarinpal/Kavenegar).

## Deprecations

| Item | Deprecated | Removal | Migration |
|------|------------|---------|-----------|
| `skip`/`limit` on admin lists | 2026-06 | TBD | Prefer `page`/`page_size` |
| Parsing payment data from `order.note` | 2026-07 | Removed | Use `payment_authority` / `payment_ref_id` |

## Exporting OpenAPI for clients

When `ENABLE_API_DOCS=false` in production, generate the contract from a dev/staging instance:

```bash
curl -s http://localhost:8000/api/openapi.json -o openapi/v1.json
npx openapi-typescript openapi/v1.json -o src/types/api.ts
```

Commit exported `openapi/v1.json` in the frontend repo or CI artifact when cutting a release.
