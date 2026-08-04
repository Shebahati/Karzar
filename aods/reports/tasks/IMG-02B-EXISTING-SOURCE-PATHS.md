# TASK-RECORD · IMG-02B

## Identity

| Field | Value |
|---|---|
| Task ID | IMG-02B |
| Title | Existing Source Paths |
| Node | IMG-02B-01-SOURCE-WORKLISTS |
| Status | in_progress |
| Progress | 20 |
| Phase completed | deterministic source worklist |
| Live discovery | not started |
| Image downloads | 0 |
| Replacements applied | 0 |

## Scope

Initial brands:

- Dasqua
- INSIZE
- SAN OU

Covers:

- products without images
- brand-matching REPLACE_REQUIRED Assignments from Pilot 001, Batch 002 and Remainder-All
- cleaner candidates for third-party-watermarked images
- manual-review queue held separately (`eligible_for_automatic_discovery = false`)

## Inputs

```text
inventory: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d

Pilot 001 human-review ZIP:
  /home/moahmmad/Projects/Karzar-image-review/IMG-02A-02-pilot-001-human-review.zip
  SHA-256: 02f8ebd66644073871d4109638625292f3c5c88c1ad60523bbcd409b8ea37b8d

Batch 002 human-review ZIP:
  /home/moahmmad/Projects/Karzar-image-review/IMG-02A-02-batch-002-human-review.zip
  SHA-256: 3402f341ec6b0f5ca9e50a0abd069191bfc1ebb28656728bd3adafd7697d7bc5

Remainder-All human-review ZIP:
  /home/moahmmad/Projects/Karzar-image-review/IMG-02A-02-REMAINDER-ALL-human-review.zip
  SHA-256: 9e40733a7bd9eece40c2cb3b84732b7dae664ef87ec3c1d4b5ef2f09e2262b87

cumulative review: 614 Assets / 1193 Assignments / 88 REPLACE_REQUIRED / 2 MANUAL_REVIEW
```

## Authoritative worklist aggregates (external)

```text
work_item_total: 1204
by_brand: dasqua 688 / insize 263 / san_ou 253
by_work_type:
  missing_image 1122
  replace_required 63
  watermark_cleaner 18
  manual_review_hold 1
by_priority: P0 892 / P1 312 / P2 0
missing_image_by_brand: dasqua 674 / insize 229 / san_ou 219
replace_required_by_brand: dasqua 7 / insize 34 / san_ou 22
watermark_cleaner_by_brand: dasqua 7 / san_ou 17 / insize 0
manual_review_hold_by_brand: dasqua 1
dedupe: input 1210 → unique 1204; multi-reason merges 6
unmatched_rows: 0
ambiguous_rows: 0
semantic_second_run_stable: true
```

## Output paths (external only)

```text
run-1: /var/tmp/karzar-image-source-paths/img02b-01-run1
run-2: /var/tmp/karzar-image-source-paths/img02b-01-run2
final: /home/moahmmad/Projects/Karzar-image-source-paths/IMG-02B-01
```

Raw worklists remain outside Git.

## Source-path contracts

```text
Dasqua: dasqua_official / www.dasquatools.com / legacy_execution_allowed=false
INSIZE: insize_tosag / www.tosag.ch / live_parser_status=pending_validation / legacy_execution_allowed=false
SAN OU: sanou_official / www.sanouchuck.com + en.sanouchuck.com / legacy_execution_allowed=false
rights_status: review_required
apply_status: not_started
network_discovery_status: not_started
```

## Safety

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

## Planned later nodes (not created / not started)

```text
IMG-02B-02 — Dasqua Official Discovery
IMG-02B-03 — INSIZE TOSAG Live Validation and Discovery
IMG-02B-04 — SAN OU Official Discovery
IMG-02B-05 — Consolidated Candidate Human Review
```

## Non-goals honored

No live crawling, downloads, DB/ProductImage/storage access, replacement execution,
manual-review resolution, rights clearance, deploy, or legacy importer execution.
