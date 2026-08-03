# Existing Image Human Review (IMG-02A-02)

**Parent task:** IMG-02A-02 — Existing Image Human Review Batches and Pilot 001 (`done` / 100)
**Child task:** IMG-02A-02-BATCH-002 — Sequential Existing Image Human Review Batch 002
**Implementation status:** Batch 002 packaging complete / human review pending
**Operational mode:** offline package generation + external human review
**Production mutation capability:** none

## Purpose

Build deterministic, offline human-review packages from the immutable IMG-02A-01 inventory:

- group validated local images by SHA-256 asset;
- select sequential review batches (Pilot 001, then Batch 002, …) with prior-batch exclusions;
- generate review previews/thumbnails **outside** Git and source storage;
- provide separate **asset-level** and **assignment-level** review forms;
- ship a self-contained `review.html` with **no** `http://`, `https://`, `image_url`, or `source_relative_path` in the browser payload.

## Current status

```text
IMG-02A-02 (parent): done / 100
Pilot 001 packaging: complete
Pilot 001 human review: complete
IMG-02A-02-BATCH-002: in_progress / 70
Batch 002 packaging: complete
Batch 002 human review: pending
Batch 002 decisions applied: none
replacement execution: not started
```

“done” on the parent covers governed batch tooling, Pilot 001 packaging, and Pilot 001
human review only. Batch 002 packaging does **not** apply decisions or replacements.

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

### Batch 002 (packaging complete; human review pending)

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
Batch 002 ZIP SHA-256: 1112f104c6d4746f9388caad5699ab03e9a9caeda4b9397d6db601db07192702
```

## Non-goals

- Database access or `ProductImage` writes
- Storage cleanup/replacement execution
- Remote HTTP/DNS/HEAD/GET or TOSAG
- OCR / automatic watermark verdicts
- Committing images, previews, raw inventory, review CSVs, review-state, or ZIP to Git
- Inferring legal rights clearance from `review_required`
- Executing the 41 Pilot replacement queue in this phase

## Authoritative input

```text
source: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
prior Pilot ZIP: /var/tmp/karzar-image-review/IMG-02A-02-pilot-001.zip
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

## Boundary claims

```text
network_requests_performed = 0
database_accessed = false
source_storage_mutations = 0
product_images_modified = false
```
