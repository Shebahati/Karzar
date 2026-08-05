# TASK-RECORD · IMG-02B

## Identity

| Field | Value |
|---|---|
| Task ID | IMG-02B |
| Title | Existing Source Paths |
| Node | IMG-02B-01-SOURCE-WORKLISTS |
| Status | in_progress |
| Progress | 40 |
| Phase completed | IMG-02B-01 worklists; R1 source-gap recalibration complete |
| Live discovery | started but incomplete — Dasqua/SAN OU calibration_failed; INSIZE partial |
| Image downloads | 18 unique external assets, INSIZE only |
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
candidate evidence before product-level precedence:
  missing_image: 1122
  replace_required: 63
  watermark_cleaner: 24
  manual_review_hold: 1
  total candidate reasons: 1210

product-level primary work types after precedence:
  missing_image: 1122
  replace_required: 63
  watermark_cleaner: 18
  manual_review_hold: 1
  total unique products: 1204

multi-reason product merges: 6
work_item_total: 1204

by_brand (primary work items): dasqua 688 / insize 263 / san_ou 253
by_priority: P0 892 / P1 312 / P2 0
missing_image_by_brand: dasqua 674 / insize 229 / san_ou 219
replace_required_by_brand: dasqua 7 / insize 34 / san_ou 22
watermark cleaner evidence before precedence by brand:
  Dasqua: 7
  INSIZE: 0
  SAN OU: 17
  total: 24
watermark_cleaner primary work_type after precedence: 18
manual_review_hold_by_brand: dasqua 1

Six watermark-cleaner reasons belong to products whose primary work type is
replace_required or another higher-precedence type. Their watermark evidence
is preserved in work_reasons and has_third_party_watermark, while the primary
work_type total remains 18.

unmatched_rows: 0
ambiguous_rows: 0
semantic_second_run_stable: true
```

## Output paths (external only)

```text
run-1: /var/tmp/karzar-image-source-paths/img02b-01-run1
run-2: /var/tmp/karzar-image-source-paths/img02b-01-run2
final: /home/moahmmad/Projects/Karzar-image-source-paths/IMG-02B-01
accepted Artifact ZIP outer SHA-256:
  fc771c8ee63768ba95bf686b129301f2c729f396d9ae8ba25c24e7cdf90bf28f
```

R2 fail-closed hardening runs (accepted 1204-product semantics unchanged):

```text
r2-run1: /var/tmp/karzar-image-source-paths/img02b-01-r2-run1
r2-run2: /var/tmp/karzar-image-source-paths/img02b-01-r2-run2
r2-final: /home/moahmmad/Projects/Karzar-image-source-paths/IMG-02B-01-R2
```

R2 hardening recorded:

- inventory contradictions rejected
- arbitrary non-empty output reuse removed
- copy-final recursive deletion removed
- ZIP basename collisions rejected

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

## Parallel live discovery (IMG-02B-02..04) — external only

Branch: `feat/img02b-parallel-source-discovery` (Draft PR #211; not merged).
Status correction (R1): live results do **not** constitute three completed lanes.

```text
IMG-02B-02 Dasqua:
  status = calibration_failed
  eligible total = 687
  R1 bounded calibration = 25
  discovered = 0 (post-R1 calib; prior pre-R1 candidates = 2, not validated)
  validated/materialized rows = 0
  manual = 1; rejected = 24 (R1 calib)
  complete = false

IMG-02B-03 INSIZE:
  status = partial
  first candidate run = 49
  second candidate run = 48
  stable intersection = 42; source drift = 7
  validated/materialized rows = 30
  unique assets = 18
  complete = false

IMG-02B-04 SAN OU:
  status = calibration_failed
  total = 253; model-bearing = 215; tokenless manual = 38
  discovered candidates = 0
  site-shape = parser_drift; lane source_unavailable = 215
  complete = false

IMG-02B status = in_progress
IMG-02B progress = 40
IMG-02B-05 = not started
```

```text
Lane outputs:
  /var/tmp/karzar-image-discovery/img02b-dasqua
  /var/tmp/karzar-image-discovery/img02b-insize
  /var/tmp/karzar-image-discovery/img02b-sanou

Downloads (partial):
  /var/tmp/karzar-image-discovery/img02b-insize-dl  (18 unique assets, 30 materialized rows)
  /var/tmp/karzar-image-discovery/img02b-dasqua-dl  (0 materialized — family_page_ambiguous)

Consolidated:
  /var/tmp/karzar-image-discovery/img02b-consolidated
  checksums digest: dbdebc40a71eb4adcfbbc129908e2600e020ef3ede2f4f9d30c97b9ab32f9153

Final review root:
  /home/moahmmad/Projects/Karzar-image-discovery/IMG-02B
```

### Lane counts (candidate stage — pre-R1 evidence)

| Lane | Requested | Discovered candidates | Rejected | Manual | Notes |
|---|---:|---:|---:|---:|---|
| IMG-02B-02 Dasqua | 687 | 2 | 685 | 0 | calibration_failed; 0 materialized (family_page_ambiguous); majority-vote/family collapse under R1 fix |
| IMG-02B-03 INSIZE | 263 | 49 (1st) / 48 (2nd) | 214 | 0 | partial; source drift; 30 materialized / 18 unique assets |
| IMG-02B-04 SAN OU | 253 | 0 | 215 (pre-R1) + 38 misclassified | 0 (pre-R1) | calibration_failed; R1: 38 tokenless → manual_review |

Cross-brand duplicate assets: 0.

### R1 recalibration evidence (2026-08-05)

```text
Dasqua bounded calib (25 products, --limit):
  discovered_candidates = 0
  validated_candidate_rows = 0
  manual_review = 1 (ambiguous_official_product)
  rejected = 24
  prior candidate↔adapter mismatches = 2 (family_page_ambiguous)
  majority vote removed; exact SKU identity; observed CDN hosts only

INSIZE reconcile:
  first_run = 49; second_run = 48; stable_intersection = 42
  source_drift_count = 7
  materialized_rows = 30; unique_assets = 18
  candidate_discovery_coverage = 15.97% (42/263)
  validated_materialization_coverage = 11.41% (30/263)

SAN OU classification (do not conflate levels):
  site-shape calibration outcome = parser_drift
    (productshow.aspx shape exists; sample models not evidenced on detail pages)
  product-lane classification:
    model_token_not_found = 38 manual-review rows
    source_unavailable = 215 model-bearing rows
  The 215 rows are source_unavailable because no governed model-to-detail-page
  mapping was proven — not confirmed product_not_published.
  discovered_candidates = 0; no full 215 re-crawl after parser_drift

IMG-02B-05 = not started
Artifact: /home/moahmmad/Projects/Karzar-image-discovery/IMG-02B.zip
  SHA-256: d922ebf4dc22db393c60f2657cc7370d2fa4c678ce340d3f3479fce1f0c6a201
```

### Resume / drift

- INSIZE **materialization** resume on `img02b-insize-dl`: semantic_manifest_stable=true, asset_set_stable=true, unchanged_rows=30, reused_existing_assets=18.
- INSIZE **candidate** re-discovery: source drift (49→48; e.g. SKU 1120-500 remapped) — R1 reconciles both runs; do not silently prefer first run.
- SAN OU pre-R1 `model_token_not_found` (38) was wrongly rejected; R1 reclassifies as manual_review with `eligible_for_automatic_discovery=false`.

### Safety (discovery phase)

```text
database_accessed = false
ProductImage_modified = false
application_storage_mutations = 0
replacement_execution = false
rights_cleared = 0
rights_status = review_required
apply_status = not_started
```

## Planned later nodes (not started)

```text
IMG-02B-05 — Consolidated Candidate Human Review
```

## Non-goals honored (cumulative)

No DB/ProductImage/storage mutation, replacement execution, manual-review resolution,
rights clearance, deploy, or legacy importer execution. Raw discovery artifacts remain
outside Git.

## R2 / R1 status

```text
R2 fail-closed output and extraction hardening complete (IMG-02B-01)
Parallel discovery code on feat/img02b-parallel-source-discovery (Draft #211)
R1 source-gap recalibration complete — overall live discovery still incomplete
IMG-02B = in_progress / 40
images downloaded = 18 unique external assets (INSIZE only)
Dasqua unique assets = 0; SAN OU unique assets = 0
replacements applied = 0
IMG-02B-05 = not started
```
