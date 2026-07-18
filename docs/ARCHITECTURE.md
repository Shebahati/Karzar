# Karzar API Architecture (FastAPI + SQLAlchemy 2.0 + PostgreSQL)

**Updated:** 2026-07-18 — structure refactor R0–R2 (+ partial R3).  
**Contract rule:** Internal file moves must not change `/api/v1` paths or payloads. Frontend docs remain authoritative for shapes.

## Root layout

```text
karzar/
├── app/
│   ├── main.py                 # bootstrap, middleware, /health /ready
│   ├── api/
│   │   ├── deps.py             # authn/authz, step-up
│   │   ├── v1/__init__.py      # mounts routers (URL prefixes unchanged)
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── product.py              # thin aggregator
│   │       ├── product_common.py       # shared product helpers
│   │       ├── products_catalog.py     # PLP/PDP/related/statistics
│   │       ├── products_admin.py       # CRUD/stock/change-log
│   │       ├── products_images.py
│   │       ├── products_reviews.py
│   │       ├── storefront.py           # thin aggregator
│   │       ├── storefront_content.py   # blog/hero/contact
│   │       ├── checkout.py             # POST /checkout
│   │       ├── order.py / payment.py / cart.py
│   │       ├── category.py / brand.py / cms.py / users.py
│   ├── core/                   # config, security, errors, throttle, health
│   ├── services/               # business orchestration
│   ├── crud/
│   │   ├── otp.py              # OTP persistence (hashed codes)
│   │   ├── cart_persistence.py / refresh_tokens.py / audit.py / idempotency.py
│   │   ├── platform.py         # SHIM re-export (compat)
│   │   ├── content.py          # CMS + re-exports OTP for compat
│   │   ├── product.py / category.py / brand.py / commerce.py / …
│   ├── schemas/                # Pydantic API contracts
│   ├── db/models/              # ORM
│   └── utils/                  # helpers (+ utils/category package facade)
├── alembic/versions/
├── docs/                       # contracts, go-live, architecture, examples/
├── tests/
├── scripts/
└── Dockerfile / docker-compose*.yml
```

## Request flow

1. HTTP → security middleware → `app/api/endpoints`
2. Dependencies in `app/api/deps.py` (JWT, step-up, optional user)
3. Prefer `app/services/*` for orchestration
4. Persistence via `app/crud/*` → `app/db/models/*`
5. Response shaping via `app/schemas/*` + presenters in `utils/`
6. Error envelope from `app/core/errors.py`

## Compatibility shims

- `crud/platform.py` re-exports cart/refresh/audit/idempotency modules.
- `crud/content.py` still exports OTP helpers (implementation lives in `crud/otp.py`).
- `api/v1` still mounts **one** `product.router` and **one** `storefront.router` — public URLs unchanged.

## Security posture (unchanged by refactor)

- JWT + token_version revocation; refresh rotation
- Step-up PIN (single-use jti) for destructive admin actions
- Rate limits / public throttles via Redis when configured
- OTP stored as SHA-256 (`otp_codes.code` length 64)
- Production validators reject weak PIN, wildcard CORS, OTP echo, mock payment in production
- Image URL SSRF guard; body size limits; optional HTTPS / trusted hosts

## Related docs

- [API_CONTRACT.md](API_CONTRACT.md) — index for frontend
- [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md) — FE/BE parity
- [BACKEND_STRUCTURE_REFACTOR_MAP.md](BACKEND_STRUCTURE_REFACTOR_MAP.md) — refactor plan
- [GO_LIVE_EXECUTION_PLAN.md](GO_LIVE_EXECUTION_PLAN.md) — launch checklist
