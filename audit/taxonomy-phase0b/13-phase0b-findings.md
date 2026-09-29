# Phase 0B Findings (auto)

Snapshot: 2026-09-27T10:06:26Z
transaction_read_only: on
Live products: 6536
Visible: 1368 (API Phase0=1368)
PT coverage live: 8.063% (527/6536)
Knowledge nodes: 0; assignments: 0
Hesabfa codes populated: 0/138

## Missing IDs still referenced (active import/runtime)
- id=33 reachability=ACTIVE_IMPORT files=seed; azarsanat DEPTH2; zcc tests/fixtures
- id=34 reachability=ACTIVE_IMPORT files=seed; azarsanat DEPTH2

## Severity reassessment notes
- Azarsanat 33/34: ACTIVE_IMPORT (manual script). Missing parents are skipped (`missing parent` log) — does not auto-run in production request path. Severity → P1 (blocks correct AST import leaf padding / risks misfile if parents were assumed present), not continuous P0 runtime corruption.
- ZCC 166 SAFE_PATH_RULES / Cat-B pins: ACTIVE_IMPORT — P1 governance risk (numeric PK as semantic id); not a live request-path P0.
- Nav group root_category_ids: ACTIVE_PRODUCTION_RUNTIME data (presentation).
