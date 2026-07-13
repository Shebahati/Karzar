# API contract reference

Production may set `ENABLE_API_DOCS=false`, so interactive Swagger is not always available. Use the documents below as the **source of truth** for frontend and admin-panel integration.

## Primary contract documents

| Document | Audience | Contents |
|----------|----------|----------|
| [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md) | Storefront + Admin | **Primary** — parity checklist, gaps, phased work, E2E flows |
| [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) | Storefront Next.js | PLP/PDP, checkout, cart, auth, error envelope, examples |
| [BACKEND_CHANGES.md](../BACKEND_CHANGES.md) | Frontend sessions | Recent deltas, new endpoints, error codes, manual curl tests |
| [API_CHANGELOG.md](API_CHANGELOG.md) | All clients | Versioning policy, breaking vs non-breaking changes |
| [TESTING.md](TESTING.md) | Backend devs | pytest markers, CI, Postgres/Redis integration tests |

## OpenAPI / Swagger

| Env | `ENABLE_API_DOCS` | URLs |
|-----|-------------------|------|
| Local dev | `true` (default) | `/api/docs`, `/api/redoc`, `/api/openapi.json` |
| Staging | `true` recommended | Same paths |
| Production | `false` recommended | Export JSON from staging; do not rely on live docs |

## Endpoint map (v1)

Base path: `/api/v1`

| Module | Prefix | Key routes |
|--------|--------|------------|
| Auth | `/auth` | register, login, refresh, logout, OTP, verify-pin |
| Products | `/products` | CRUD, stock, images, soft delete/restore |
| Categories | `/categories` | tree, CRUD, spec-labels, spec-filter-options, spec-templates |
| Brands | `/brands` | CRUD (delete requires step-up) |
| Cart | `/cart` | get, add/update/remove items, merge on login |
| Orders | `/orders` | admin list/detail/status/quote, `/me`, `/track/{code}` |
| Payments | `/payments` | init, callback (GET), verify, refund |
| Users | `/users` | admin user list/search/update |
| CMS | `/cms` | blog, hero slides, product comments (admin) |
| Storefront | `/` | `/checkout`, `/contact`, `/blog`, `/hero-slides` |

System (outside v1): `GET /health`, `GET /ready`, `GET /metrics` (when enabled).

## Error envelope (all modules)

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Human-readable summary",
  "details": [{ "field": "sku", "message": "already exists" }]
}
```

## Keeping contract in sync

1. Backend change → update [API_CHANGELOG.md](API_CHANGELOG.md) and [BACKEND_CHANGES.md](../BACKEND_CHANGES.md).
2. Run `pytest` and contract tests (`tests/test_p5_contract.py`, `tests/test_p1_contract.py`).
3. Export `openapi.json` from dev and diff in frontend CI.
4. For mock API drift, prefer generated types from OpenAPI over hand-written mocks.
