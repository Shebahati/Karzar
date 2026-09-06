# Karzar

B2B/B2C industrial-tools commerce monorepo.

| Path | Role |
|------|------|
| `app/`, `alembic/` | FastAPI + SQLAlchemy + Postgres |
| `frontend/Storefront/` | Public shop (Next.js 16, RTL/FA, `:3000`) |
| `frontend/admin-panel/` | Admin (Next.js 16, `:3001`) |
| `openapi/v1.json` | Machine API contract |
| `.github/workflows/` | CI + **manual** staging/production deploy |

- **Repo:** [Shebahati/Karzar](https://github.com/Shebahati/Karzar)
- **Live shop:** `https://www.karzartools.com`
- **API:** `https://api.karzartools.com`

## Authority (one concept → one active doc)

| Topic | Authority |
|-------|-----------|
| Agent / safety floor | [`AGENTS.md`](AGENTS.md) |
| Local setup, tests, branches | [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) |
| Architecture map | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Binding criteria index | [`docs/architecture/CANON-LOCK.md`](docs/architecture/CANON-LOCK.md) |
| API shapes | [`openapi/v1.json`](openapi/v1.json) · [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) · [`docs/API_CHANGELOG.md`](docs/API_CHANGELOG.md) |
| Deploy, backup, incidents | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) |
| Checkout, availability, payments | [`docs/COMMERCE.md`](docs/COMMERCE.md) |
| Accounting / warehouse | [`docs/HESABFA.md`](docs/HESABFA.md) |
| SEP gateway | [`docs/SEP_PAYMENT_GATEWAY.md`](docs/SEP_PAYMENT_GATEWAY.md) |
| Catalog writes | [`docs/architecture/data-ingestion-policy.md`](docs/architecture/data-ingestion-policy.md) |
| Process checks (CI; not a Charter supersession) | [`aods/README.md`](aods/README.md) · `CR-024` |
| Security reports | [`SECURITY.md`](SECURITY.md) |
| Work status | [GitHub Issues](https://github.com/Shebahati/Karzar/issues) / PRs |

Accepted ADRs/RFCs and the knowledge-spec pack stay under `docs/architecture/` and are indexed by Canon Lock. Historical material lives under [`docs/archive/`](docs/archive/) and is **not** current guidance.

## Facts that docs must not contradict

- Site inventory is binary `is_available` (موجود / ناموجود). Numeric warehouse stock is Hesabfa-only.
- Frontend API env var is `NEXT_PUBLIC_API_BASE_URL` (not `NEXT_PUBLIC_API_URL`).
- Backend coverage gate is **68%** (`pyproject.toml`).
- Staging deploy is **`workflow_dispatch` only** — not push-to-`main` auto-deploy. Staging shares the live VPS (`CR-011`).
- Production **cannot** boot with `PAYMENT_PROVIDER=mock`. Do not use mock as a production rollback.
- Admin edge session is a signed **HttpOnly** cookie; do not document JWT-in-`localStorage` as the admin session model.
- SEP integration **exists** in code. A successful real/test charge is **not yet proven**.
- Canonical PDP is `/product/{slug}`; `/product/{id}` **301**s to slug (ADR-010).

## Quick start

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md). Do not point catalog scripts at production.
