# UPDATED FINAL REPORT — Preservation gate before ownership remediation

```text
STATUS = MORE_EVIDENCE_REQUIRED → READY_FOR_OWNER_REMEDIATION (plan only)
CHOWN of current 17-command proposal = NO
DEPLOY = NO
MERGE #443 now = NO
```

## Entry (re-fetched)

| Item | Value |
|------|--------|
| origin/main | `d74f8365c164087686ddd88a4796c8e97eb986f3` |
| PR #443 head | `83169c53a705bb1a969a7aeb7cd5bcfeac16326f` (+ this evidence commit) |
| behind main | 0 |
| mergeable | MERGEABLE / CLEAN (implementation CI) |
| canary | FAIL (17 root-owned) — remediation blocked pending preserve |

## Findings summary

| Metric | Count |
|--------|------:|
| Objects | 17 |
| Tracked on current main | 0 |
| Untracked on main / history-or-never | 17 |
| Git history / open PR | 14 |
| Never tracked (`_ops/**`) | 3 |
| Next deploy WOULD_DELETE | 17 |
| WOULD_KEEP / REPLACE / EXCLUDED | 0 |

## Disposition counts

| Disposition | Count |
|-------------|------:|
| PRESERVE_REQUIRED | 11 |
| PRESERVE_UNTIL_VERIFIED_DUPLICATE | 3 |
| RELOCATE_OUT_OF_LIVE_CHECKOUT | 3 |
| REGENERABLE_EPHEMERAL | 0 |
| SAFE_TO_DELETE_AFTER_EVIDENCE_CAPTURE | 0 |
| UNKNOWN_DO_NOT_TOUCH | 0 |

## Why the original chown list is unsafe

Enabling runner unlink on these paths would allow the next `rsync --delete` from main to destroy:

- N4120 recovery/rollback/apply evidence (operation `APPLIED_VERIFIED`)
- live alias CSV (SHA matches PR #444, not main)
- supplier workbook under `_ops/input` (pinned SHA `65a92337…`)

GitHub open branches hold many byte-identical blobs but are **unmerged** — insufficient alone for recovery/rollback retention.

## Canonical external storage

```text
existing: /opt/karzar/preserve (root) — suitable
alternate: /opt/karzar/catalog-apply-backups
NEW top-level invent: NO
```

## PR #443

| Aspect | Status |
|--------|--------|
| Preflight implementation | READY (CI green) |
| VPS canary | FAIL |
| Safe to merge for deploy | **NO** until Owner preserve → preflight PASS |
| This preservation gate | Evidence-only update |

## Next Owner-authorized mutation (single plan)

See `REMEDIATION_EXECUTION_PLAN.md` Phases A→H. First concrete action: approve/create preserve subdirs under `/opt/karzar/preserve` and copy PRESERVE_REQUIRED set with SHA256 verification — **not** chown.
## Phase C0 — cleanup allowlist freeze

See `FINAL_CLEANUP_PLAN.md`. Status: **READY_FOR_OWNER_CLEANUP**.
`PHASE_C_DELETE_ROOTS` = 8 exact paths; `PHASE_D_CHOWN_PATHS` = 0.
No VPS mutation performed in C0.
