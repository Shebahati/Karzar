# FINAL REPORT — Phase A2+B2 Remaining-19 Preservation

```text
STATUS = PRESERVED_VERIFIED
PHASE_A2_PRESERVATION = VERIFIED
PHASE_B2_SHA_VERIFY = PASS
LIVE_CLEANUP_AUTHORIZED = NO
OWNERSHIP_REMEDIATION_AUTHORIZED = NO
PR443_SYNC_REQUIRED_BEFORE_CLEANUP_FINAL_GATE = YES
```

## Entry

| Item | Value |
|------|--------|
| host | srv5944957438 |
| UTC | 2026-10-07T07:35:06Z |
| origin/main | `c73899eff625cb171a2754a856467ebc3a81b57a` |
| PR #443 head | `0b54599c89ddc4c198ffe39e52f7b98b59183859` |
| behind main | 5 |
| ahead | 4 |

## Destination

`/opt/karzar/preserve/insize-remaining19-20261006/` — root:root, dirs 0755, files 0600

## Critical

| Gate | Destination SHA PASS |
|------|----------------------|
| recovery | YES (`e14533ccd01a40f88cd6fc906d7fd7289a938e5ecaf1dd181318f76c7fe397f9`) |
| rollback | YES (`53143b29176d2c056d789e75985cb783266502facf674dbce28774f66d4d1a61`) |
| apply report | YES |
| identity matrix | YES |

## Copy

| Metric | Value |
|--------|------:|
| regular files | 12 |
| SHA/size matches | 12 |
| mismatches | 0 |
| additional audit-tree files | 0 |
| total bytes | 61926 |

## Manifest

```text
/opt/karzar/preserve/insize-remaining19-20261006/PRESERVATION_MANIFEST.csv
SHA256 = a9a97301bf84518841c709c3585f3b6179c02fd42600c415e27638ad4de07bb4
rows = 12
safe_to_remove_source = ALL NO
```

## Previous N4120 preservation

manifest intact = YES (`b599f88b…`)

## Source postcheck

All 13 remaining-19 live objects present; SHA/owner/mode unchanged.

## Preflight after preserve

```text
status = FAIL
unexpected_ownership = 30
new beyond known 30 = 0
```

## Next

1. Sync #443 onto latest main (separate task)
2. Re-evaluate delete set vs latest main
3. Owner-authorize Phase C/D cleanup for preserved untracked live artifacts only
4. Preflight must reach unexpected_ownership=0 before merge
