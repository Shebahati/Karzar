# Deployment ownership preflight — 2026-10-06

Implements the durable fail-closed ownership preflight designed in
`audit/deployment-ownership-audit-2026-10-06/PREFLIGHT_DESIGN.md` (PR #440).

## Safety

```text
VPS_FILE_MUTATION = NO
CHOWN / CHMOD / DELETE / DEPLOY = NO
AUTO_CHOWN = NO
```

## Deliverable

- Script: `deploy/staging/scripts/deploy_ownership_preflight.py`
- Workflow gate: `.github/workflows/deploy-staging.yml` step
  `Ownership preflight (fail-closed before rsync)` immediately before
  `Sync backend → /opt/karzar/Karzar`
- Tests: `tests/test_deploy_ownership_preflight.py`

## Current VPS canary

See `CURRENT_VPS_PREFLIGHT.json` and `FINAL_REPORT.md`.

```text
STATUS = REMEDIATION_REQUIRED
```

Unexpected root-owned paths remain under the live checkout after prior root ops.
Owner must remediate with exact-path `chown` before the next Deploy Staging.
This pack does not perform that remediation.
