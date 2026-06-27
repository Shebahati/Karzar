# AGENTS.md

## Cursor Cloud specific instructions

This is a single Python 3.12 FastAPI backend ("Karzar – Industrial Lathe Tools API"). There is no frontend; the UI is the auto-generated Swagger docs at `/api/docs`. Standard commands live in `README.md`; only the non-obvious cloud caveats are captured here.

### Startup (run before using the app)

The update script only refreshes the Python venv (`.venv`). PostgreSQL and the Python deps persist in the VM snapshot, but services are NOT auto-started. On a fresh session:

1. Start PostgreSQL (installed locally, not via Docker — Docker is not available):
   `sudo pg_ctlcluster 16 main start`
2. Activate the venv: `source .venv/bin/activate`
3. Apply migrations if needed: `alembic upgrade head`
4. Run the dev server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Database / env notes

- A local Postgres role `postgres` (password `postgres`) and database `karzar_db` already exist. The committed `.env` points at `localhost:5432` with `REDIS_HOST=` (Redis disabled — it is only used for an optional `/ready` ping).
- `.env` uses `DEBUG=True` for local dev; `config.py` rejects weak `SECRET_KEY` (<32 chars) and weak `ADMIN_STEP_UP_PIN` only when `DEBUG=False`.
- App startup runs lifespan hooks that bootstrap a super admin (`09120000000` / `change-me-admin-password` from `.env`) and seed a small catalog (categories + brands), so a reachable DB is required at boot.
- Product create/update/delete requires a super admin Bearer token; destructive actions also need an `X-Step-Up-Token` (obtain via `POST /api/v1/auth/verify-pin`, PIN `84729101`).

### Tests

- `pytest` runs fully offline against in-memory SQLite (see `tests/conftest.py`) — no Postgres/Redis needed. `requirements-dev.txt` is required.
- There is no configured linter (no ruff/flake8/black config in the repo).
