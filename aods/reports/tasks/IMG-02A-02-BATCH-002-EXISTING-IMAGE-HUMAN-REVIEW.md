# TASK-RECORD · IMG-02A-02-BATCH-002

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-02-BATCH-002 |
| Title | Sequential Existing Image Human Review Batch 002 |
| Parent | IMG-02A-02 (`done` / 100 — not reopened) |
| Change class | C2 / R1 |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Branch | `feat/existing-image-review-batch-002` |
| Status | in_progress |
| Progress | 90 |
| Draft/Ready PR | #205 |
| Batch ID | IMG-02A-02-BATCH-002 |

## Goal

Generalize Pilot-001-only tooling into deterministic sequential review batches; package
Batch 002 = exactly 100 previously unselected unique local assets; integrate completed
human-review evidence; correct schema `batch_id_default`.

## Non-goals honored

- No Batch 002 decision application / replacement execution
- No Pilot 001 label changes
- No DB / ProductImage / storage mutation
- No remote fetches / OCR auto-verdicts
- No commit of previews, manifests, review CSVs/state, or ZIP

## Current disposition

```text
Status: in_progress
Progress: 90
Batch 002 packaging: complete
Batch 002 human review: complete
review evidence: external and validated
schema Batch identity defect: corrected
image decisions applied: none
Replacement execution: not started
Database mutation: none
ProductImage mutation: none
Storage mutation: none
```

## Aggregates (authoritative packaging)

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
second-run semantic stability: yes (selection + preview/thumb maps)
old Batch 002 ZIP SHA-256: 1112f104c6d4746f9388caad5699ab03e9a9caeda4b9397d6db601db07192702
corrected Batch 002 ZIP SHA-256: 6d15fc266d5b22ceba343e0ad50bcfa4df192245571383f6091631984cf70a60
network requests: 0
```

## Human-review aggregates (validated)

```text
assets reviewed: 100
assignments reviewed: 212
watermark: distributor_or_retailer=36 none_visible=64
asset decisions: KEEP=32 KEEP_AS_SECONDARY=30 PREFER_REPLACEMENT=33 REPLACE_REQUIRED=5 MANUAL_REVIEW=0
assignment suitability: exact_or_likely_exact=50 family_shared_plausible=144 likely_mismatch=17 insufficient_context=1
assignment decisions: KEEP=32 KEEP_AS_SECONDARY=97 PREFER_REPLACEMENT=65 REPLACE_REQUIRED=17 MANUAL_REVIEW=1
brand watermark: ASTPOWER 13/13; Dasqua 1/11; INSIZE 0/44; Mitutoyo 0/10; SAN OU 1/1; TERMA 21/21
rights cleared: 0
human-review ZIP SHA-256: 3402f341ec6b0f5ca9e50a0abd069191bfc1ebb28656728bd3adafd7697d7bc5
review-state import-compatible with corrected package: yes
```

## Cumulative (Pilot + Batch 002)

```text
unique Assets reviewed: 200
assignments reviewed: 677
ShopMill watermark assets: 88
REPLACE_REQUIRED assignments: 58
MANUAL_REVIEW assignments: 2
remaining unique assets: 414
```

## Schema R1

`review_schema_document(batch_id)` now emits `batch_id_default` for the governed batch.
Pilot still defaults to `IMG-02A-02-PILOT-001`; Batch 002 emits `IMG-02A-02-BATCH-002`.

## Outstanding later work (not started)

- PR #205 merge → mark child done/100
- replacement-source discovery / owner approval / apply (58 queued informational)
- remaining unique assets after Batch 002 (414)
