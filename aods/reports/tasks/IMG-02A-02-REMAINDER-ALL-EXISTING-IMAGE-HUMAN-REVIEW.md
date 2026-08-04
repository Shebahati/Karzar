# TASK-RECORD · IMG-02A-02-REMAINDER-ALL

## Identity

| Field | Value |
|---|---|
| Task ID | IMG-02A-02-REMAINDER-ALL |
| Batch ID | IMG-02A-02-REMAINDER-ALL |
| Parent | IMG-02A-02 (`done` / 100 — not reopened) |
| Dependency | IMG-02A-02-BATCH-002 (`done` / 100) |
| Status | done |
| Progress | 100 |
| Merged PR | #207 |
| Implementation head | `c236e0cb4fd087a5d4cf9c8ef259bd27f010ce83` |
| Merge commit | `5ea3f54edb2dcf83f374ea34bec9073973ce8f2f` |
| Packaging | complete |
| Human review | complete |
| Human-review evidence | external and validated |
| Decisions applied | none |
| Replacement execution | not started |

## Goal

Package all remaining existing-image assets after Pilot 001 and Batch 002 into one
governed offline human-review package; validate and integrate completed human-review
evidence; merge via PR #207. No image decisions or replacements applied.

## Non-goals honored

- No image replacement execution
- No ProductImage writes / database access
- No source-storage mutation
- No network image requests
- No deploy
- No modification of Pilot 001 or Batch 002 human decisions
- No commit of raw review CSV/JSON/ZIP, previews, or thumbnails
- No legal rights clearance
- IMG-02B not started

## Final disposition

```text
Status: done
Progress: 100
Merged PR: #207
Implementation head: c236e0cb4fd087a5d4cf9c8ef259bd27f010ce83
Merge commit: 5ea3f54edb2dcf83f374ea34bec9073973ce8f2f
Packaging: complete
Human review: complete
Human-review evidence: external and validated
Decisions applied: none
Replacement execution: not started
database mutation: none
ProductImage mutation: none
storage mutation: none
network mutation: none
```

“done / 100” means the governed package, complete human-review coverage,
evidence validation, implementation merge and PMO closure are complete.

It does not mean any replacement image was sourced, approved or applied.
It does not mean rights were cleared.

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
source package SHA-256:
48d3466db5ac40356dafd1dbc83ec9edf16ba8d401981d035f35a00d220df960
zip bytes: 62309721
preview/thumbnails: 414 / 414
remote-deferred rows: 1
pre-screen counts: low_resolution=71, extreme_aspect=2, transparent_background=73, busy_border=3
semantic second-run stability: true
offline html/url contract: pass
prior-batch evidence path sanitization: pass (basename only)
raw evidence committed: no
```

## Human-review evidence (external only)

```text
human-review ZIP SHA-256:
9e40733a7bd9eece40c2cb3b84732b7dae664ef87ec3c1d4b5ef2f09e2262b87
human-review internal checksum items: 10
human-review checksum failures: 0
Asset review coverage: 414 / 414
Assignment review coverage: 516 / 516
review-state import-compatible with Remainder-All review.html: yes
rights_status: all review_required (cleared_by_owner = 0)
UNREVIEWED: 0
raw evidence committed: no
```

## Remainder-All Asset aggregates (authoritative)

```text
Remainder-All Assets reviewed: 414 / 414

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
Remainder-All Assignments reviewed: 516 / 516
Remainder-All REPLACE_REQUIRED Assignments: 30
Remainder-All MANUAL_REVIEW Assignments: 0

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

No replacements have been sourced, approved, or applied.

## Cumulative program disposition

```text
Cumulative unique Assets reviewed: 614 / 614
Cumulative Assignments reviewed: 1193 / 1193
Remaining unique Assets: 0
Cumulative REPLACE_REQUIRED Assignments: 88
Cumulative MANUAL_REVIEW Assignments: 2
Rights cleared: 0

Pilot 001 REPLACE_REQUIRED Assignments: 41
Batch 002 REPLACE_REQUIRED Assignments: 17
Remainder-All REPLACE_REQUIRED Assignments: 30

Pilot 001 MANUAL_REVIEW Assignments: 1
Batch 002 MANUAL_REVIEW Assignments: 1
Remainder-All MANUAL_REVIEW Assignments: 0
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

## Historical (pre-merge) PR disposition

While PR #207 was open the task was intentionally held at `in_progress` / `90`.
That open-state wording is historical only and no longer current.

## Outstanding later work

- source discovery for products without images
- replacement-source discovery for 88 queued Assignments
- resolution of 2 manual-review Assignments
- owner approval
- staging application
- production application
- legal rights clearance where required

Next governed implementation stage is **IMG-02B — Existing Source Paths**
(initial brands: Dasqua, INSIZE, SAN OU). IMG-02B is **not** started.
