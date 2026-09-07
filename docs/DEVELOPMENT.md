# Development

Operational how-to. Binding criteria stay in [`architecture/CANON-LOCK.md`](architecture/CANON-LOCK.md). Branch rules: [`development/git-development-workflow.md`](development/git-development-workflow.md). Standards pack: [`development/standards/`](development/standards/).

## Stack

FastAPI + SQLAlchemy async + Postgres + Redis. Storefront and admin: Next.js 16 / React 19 / Tailwind 3 / TanStack Query. Locale: `lang="fa"` `dir="rtl"`.

## Local backend

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
# or: python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
# uvicorn app.main:app --reload --port 8000
```

| Host port | Service |
|-----------|---------|
| 8000 | API (`/health`, `/ready`, `/api/docs` when `ENABLE_API_DOCS=true`) |
| 5435 | Postgres |
| 6379 | Redis |

Templates: `.env.example` (dev), `.env.staging.example` (staging checklist). Never commit real secrets.

## Local frontends

```bash
cd frontend/Storefront && cp .env.example .env.local && npm ci && npm run dev -- --port 3000
cd frontend/admin-panel && cp .env.example .env.local && npm run dev -- --port 3001
```

| Variable | Truth |
|----------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | Default `http://localhost:8000/api/v1`. This is the only public API base name. |
| `NEXT_PUBLIC_USE_MOCK` | Local mock only. Production must be `false`. |

Admin scripts: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.

## Tests

```bash
# Backend — SQLite default; CI uses Postgres 15 + Redis 7
pytest
USE_POSTGRES_TESTS=1 pytest
ruff check app tests

# Coverage gate (single SoT): 68%
# pyproject.toml [tool.coverage.report] fail_under = 68
# .github/workflows/backend-ci.yml --cov-fail-under=68
```

Database truncation, category/brand/admin seed, and the test-admin bcrypt hash run only for tests that opt into `override_database` (fixture dependency, `usefixtures`, or a `super_admin_headers` / `purchase_customer_headers` request). Pure helper tests do not open Postgres.

```bash
# Iteration — no database fixture (parsers, taxonomy, image helpers, fixture guards)
pytest tests/test_category_tree.py tests/test_jsonb_filters.py tests/test_conftest_fixtures.py -q

# Iteration — one DB-backed slice (still uses real Postgres when USE_POSTGRES_TESTS=1)
USE_POSTGRES_TESTS=1 pytest tests/test_product_endpoints.py tests/test_c_security_authz.py -q

# Before final submission — same gate as backend-ci.yml `test`
alembic upgrade head
USE_POSTGRES_TESTS=1 pytest --cov=app --cov-report=term-missing --cov-fail-under=68
```

Do not run the full suite after every small edit. Do not run the full suite for a docs-only change unless a binding rule requires it.

## Schema and API shape

- Schema changes: Alembic only (`docs/development/standards/alembic-and-schema-change-rules.md`).
- Endpoints own `commit`/`rollback`; services/CRUD flush only (`ARCHITECTURE.md`).
- After any API shape change: regenerate `openapi/v1.json` in the same PR, update `API_CHANGELOG.md` if contract-affecting, run `python3 aods/tools/aods_validate.py --gate openapi`.

## Git

- Never develop on `main`. Prefixes: `feature/*`, `fix/*`, `hotfix/*`, `chore/*`, `docs/*`. `feat/*` is grandfathered only (`CR-002`). Cloud Agent `cursor/*` is platform-imposed.
- PR required. Humans push and merge unless a human explicitly orders otherwise in-session.
- No force-push to `main`. No dependency add/remove/upgrade without escalation.
- Catalog writers: `KARZAR_API_BASE=http://127.0.0.1:8000/api/v1` only (ADR-012).

## Auth (as-built)

- Storefront: OTP primary.
- Admin: password login; signed **HttpOnly** edge cookie `karzar_admin_session` after `/auth/me` proves `super_admin`. AuthGate re-checks API session + role. Destructive admin actions need step-up PIN (`X-Step-Up-Token`).
- JWT-in-`localStorage` is **not** the admin session model.

## Validation (on demand)

```bash
python3 aods/tools/aods_validate.py
python3 aods/tools/aods_validate.py --gate openapi
python3 aods/tools/aods_validate.py --gate ingestion-boundary
```

See [`../aods/README.md`](../aods/README.md).
