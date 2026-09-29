# Hesabfa identity ambiguity resolution — 2026-09-29

Read-only forensic evidence for three catalog identity cases left ambiguous by
[the activation reconciliation](../hesabfa-activation-reconcile-2026-09-29/README.md).
Class `EVIDENCE`. This file is not Canon. Lifecycle policy stays in
[`docs/HESABFA.md`](../../docs/HESABFA.md). Recommendations here do not
authorize a mapping update, an item save, or a remote duplicate cleanup.

## Scope

| Site product | SKU | Prior reason |
|-------------:|-----|--------------|
| 1627 | `6112-1287` | `duplicate_remote_product_code` |
| 2297 | `103-143` | `duplicate_remote_product_code` |
| 3685 | `4824-16` | `mapping_code_mismatch` (local code `000893`) |

The three rows match `ambiguous.csv` from the activation reconciliation.
No other ambiguity class was scanned, except ownership of the candidate codes
above.

## Live identity

| Item | Value |
|------|-------|
| Workflow run | `36573378913` |
| Audit HEAD | `85f3184fb6f3cc2adbd88d7a630351e126bc64b6` |
| Host | `srv5944957438` |
| API container | `lathe_api` |
| DB container | `lathe_postgres` |
| Database | `karzar_staging` |
| Volume | `karzar_postgres_data` |
| `APP_ENV` | `staging` (CR-011 label) |
| `KARZAR_DATA_PLANE` | unset, inferred live |
| Alembic | `t3u4v5w6x7y8` |
| `transaction_read_only` | `on` |
| Database writes | `0` |
| Remote writes | `0` |
| `item/save` calls | `0` |
| Mapping writes | `0` |
| `REMOTE_WRITE_METHODS_REACHABLE` | `0` |

Source was fetched into `/tmp/karzar-hesabfa-ambiguity/85f3184fb6f3cc2adbd88d7a630351e126bc64b6`
and executed with `PYTHONPATH` inside `lathe_api`. The live tree under
`/opt/karzar/Karzar` was left unchanged. Hesabfa credentials were present and
were not recorded.

Hesabfa read was `item/getItems` only. Pagination fetched 3775 of 3775 reported
items across 38 pages. Unique remote `Code` count equals the fetch. The earlier
activation scan reported 3774 items. This resolution uses the 3775-item fetch.

## Decisions

| SKU | Resolution | Detail |
|-----|------------|--------|
| `6112-1287` | `UNRESOLVED` | Two remote ProductCode matches. See `resolution.md`. |
| `103-143` | `UNRESOLVED` | Two remote ProductCode matches with the same normalized name. |
| `4824-16` | `RESOLVED` | Mapped code `000893` is absent. Unique ProductCode match is code `001287`. Mapping class `STALE_CODE`. |

No row was updated. The proposed mapping statement in `resolution.md` was not
executed.

## Files

| File | Role |
|------|------|
| `IDENTITY_PROBE.json` | Host, database, pagination, and write counters |
| `cases.json` | One decision object per case |
| `remote_candidates.csv` | Sanitized remote identity rows for these cases |
| `local_ownership.csv` | Local mapping and SKU ownership of each candidate code |
| `resolution.md` | Decision table and required extra evidence |
| `raw-sanitized.json` | Filtered read-only facts for these cases only |
| `sha256sums.txt` | Digests of the files above and this README |

Catalog identifiers, Hesabfa codes, and product names are included. Price
amounts, secrets, and customer fields are omitted. Price state is boolean only.
`SECRETS_FOUND=0`. `CUSTOMER_PII_FOUND=0`.
