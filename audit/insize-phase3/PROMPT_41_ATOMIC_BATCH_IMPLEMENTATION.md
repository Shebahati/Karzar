# Prompt 41 — Governed KB Batch Assert Atomic Service

**Status:** Implemented in code/tests. **Not deployed. Not used for live Batch 1 yet.**

## Architecture

```text
POST /api/v1/knowledge/products/{product_id}/kb-batch-assert
        │
        ▼
knowledge_batch.py  (super-admin; single await db.commit())
        │
        ▼
knowledge_batch_assert_service.execute_kb_batch_assert(session)
        │
        ├── safety gates (freeze / plane / alembic)
        ├── allowlist checks (manifest SHA, INSIZE, NULL PT, artifact id=1)
        ├── SELECT Product … FOR UPDATE
        ├── assignment_service.assign_product_type
        ├── fact_service.create_fact × 3
        ├── evidence_service.link_artifact_to_fact × 3
        └── postconditions (asserted only, JSONB fingerprint unchanged)
```

Option A endpoint + Option B orchestration of existing domain services.

## Transaction boundary

One HTTP request = one SQLAlchemy session = **one commit**.

| Outcome | Effect |
|---------|--------|
| Success | `product_type_id` NULL→1 + 3 asserted Facts + 3 revision-1 rows + 3 Evidence links |
| Any failure | `get_db` rollback → **0 writes** for that SKU |

No partial SKU state via this endpoint.

## Safety gates (HTTP 409, no writes)

- `KARZAR_DEPLOY_FREEZE=true`
- `environment_identity.plane=live`
- `alembic_version=n7o8p9q0r1s2`
- `manifest_sha256=0c9f19d94db6e134e82550d51b7bcd1087e43ba5faf2bf0d70e62fc0390363c7`
- Product: exact SKU, INSIZE brand, active, not deleted, `product_type_id IS NULL`
- PT id=1 `GEN_CALIPER` active; Definition id=1 v1 active
- Artifact DB id=1 checksum = OEM 108A SHA
- Exactly 3 Facts (`def.measurement_range|resolution|accuracy`) and 3 Evidence links
- No existing Facts for those definitions

## Forbidden

Publish · Artifact create · JSONB mutation · PT/Definition/Dictionary/taxonomy create · commercial Product field updates

## Concurrency

Product row locked with `SELECT … FOR UPDATE` before mutation (same pattern as PT-W3A assignment).

## Audit (unchanged systems)

- `product_type.assign` + `product_change_logs`
- `knowledge_fact_revisions` (revision_number=1, status=asserted)
- `knowledge_evidence_link.create`

## Future Batch 1 usage

After **merge + live deploy**:

1. Fresh logical backup  
2. Confirm freeze / plane / alembic  
3. For each of the 12 manifest SKUs (stop-on-first-failure):

```http
POST /api/v1/knowledge/products/{product_id}/kb-batch-assert
Authorization: Bearer <super-admin>
```

Body = exact values from  
`audit/insize-phase3/INSIZE_BATCH1_12SKU_EXECUTION_MANIFEST.json`  
(SHA `0c9f19d94…`).

4. Assert-only — **do not publish** until a separate Owner authorization.

## Files

| Path | Role |
|------|------|
| `app/services/knowledge_batch_assert_service.py` | Orchestrator |
| `app/api/endpoints/knowledge_batch.py` | Endpoint |
| `app/schemas/knowledge.py` | Request/response |
| `app/api/v1/__init__.py` | Router mount |
| `openapi/v1.json` | Contract |
| `tests/test_knowledge_batch_assert.py` | Atomic + gate tests |

**Migration:** none. **Deploy:** required before live Batch 1.
