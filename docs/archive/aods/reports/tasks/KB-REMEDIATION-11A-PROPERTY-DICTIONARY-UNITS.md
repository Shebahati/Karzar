# TASK-RECORD · KB-REMEDIATION-11A

| Field | Value |
|-------|-------|
| Task ID | KB-REMEDIATION-11A |
| Title | Property Dictionary runtime — Units + Definitions + Aliases (A3) |
| Change class | C3 — Schema-affecting |
| Role | R-DB-ARCH / Platform (IMPL-schema-migration) |
| Branch | `feat/kb-remediation-11a-property-dictionary` |
| Base | `origin/main` @ `4a36b7a` |
| Outcome | COMPLETE locally — awaiting human commit/PR (HC-08 for apply) |

## RESTATE

Implement Prompt 11A / Alembic A3 only: empty overlay tables `knowledge_units`, `knowledge_property_definitions`, `knowledge_property_aliases`; idempotent CLI import from Git seed; super-admin read API. No templates tables, no PT Definitions/membership, no Facts/Evidence, no Product/Type assignment, no JSONB dual-write, no Storefront/Admin UI, no Alembic seed INSERT.

## Observed conventions (recorded)

| Concern | Observation | Choice |
|---------|-------------|--------|
| PK | Integer on KnowledgeEdge / ProductType | Integer PKs |
| Status | String + CHECK | `draft\|active\|deprecated` |
| Timestamps | `Base.created_at` / `updated_at` | Inherited; migration mirrors server defaults |
| Unit aliases | SPEC lists aliases per unit | JSONB `knowledge_units.aliases` (no 4th table) |
| Property aliases | SPEC §4 / seed `definitions[].aliases[]` | Separate table; UNIQUE(`alias_normalized`) |
| Alias normalize | Implementer convention | NFC + strip + casefold |
| Mutation | Master §12 Prompt 11A “admin read/seed import” | CLI/service import; HTTP **GET only** |
| Alembic head before | `e6f7a8b9c0d1` | New rev `f7a8b9c0d1e2` |
| Templates in seed | Present for authoring | Validated/ignored — **never persisted** |

## Allowlist (exact)

- `app/db/models/knowledge.py`
- `app/db/models/__init__.py`
- `app/schemas/knowledge.py`
- `app/crud/knowledge.py`
- `app/services/property_dictionary_service.py`
- `app/api/endpoints/knowledge.py`
- `alembic/versions/f7a8b9c0d1e2_knowledge_property_dictionary_11a.py`
- `scripts/seed_property_dictionary.py`
- `tests/test_property_dictionary_runtime.py`
- `openapi/v1.json`
- `docs/API_CHANGELOG.md`
- `aods/reports/tasks/KB-REMEDIATION-11A-PROPERTY-DICTIONARY-UNITS.md`
- `project-management/exports/tasks.json`
- `project-management/CHANGELOG.md`
- `project-management/DONE.md`
- `project-management/KANBAN_BOARD.md`
- `project-management/progress/KNOWLEDGE_BASE_PROGRESS.md`
- `project-management/sprints/SPRINT_05.md`

## Pre-commit controls (2026-08-02)

### 1. `aods/tools/aods_validate.py` not in 11A diff

```text
$ git diff -- aods/tools/aods_validate.py
(empty)

$ git diff --name-status origin/main
M	app/api/endpoints/knowledge.py
M	app/crud/knowledge.py
M	app/db/models/__init__.py
M	app/db/models/knowledge.py
M	app/schemas/knowledge.py
M	docs/API_CHANGELOG.md
M	openapi/v1.json
M	project-management/CHANGELOG.md
M	project-management/DONE.md
M	project-management/KANBAN_BOARD.md
M	project-management/exports/tasks.json
M	project-management/progress/KNOWLEDGE_BASE_PROGRESS.md
M	project-management/sprints/SPRINT_05.md
(+ untracked allowlist files: migration, service, CLI, runtime tests, this report)
```

**Verdict:** `aods_validate.py` unchanged — OK to commit from this control.

### 2. Second import — numeric counters + stable IDs

Import #1 counters:

| metric | value |
|--------|------:|
| units_created / updated / unchanged | 2 / 0 / 0 |
| properties_created / updated / unchanged | 9 / 0 / 0 |
| aliases_created / updated / unchanged | 36 / 0 / 0 |
| failed | 0 |

Import #2 counters (explicit):

| metric | value |
|--------|------:|
| units_created / updated / unchanged | **0 / 0 / 2** |
| properties_created / updated / unchanged | **0 / 0 / 9** |
| aliases_created / updated / unchanged | **0 / 0 / 36** |
| failed | **0** |

Stable integer PKs (import1 == import2):

- units: `[1, 2]`
- definitions: `[(1, def.measurement_range) … (9, def.battery_type)]`
- aliases: ids `1..36` unchanged (`STABLE_IDS True`)

### 3. OpenAPI path delta vs `origin/main`

| | |
|--|--|
| paths old → new | 85 → 90 |
| removed | (none) |
| added | only the five admin dictionary GETs below |

```text
ADDED:
  /api/v1/knowledge/dictionary/aliases          GET
  /api/v1/knowledge/dictionary/properties       GET
  /api/v1/knowledge/dictionary/properties/{definition_id}  GET
  /api/v1/knowledge/dictionary/units            GET
  /api/v1/knowledge/dictionary/units/{unit_id}  GET
```

No public dictionary route; no HTTP import/POST/PUT/PATCH/DELETE on dictionary paths. Aliases appear nested on property list/detail and via admin `GET .../aliases`.

### 4. AODS gates (requested set) — full output

```text
AODS validation — 5 gate(s), base=origin/main
  PASS  links                256 checked
  PASS  registry             256 checked
  PASS  pmo                  38 checked
  PASS  naming               1051 checked
  PASS  openapi              1 checked

RESULT: PASS — 0 new findings, 0 baselined
```

Command:

```bash
python3 aods/tools/aods_validate.py \
  --gate links --gate registry --gate pmo --gate naming --gate openapi
```

## Architecture checklist (code review)

| Requirement | Evidence |
|-------------|----------|
| Cross-property alias collision not silently reassigned | `validate_seed` rejects collisions; import raises if `existing.definition_id != definition_id` |
| Full validation before first DB write | `validate_seed(data)` before dry-run return and before upsert loop |
| Service does not commit | `import_property_dictionary` returns; CLI `session.commit()` only when not dry-run |
| Dry-run no flush/mutation | early return after validate; no `db.add`/`flush` |
| Datatype/unit constraints | Python closed-set + Alembic/ORM CHECKs on `data_type` / `dimension` / `status` |
| Second import preserves stable IDs | upsert by natural keys; evidence + tests assert PK tuples equal |
| API super-admin-only | every dictionary route `Depends(get_current_super_admin)` |
| Migration no seed / Product / JSONB | `f7a8b9c0d1e2` create/drop tables only |

## Migration evidence (disposable Postgres 15)

| Step | Result |
|------|--------|
| `alembic upgrade e6f7a8b9c0d1` | PASS |
| Pre-seed Product | id=1 SKU=`11A-EVIDENCE-001` `product_type_id=1` specs_md5=`83c29e840214532544141b2569110ba7` |
| `alembic upgrade f7a8b9c0d1e2` | PASS → head |
| Empty after upgrade | units=0 defs=0 aliases=0 |
| Forbidden tables | `knowledge_spec_templates` / `knowledge_template_properties` **absent** |
| Product after upgrade | same id / md5 / product_type_id |
| First CLI import | created 2/9/36; updated 0; unchanged 0; failed 0; seed_version `0.1.0`; checksum `60a059a7eda3408add9656fcd8e1b30c125955c5d7c85b51ca9ba09529ad6099` |
| Second CLI import | created **0**; updated **0**; unchanged **2/9/36**; failed **0**; integer PKs identical |
| `alembic downgrade -1` | PASS → `e6f7a8b9c0d1`; dictionary tables dropped; Product md5 preserved |
| `alembic upgrade head` | PASS → `f7a8b9c0d1e2` |

Lock/rollback notes: migration creates empty tables only (no INSERT); downgrade drops the three tables; Product/Type/JSONB untouched throughout.

## Tests

```text
pytest tests/test_property_dictionary_runtime.py tests/test_property_dictionary_v0.py -q
15 passed
```

Coverage: alias normalize; seed validation (datatype / collision); import idempotency with **created/updated/unchanged/failed** + stable PKs; dry-run no mutation; Product JSONB preservation; no template ORM tables; invalid-seed no mutation; uniqueness IntegrityError; admin API 401/403/200; no HTTP import/POST on dictionary routes.

## Admin API (super-admin only)

- `GET /api/v1/knowledge/dictionary/units`
- `GET /api/v1/knowledge/dictionary/units/{unit_id}`
- `GET /api/v1/knowledge/dictionary/properties` (+ nested aliases)
- `GET /api/v1/knowledge/dictionary/properties/{definition_id}`
- `GET /api/v1/knowledge/dictionary/aliases`

Import: `python scripts/seed_property_dictionary.py [--seed PATH] [--dry-run]`

## Deliberately not done

- PT-W2 Definitions / Attribute Memberships
- Facts / Evidence / taxonomy
- HTTP import endpoint
- Storefront or Admin stewardship UI (Prompt 10)
- Template persistence
- Dependency adds/upgrades
- Commit / push / PR / merge / deploy / live DB apply (HC-08)

## Next wave

**PT-W2 — Product Type Definitions and Attribute Memberships** (after 11A merge).
