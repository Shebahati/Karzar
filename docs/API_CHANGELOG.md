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

\* Document in this file and in [BACKEND_CHANGES.md](BACKEND_CHANGES.md); frontend should handle new validation errors.

## Current baseline: API v1.0

**Status:** Active  
**Contract references:** [API_CONTRACT.md](API_CONTRACT.md), [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)

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

- No API shape changes; coverage gate 62%, ruff/mypy in CI, expanded test suite (160+ tests).

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

- Added `tests/test_d_catalog_audit.py` (inactive PDP, slug lookups, stock PUT guard, admin stats/change-log, SEO field exposure debt assertion).
- Confirmed: product/category/brand `meta_*` and product `slug` exist in DB but are not yet in API responses (non-breaking future addition).

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
