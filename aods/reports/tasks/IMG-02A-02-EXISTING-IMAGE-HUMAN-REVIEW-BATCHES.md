# TASK-RECORD · IMG-02A-02

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-02 |
| Title | Existing Image Human Review Batches and Pilot 001 |
| Change class | C1 |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Branch | `feat/existing-image-review-batches` |
| Status | in_progress |
| Progress | 70 |
| Base | `225960fc7a4bbee158bc0b88c36442c6296e2e62` |

## Goal

Deterministic offline human-review packages over the IMG-02A-01 inventory, with Pilot 001 = 100 unique local assets.

## Non-goals honored

- No DB / ProductImage / storage mutation
- No remote fetches / TOSAG / OCR auto-verdicts
- No commit of previews, manifests, ZIP, or raw inventory

## Deliverables

- CLI: `scripts/build_existing_image_review_batches.py`
- Package: `scripts/image_review/`
- Tests: `tests/test_existing_image_review_batches.py`
- Operator doc: `docs/EXISTING_IMAGE_HUMAN_REVIEW.md`

## Current disposition

```text
Pilot generation: complete
Human review: pending
Image decisions applied: none
Database / storage mutation: none
```

## Aggregate evidence (authoritative Pilot 001)

```text
source snapshot digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
pilot batch ID: IMG-02A-02-PILOT-001
selected unique assets: 100
shared assets selected: 50
singleton assets selected: 50
assignment rows included: 465
brands represented (6): ASTPOWER | ای اس تی پاور; Dasqua | داسکوا; INSIZE | اینسایز; Mitutoyo | میتوتویو; SAN OU | سانو; TERMA | ترما
low-resolution candidates: 6
extreme-aspect candidates: 0
transparent-background candidates: 48
busy-border candidates: 4
preview count: 100
thumbnail count: 100
semantic second-run stability: OK
network requests: 0 (--network none)
database access: false
storage mutations: 0 (mtime signature unchanged; 1193 files)
raw pilot outputs: /var/tmp/karzar-image-review/img02a02-pilot-001/
Pilot ZIP: /var/tmp/karzar-image-review/IMG-02A-02-pilot-001.zip
Pilot ZIP SHA-256: 11b55eee567029ca2382dbecae6d7bb9170dbafc19b8465c53b470bb859f08d9
```
