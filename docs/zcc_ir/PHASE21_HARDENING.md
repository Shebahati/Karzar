# ZCC.ir Phase 2.1 — approval manifest hardening

Read-only operator tooling. No catalog apply.

## Canonical approval identity

- `CANONICAL_IMPORT_PLAN_SHA256` — owner approval hash (semantic plan + `karzar_snapshot_sha256`; excludes volatile metadata only).
- `IMPORT_MANIFEST_SHA256` — **legacy** self-description hash (full JSON object minus only the `IMPORT_MANIFEST_SHA256` field). Validated independently from canonical.
- On-disk file digest — `import_manifest.json.sha256` sidecar (SHA-256 of final JSON bytes). Not embedded inside the JSON.

## Validation layers

```bash
python3 scripts/zcc_ir_import_plan.py validate --manifest data/zcc_ir_phase2/import_manifest.json
```

Reports include:

- `CONTENT_SOURCE_QUALITY_VALID` / `CONTENT_MUTATION_PLAN_VALID`
- `ALL_MANIFEST_LOGICAL_COLLISION_GROUPS` — full forensic graph (includes NOOP/HOLD-only clusters)
- `MUTATION_BLOCKING_COLLISION_GROUPS` — clusters that block CREATE_PLAN / UPDATE_CONTENT_PLAN
- Independent `CANONICAL_HASH_MISMATCH` vs `LEGACY_HASH_MISMATCH` diagnostics

Phase 2 `plan` requires `--karzar-snapshot` (file-backed CSV). `--read-db` is rejected before any DB access.

## Phase 2.1 analysis (gitignored outputs)

```bash
python3 scripts/zcc_ir_phase21_analyze.py \
  --manifest data/zcc_ir_phase2/import_manifest.json \
  --karzar-snapshot /path/to/karzar_catalog_snapshot.csv
```
