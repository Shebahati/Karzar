# Phase 2F provenance correction (additive)

Immutable original evidence is **unchanged**.

## Defect

`REAL_APPLY_MANIFEST.json.latest_main_sha` recorded:

`8a0ab9347968db1b7f4de4b36c0d86ed2cd6c8dc`

That value is the **PHASE2F_APPLY_LOGIC_SHA**, not `origin/main` at branch creation.

## Correct historical facts

| Field | Value |
|-------|-------|
| Actual main at Phase 2F branch base | `9fc607ab90170375069c0d5b11ec33f4f64ae9dd` |
| Historical apply logic SHA | `8a0ab9347968db1b7f4de4b36c0d86ed2cd6c8dc` |
| Historical evidence commit | `80d3b0010ab9b6b8d8f7a40a7333d9b600d81d95` |
| Ancestry | `merge-base(8a0ab934…, 9fc607ab…) = 9fc607ab…` |

## Impact

Metadata labeling only. No impact on DB transaction `txid=29255`, candidate cohort, backup, logs, or post-commit verification.

Machine-readable twin: `PHASE2F_PROVENANCE_CORRECTION.json`.
