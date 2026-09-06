# TASK-RECORD · IMG-02A-02

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-02 |
| Title | Existing Image Human Review Batches and Pilot 001 |
| Change class | C1 |
| Prompt | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| Status | done |
| Progress | 100 |
| Merged PR | #203 |
| Implementation head | `86c7249158776688bf7bdf4a0a7a8a8fe358f107` |
| Merge commit | `023047b8cd0c82b48428f0c5037121e9f0471b24` |
| Base (pre-merge) | `225960fc7a4bbee158bc0b88c36442c6296e2e62` |

## Goal

Deterministic offline human-review packages over the IMG-02A-01 inventory, with Pilot 001 = 100 unique local assets; human review evidence validated externally.

## Non-goals honored

- No DB / ProductImage / storage mutation
- No remote fetches / TOSAG / OCR auto-verdicts
- No commit of previews, manifests, review CSVs/state, or ZIP
- No replacement execution in this task

## Final current disposition

```text
Status: done
Progress: 100
Merged PR: #203
Merge commit: 023047b8cd0c82b48428f0c5037121e9f0471b24
Pilot generation: complete
Pilot human review: complete
Replacement execution: not started
Database mutation: none
ProductImage mutation: none
Storage mutation: none
```

“done” covers governed batch tooling, Pilot 001 packaging, and Pilot 001
human-review integration only — not replacement sourcing or application.

## Chronology

1. Initial Pilot tooling (branch `feat/existing-image-review-batches`, Draft PR #203).
2. Authoritative Pilot generation (external under `/var/tmp/karzar-image-review/`).
3. Human review completed externally and validated (100 assets / 465 assignments).
4. R1 offline-HTML correction (`review.html` payload strips URLs/paths; corrected ZIP SHA below).
5. PR #203 merge @ `023047b8cd0c82b48428f0c5037121e9f0471b24`.

## Human-review aggregates (validated)

```text
assets reviewed: 100
assignments reviewed: 465
watermark: distributor_or_retailer=52 none_visible=48
asset decisions: KEEP=19 KEEP_AS_SECONDARY=20 PREFER_REPLACEMENT=52 REPLACE_REQUIRED=8 MANUAL_REVIEW=1
assignment suitability: exact_or_likely_exact=47 family_shared_plausible=376 likely_mismatch=41 insufficient_context=1
assignment decisions: KEEP=19 KEEP_AS_SECONDARY=203 PREFER_REPLACEMENT=201 REPLACE_REQUIRED=41 MANUAL_REVIEW=1
brand watermark (distributor_or_retailer / assets):
  ASTPOWER 20/20; Dasqua 4/12; INSIZE 0/31; Mitutoyo 0/9; SAN OU 10/10; TERMA 18/18
watermark assets: 52
REPLACE_REQUIRED assignments: 41
MANUAL_REVIEW assignments: 1
rights cleared: 0
rights: all review_required; no cleared_by_owner
Pilot is not statistically representative of all 1193 local images.
```

Principal mismatch groups (from owner report / REPLACE_REQUIRED queue):

```text
SAN OU Adapter Plates represented by complete chuck images: 8 assignments
SAN OU keyed chucks represented by a chuck-key image: 11
INSIZE granite surface plates represented by packaging: 7
Dasqua bore-gauge products represented by a single probe: 5
ASTPOWER DR230/DR313 replacement stones represented by machine images: 8
Mitutoyo indicator represented only by a dial face: 1
Dasqua Shore hardness tester represented by gauge blocks: 1
total REPLACE_REQUIRED assignments: 41
```

## Aggregate evidence (authoritative Pilot 001 packaging)

```text
source snapshot digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
pilot batch ID: IMG-02A-02-PILOT-001
selected unique assets: 100 (50 shared + 50 singleton)
assignment rows: 465
old Pilot ZIP SHA-256: 11b55eee567029ca2382dbecae6d7bb9170dbafc19b8465c53b470bb859f08d9
new corrected Pilot ZIP SHA-256: fc7a1206556c01dbe0fe73dea66bbde042fec06cf556c4c61bbfdd0094e9d300
network requests: 0
database access: false
storage mutations: 0
raw outputs / human-review: external under /var/tmp/karzar-image-review/
```

## Completed task scope

- tooling
- Pilot packaging
- human review integration

## Outstanding later work (not started here)

- replacement-source discovery
- owner approval of replacement assets
- staging application
- production application
- remaining 514 unique assets

## R1 note

Offline `review.html` browser payload must contain zero `http://` / `https://` / `image_url` / `source_relative_path` fields while retaining Product/SKU identity and preview filenames.
