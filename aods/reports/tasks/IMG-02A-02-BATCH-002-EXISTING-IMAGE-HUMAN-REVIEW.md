# TASK-RECORD · IMG-02A-02-BATCH-002

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-02-BATCH-002 |
| Title | Sequential Existing Image Human Review Batch 002 |
| Parent | IMG-02A-02 (`done` / 100 — not reopened) |
| Change class | C2 |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Branch | `feat/existing-image-review-batch-002` |
| Status | in_progress |
| Progress | 70 |
| Batch ID | IMG-02A-02-BATCH-002 |

## Goal

Generalize Pilot-001-only tooling into deterministic sequential review batches and package
Batch 002 = exactly 100 previously unselected unique local assets.

## Non-goals honored

- No Batch 002 human-review decisions in this task
- No Pilot 001 label changes
- No replacement execution (including the 41 Pilot queue)
- No DB / ProductImage / storage mutation
- No remote fetches / OCR auto-verdicts
- No commit of previews, manifests, review CSVs/state, or ZIP

## Current disposition

```text
Batch 002 packaging: complete
Batch 002 human review: pending
Batch 002 decisions applied: none
Replacement execution: not started
Database mutation: none
ProductImage mutation: none
Storage mutation: none
```

## Aggregates (authoritative packaging run)

```text
source unique assets: 614
excluded Pilot 001 assets: 100
eligible before Batch 002: 514
selected Batch 002 assets: 100
shared/singleton: 50 / 50
assignment rows: 212
brands represented: 6
remaining after Batch 002: 414
Pilot overlap: 0
fallback_used: false
pre-screen: low_resolution=9 extreme_aspect=1 transparent_bg=28 busy_border=3
preview/thumbnail counts: 100 / 100
second-run semantic stability: yes
Batch 002 ZIP SHA-256: 1112f104c6d4746f9388caad5699ab03e9a9caeda4b9397d6db601db07192702
network requests: 0
```

## Completed in this task

- sequential selection with prior-batch exclusions
- Pilot 001 selection compatibility preserved
- Batch 002 offline package + ZIP (external)
- focused + regression tests

## Outstanding later work (not started)

- Batch 002 human review
- replacement-source discovery / owner approval / apply
- remaining unique assets after Batch 002 (414)
