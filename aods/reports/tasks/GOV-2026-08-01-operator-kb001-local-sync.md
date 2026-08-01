# Operator residual — KB-001 local Alembic + projection sync

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Owner order** | «1.» = local alembic upgrade + projections/sync |
| **Env** | Cloud agent VM (no Docker); native PostgreSQL 16 + uvicorn on `127.0.0.1:8000` |
| **ADR** | ADR-012 Category A local only — not staging/prod |

## Commands / results

### 1. `alembic upgrade head`

**PASS** — migrated through `d5e6f7a8b9c0` (`knowledge_edges`).

### 2. API ready

```text
GET /ready → {"status":"ready","database":"ok","redis":"disabled"}
Bootstrap: super admin 09120000000 + sample product DEV-CHECKOUT-001
```

### 3. `POST /api/v1/knowledge/projections/sync`

```json
{
  "products_scanned": 1,
  "articles_scanned": 0,
  "edges_upserted": 2,
  "edges_deprecated": 0
}
```

Re-sync (idempotent): `edges_upserted` stable / no growth of deprecated beyond projector policy.

### 4. Read proof

`GET /api/v1/knowledge/edges` → **total=2**

| edge_type | count |
|-----------|------:|
| PRODUCT_BELONGS_TO_CATEGORY | 1 |
| PRODUCT_BRANDED_AS | 1 |

`GET /api/v1/knowledge/products/1/neighborhood` → category + brand edges present; articles empty (no CMS seed).

## Notes

- Agent previously deferred this (Day-3 close) because Docker/`lathe_api` were absent; this run used apt PostgreSQL + uvicorn instead.
- Local `.env` is gitignored and was not committed.
- Admin UI (#183) can now point `NEXT_PUBLIC_API_BASE_URL` at this API to see live edges (or keep mock).

## Residual for human laptop (optional)

On your own Category A compose stack, same checklist in `docs/architecture/specs/seeds/README.md` — this VM proof does not replace your machine if you need your full catalog data.
