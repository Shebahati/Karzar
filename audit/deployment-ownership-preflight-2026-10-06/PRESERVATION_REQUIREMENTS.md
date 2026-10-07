# Preservation requirements (read-only gate)

```text
VPS_MUTATION = NO
OWNERSHIP_MUTATION = NO
FILE_RELOCATION = NO
```

## Invariant

If `disposition = PRESERVE_REQUIRED` and next deploy `WOULD_DELETE`, then:

```text
ownership remediation (chown) is FORBIDDEN
until a durable copy exists outside rsync --delete scope
```

All 17 findings are absent from `origin/main` and are **not** rsync-excluded → next Deploy Staging from main models **WOULD_DELETE** for every object.

## Recovery / rollback special rule

For:

- `RECOVERY_N4120_20261006T141319Z.json`
- `N4120_ROLLBACK.csv`

Future deletion requires **all** of:

1. byte-identical preserved copy  
2. SHA256 recorded  
3. destination outside rsync-managed `/opt/karzar/Karzar`  
4. understood retention  

Byte-identical blobs exist on unmerged `origin/chore/insize-n4120-identity-alias` (PR #442). That is **not** accepted alone as durable retention.

## Existing non-live ops storage (discovered)

| Path | Owner | Outside live rsync? | Suitability |
|------|-------|---------------------|-------------|
| `/opt/karzar/preserve` | root | YES | **Best existing** host preserve area (already used for SEP/checkout preserve artifacts) |
| `/opt/karzar/catalog-apply-backups` | root | YES | Suitable for apply/rollback style packs (has prior INSIZE/price backups + SHA files) |
| `/opt/karzar/rollout-backups` | root | YES | Price-rollout history; acceptable alternate |
| `/opt/karzar/tmp` | root 700 | YES | Ephemeral; **not** for recovery retention |
| `/opt/karzar/logs` | github-runner | YES | Deploy logs only; **not** for recovery packs |
| `/opt/karzar/_held_out` | root | YES | Unrelated held-out frontend bits; do not overload |

```text
CANONICAL_EXTERNAL_OPS_LOCATION = /opt/karzar/preserve
(with catalog-apply-backups as apply-backup alternate)
NEW subdirectory approval: Owner should authorize
  /opt/karzar/preserve/insize-n4120-20261006/
  /opt/karzar/preserve/insize-workbook-20261006/
before writes.
```

No new top-level hierarchy invented; reuse `/opt/karzar/preserve`.

## Proposed preservation manifest schema (future mutation)

```text
source_path
source_SHA256
source_size
source_owner
destination_path
destination_expected_owner
destination_SHA256
reason
retention_class
safe_to_remove_source
```

## Related open PRs (do not merge here)

| PR | Branch | Relevance |
|----|--------|-----------|
| #442 | `chore/insize-n4120-identity-alias` | Byte-identical N4120 audit + apply scripts |
| #444 | `chore/insize-remaining-19-final` | Live alias CSV + LOCKED_TRAILING_A_SKUS SHA |

## Workbook SHA

```text
65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a
```

Pinned in apply wrapper + FREEZE/APPLY reports. Byte-identical Owner laptop copy proven; VPS live copy still must leave the checkout.
