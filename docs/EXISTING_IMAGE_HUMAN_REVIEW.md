# Existing Image Human Review (IMG-02A-02)

**Parent task:** IMG-02A-02 — Existing Image Human Review Batches and Pilot 001 (`done` / 100)
**Child tasks:** IMG-02A-02-BATCH-002 (closed) + IMG-02A-02-REMAINDER-ALL (open)
**Implementation status:** remainder-all packaging complete / human review pending / decisions not applied
**Merged PR:** #205 (Batch 002)
**Merge commit:** `1f391c0a3591c09888d12fbd5ec6d4ef8085de82` (Batch 002)
**Operational mode:** offline package generation + external human review
**Production mutation capability:** none

## Purpose

Build deterministic, offline human-review packages from the immutable IMG-02A-01 inventory:

- group validated local images by SHA-256 asset;
- select sequential review batches (Pilot 001, then Batch 002, …) with prior-batch exclusions;
- generate review previews/thumbnails **outside** Git and source storage;
- provide separate **asset-level** and **assignment-level** review forms;
- ship a self-contained `review.html` with **no** `http://`, `https://`, `image_url`, or `source_relative_path` in the browser payload;
- emit `review-schema.json` with `batch_id_default` equal to the governed batch ID.

## Current status

```text
IMG-02A-02 (parent): done / 100
Pilot 001 packaging: complete
Pilot 001 human review: complete
IMG-02A-02-BATCH-002: done / 100
IMG-02A-02-REMAINDER-ALL: in_progress / 70
Batch 002 merged PR: #205 @ 1f391c0a3591c09888d12fbd5ec6d4ef8085de82
remainder-all packaging: complete
remainder-all human review: pending
decisions applied: none
replacement execution: not started
review evidence: external, validated, not committed
schema batch identity correction: complete
```

“done” on Batch 002 means packaging, human review integration, schema correction and merge
are complete. It does **not** mean any image replacement was sourced, approved or applied.
58 cumulative replacements and 2 cumulative manual-review assignments remain queued only.
Rights remain `review_required`.

### Remainder-all package (current)

```text
task_id/batch_id: IMG-02A-02-REMAINDER-ALL
selection_mode: all_remaining
source unique assets: 614
prior reviewed assets excluded: 200
eligible before selection: 414
selected unique assets: 414
shared/singleton split: 88 / 326
assignments retained: 516
remaining unique assets after selection: 0
prior overlap: 0
brands represented: 6
pre-screen aggregate counts: low_resolution=71, extreme_aspect=2, transparent_background=73, busy_border=3
preview/thumbnail counts: 414 / 414
remote-deferred rows: 1
semantic second-run stability: true
ZIP SHA-256: 48d3466db5ac40356dafd1dbc83ec9edf16ba8d401981d035f35a00d220df960
ZIP bytes: 62309721
human review: pending
decisions applied: none
replacement execution: not started
```

The remainder package exists externally and remains pending human visual review before any downstream decision integration.

### Pilot 001 (historical / complete)

```text
assets reviewed: 100
assignments reviewed: 465
ShopMill-visible watermark assets: 52
REPLACE_REQUIRED assignments: 41
MANUAL_REVIEW assignments: 1
rights: all review_required (no cleared_by_owner)
corrected Pilot ZIP SHA-256: fc7a1206556c01dbe0fe73dea66bbde042fec06cf556c4c61bbfdd0094e9d300
```

### Batch 002 (complete; decisions not applied)

```text
source unique assets: 614
excluded Pilot 001 assets: 100
eligible before selection: 514
selected unique assets: 100
shared/singleton: 50 / 50
assignment rows: 212
brands represented: 6
remaining after selection: 414
Pilot overlap: 0
fallback_used: false
preview/thumbnail counts: 100 / 100
old Batch 002 ZIP SHA-256: 1112f104c6d4746f9388caad5699ab03e9a9caeda4b9397d6db601db07192702
corrected Batch 002 ZIP SHA-256: 6d15fc266d5b22ceba343e0ad50bcfa4df192245571383f6091631984cf70a60
human-review ZIP SHA-256: 3402f341ec6b0f5ca9e50a0abd069191bfc1ebb28656728bd3adafd7697d7bc5
```

Validated Batch 002 human-review aggregates (deterministic batch only — **not** representative of all 1193 local images):

```text
assets reviewed: 100
assignments reviewed: 212
watermark: distributor_or_retailer 36 / none_visible 64
asset decisions: KEEP 32, KEEP_AS_SECONDARY 30, PREFER_REPLACEMENT 33, REPLACE_REQUIRED 5, MANUAL_REVIEW 0
assignment suitability: exact_or_likely_exact 50, family_shared_plausible 144, likely_mismatch 17, insufficient_context 1
assignment decisions: KEEP 32, KEEP_AS_SECONDARY 97, PREFER_REPLACEMENT 65, REPLACE_REQUIRED 17, MANUAL_REVIEW 1
brand watermark (distributor_or_retailer / assets):
  ASTPOWER 13/13; Dasqua 1/11; INSIZE 0/44; Mitutoyo 0/10; SAN OU 1/1; TERMA 21/21
rights cleared: 0 (all review_required)
```

Principal mismatch groups (REPLACE_REQUIRED queue):

```text
tool-set images assigned to standalone tools: 8 assignments
SAN OU adapter plates represented by a complete chuck: 3
data-transfer cables represented by a digital caliper: 2
ASTPOWER replacement stones represented by complete machines: 2
INSIZE coating-thickness gauge represented by an incomplete probe/part: 1
Dasqua center gauge represented by a promotional display: 1
total REPLACE_REQUIRED assignments: 17
```

Manual review:

```text
AST-BS1-8: 1 assignment
reason: product title/model context is insufficient for a definitive suitability verdict
```

### Cumulative program (Pilot + Batch 002)

```text
unique Assets reviewed cumulatively: 200
assignments reviewed cumulatively: 677
visible ShopMill-watermarked Assets cumulatively: 88
REPLACE_REQUIRED assignments cumulatively: 58
MANUAL_REVIEW assignments cumulatively: 2
unique Assets remaining after Batch 002: 414
```

The cumulative replacement queue is informational only. None of the 58 replacements have been applied.

## Non-goals

- Database access or `ProductImage` writes
- Storage cleanup/replacement execution
- Remote HTTP/DNS/HEAD/GET or TOSAG
- OCR / automatic watermark verdicts
- Committing images, previews, raw inventory, review CSVs, review-state, or ZIP to Git
- Inferring legal rights clearance from `review_required`
- Executing Pilot or Batch 002 replacement queues in this phase

## Authoritative input

```text
source: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
prior Pilot ZIP: /var/tmp/karzar-image-review/IMG-02A-02-pilot-001.zip
Batch 002 human-review ZIP SHA-256: 3402f341ec6b0f5ca9e50a0abd069191bfc1ebb28656728bd3adafd7697d7bc5
```

## Commands

Pilot 001 (no prior batches; selection contract unchanged):

```bash
python scripts/build_existing_image_review_batches.py \
  --source-dir /absolute/path/to/img02a01-20260803T121056Z \
  --storage-root /absolute/path/to/data/uploads/products \
  --output-dir /absolute/empty/path/outside/repo \
  --zip-path /absolute/path/IMG-02A-02-pilot-001.zip
```

Batch 002:

```bash
python scripts/build_existing_image_review_batches.py \
  --source-dir /absolute/path/to/img02a01-20260803T121056Z \
  --storage-root /absolute/path/to/data/uploads/products \
  --output-dir /absolute/empty/path/outside/repo/img02a02-batch-002 \
  --zip-path /absolute/path/IMG-02A-02-batch-002.zip \
  --task-id IMG-02A-02-BATCH-002 \
  --batch-id IMG-02A-02-BATCH-002 \
  --prior-batch-dir /absolute/path/to/verified-pilot-package \
  --shared-count 50 \
  --singleton-count 50
```

Remainder-all:

```bash
python scripts/build_existing_image_review_batches.py \
  --source-dir /absolute/path/to/img02a01-20260803T121056Z \
  --storage-root /absolute/path/to/data/uploads/products \
  --output-dir /absolute/empty/path/outside/repo/img02a02-remainder-all \
  --zip-path /absolute/path/IMG-02A-02-REMAINDER-ALL.zip \
  --task-id IMG-02A-02-REMAINDER-ALL \
  --batch-id IMG-02A-02-REMAINDER-ALL \
  --prior-batch-dir /absolute/path/to/verified-pilot-package \
  --prior-batch-dir /absolute/path/to/verified-batch-002-package \
  --all-remaining
```

## Boundary claims

```text
network_requests_performed = 0
database_accessed = false
source_storage_mutations = 0
product_images_modified = false
```
