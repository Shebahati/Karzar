# PROMPT 107 RESULT — Alembic pin lineage compatibility

**Date:** 2026-09-24  
**Branch:** `fix/kb-wave-alembic-pin-compatibility`

## Root cause

`assert_environment_gates` compared `alembic_version` with exact equality to
`environment_pins.alembic`. After PR3-B.1 (`s2t3u4v5w6x7` revising
`r1s2t3u4v5w6`), sealed `INSIZE_WAVE_001` correctly retained its sealed pin but
Evidence Validation fail-closed on a compatible descendant.

## Semantics (SSOT)

`environment_pins.alembic` means:

> sealed **minimum compatible** Alembic lineage revision; runtime must equal
> that revision or be a **descendant** of it in the application's Alembic
> revision graph.

Not: lexical ordering, forever-exact head, or arbitrary relaxation.

Plane and `freeze_required` remain exact.

## Implementation

- `app/services/alembic_revision_compat.py` — `is_runtime_revision_compatible`
- Wired into `knowledge_batch_assert_service._assert_safety_gates` (shared by
  execute, evidence validate, batch assert)

## Safety

No sealed Wave mutation. No deploy. No live validate-evidence in this PR.
