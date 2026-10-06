# FINAL REPORT — Deployment ownership preflight

```text
STATUS = REMEDIATION_REQUIRED
DEPLOY = NO
AUTO_CHOWN = NO
VPS_MUTATION = NO
```

## Entry

| Check | Result |
|-------|--------|
| PR #440 merged | YES (`d74f836`) |
| Branch | `fix/deploy-ownership-preflight` from `origin/main` |
| Implementation | Complete |
| Current VPS canary | **FAIL** (drift remains) |

## Implementation

| Item | Value |
|------|--------|
| Script | `deploy/staging/scripts/deploy_ownership_preflight.py` |
| Workflow | `.github/workflows/deploy-staging.yml` |
| Execution point | After incoming verify; before Sync backend rsync |
| Auto-chown | NO |

## Contract

```text
runner = github-runner
managed = /opt/karzar/{incoming,Karzar,frontend} + managed descendants
expected ownership = github-runner:github-runner for deploy-managed content
root-only exclusions = .env, .deploy-secrets, backups/, uploads/, logs/, …
```

## Current VPS read-only canary (2026-10-06)

From `CURRENT_VPS_PREFLIGHT.json`:

```text
runner=github-runner uid=1000 gid=1000
managed_paths=3
objects_checked=1789
unexpected_ownership=17
undeletable=0
unreplaceable=0
status=FAIL
```

Offending classes (metadata only):

- `scripts/ops/insize_n4120_*` (root)
- `docs/architecture/specs/product-naming-v1/INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv` (root)
- `audit/insize-price-20-n4120/**` (root) — destination-only orphan class
- `/opt/karzar/Karzar/_ops/**` (root) — ad-hoc root workspace inside live checkout

Secrets remain host-controlled and excluded from ownership requirement:

```text
/opt/karzar/Karzar/.env → root:github-runner 640
/opt/karzar/.deploy-secrets → root:github-runner 640
```

## Owner remediation (not executed)

Exact paths only (from canary findings). Enumerate; no wildcards; no
`chown -R /opt/karzar`:

```bash
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/scripts/ops/run_insize_n4120_identity_alias_apply.sh
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/scripts/ops/insize_n4120_identity_alias_apply.py
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/docs/architecture/specs/product-naming-v1/INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/FREEZE.json
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/N4120_PROOF_MATRIX.csv
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/APPLY_REPORT.json
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/RECOVERY_N4120_20261006T141319Z.json
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/SYNC_REPORT.json
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/N4120_ROLLBACK.csv
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/N4120_WORKBOOK_FAMILY.csv
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/N4120_BASELINE.csv
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/N4120_PRICE_DRY_RUN.csv
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/audit/insize-price-20-n4120/LOCKED_TRAILING_A_SKUS.txt
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/_ops
sudo chown github-runner:github-runner -- /opt/karzar/Karzar/_ops/input
sudo chown github-runner:github-runner -- '/opt/karzar/Karzar/_ops/input/موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx'
```

Prefer moving `_ops` out of the live checkout entirely after ownership repair.

## Merge readiness

```text
IMPLEMENTATION = READY
TESTS = READY
WORKFLOW_ORDER = READY
FREEZE_SAFETY = READY
VPS_CANARY = FAIL → REMEDIATION_REQUIRED
DEPLOY_OWNERSHIP_PREFLIGHT = NOT_READY for production deploy until Owner remediates
```

Merge of the guard is still useful: after merge + Owner chown, the next Deploy
Staging will enforce the gate. Do not deploy until canary would PASS.
