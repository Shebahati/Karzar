# VPS read-only ShopMill preflight bundle

**Purpose:** Resolve live uploads volume + verify all **410** affected serving paths.  
**Mutations:** none (no apply, backup, chmod, restore, deploy, DB writes).

## Contents

```text
manifests/target-serving-paths.csv     # 410 paths + expected/repaired hashes
manifests/unique-assets.csv            # 163 unique expected_source_sha256
manifests/remediation-manifest.csv     # full remediation rows (optional input)
scripts/production_preflight.py       # copy of read-only checker (prefer repo)
scripts/shopmill_production_preflight.py
```

Prefer running from the git checkout on the VPS (`/opt/karzar/Karzar`) after this branch’s files are present:

* `scripts/shopmill_production_preflight.py`
* `scripts/shopmill_watermark/production_preflight.py`
* `aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/remediation-manifest.durable-paths.csv`

## Safety controls

* Rejects absolute / `..` / escaping paths
* Refuses `--report-dir` under `PRODUCTS_STORAGE_ROOT`
* Uses `lstat` + regular-file check; rejects symlinks
* SHA-256 read only
* Never writes under uploads

## Hash rule

`SOURCE_CHANGED` = production bytes ≠ `expected_source_sha256` used to build the staged repair.  
**Do not apply** that staged repair; a later phase must regenerate Method C from exact production bytes.

## Expected counts

```text
TARGET_PATHS_EXPECTED=410
UNIQUE_ASSETS_EXPECTED=163
```

## After this preflight

Only if results are coherent, a **later authorized** phase may:

1. targeted backup of the exact serving paths to modify  
2. apply / regenerate  

This bundle does **not** perform those steps.
