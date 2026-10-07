# FINAL REPORT — Phase A+B Preservation

```text
STATUS = PRESERVED_VERIFIED
PHASE_A_PRESERVATION = VERIFIED
PHASE_B_SHA_VERIFY = PASS
LIVE_CLEANUP_AUTHORIZED = NO
OWNERSHIP_REMEDIATION_AUTHORIZED = NO
```

## Entry

| Item | Value |
|------|--------|
| host | srv5944957438 |
| UTC | 2026-10-07T07:11:29Z |
| user | root uid=0 |
| origin/main | d74f8365c164087686ddd88a4796c8e97eb986f3 |
| PR #443 head (start) | ad29c7acf7b4b759529c7248e2d5d6a0b1aaee60 |
| plan drift | NO |

## Destinations

| Path | Ownership | Modes |
|------|-----------|-------|
| `/opt/karzar/preserve/insize-n4120-20261006/` | root:root | dirs 755 / files 600 |
| `/opt/karzar/preserve/insize-workbook-20261006/` | root:root | dirs 755 / files 600 |

Convention matched existing `/opt/karzar/preserve` siblings (root:root, files 600).

## Critical hashes

| Gate | Expected | PASS |
|------|----------|------|
| recovery | `0048f19c9ea5da3319acf54bf7f77cb9dae4afa900f8994492f7aa161f4b07a9` | YES |
| rollback | `be8b4c55de397bed57904aa27e48b714417f58b5bd63c39d2c7df28dfef375c9` | YES |
| workbook | `65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a` | YES |
| alias CSV | `0449ba50a46233e462b230478c8ca18d2cd4c86e21e521e7137e34afee81f696` | YES |

Laptop workbook recheck: **PASS** (same SHA).

## Copy verification

| Metric | Value |
|--------|------:|
| files copied | 14 |
| SHA matches | 14 |
| size matches | 14 |
| mismatches | 0 |
| total source bytes | 2643574 |

## Manifest

```text
/opt/karzar/preserve/insize-n4120-20261006/PRESERVATION_MANIFEST.csv
rows = 14
SHA256 = b599f88b32467dc6f21e67375ca5c85a937dcd6af6a75431abf0d77ee95247c0
safe_to_remove_source = ALL NO
```

## Source postcheck

Original 17 findings: exist=YES, ownership/mode/SHA unchanged=YES.

## Preflight after preserve

```text
status = FAIL
unexpected_ownership = 30
expected failure because live sources remain = YES
```

Note: scan also reports additional root-owned `insize-price-20-remaining-19/**` and remaining19 scripts (outside this Phase A set). Not remediated.

## Next

Separate Owner authorization for Phase C/D (remove/relocate live artifacts; ownership). Do not merge #443 yet.
