# Existing Image Human Review (IMG-02A-02)

**Task:** IMG-02A-02 — Existing Image Human Review Batches and Pilot 001
**Implementation status:** merged to main
**Merged PR:** #203
**Merge commit:** `023047b8cd0c82b48428f0c5037121e9f0471b24`
**Operational mode:** offline package generation + human review evidence (external)
**Production mutation capability:** none

## Purpose

Build a deterministic, offline human-review package from the immutable IMG-02A-01 inventory:

- group validated local images by SHA-256 asset;
- select Pilot 001 (exactly 100 unique local assets);
- generate review previews/thumbnails **outside** Git and source storage;
- provide separate **asset-level** and **assignment-level** review forms;
- ship a self-contained `review.html` with **no** `http://`, `https://`, `image_url`, or `source_relative_path` in the browser payload.

## Current status

```text
IMG-02A-02 status: done
progress: 100
Pilot generation: complete
Pilot human review: complete
review evidence: external, validated, not committed
image decisions applied: none
replacement execution: not started
```

“done” applies only to governed batch tooling, Pilot 001 packaging,
and Pilot 001 human review.
It does not mean the 41 replacements were sourced or applied.

Validated human-review aggregates (Pilot 001 only — **not** representative of all 1193 local images):

```text
assets reviewed: 100
assignments reviewed: 465
watermark: distributor_or_retailer 52 / none_visible 48
asset decisions: KEEP 19, KEEP_AS_SECONDARY 20, PREFER_REPLACEMENT 52, REPLACE_REQUIRED 8, MANUAL_REVIEW 1
assignment suitability: exact_or_likely_exact 47, family_shared_plausible 376, likely_mismatch 41, insufficient_context 1
assignment decisions: KEEP 19, KEEP_AS_SECONDARY 203, PREFER_REPLACEMENT 201, REPLACE_REQUIRED 41, MANUAL_REVIEW 1
ShopMill-visible watermark assets: 52
assignments requiring replacement: 41
manual-review assignments: 1
rights: all review_required (no cleared_by_owner)
corrected Pilot ZIP SHA-256: fc7a1206556c01dbe0fe73dea66bbde042fec06cf556c4c61bbfdd0094e9d300
```

## Non-goals

- Database access or `ProductImage` writes
- Storage cleanup/replacement execution
- Remote HTTP/DNS/HEAD/GET or TOSAG
- OCR / automatic watermark verdicts
- Committing images, previews, raw inventory, review CSVs, review-state, or ZIP to Git
- Inferring legal rights clearance from `review_required`

## Authoritative input

```text
source: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
```

## Command

```bash
python scripts/build_existing_image_review_batches.py \
  --source-dir /absolute/path/to/img02a01-20260803T121056Z \
  --storage-root /absolute/path/to/data/uploads/products \
  --output-dir /absolute/empty/path/outside/repo \
  --zip-path /absolute/path/IMG-02A-02-pilot-001.zip
```

## Boundary claims

```text
network_requests_performed = 0
database_accessed = false
source_storage_mutations = 0
product_images_modified = false
```
