# ZCC.ir Phase 2.1 — approval manifest hardening

Read-only operator tooling. No catalog apply.

## Canonical approval identity

- `CANONICAL_IMPORT_PLAN_SHA256` — owner approval hash (excludes volatile metadata only).
- `RAW_MANIFEST_FILE_SHA256` — full JSON file bytes (optional, informational).
- Legacy `IMPORT_MANIFEST_SHA256` equals canonical on newly generated manifests.

Volatile exclusions: `git_sha`, `karzar_snapshot_timestamp`, `generated_at`, hash fields, per-entry `source_timestamp`.

## Validation layers

```bash
python3 scripts/zcc_ir_import_plan.py validate --manifest data/zcc_ir_phase2/import_manifest.json
```

Reports:

- `CONTENT_PLAN_VALID` / `COMMERCE_PLAN_VALID`
- `CONTENT_BLOCKING_ERROR_COUNT` — diagnostic messages (may exceed row count)
- `CONTENT_BLOCKING_ROW_COUNT` — unique `source_url` with content findings
- `CONTENT_COLLISION_GROUP_COUNT` — duplicate identity/SKU clusters

Zero source price → `COMMERCE_INVALID` only (no sellable price). Content planning may still be valid.

## Phase 2.1 analysis (gitignored outputs)

```bash
python3 scripts/zcc_ir_phase21_analyze.py \
  --phase1-dir data/zcc_ir \
  --phase2-dir data/zcc_ir_phase2 \
  --manifest data/zcc_ir_phase2/import_manifest.json
```

Writes under `data/zcc_ir_phase2/` (gitignored): duplicate CSV, owner packets, `duplicate_validation_summary.json`.
