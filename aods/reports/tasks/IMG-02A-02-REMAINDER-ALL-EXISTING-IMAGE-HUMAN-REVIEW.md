# TASK-RECORD · IMG-02A-02-REMAINDER-ALL

## Identity

| Field | Value |
|---|---|
| Task ID | IMG-02A-02-REMAINDER-ALL |
| Batch ID | IMG-02A-02-REMAINDER-ALL |
| Parent | IMG-02A-02 (`done` / 100 — not reopened) |
| Dependency | IMG-02A-02-BATCH-002 (`done` / 100) |
| Status | in_progress |
| Progress | 90 |
| Draft PR | #207 |
| Packaging | complete |
| Human review | complete |
| Human-review evidence | external and validated |
| Decisions applied | none |
| Replacement execution | not started |

## Goal

Package all remaining existing-image assets after Pilot 001 and Batch 002 into one
governed offline human-review package; validate and integrate completed human-review
evidence into PR #207. No image decisions or replacements applied.

## Non-goals honored

- No image replacement execution
- No ProductImage writes / database access
- No source-storage mutation
- No network image requests
- No deploy / merge
- No modification of Pilot 001 or Batch 002 human decisions
- No commit of raw review CSV/JSON/ZIP, previews, or thumbnails
- No legal rights clearance

## Authoritative source + prior proof

```text
inventory source: /var/tmp/karzar-image-audit/img02a01-20260803T121056Z
checksums.sha256 digest: 4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d
valid local rows: 1193
unique local assets: 614

pilot zip sha256: fc7a1206556c01dbe0fe73dea66bbde042fec06cf556c4c61bbfdd0094e9d300
batch-002 zip sha256: 6d15fc266d5b22ceba343e0ad50bcfa4df192245571383f6091631984cf70a60
prior package count: 2
prior asset union: 200
prior assignment union: 677
prior overlap: 0
```

## Selection + assignment contract (all remaining)

```text
selection_mode: all_remaining
source unique assets: 614
excluded prior assets: 200
eligible before selection: 414
selected unique assets: 414
shared assets selected: 88
singleton assets selected: 326
assignment rows: 516
remaining after selection: 0
prior overlap: 0
duplicate selected assets: 0
duplicate assignments: 0
fallback_used: false
brands represented: 6
```

## Output evidence (external only)

```text
output dir run-1: /var/tmp/karzar-image-review/img02a02-remainder-all
output dir run-2: /var/tmp/karzar-image-review/img02a02-remainder-all-run2
zip path: /var/tmp/karzar-image-review/IMG-02A-02-REMAINDER-ALL.zip
copied zip: /home/moahmmad/Projects/Karzar-image-review/IMG-02A-02-REMAINDER-ALL.zip
zip sha256: 48d3466db5ac40356dafd1dbc83ec9edf16ba8d401981d035f35a00d220df960
zip bytes: 62309721
preview/thumbnails: 414 / 414
remote-deferred rows: 1
pre-screen counts: low_resolution=71, extreme_aspect=2, transparent_background=73, busy_border=3
semantic second-run stability: true
offline html/url contract: pass
prior-batch evidence path sanitization: pass (basename only)
```

## Human-review evidence (external only)

```text
human-review zip: /home/moahmmad/Projects/Karzar-image-review/IMG-02A-02-REMAINDER-ALL-human-review.zip
outer SHA-256: 9e40733a7bd9eece40c2cb3b84732b7dae664ef87ec3c1d4b5ef2f09e2262b87
extract dir: /var/tmp/karzar-image-review/human-review/img02a02-remainder-all
internal checksum items: 10
internal checksum failures: 0
Asset review coverage: 414 / 414
Assignment review coverage: 516 / 516
review-state import-compatible with Remainder-All review.html: yes
rights_status: all review_required (cleared_by_owner = 0)
UNREVIEWED: 0
```

Raw package and human-review evidence remain outside Git. Only aggregates are recorded here.

## Remainder-All Asset aggregates (authoritative)

```text
Assets reviewed: 414

watermark_status:
  distributor_or_retailer: 75
  none_visible: 339

asset_decision:
  KEEP: 274
  KEEP_AS_SECONDARY: 53
  PREFER_REPLACEMENT: 76
  REPLACE_REQUIRED: 11
  MANUAL_REVIEW: 0
  BROKEN_OR_UNAVAILABLE: 0

quality_status:
  good: 401
  acceptable: 7
  weak: 5
  poor: 0
  unusable: 1

background_status:
  clean_white: 414

crop_status:
  good: 400
  excessive_whitespace: 14
```

ShopMill is treated as a distributor/retailer watermark.
Manufacturer logos printed on the product itself were not classified as third-party watermarks.
Absence of a watermark does not imply legal clearance.

## Remainder-All Assignment aggregates (authoritative)

```text
Assignments reviewed: 516

suitability_status:
  exact_or_likely_exact: 323
  family_shared_plausible: 163
  likely_mismatch: 19
  insufficient_context: 11

assignment_decision:
  KEEP: 276
  KEEP_AS_SECONDARY: 103
  PREFER_REPLACEMENT: 107
  REPLACE_REQUIRED: 30
  MANUAL_REVIEW: 0
  BROKEN_OR_UNAVAILABLE: 0
```

## Brand evidence

```text
ASTPOWER:
  Assets: 32
  Assignments: 50
  ShopMill-watermarked Assets: 32
  REPLACE_REQUIRED Assignments: 12

Dasqua:
  Assets: 13
  Assignments: 13
  ShopMill-watermarked Assets: 2
  REPLACE_REQUIRED Assignments: 0

INSIZE:
  Assets: 236
  Assignments: 299
  ShopMill-watermarked Assets: 0
  REPLACE_REQUIRED Assignments: 16

Mitutoyo:
  Assets: 92
  Assignments: 92
  ShopMill-watermarked Assets: 0
  REPLACE_REQUIRED Assignments: 2

SAN OU:
  Assets: 2
  Assignments: 6
  ShopMill-watermarked Assets: 2
  REPLACE_REQUIRED Assignments: 0

TERMA:
  Assets: 39
  Assignments: 56
  ShopMill-watermarked Assets: 39
  REPLACE_REQUIRED Assignments: 0
```

## Principal replacement groups (queue only)

```text
complete ASTPOWER machine image used for accessory or consumable: 5 Assignments
ShopMill technical diagram instead of direct product photo: 7 Assignments
clearly wrong or incomplete image: 6 Assignments
INSIZE shared-image model mismatch: 8 Assignments
catalog/specification page instead of independent product image: 4 Assignments
total REPLACE_REQUIRED: 30 Assignments
```

Principal affected SKUs include:

```text
AST-13MA, AST-26MA, FTV313, TS20, TS42, AST-GZD160, AST-GZD210, AST-GZD270,
AST-VH320, AST-VH345, AST-VH430, AST-VW105, 3050S, 518-230, 1150-1000,
ISH-SDM, ISH-STAC, ISH-STD, 1120-500, 2342-202, 2372-360, 3101-300,
3108-100, 3260-25SA, 4860-212, 4922-150, 6511-241, 6511-24, HDT-LP200B, HDT-LP200
```

No replacements have been sourced, approved, or applied in this node.

## Cumulative program disposition

```text
unique Assets reviewed cumulatively: 614 / 614
Assignments reviewed cumulatively: 1193 / 1193
unique Assets remaining: 0

Pilot 001 REPLACE_REQUIRED Assignments: 41
Batch 002 REPLACE_REQUIRED Assignments: 17
Remainder-All REPLACE_REQUIRED Assignments: 30
cumulative REPLACE_REQUIRED Assignments: 88

Pilot 001 MANUAL_REVIEW Assignments: 1
Batch 002 MANUAL_REVIEW Assignments: 1
Remainder-All MANUAL_REVIEW Assignments: 0
cumulative MANUAL_REVIEW Assignments: 2
```

Human review coverage of all existing validated local image Assets is complete.

The 88 replacement decisions and 2 manual-review decisions are queues only.

No replacement has been sourced, approved or applied.

The replacement program is **not** complete.

## Safety boundary proof

```text
network_requests_performed: 0
database_accessed: false
product_images_modified: false
source_storage_mutations: 0
repository_raw_review_evidence_tracked: 0
```

## PR disposition (while open)

```text
Draft/Ready PR: #207
branch: feat/existing-image-review-remainder-all
task status while PR open: in_progress / 90
do not mark done/100 before PR #207 merges
do not create another remainder task
```

## Outstanding later work

- replacement-source discovery for the cumulative queues (88 REPLACE_REQUIRED + 2 MANUAL_REVIEW)
- owner approval
- staging application
- production application
- legal rights clearance (separate from visual review)
