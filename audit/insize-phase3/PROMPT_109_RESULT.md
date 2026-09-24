# PROMPT 109 RESULT — PR3-B.3 Governed Wave Publish

**Date:** 2026-09-24  
**Branch:** `feat/kb-wave-pr3b3-publish`  
**Scope:** Code + tests + OpenAPI/AODS. No deploy. No live Publish. No merge.

## Meaning of Wave Published

All Facts in the governed Wave scope are confirmed published under Wave
orchestration. Already-published Facts may be safely resumed/skipped without
creating duplicate revisions (critical for `INSIZE_WAVE_001`, whose 36 scope
Facts were published before Wave Registry existed).

## Architecture discovery

| Item | Detail |
|------|--------|
| Canonical Fact publish | `knowledge_fact_service.publish_fact` |
| Wave run reuse | `knowledge_wave_runs` / `knowledge_wave_run_items`, `run_type=publish` (CHECK already allows `publish`) |
| Migration | **NONE** |
| Lifecycle SSOT | `knowledge_wave_lifecycle.assert_transition` |
| Env gates | `assert_environment_gates` (plane / alembic lineage / freeze) |

## Delivered

| Item | Detail |
|------|--------|
| Service | `app/services/knowledge_wave_publish_service.py` — `publish_wave` |
| API | `POST /api/v1/knowledge/waves/{wave_id}/publish` |
| Transitions | EvidenceValidated → Publishing → Published; Failed→Publishing only after a prior publish run |
| Audit | `wave.publish`, `wave.publish.start`, `wave.publish.complete`, `wave.publish.fail` |
| Tests | `tests/test_knowledge_waves_prompt109.py` (+ Prompt 101 edge updates) |
| Docs | API_CHANGELOG + OpenAPI + AODS registry + this artifact |

## Idempotency / resume

- Already `published` Facts: skip; no second `publish_fact`; no new revision.
- `asserted` Facts: call canonical `publish_fact`.
- Missing/invalid/conflict: fail closed; Wave → Failed; no silent Published.
- Resume: POST publish again from Failed **only when the latest wave run is a
  failed `publish` run**; skips already-published Facts. Assert Failed (latest
  run = assert) must re-seal via PR3-A — publish stays closed.

## Scale

Synchronous HTTP loop over sealed Wave product allowlist only (not catalog-wide),
one commit per product — same boundary as Wave execute. Suitable for 12-SKU
pilot and ~50 SKUs. Waves of 500–5000 should reuse this ledger/service behind a
future background worker (not in this PR).

## Safety invariants preserved

- No `products.specifications` / JSONB dual-write
- No Evidence mutation on success path
- No sealed manifest/policy mutation
- No re-run of Assert or Evidence Validation
- No parallel Fact-publish engine

## Live safety (this prompt)

- No `POST …/waves/INSIZE_WAVE_001/publish`
- No deploy / merge
- Live remains `INSIZE_WAVE_001=EvidenceValidated`
