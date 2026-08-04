# Image Source Paths (IMG-02B)

**Task:** IMG-02B — Existing Source Paths (`in_progress` / 20)
**Phase completed:** deterministic source worklist (IMG-02B-01)
**Live discovery:** not started
**Image downloads:** 0
**Replacements applied:** 0

## Purpose

Build governed, deterministic, read-only source-discovery worklists for selected brands
from the immutable IMG-02A-01 inventory and the three completed existing-image human-review
bundles. Later nodes will consume these worklists for live adapters.

## Initial brands

- Dasqua
- INSIZE
- SAN OU

## Work types

| Type | Meaning | Priority |
|------|---------|----------|
| `missing_image` | Non-deleted product with zero ProductImage rows | P0 active+available / P1 active unavailable / P2 inactive |
| `replace_required` | Brand-matching REPLACE_REQUIRED assignment | P0 |
| `watermark_cleaner` | Third-party-watermarked asset needing cleaner image | P1 |
| `manual_review_hold` | MANUAL_REVIEW assignment (held; no auto discovery) | P0 |

Precedence when the same product appears in multiple queues:

```text
manual_review_hold > replace_required > missing_image > watermark_cleaner
```

All contributing reasons are retained in `work_reasons`.

## Authoritative inputs

```text
inventory: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d

human-review ZIPs under /home/moahmmad/Projects/Karzar-image-review:
  IMG-02A-02-pilot-001-human-review.zip
    SHA-256 02f8ebd66644073871d4109638625292f3c5c88c1ad60523bbcd409b8ea37b8d
  IMG-02A-02-batch-002-human-review.zip
    SHA-256 3402f341ec6b0f5ca9e50a0abd069191bfc1ebb28656728bd3adafd7697d7bc5
  IMG-02A-02-REMAINDER-ALL-human-review.zip
    SHA-256 9e40733a7bd9eece40c2cb3b84732b7dae664ef87ec3c1d4b5ef2f09e2262b87

cumulative human review: 614 Assets / 1193 Assignments / 88 REPLACE_REQUIRED / 2 MANUAL_REVIEW
```

The Pilot source package (`IMG-02A-02-pilot-001.zip`) is **not** interchangeable with the
Pilot human-review bundle.

## Current worklist aggregates

```text
work items: 1204
Dasqua / INSIZE / SAN OU: 688 / 263 / 253
missing_image: 1122 (674 / 229 / 219)
replace_required: 63 (7 / 34 / 22)
watermark_cleaner: 18 (7 / 0 / 17)
manual_review_hold: 1 (Dasqua only; ASTPOWER manual hold excluded as non-target brand)
priority: P0 892 / P1 312 / P2 0
unmatched: 0
ambiguous: 0
semantic_second_run_stable: true
```

Generated outputs remain external:

```text
/var/tmp/karzar-image-source-paths/img02b-01-run1
/var/tmp/karzar-image-source-paths/img02b-01-run2
/home/moahmmad/Projects/Karzar-image-source-paths/IMG-02B-01
```

## Source-path contracts (future discovery)

### Dasqua

- Adapter candidate: `dasqua_official`
- Class: official manufacturer
- Hosts: `www.dasquatools.com`
- Legacy script `scripts/import_dasqua_images_from_official.py` is mutation-capable and
  **must not** be executed by this phase (`legacy_execution_allowed = false`)

### INSIZE

- Adapter candidate: `insize_tosag`
- Class: authorized distributor candidate
- Hosts: `www.tosag.ch`
- Live parser status: pending validation
- Absence of an official INSIZE source here is **not** rights clearance

### SAN OU

- Adapter candidate: `sanou_official`
- Class: official manufacturer
- Hosts: `www.sanouchuck.com`, `en.sanouchuck.com`
- Legacy `scripts/sanou_official_catalog_enrich.py` is a content-enrichment/API tool,
  **not** an approved image-discovery adapter (`legacy_execution_allowed = false`)

All contracts keep:

```text
rights_status = review_required
apply_status = not_started
network_discovery_status = not_started
```

## Command

```bash
python scripts/build_image_source_worklists.py \
  --source-dir /absolute/path/to/img02a01-20260803T121056Z \
  --review-root /absolute/path/to/Karzar-image-review \
  --extract-root /absolute/empty/external/extract-dir \
  --output-dir /absolute/empty/external/output-dir \
  --compare-with /absolute/path/to/prior-output-dir \
  --copy-final-to /absolute/external/IMG-02B-01
```

## Planned later nodes (not started; no PMO tasks yet)

```text
IMG-02B-02 — Dasqua Official Discovery
IMG-02B-03 — INSIZE TOSAG Live Validation and Discovery
IMG-02B-04 — SAN OU Official Discovery
IMG-02B-05 — Consolidated Candidate Human Review
```

## Boundary claims

```text
network_requests_performed = 0
database_accessed = false
ProductImage_modified = false
source_storage_accessed = false
source_storage_mutations = 0
images_downloaded = 0
replacement_execution = false
rights_cleared = 0
```
