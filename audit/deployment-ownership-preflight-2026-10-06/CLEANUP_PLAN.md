# FINAL CLEANUP PLAN — Phase C0 Freeze

```text
STATUS = READY_FOR_OWNER_CLEANUP
CLEANUP_ALLOWLIST_FROZEN = YES
OWNERSHIP_ALLOWLIST_FROZEN = YES
OWNER_MUTATION_AUTHORIZATION = NO
```

## Sync

| Item | Value |
|------|--------|
| latest main | `c73899eff625cb171a2754a856467ebc3a81b57a` |
| old #443 head | `d162a685af8bab1ef96fe57d00dac5c3cad11be9` |
| merge-base | `c73899eff625cb171a2754a856467ebc3a81b57a` |
| behind | 0 |
| conflicts | 0 |

## Related PRs

| PR | State | Merged | Role |
|----|-------|--------|------|
| #442 | OPEN | NO | N4120 / alias / scripts content (not on main) |
| #444 | OPEN | NO | remaining-19 / scripts / alias content (not on main) |

Open PR presence does **not** protect live VPS objects from `rsync --delete`.

## Finding universe

```text
total = 30
LIVE_FINDINGS_30_PATHSET_SHA256 = ac89a419a56b40faa241f3a435cbf4dd54d46e6d64555d4d8f3490a7e3a18aa5
```

## Next rsync (origin/main → live, dry-run)

```text
RSYNC_DELETE = 30
RSYNC_KEEP = 0
RSYNC_REPLACE = 0
RSYNC_EXCLUDED = 0
RSYNC_UNKNOWN = 0
```

## Disposition reconcile

| Class | Count |
|-------|------:|
| DELETE_PRESERVED_UNTRACKED | 8 |
| NO_ACTION_CHILD_OF_DELETE_ROOT | 22 |
| KEEP_TRACKED_AND_FIX_OWNERSHIP | 0 |
| KEEP_EXCLUDED | 0 |
| BLOCKED_UNPRESERVED | 0 |
| BLOCKED_UNKNOWN | 0 |
| **Total** | **30** |

## PHASE_C_DELETE_ROOTS (exact; no wildcards)

```text
/opt/karzar/Karzar/audit/insize-price-20-n4120
/opt/karzar/Karzar/audit/insize-price-20-remaining-19
/opt/karzar/Karzar/_ops
/opt/karzar/Karzar/scripts/ops/insize_n4120_identity_alias_apply.py
/opt/karzar/Karzar/scripts/ops/run_insize_n4120_identity_alias_apply.sh
/opt/karzar/Karzar/scripts/ops/insize_remaining19_identity_alias_apply.py
/opt/karzar/Karzar/scripts/ops/run_insize_remaining19_identity_alias_apply.sh
/opt/karzar/Karzar/docs/architecture/specs/product-naming-v1/INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv
```

count = 8

## PHASE_D_CHOWN_PATHS

```text
(empty)
```

count = 0

## Tree proofs

| Tree | TREE_PRESERVATION_COMPLETE | safe cleanup root |
|------|----------------------------|-------------------|
| audit/insize-price-20-n4120 | YES (10/10 files) | YES |
| audit/insize-price-20-remaining-19 | YES (10/10 files) | YES |
| _ops | YES (workbook only; 0 extras) | YES |

## Alias CSV

```text
current-main status = NOT_TRACKED_CURRENT_MAIN
open PR content = both (#442 and #444)
final disposition = DELETE_PRESERVED_UNTRACKED
preserved SHA = 0449ba50a46233e462b230478c8ca18d2cd4c86e21e521e7137e34afee81f696
```

## Scripts

| Script | main | disposition |
|--------|------|-------------|
| insize_n4120_identity_alias_apply.py | absent | DELETE_PRESERVED_UNTRACKED |
| run_insize_n4120_identity_alias_apply.sh | absent | DELETE_PRESERVED_UNTRACKED |
| insize_remaining19_identity_alias_apply.py | absent | DELETE_PRESERVED_UNTRACKED |
| run_insize_remaining19_identity_alias_apply.sh | absent | DELETE_PRESERVED_UNTRACKED |

## Safety (this phase)

```text
VPS mutation = NO
delete = NO
chown = NO
deploy = NO
merge #443 = NO
```

## Next

Owner-authorize one Phase C/D execution using **only** these exact-path allowlists.
After cleanup, re-run ownership preflight and require `unexpected_ownership=0` before merging #443.

## Naming note

AODS reserved-token `final` forbids `FINAL_*` filenames. Artifacts are frozen as `CLEANUP_*` / `PHASE_C_*` / `PHASE_D_*` / `C0_SYNC_STATE.json` (same content/intent as the Phase C0 mission filenames).
