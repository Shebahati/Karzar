# PROMPT_66_RESULT

```text
PROMPT_66_RESULT

STATUS: COMPLETE (DESIGN ONLY — NO CODE / NO MIGRATION / NO EXECUTION)

Authority basis (implemented today):
  PR1 tables: knowledge_waves|products|runs|run_items (o8p9q0r1s2t3)
  PR2 seal+validate: Draft|Reviewed|Sealed (p9q0r1s2t3u4)
  Atomic SKU unit: POST .../products/{id}/kb-batch-assert
    (knowledge_batch_assert_service.execute_kb_batch_assert —
     single DB transaction per SKU; no commit inside service;
     freeze/plane/alembic gates; Batch-1 SHA + GEN_CALIPER literals)
  Live Batch-1 outcome (untouched by this design):
    45 published Facts | 45 Evidence links | 1 Artifact | 15 INSIZE typed SKUs
    Batch-1 manifest SHA:
      0c9f19d94db6e134e82550d51b7bcd1087e43ba5faf2bf0d70e62fc0390363c7

---------------------------------------------------------------------------
Execution model:
---------------------------------------------------------------------------

Service (proposed name): knowledge_wave_execute_service

PR3-A scope = assert orchestration only (run_type='assert').
Does NOT publish, create Evidence Artifacts, or mutate product JSONB.

Responsibilities (ordered):

  1) resolve_sealed_wave(wave_pk | wave_id | manifest_sha256)
       load wave + products (selectinload)
       require status ∈ {Sealed, Executing}
         - Sealed: start new assert run
         - Executing: resume only (see Failure handling)

  2) verify_manifest_sha
       recompute canonical seal payload (PR2 compute_manifest_sha256)
       require recomputed == wave.manifest_sha256
       refuse if drift (immutable surface broken)

  3) verify_environment_pins
       Read pins from sealed policy_json.environment_pins (PR3-A convention)
         { "plane": "...", "alembic": "...", "freeze_required": true }
       Compare live sentinels:
         KARZAR_DEPLOY_FREEZE == "true" when freeze_required
         environment_identity.plane == pins.plane
         alembic_version.version_num == pins.alembic
       Same semantics as today's kb-batch-assert gates, but values from
       the wave — not BATCH1_* module constants.

  4) create_wave_run
       Insert knowledge_wave_runs row:
         run_type='assert', status='created' → 'running'
         created_by=actor
         (PR3 additive columns recommended — see roadmap)
       Snapshot manifest_sha256 on the run (pin audit)
       Materialize knowledge_wave_run_items one per allowlist SKU:
         status='pending', product_id + sku_snapshot from wave_products
       Transition wave: Sealed → Executing (once, on first assert run start)

  5) execute_sku_units (sequential, stop-on-first-hard-failure default)
       For each pending item in stable order (product_id ASC):
         mark item running
         call existing kb-batch-assert unit (see Assertion flow)
         commit one SKU transaction on success
         update item → success|failed|skipped + error_message
       Never multi-SKU distributed transaction.

  6) finalize_run
       If all items success|skipped → run completed; wave Executing → Asserted
       If any failed (stop policy) → run failed; wave Executing → Failed
         (Failed is a wave status extension — PR3 migration)
       If operator abort → run aborted; wave Executing → Aborted|Failed
         (policy choice: Aborted preferred; Failed for resume-from-Sealed)

Architectural stance:
  Wave execution ORCHESTRATES kb-batch-assert; it does not fork a second
  assert path. kb-batch-assert remains the sole SKU mutation unit for
  assert+evidence-link creation in PR3-A.

---------------------------------------------------------------------------
Run lifecycle:
---------------------------------------------------------------------------

Prompt-66 target statuses for knowledge_wave_runs.status:

  created → running → completed
                    → failed
                    → aborted

  Also allowed: created → aborted (cancelled before first SKU)

Transitions (deny-by-default):

  created  → running     (executor acquired; first item about to start)
  created  → aborted     (operator cancel before work)
  running  → completed   (all items terminal success|skipped; none failed)
  running  → failed      (hard item failure under stop-on-first policy,
                          or exhausted retries)
  running  → aborted     (operator abort mid-run; current SKU rolled back
                          if uncommitted; prior SKUs remain committed)
  completed / failed / aborted → ∅   (terminal; never reopen same run_id)

PR1 CHECK today: ('running','succeeded','failed','aborted')
PR3-A migration MUST align vocabulary:
  succeeded → completed
  add created
  (additive CHECK replace; empty tables OK; no live run rows yet)

Wave status transitions owned by execute service (PR3 statuses):

  Sealed    → Executing     (on run start)
  Executing → Asserted      (run completed, allowlist covered)
  Executing → Failed        (run failed)
  Executing → Aborted       (run aborted; optional — may map to Failed)
  Failed    → Sealed        (operator re-approve same SHA; new run only)
  Asserted  → (out of PR3-A; evidence/publish later)

Forbidden in PR3-A:
  Draft|Reviewed → Executing
  Sealed → Asserted (must pass Executing + ledger)
  Any publish / EvidenceValidated transition

---------------------------------------------------------------------------
Run items:
---------------------------------------------------------------------------

Prompt-66 per-SKU statuses for knowledge_wave_run_items.status:

  pending → running → success
                    → failed
                    → skipped

  Also: pending → skipped (precheck: already asserted under resume rules)

Transitions:

  pending → running     (SKU unit opened)
  pending → skipped     (idempotent resume: Facts already present / PT
                         already assigned and policy says resume=ok)
  running → success     (kb-batch-assert returned OK; commit succeeded)
  running → failed      (validation/conflict/exception; DB rolled back
                         for this SKU only)
  success|failed|skipped → ∅   (terminal)

PR1 CHECK today: ('pending','ok','failed','skipped')
PR3-A migration MUST align:
  ok → success
  add running

Item row contract (PR3 additive recommended):
  product_id, sku_snapshot (already present)
  error_message (already present)
  + started_at / finished_at
  + resumed boolean (true when skip/success via existing Facts path)
  + result_json (optional: fact_ids created, specs_fingerprint)
  NO mandatory Fact FK (Prompt 64 invariant); fact_ids only in JSON if needed

Ordering: product_id ASC (stable, matches Batch-1 operator habit).

---------------------------------------------------------------------------
Assertion flow:
---------------------------------------------------------------------------

How execution calls kb-batch-assert (preferred PR3-A):

  A) Keep HTTP/service unit as the SKU boundary:
       execute_kb_batch_assert(db, product_id=..., manifest_sha256=wave.SHA,
         sku=..., product_type_id=wave.product_type_id,
         definition_id=wave.definition_id,
         facts=..., evidence_links=..., change_reason=..., actor=...)
     Endpoint still commits once per request.

  B) Wave executor calls the SAME service function in-process
     (not nested HTTP), with:
       - its own AsyncSession per SKU commit boundary, OR
       - one session + commit after each SKU (same as today's runner)
     On exception: rollback that SKU only; mark item failed; stop.

Generalization of kb-batch-assert (PR3-A companion, still no Batch rewrite):

  Phase G1 (shim, required before non-Batch waves):
    If manifest_sha256 == BATCH1_SHA → keep current constants
      (INSIZE / GEN_CALIPER / artifact 1 / no-existing-facts)
    Else → resolve Sealed|Executing wave by SHA and apply wave policy:
      brand from wave.brand
      product_type_id / definition_id from wave
      freeze/plane/alembic from wave.policy_json.environment_pins
      allowlist membership: (product_id, sku) ∈ wave_products
      resume rules from wave.policy_json.validation_rules

  Phase G2 (cleanup, later): drop BATCH1_* literals; Batch-1 becomes a
    backfilled Published/Archived wave row (INSIZE_WAVE_001) resolved by SHA.

What kb-batch-assert MUST continue to guarantee under wave orchestration:

  ✓ Atomic SKU transaction (assign PT + create asserted Facts + Evidence
    links in one commit; rollback clean on failure)
  ✓ No product.specifications / JSONB mutation
  ✓ No Fact publish (status stays asserted; publish is later PR)
  ✓ No Evidence Artifact create (links only to existing artifact ids
    declared by wave policy / Batch artifact)

Fact payload source for PR3-A:
  Out of band for design — executor receives per-SKU fact bundles from
  operator-supplied run request OR from wave-attached sealed artifact
  refs (future). PR3-A minimum: execute-assert request body carries
  allowlisted SKU payloads keyed by product_id, validated against
  wave_products before any mutation.

---------------------------------------------------------------------------
Failure handling:
---------------------------------------------------------------------------

Partial wave failure:
  Prior SKUs that committed remain in KB (asserted Facts + links).
  Failing SKU leaves no partial Facts (transaction rollback).
  Remaining pending items stay pending (not marked failed).
  wave_run.status = failed; wave.status = Failed (or stay Executing
  until finalize — prefer Failed for clear operator signal).

Resume behavior:
  New wave_run (never reopen failed run_id).
  Prerequisites: wave.status ∈ {Sealed, Failed→Sealed re-approval,
    or Executing if soft-resume policy enabled}.
  Recommended PR3-A: Failed → Sealed (same SHA) then new execute-assert.
  For each SKU:
    If Facts already exist for (product, definition set) AND
       validation_rules.resume_existing_facts == true
       → item skipped (or success+resumed=true); no re-create
    If product_type_id already == wave.product_type_id AND
       resume_existing_assignment == true
       → skip assignment conflict; continue Facts if missing
    Else run full kb-batch-assert unit

Retry policy:
  Default: stop-on-first-hard-failure; no automatic retry of failed SKU
    inside the same run.
  Operator may start a new run after fix (data/manifest/env).
  Soft/transient errors (optional later): at-most-once retry of same item
    while run still running — not required for PR3-A.

Idempotency:
  Keys: (wave.manifest_sha256, product_id, definition set)
  Re-entry of completed SKU → skipped/success resumed, not duplicate Facts
  Unique wave product allowlist already prevents duplicate SKU rows
  Concurrent execute-assert on same wave: refuse if another run is
    status=running (409); one active assert run per wave

Abort:
  POST .../waves/{id}/abort-run {run_id, change_reason}
  Sets current running item → failed or leaves pending; run → aborted
  Does not delete Facts from prior successful items

---------------------------------------------------------------------------
Security:
---------------------------------------------------------------------------

Hard gates for execute-assert (all required):

  1) Authentication/Authorization
       get_current_super_admin only
       change_reason required; audit: wave.execute_assert / wave.run.abort

  2) Sealed (or Executing resume) wave only
       Draft/Reviewed → 409
       SHA verify must pass

  3) Freeze gate
       KARZAR_DEPLOY_FREEZE=true when pins.freeze_required (default true)

  4) Plane gate
       environment_identity.plane == policy_json.environment_pins.plane

  5) Alembic pin
       alembic_version == policy_json.environment_pins.alembic

  6) Allowlist gate
       Requested SKU payloads ⊆ knowledge_wave_products for that wave

  7) Immutability
       Execute never PATCHes wave brand/policy/PT/definition/products
       Only status + append-only runs/items

Category A local vs Category B production:
  Same dual-control as Batch-1 (AGENTS.md / ingestion_boundary).
  Wave pins make plane/alembic explicit per wave instead of code constants.

---------------------------------------------------------------------------
Compatibility:
---------------------------------------------------------------------------

Existing live Batch-1 surface remains untouched by PR3-A design and by
any later empty-table migration:

  INSIZE Batch-1 / gold path (conceptual wave_id INSIZE_WAVE_001):
    12 Batch-1 SKUs asserted+published (Facts 10–45)
    Pilot 0 Facts 1–9 + Artifact 1
    Total 45 Facts | 45 Evidence links | 15 INSIZE typed SKUs
    Manifest SHA
      0c9f19d94db6e134e82550d51b7bcd1087e43ba5faf2bf0d70e62fc0390363c7

How untouched is guaranteed:

  - PR3-A ships code paths behind new endpoints; no DML backfill in
    the execution PR unless Owner separately authorizes INSIZE_WAVE_001
    registry insert.
  - kb-batch-assert Batch-1 SHA shim keeps current behavior for the
    existing HTTP unit until G2 cleanup.
  - No ALTER on knowledge_facts / evidence / products / JSONB.
  - Wave tables start empty; execute against new Sealed waves only.
  - Optional later: insert INSIZE_WAVE_001 as Published/Archived with
    historical run seed — Facts rows themselves never rewritten.

---------------------------------------------------------------------------
Implementation roadmap:
---------------------------------------------------------------------------

PR3-A (this design → next code prompt):
  M1 Additive migration
    - Extend knowledge_waves.status CHECK: +Executing +Asserted +Failed
      (+Aborted if chosen)
    - Align wave_runs.status CHECK to created|running|completed|failed|aborted
    - Align wave_run_items.status CHECK to pending|running|success|failed|skipped
    - Optional columns: runs.manifest_sha256_snapshot, started_at, finished_at,
      stop_reason; items.started_at, finished_at, resumed, result_json
    - Downgrade drops only new constraints/columns; no KB table touches
  M2 Service knowledge_wave_execute_service
    - resolve / verify SHA / verify pins / create run+items / loop SKUs
    - call execute_kb_batch_assert; commit per SKU; finalize wave status
  M3 API
    - POST /knowledge/waves/{id}/execute-assert
    - POST /knowledge/waves/{id}/runs/{run_id}/abort (optional same PR)
    - GET  /knowledge/waves/{id}/runs[/{run_id}]
  M4 kb-batch-assert G1 shim (wave resolve by SHA; Batch-1 SHA preserved)
  M5 Tests: seal→execute happy path (local fixtures); Draft cannot execute;
     SHA mismatch refuse; freeze/plane/alembic refuse; partial failure +
     resume skip; Facts/JSONB untouched assertions
  M6 OpenAPI + API_CHANGELOG + aods validate

Explicitly NOT in PR3-A:
  EvidenceValidated / Publishing / Published orchestration
  Live Wave creation / Batch-1 backfill
  Deploy / production migration apply
  Async job worker (sync sequential executor is enough for ≤15–50 SKUs;
    async deferred if needed)

PR3-B (later): evidence validate + publish orchestration using run ledger
PR3-C (later): INSIZE_WAVE_001 backfill + G2 remove BATCH1 literals

---------------------------------------------------------------------------
Blockers:
---------------------------------------------------------------------------

  1) Schema drift vs Prompt-66 vocabulary
     PR1 CHECKs use succeeded/ok; Prompt-66 wants completed/success +
     created/running — migration mandatory before execute APIs.

  2) environment_pins not first-class columns yet
     PR3-A stores pins under policy_json.environment_pins (sealed
     immutable). Optional later columns if queryability needed.

  3) Fact/Evidence payload packaging for non-Batch waves
     Executor needs a sealed or request-bound per-SKU payload source;
     Batch-1 can keep using existing manifest JSON files via shim.

  4) Owner authorization still required before any live execute
     (freeze dual-control + Category B) — out of this design prompt.

  5) No Accepted Canon conflict found for additive overlay tables;
     execution must not invent publish/JSONB rights.

STOP.
  No code.
  No migration.
  No execution.
  No Fact/Evidence writes.
  No deploy.
```
