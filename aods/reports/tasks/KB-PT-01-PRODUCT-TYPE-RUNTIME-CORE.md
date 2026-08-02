# TASK-RECORD · KB-PT-01

| Field | Value |
|-------|-------|
| Task ID | KB-PT-01 |
| Title | Introduce Product Type runtime core + nullable Product FK |
| Change class | C3 — Schema-affecting |
| Role | R-DB-ARCH / Platform (IMPL-schema-migration) |
| Branch | `feat/kb-pt-01-runtime-core` |
| Base | `origin/main` @ `e7ab2ef` (PR #194 Board Accept on main) |
| Outcome | COMPLETE locally — awaiting human commit/PR (HC-08 for apply); integrity gaps closed by **KB-PT-01A** |

## RESTATE

Implement PT-W1 only: first-class `product_types` + nullable indexed `products.product_type_id` with restrictive FK delete; preserve `products.id` as PKE; no Definition/membership/Property Dictionary/readout/taxonomy/seed/backfill/public API.

## Observed repository conventions (recorded)

| Concern | Observation | Choice |
|---------|-------------|--------|
| PK | Category/Brand/Product use `Integer` | `product_types.id` Integer |
| Slug | Category/Brand unique indexed slug | `slug` String(200) unique |
| Status | KnowledgeEdge String + CHECK | `status` String + `ck_product_types_status` |
| Timestamps | `Base.created_at` / `updated_at` tz | Inherited from Base |
| FK delete | `category_id`/`brand_id` omit `ondelete` | Same → PG `confdeltype=a` (NO ACTION) |
| Alembic head before | `d5e6f7a8b9c0` | New rev `e6f7a8b9c0d1` |
| API | Explicit Pydantic schemas | No `product_type_id` in ProductCreate/Update/Response |

## Allowlist (exact)

- `app/db/models/product_type.py` (new)
- `app/db/models/product.py`
- `app/db/models/__init__.py`
- `alembic/versions/e6f7a8b9c0d1_product_types_pt_w1.py`
- `tests/test_product_type_pt_w1.py`
- `aods/registry/document-registry.yaml` (Board minute `on_main: true`)
- `aods/reports/tasks/KB-PT-01-PRODUCT-TYPE-RUNTIME-CORE.md`
- `project-management/exports/tasks.json`
- `project-management/CHANGELOG.md`
- `project-management/DONE.md`
- `project-management/KANBAN_BOARD.md`
- `project-management/progress/KNOWLEDGE_BASE_PROGRESS.md`
- `project-management/sprints/SPRINT_05.md`

## Migration evidence

| Step | Result |
|------|--------|
| `alembic upgrade head` (Docker net → Postgres 15) | PASS → `e6f7a8b9c0d1` |
| Schema | `product_types` present; unique code/slug; CHECK status |
| `products.product_type_id` | nullable = true |
| FK `fk_products_product_type_id_product_types` | `confdeltype = a` (NO ACTION) |
| Index | `ix_products_product_type_id` |
| Seed rows | `product_types` count = 0 |
| Non-null assignments | 0 |
| `alembic downgrade -1` | PASS → `d5e6f7a8b9c0` |
| `alembic upgrade head` again | PASS → `e6f7a8b9c0d1` |

Lock/rollback notes: nullable ADD COLUMN without default is metadata-only on modern Postgres; no table rewrite; no data SQL; downgrade drops FK/index/column/table only.

## Tests

```text
pytest tests/test_product_type_pt_w1.py -q
18 passed
```

Coverage: create; code/slug unique; lifecycle valid/invalid; null FK; assign FK; RESTRICT delete unloaded (`passive_deletes="all"` + PRAGMA on SQLite); **RESTRICT delete with `selectinload(ProductType.products)` loaded**; product delete keeps type; category change independent; no seed/backfill; no readout columns; JSONB unchanged on assign; no public routes; migration has no CASCADE/SET NULL/INSERT.

## KB-PT-01A — Integrity gap closure (2026-08-02)

### Deletion integrity

| Item | Result |
|------|--------|
| Relationship | `passive_deletes="all"` on `ProductType.products` |
| Unloaded collection delete | IntegrityError; FK preserved (existing test) |
| Loaded collection delete (`selectinload`) | IntegrityError; Product + non-null `product_type_id` preserved |
| DB FK | unchanged NO ACTION (`confdeltype=a`); no SET NULL / CASCADE |

### Populated pre-migration evidence (disposable Docker Postgres)

Parent revision `d5e6f7a8b9c0` → insert Product → upgrade `e6f7a8b9c0d1` → downgrade → upgrade.

| Field | Value |
|-------|-------|
| SKU | `PTW1A-PRE-001` |
| Product ID | `1` |
| Product count before/after | `1` / `1` |
| specs md5 before | `b372e4aa4ae597be4300451a8fce2fc2` |
| specs md5 after upgrade | identical |
| specs md5 after downgrade | identical |
| specs md5 after second upgrade | identical |
| `product_type_id` after upgrade | NULL |
| Product Type rows | `0` |
| Non-null assignments | `0` |
| Exit codes | parent upgrade 0; PT-W1 upgrade 0; downgrade 0; re-upgrade 0 |

Nested JSONB marker present: `ptw1_probe=pre-migration-marker-01A`.

## PROVED ABSENT

- Caliper/catalogue seed
- Assignment backfill
- Readout persistence
- Category auto-assignment
- JSONB↔Facts dual-write
- Product Type Definition / Attribute Membership
- Taxonomy bridge / PRODUCT_CLASSIFIED_AS
- Public Product Type endpoints
- Frontend changes
- Silent ORM FK-nulling on loaded ProductType.products delete

## NEXT WAVE

**KB-REMEDIATION-11A** — Runtime Property Definitions, aliases, and Units only (after PT-W1 merge). Do not start PT-W2 before 11A.
