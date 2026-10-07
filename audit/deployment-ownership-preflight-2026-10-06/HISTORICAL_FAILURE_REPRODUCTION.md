# Historical failure reproduction

## Production incident (authority)

| Field | Value |
|-------|--------|
| Run | GitHub Actions `37468470923` |
| Failure | `rsync` exit 23 — Permission denied unlink/mkstemp; `chgrp` not permitted |
| Tree | `/opt/karzar/Karzar` |
| Runner | `github-runner` |
| Evidence pack | `audit/deployment-ownership-audit-2026-10-06/` (PR #440) |

Contributing objects included root-owned content under `deploy/`, `services/`, and
destination-only orphan dirs under `audit/` that `rsync --delete` could not remove.

## Local model (this PR)

CI cannot safely create `uid=0` objects. Tests inject `stat_fn` / `access_fn` /
`dry_run_fn` seams:

1. **Old behavior modelled:** destination-only undeletable + unreplaceable transfer
   targets produce the same hazard class as run `37468470923`.
2. **New behavior proven:** `run_preflight` returns `FAIL` with
   `unexpected_ownership` / `undeletable` / `unreplaceable` counts; only the
   dry-run plan callback runs — no mutating rsync.

Primary test: `test_historical_failure_model_preflight_before_rsync`.

## Workflow prevention

`.github/workflows/deploy-staging.yml` places
`Ownership preflight (fail-closed before rsync)` immediately before
`Sync backend → /opt/karzar/Karzar`. A nonzero preflight exit aborts the job;
the Sync step does not run.

## Live canary cross-check

`CURRENT_VPS_PREFLIGHT.json` on 2026-10-06 reported `status=FAIL` with 15
unexpected root-owned managed paths (including `audit/insize-price-20-n4120` and
`_ops`). That is the same failure class the gate is designed to stop before rsync.
No ownership mutation was performed during the canary.
