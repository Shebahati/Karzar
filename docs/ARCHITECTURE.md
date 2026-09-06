# Architecture

Runtime map. Binding decisions: [`architecture/CANON-LOCK.md`](architecture/CANON-LOCK.md). API shapes: [`../openapi/v1.json`](../openapi/v1.json).

## Layout

```text
app/
  main.py                 # bootstrap, /health /ready /metrics
  api/v1/                 # mounts routers — public prefixes unchanged
  api/endpoints/          # HTTP handlers own commit/rollback
  api/deps.py             # authn/authz, step-up
  services/               # orchestration (flush only)
  crud/                   # persistence (flush/refresh only)
  schemas/                # Pydantic contracts
  db/models/              # ORM
  core/                   # config, security, errors, throttle
alembic/versions/
frontend/Storefront/      # Next.js 16 public shop
frontend/admin-panel/     # Next.js 16 admin
openapi/v1.json           # committed snapshot
```

Routers are mounted from `app/api/v1/__init__.py`. Internal file splits must not change `/api/v1` paths or payloads.

## Request flow

1. HTTP → security middleware → endpoint
2. `app/api/deps.py` (session/JWT, step-up, optional user)
3. `app/services/*` for orchestration
4. `app/crud/*` → `app/db/models/*`
5. `app/schemas/*` for response shape
6. Error envelope from `app/core/errors.py`

## Transaction ownership

HTTP handlers own `await db.commit()` / `rollback()`. Services and CRUD **flush only**, unless a documented worker owns its session.

Money-path callbacks commit only expected outcomes; unexpected errors roll back.

## Security posture (as-built)

- Admin edge session: signed HttpOnly cookie after `/auth/me` proves `super_admin`
- Refresh rotation / token_version revocation on API JWTs
- Step-up PIN (single-use) for destructive admin actions
- Production boot rejects weak PIN, wildcard CORS, OTP echo, **mock payment**, console SMS, empty `TRUSTED_HOSTS`

## Knowledge overlay

PKE identity = `products.id` (ADR-014). Primary Product Type = nullable `products.product_type_id` (ADR-015). Graph edges/Facts are a Postgres overlay (ADR-013). Dual-write and generative RAG stay deferred (`CANON-LOCK.md`).

## Deploy topology

One VPS today serves public traffic. `deploy-staging.yml` is **manual** `workflow_dispatch` on `main`. There is no isolated staging host (`CR-011`). Treat a qualifying deploy as a live release. See [`OPERATIONS.md`](OPERATIONS.md).
