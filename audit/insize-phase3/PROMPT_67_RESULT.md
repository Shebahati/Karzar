# PROMPT_67_RESULT

```text
PROMPT_67_RESULT

STATUS: COMPLETE (API CONTRACT DESIGN ONLY — NO CODE / NO MIGRATION / NO EXECUTION)

Authority:
  PR1 tables + PR2 Seal/Validate (implemented)
  PR3-A execution model: PROMPT_66_RESULT
  SKU unit: POST /api/v1/knowledge/products/{product_id}/kb-batch-assert
  Prefix for all routes below: /api/v1/knowledge
  Auth: get_current_super_admin on every route

Path ID conventions (binding for PR3-A implementation):
  {wave_id}  = knowledge_waves.wave_id (VARCHAR unique business id)
               NOT the integer PK (integer remains available via
               GET /waves/{wave_pk} from PR1)
  {run_id}   = knowledge_wave_runs.id (integer PK)

---------------------------------------------------------------------------
API:
---------------------------------------------------------------------------

### 1) POST /waves/{wave_id}/execute

Purpose:
  Start assert orchestration for a Sealed wave.
  Creates wave_run + pending items, transitions Sealed → Executing,
  then processes SKU units (sync sequential in PR3-A).

Gates (all required; fail closed before any KB mutation):
  - super-admin
  - wave exists by wave_id
  - wave.status == Sealed
      (Executing/Failed → use resume; Draft/Reviewed → 409)
  - recompute PR2 canonical manifest SHA == wave.manifest_sha256
  - freeze gate: KARZAR_DEPLOY_FREEZE == "true"
      when policy_json.environment_pins.freeze_required is true (default true)
  - plane gate: environment_identity.plane == pins.plane
  - alembic pin: alembic_version == pins.alembic
  - no other knowledge_wave_runs for this wave with status=running (409)
  - request SKU set ⊆ wave_products allowlist

Request body:

  {
    "change_reason": "string, required, 1..4000",
    "sku_units": [                    // required, non-empty
      {
        "product_id": 123,
        "sku": "1108-150",            // must match wave_products.sku_snapshot
        "facts": [ /* same shape as kb-batch-assert facts */ ],
        "evidence_links": [ /* same shape as kb-batch-assert links */ ]
      }
    ],
    "stop_on_first_failure": true     // optional, default true
  }

  Rules:
    - Every allowlist SKU SHOULD appear in sku_units for a full-wave assert.
      Partial allowlist execute is FORBIDDEN in PR3-A (422) unless
      policy_json.validation_rules.allow_partial_execute == true
      (default false).
    - facts/evidence_links payloads are NOT stored on the wave table;
      they travel with the execute request (or later sealed artifact pack).
    - Idempotency-Key header: optional; if present, duplicate execute with
      same key within TTL returns prior wave_run_id (409/200 policy:
      prefer 200 with existing run if completed, 409 if running).

Response 201 Created:

  {
    "wave_run_id": 42,
    "wave_id": "INSIZE-CALIPER-WAVE-002",
    "wave_pk": 7,
    "wave_status": "Executing" | "Asserted" | "Failed",
    "status": "running" | "completed" | "failed",
    "manifest_sha256": "hex64",
    "created_items": [
      {
        "run_item_id": 1,
        "product_id": 123,
        "sku_snapshot": "1108-150",
        "status": "pending" | "running" | "success" | "failed" | "skipped"
      }
    ],
    "progress": {
      "total": 12,
      "pending": 0,
      "running": 0,
      "success": 11,
      "failed": 1,
      "skipped": 0
    },
    "stop_reason": null | "string"
  }

  Sync semantics (PR3-A):
    Handler may run the full SKU loop before returning, so status can be
    terminal (completed/failed) on the same response. created_items then
    reflects final item statuses. Long-running async worker is OUT of scope.

Errors (HTTP):
  401/403 auth
  404 wave_id unknown
  409 not Sealed | SHA drift | another run running | freeze/plane/alembic
  422 validation (empty units, allowlist mismatch, malformed facts)
  500 unexpected after partial progress (run marked failed; see run GET)


### 2) GET /wave-runs/{run_id}

Purpose:
  Read-only progress + item ledger for one assert run.

Response 200:

  {
    "run_id": 42,
    "run_type": "assert",
    "status": "created" | "running" | "completed" | "failed" | "aborted",
    "created_by": 1,
    "created_at": "ISO-8601",
    "started_at": "ISO-8601" | null,
    "finished_at": "ISO-8601" | null,
    "manifest_sha256_snapshot": "hex64",
    "stop_reason": null | "string",
    "wave": {
      "id": 7,
      "wave_id": "INSIZE-CALIPER-WAVE-002",
      "status": "Executing" | "Asserted" | "Failed" | "Sealed" | ...,
      "manifest_sha256": "hex64",
      "brand": "INSIZE",
      "product_type_id": 1,
      "definition_id": 1
    },
    "progress": {
      "total": 12,
      "pending": 3,
      "running": 1,
      "success": 7,
      "failed": 1,
      "skipped": 0
    },
    "items": [
      {
        "run_item_id": 1,
        "product_id": 123,
        "sku_snapshot": "1108-150",
        "status": "success",
        "resumed": false,
        "error_message": null,
        "result": {
          "fact_ids": [10, 11, 12],
          "evidence_link_ids": [10, 11, 12],
          "specifications_fingerprint": "hex64"
        },
        "started_at": "ISO-8601" | null,
        "finished_at": "ISO-8601" | null
      }
    ]
  }

Errors: 401/403; 404 run_id unknown


### 3) POST /wave-runs/{run_id}/resume

Purpose:
  Continue a failed assert run without duplicating Facts.
  Creates a NEW wave_run (recommended) OR re-opens pending items —
  BINDING CHOICE for PR3-A: create NEW run_id linked to same wave,
  copying pending/failed SKUs as pending; prior run stays failed
  (immutable ledger). Response returns the new wave_run_id.

  Prompt text says resume on {run_id}; contract:

    Input run_id = failed run to resume FROM (source ledger).
    Output wave_run_id = NEW run (never mutates terminal source run
    except optional audit pointer).

Rules:
  - source run.status == failed only (completed/aborted/running → 409)
  - parent wave.manifest_sha256 unchanged and still verifies
  - parent wave.status ∈ {Failed, Sealed}
      If Failed: transition Failed → Executing on new run start
      (Failed → Sealed re-approval NOT required if same SHA and
       policy_json.validation_rules.resume_from_failed == true;
       default true for PR3-A)
  - same gates as execute: super-admin, freeze, plane, alembic, SHA
  - no duplicate Facts (see Idempotency)
  - only SKUs that are not already success|skipped on ANY prior assert
    run for this wave+manifest are queued; prior successes become
    skipped+resumed on the new run

Request body:

  {
    "change_reason": "string, required",
    "sku_units": [ ... ] | null,   // null = reuse payloads from source
                                   // run's stored request snapshot if
                                   // PR3 stores run_request_json;
                                   // else required for remaining SKUs
    "stop_on_first_failure": true
  }

Response 201: same shape as execute response (new wave_run_id).

Errors:
  409 source not failed | SHA changed | wave not Failed/Sealed |
      another run running
  422 missing sku_units when no stored snapshot
  404 run_id unknown


Out of PR3-A API (explicit non-goals):
  POST .../publish, validate-evidence, abort (may be PR3-A.1)
  PATCH sealed wave fields
  Nested public wrap of kb-batch-assert (remains separate SKU API)

---------------------------------------------------------------------------
Services:
---------------------------------------------------------------------------

Module: app/services/knowledge_wave_execute_service.py
(name stable; Prompt 66 used knowledge_wave_execute_service)

### execute_wave(*, wave_id: str, sku_units, change_reason, actor,
                 stop_on_first_failure=True) → ExecuteResult

  1. Load wave by wave_id + products
  2. Require Sealed
  3. verify_manifest_sha(wave)
  4. resolve_wave_policy(wave) → pins + validation_rules + brand/PT/def
  5. assert_environment_gates(pins)
  6. Validate sku_units ⊆ allowlist; build ordered worklist
  7. Insert run (created→running) + items (pending); Sealed→Executing
  8. Audit wave.execute + wave.run.start
  9. For each item: execute_run_item(...); commit per SKU
 10. Finalize run completed|failed; wave Asserted|Failed
 11. Audit wave.run.complete | wave.run.fail
 12. Return ExecuteResult (wave_run_id, status, created_items, progress)

### execute_run_item(*, db, wave, run, item, sku_unit, policy, actor)
    → ItemResult

  - Mark item running
  - Call resolve path into kb-batch-assert unit:
      execute_kb_batch_assert(db, product_id=..., manifest_sha256=wave.SHA,
        sku=..., product_type_id=policy.product_type_id,
        definition_id=policy.definition_id,
        facts=sku_unit.facts, evidence_links=sku_unit.evidence_links,
        change_reason=..., actor=...)
  - On success: item success; audit wave.item.success; return fact_ids
  - On idempotent hit (see Idempotency): item skipped|success + resumed;
      audit wave.item.success with resumed=true
  - On hard failure: rollback SKU txn; item failed; audit wave.item.fail;
      raise StopRun if stop_on_first_failure

  Never commits inside execute_run_item when used under execute_wave —
  OR commits once per item at execute_wave boundary (same as Prompt 66).
  Binding: one commit per SKU at execute_wave loop (endpoint does not
  wrap the whole wave in one transaction).

### resolve_wave_policy(wave) → WavePolicy

  Returns frozen view:
    {
      wave_id, manifest_sha256,
      brand, product_type_id, definition_id,
      environment_pins: {plane, alembic, freeze_required},
      validation_rules: {
        resume_existing_facts: bool,          // default true
        resume_existing_assignment: bool,     // default true
        resume_from_failed: bool,             // default true
        allow_partial_execute: bool,          // default false
        property_set: [definition_id, ...]    // expected Fact defs
      },
      allowlist: [(product_id, sku_snapshot), ...]
    }

  Source: wave columns + policy_json (sealed immutable).
  Batch-1 shim: if manifest_sha256 == BATCH1_SHA, overlay today's
  REQUIRED_* constants for parity until G2 backfill.

Internal helpers (not HTTP):
  verify_manifest_sha(wave)
  assert_environment_gates(pins)
  resume_wave_run(source_run_id, ...)  // used by resume endpoint

---------------------------------------------------------------------------
Idempotency:
---------------------------------------------------------------------------

Identity key for a SKU assert unit:

  (manifest_sha256, product_id, definition_id=wave.definition_id,
   property_set = frozenset(fact.definition_id for facts in unit))

Expected behavior when the same key is presented again
(same wave, same SKU, same Definition, same property set):

  Case A — prior run_item success for this wave+manifest+product:
    Do NOT call create_fact again.
    Item → skipped (or success) with resumed=true.
    Return existing fact_ids in result if discoverable.

  Case B — product already has Facts for the property_set
    (Batch-1 live rows; or prior partial wave):
    If validation_rules.resume_existing_facts:
      treat as success/skipped resumed; no duplicate Facts.
    Else:
      Fact conflict error (409) → item failed.

  Case C — product.product_type_id already == wave.product_type_id:
    If resume_existing_assignment: skip assign; continue Facts if missing.
    Else: SKU conflict (409) → item failed.

  Case D — concurrent execute/resume while run running:
    409 CONFLICT on wave (one active running assert run).

  Case E — execute called twice on Sealed with empty prior success:
    First wins (Sealed→Executing). Second while running → 409.
    After Asserted → execute → 409 (use new wave / supersede path later).

  Case F — resume after partial failure:
    Successful SKUs from prior runs → skipped+resumed.
    Failed/pending SKUs → re-queued as pending on NEW run.
    No Fact row updates; only new Facts for remaining SKUs.

JSONB / publish:
  Still never mutated / never published by execute or resume.

---------------------------------------------------------------------------
Errors:
---------------------------------------------------------------------------

Canonical error_code mapping (existing ErrorCode enum; details[].field):

  validation failure
    HTTP 422 VALIDATION_FAILED
    fields: change_reason, sku_units, products.*, facts.*,
            evidence_links.*, wave_id (malformed), allow_partial_execute

  environment mismatch
    HTTP 409 CONFLICT
    fields: KARZAR_DEPLOY_FREEZE | environment_identity.plane |
            alembic_version | policy_json.environment_pins.*

  manifest / seal mismatch
    HTTP 409 CONFLICT
    fields: status (not Sealed), manifest_sha256 (drift)

  SKU conflict
    HTTP 409 CONFLICT
    fields: sku | product_id | product_type_id | allowlist |
            deleted_at | is_active | brand
    (mirrors kb-batch-assert product gate failures)

  Fact conflict
    HTTP 409 CONFLICT
    fields: facts | definition_id | entity_id
    when existing Facts block create and resume_existing_facts=false
    OR unexpected duplicate under unique (entity, definition)

  Evidence conflict
    HTTP 409 CONFLICT
    fields: evidence_links | artifact_id | relation_type
    when link target Fact missing, artifact missing, or duplicate
    governed link violates uniqueness — no Artifact create attempted

  run state conflict
    HTTP 409 CONFLICT
    fields: run_id.status | wave.status | concurrent_run

  not found
    HTTP 404 NOT_FOUND
    fields: wave_id | run_id | product_id

All errors: no partial commit for the failing SKU; prior SKU commits
remain. Run/item ledger records error_message from details.message.

---------------------------------------------------------------------------
Audit:
---------------------------------------------------------------------------

Use existing record_audit / record_audit_log.
entity_type = "knowledge_wave" | "knowledge_wave_run" | "knowledge_wave_run_item"
entity_id = respective PK

Required actions (exact strings):

  wave.execute
    when execute endpoint accepted gates and created run
    details: wave_id, wave_pk, wave_run_id, manifest_sha256,
             sku_count, change_reason

  wave.run.start
    when run status → running (may be same txn as execute)
    details: wave_run_id, wave_id, run_type=assert

  wave.run.complete
    when run → completed and wave → Asserted
    details: wave_run_id, progress, manifest_sha256

  wave.run.fail
    when run → failed and wave → Failed
    details: wave_run_id, stop_reason, failed_product_id?, progress

  wave.item.success
    per SKU success OR skipped-as-resume
    details: run_item_id, product_id, sku, resumed, fact_ids?

  wave.item.fail
    per SKU hard failure
    details: run_item_id, product_id, sku, error_code, error_message

Also recommended (not required by Prompt 67 name list):
  wave.run.resume   — when resume creates a new run from failed source
  wave.execute already covers first start; resume emits wave.run.resume
  then wave.run.start on the new run.

No audit event implies KB publish.

---------------------------------------------------------------------------
Security:
---------------------------------------------------------------------------

  - All three endpoints: get_current_super_admin only
  - Execute: Sealed only (+ gates above)
  - Resume: failed run only + same manifest + env gates
  - change_reason required on mutating endpoints
  - Category A/B ingestion boundary unchanged; live execute still
    requires Owner-authorized freeze dual-control (ops, not this design)
  - No step-up required for PR3-A (match kb-batch-assert); may add later

---------------------------------------------------------------------------
Implementation scope:
---------------------------------------------------------------------------

IN (next code prompt / PR3-A):
  - Additive migration: wave statuses Executing|Asserted|Failed;
    run/item status vocabulary alignment (PROMPT_66)
  - Optional additive columns: run snapshot/timestamps; item resumed/result
  - Services: execute_wave, execute_run_item, resolve_wave_policy
  - Endpoints: execute, GET wave-runs, resume
  - kb-batch-assert G1 SHA→wave resolve shim
  - Tests + OpenAPI + API_CHANGELOG + audit assertions
  - Sync sequential executor only

OUT:
  - Publish / EvidenceValidated APIs
  - Async job queue
  - Live Wave data / INSIZE_WAVE_001 backfill
  - Deploy / production migration apply
  - Abort endpoint (optional fast-follow)
  - Changing PR1 path style for GET /waves/{wave_pk}
    (execute uses business wave_id as specified here)

---------------------------------------------------------------------------
Blockers:
---------------------------------------------------------------------------

  1) PR1/PR2 path uses integer wave_pk; Prompt 67 execute uses string
     wave_id — implementation must add lookup-by-wave_id (no ambiguity
     if wave_id is always non-numeric-prefixed; document collision policy:
     wave_id strings never purely integer-only OR prefer exact wave_id match).

  2) Run/item CHECK vocabulary still PR1 (succeeded/ok) — migration
     required before these contracts can persist Prompt-66/67 statuses.

  3) Resume payload source: need run_request_json snapshot column OR
     require sku_units on every resume (choose in implementation PR;
     design allows both; prefer snapshot for operator ergonomics).

  4) environment_pins must be present in sealed policy_json for non-Batch
     waves; Batch-1 shim covers legacy SHA until backfill.

  5) No Accepted Canon conflict for additive overlay APIs; must not grant
     publish or JSONB rights.

STOP.
  No code.
  No migration.
  No execution.
  No Fact/Evidence writes.
  No deploy.
```
