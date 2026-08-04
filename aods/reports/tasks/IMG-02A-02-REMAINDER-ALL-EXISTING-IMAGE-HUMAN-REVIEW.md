# TASK-RECORD · IMG-02A-02-REMAINDER-ALL

## Identity

| Field | Value |
|---|---|
| Task ID | IMG-02A-02-REMAINDER-ALL |
| Batch ID | IMG-02A-02-REMAINDER-ALL |
| Parent | IMG-02A-02 |
| Dependency | IMG-02A-02-BATCH-002 |
| Status | in_progress |
| Progress | 70 |
| Human review | pending |
| Decisions applied | none |
| Replacement execution | not started |

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

## Safety boundary proof

```text
network_requests_performed: 0
database_accessed: false
product_images_modified: false
source_storage_mutations: 0
repository_modified_by_batch_run: false
```

Raw outputs (manifests/templates/previews/thumbs/review-state/zip) remain outside Git.
