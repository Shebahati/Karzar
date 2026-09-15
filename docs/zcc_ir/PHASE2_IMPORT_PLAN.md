# zcc.ir Phase 2 — import plan (read-only)

Phase 2 produces a deterministic import **plan** and manifest. It does not create, update, or delete catalog rows.

## Prerequisites

- Phase 1 artifacts under `data/zcc_ir/` (from `scripts/zcc_ir_catalog_discover.py`)
- Full Karzar catalog CSV (`catalog_target.snapshot` format) or local non-production `--read-db`

## Generate plan

```bash
python3 scripts/zcc_ir_import_plan.py plan \
  --phase1-dir data/zcc_ir \
  --output-dir data/zcc_ir_phase2 \
  --karzar-snapshot /path/to/full_current_catalog.csv
```

## Validate manifest

```bash
python3 scripts/zcc_ir_import_plan.py validate \
  --manifest data/zcc_ir_phase2/import_manifest.json
```

Allowed manifest operations: `NOOP`, `CREATE_PLAN`, `UPDATE_CONTENT_PLAN`, `HOLD` only.

`PRODUCTION_DB_MUTATION = ZERO` · `CATALOG_APPLY = NO`
