# PROMPT 117 RESULT — Fix Execute Failure Path + Inactive Product KB Policy + Governed Recovery

**Date:** 2026-09-24  
**Branch:** `fix/kb-wave-execute-recovery`  
**Scope:** Code + tests + docs/AODS/OpenAPI summary. **No deploy. No Live recovery. No merge. No product activation.**

## Incident (Live — unchanged by this prompt)

```text
wave_id=INSIZE_WAVE_003  wave_pk=3  status=Executing
assert_run_id=5  run_status=running
items: 2 success (1111-100, 1114-150) / 12 pending
Facts +6  Evidence links +6  (failure at 1114-200 is_active=false → MissingGreenlet)
```

## Phase 1 — Root-cause audit

| Question | Finding |
|----------|---------|
| Why `MissingGreenlet` on `actor.id`? | Failure path does `await db.rollback()` after a committed SKU, then `record_audit(..., actor_user_id=actor.id)`. Rollback expires ORM instances; lazy load of `User.id` requires an async greenlet → crash. |
| Does rollback/commit expire actor? | Yes for **rollback**. Session uses `expire_on_commit=False`, so success-path commit is usually fine; failure rollback is the hazard. |
| Other expired-ORM touch points | `_finalize_failure` / `_finalize_success` / item fail audit previously all used `actor.id`. |
| Where is `is_active` gated? | Canonical `knowledge_batch_assert_service._load_product_for_batch` (not Wave-only). Wave execute only calls batch-assert. |
| Gate scope | Removed from KB assert eligibility. Storefront/commercial gates unchanged. |

## Architecture decision

Knowledge assertion is orthogonal to storefront commercial state.

A product may be `is_active=false`, unavailable, or unpriced and still receive Product Type, Facts, Evidence, and (later) Published Knowledge.

Do **not** activate products merely to ingest technical specifications.

## Failure-handler fix

- Capture `actor_user_id = int(actor.id)` at the start of `execute_wave` / `resume_wave_run`.
- Pass the primitive through item success/fail audit, run finalize, and interrupted resume audit.
- Shared `_process_assert_items` + `_mark_item_failed_and_finalize` with last-resort force to `run=failed` / `Wave=Failed` if audit itself fails — never leave `Executing` + `running`.

## KB eligibility rule

| Gate | KB assert |
|------|-----------|
| `is_active=false` | **Allowed** |
| `is_available` / price / images / JSONB | Not required |
| `deleted_at IS NOT NULL` | Rejected |
| Wrong Product Type | Rejected |
| SKU ≠ product row / allowlist | Rejected |
| Manifest / env pins / definition | Unchanged fail-closed |

## Recovery semantics (chosen)

```text
Executing + interrupted assert run (status=running)
    ↓ POST /knowledge/wave-runs/{run_id}/resume
same run_id continues (pending/running items only)
    ↓ process remaining (batch-assert resume_existing_facts)
Asserted + run=completed
```

Failed-run resume (new run after Failed→Sealed) unchanged.

Do **not**: direct SQL status edits, delete Facts/revisions/links, restart all 14 blindly, or spawn a parallel execute engine.

## Partial-run idempotency

Test seeds 14 products, Wave=Executing, run=running, 2 success + 6 Facts/revisions/links, 12 pending; governed resume → Asserted, same `run_id`, totals 42/42/42 with only +36 new Facts/revisions/links.

## Files changed

| Path | Change |
|------|--------|
| `app/services/knowledge_batch_assert_service.py` | Remove `is_active` reject |
| `app/services/knowledge_wave_execute_service.py` | actor_user_id + robust finalize + interrupted resume |
| `app/api/endpoints/knowledge_wave_runs.py` | Resume summary |
| `tests/test_knowledge_waves_prompt117.py` | New regressions |
| `docs/API_CHANGELOG.md` | Behavior note |
| `openapi/v1.json` | Summary sync (no schema shape change) |
| `aods/registry/document-registry.yaml` | Register this artifact |
| `audit/insize-phase3/PROMPT_117_RESULT.md` | This file |

## Tests

```text
tests/test_knowledge_waves_prompt117.py  (7)
+ prompt68, 109, 104, 101, 65, 64, facts prompt12, batch_assert
```

## Prepared Live recovery plan (DO NOT EXECUTE in this prompt)

Precondition: code deployed with Prompt 117; verify baseline counts first (do not hardcode).

1. Read-only confirm: Wave003=Executing, run 5=running, progress 2 success / 12 pending, Facts/links deltas as incident.
2. `POST /api/v1/knowledge/wave-runs/5/resume` with `change_reason` documenting governed interrupted resume (sku_units from run snapshot OK).
3. Expect: same `run_id=5` → `completed`; Wave → `Asserted`; products success=14; Facts/revisions/links **+36** each (reuse existing 6).
4. Then Evidence Validate + Publish (separate authorization): publication revisions **+42**.
5. Global totals from pre-Wave003 baseline (verify first): facts=198, published=198, revisions=396, evidence_links=198 if no unrelated drift.

## Live safety this prompt

Live incident left untouched. No finalize, resume, execute, Fact/Evidence write, Publish, activation, or deploy.

## Merge readiness

`READY_FOR_OWNER_MERGE` after CI green — Owner merge only. No deploy / Live recovery until separately authorized.
