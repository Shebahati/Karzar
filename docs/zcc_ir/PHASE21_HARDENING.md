# ZCC.ir Phase 2.1 — approval manifest hardening

Read-only operator tooling. No catalog apply.

## Canonical approval identity

- `CANONICAL_IMPORT_PLAN_SHA256` — owner approval hash (semantic plan + `karzar_snapshot_sha256`; excludes volatile metadata only).
- `IMPORT_MANIFEST_SHA256` — **legacy** self-description hash (full JSON object minus only the `IMPORT_MANIFEST_SHA256` field). Not interchangeable with canonical.
- On-disk file digest — `import_manifest.json.sha256` sidecar (SHA-256 of final JSON bytes). Not embedded inside the JSON.

Volatile exclusions for canonical hash: `git_sha`, `karzar_snapshot_timestamp`, `generated_at`, hash fields, per-entry `source_timestamp` (crawl provenance is manifest-level `source_crawl_timestamp`).

## Validation layers

```bash
python3 scripts/zcc_ir_import_plan.py validate --manifest data/zcc_ir_phase2/import_manifest.json
```

Reports:

- `CONTENT_PLAN_VALID` / `COMMERCE_PLAN_VALID`
- `CONTENT_BLOCKING_ERROR_COUNT` — diagnostic messages (may exceed row count)
- `CONTENT_DIAGNOSTIC_ROW_COUNT` — unique `source_url` with content-layer diagnostics
- `LOGICAL_COLLISION_GROUP_COUNT` — logical duplicate clusters (manufacturer identity OR target SKU, union-find)
- `CONTENT_COLLISION_AFFECTED_ROW_COUNT` — all source rows participating in a logical cluster

Zero source price → `COMMERCE_INVALID` only (no sellable price). Content planning may still be valid.

## Phase 2.1 analysis (gitignored outputs)

```bash
python3 scripts/zcc_ir_phase21_analyze.py \
  --phase1-dir data/zcc_ir \
  --phase2-dir data/zcc_ir_phase2 \
  --manifest data/zcc_ir_phase2/import_manifest.json \
  --karzar-snapshot /path/to/karzar_catalog_snapshot.csv
```

Or pass `--snapshot-sha256` when the manifest-bound digest is already known. Analysis fails closed if snapshot binding does not match the manifest.

Writes under `data/zcc_ir_phase2/` (gitignored): duplicate CSV, owner packets, `duplicate_validation_summary.json`.
