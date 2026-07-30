# AGENTS.md

## Cursor Cloud specific instructions

Karzar is a monorepo with three runnable services. Standard commands live in `README.md`,
`docs/TESTING.md`, and `frontend/README.md`; this section only records the non-obvious,
durable caveats for running the stack in the Cursor Cloud VM.

### Services

| Service | Dir | Dev port | Start command |
|---------|-----|----------|---------------|
| Backend API (FastAPI) | repo root / `app/` | 8000 | `.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| Storefront (Next.js) | `frontend/Storefront` | 3000 | `npm run dev -- --port 3000` |
| Admin panel (Next.js) | `frontend/admin-panel` | 3001 | `npm run dev -- --port 3001` |

The update script provisions the Python venv (`.venv`, from `requirements-dev.txt`) and runs
`npm install` in both frontends. It does NOT install or start infrastructure — see below.

### Postgres & Redis (must be started each session)

- Installed as system packages, but this VM has **no systemd**, so they are not auto-started.
  Start them manually at the beginning of a session:
  - `sudo pg_ctlcluster 16 main start`
  - `sudo redis-server --daemonize yes`
- Native Postgres listens on **5432** (not the `5435` host mapping used by `docker-compose.yml`).
  Local DB is `karzar_db`, credentials `postgres` / `postgres`.
- Cluster data persists in the VM snapshot, so previously created rows survive across sessions;
  the daemons themselves still need restarting each session.

### Backend env & run

- `.env` (repo root, gitignored) is required to run the API. For dev use
  `POSTGRES_SERVER=127.0.0.1`, `POSTGRES_PORT=5432`, `POSTGRES_PASSWORD=postgres`,
  `DEBUG=True`, `OTP_DEV_ECHO=True`, `ENABLE_API_DOCS=True`, a 32+ char `SECRET_KEY`, and an
  8+ digit `ADMIN_STEP_UP_PIN` (weak PINs are rejected only when `DEBUG=False`).
- Run `.venv/bin/alembic upgrade head` before first start after schema changes.
- On startup the app **auto-bootstraps** a super admin (from `INITIAL_SUPER_ADMIN_*`) and a
  sample dev product, so the catalog/login are usable immediately with an empty DB.
- Docs UI: `http://localhost:8000/api/docs` (only when `ENABLE_API_DOCS=True`). Health/readiness:
  `/health`, `/ready`.

### Frontend env

- Each app reads `.env.local` (gitignored). To hit the real backend set
  `NEXT_PUBLIC_USE_MOCK=false` and `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`.
  Without this the Storefront falls back to an in-memory mock layer.

### Testing / lint / build

- Backend `pytest` defaults to **in-memory SQLite** (no DB needed). Use `USE_POSTGRES_TESTS=1`
  for Postgres/JSONB parity (matches CI). Lint: `.venv/bin/ruff check app tests`; types: `mypy app`.
- Frontend (per app dir): `npx tsc --noEmit`, `npm run lint`, `npm test` (Vitest).
- Next.js here is **16.x** (App Router) with breaking changes vs older releases — see
  `frontend/admin-panel/AGENTS.md`.

### Gotchas

- Admin brand CRUD is not a top-level menu item; it lives in a "مدیریت برندها" modal on the
  Categories page (`/catalog/categories`).
