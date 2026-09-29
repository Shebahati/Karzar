# Hesabfa activation reconciliation — 2026-09-29

Read-only evidence for PR #398. This is not Canon and it does not authorize
activation APPLY.

POLICY IMPLEMENTED: Karzar storefront `is_active`, availability, price removal,
and soft delete do not write Hesabfa item `active`.

CURRENT REMOTE STATE RECONCILED: the scan below. Mapped inactive items were
identified and left unchanged.

## Run

| Item | Value |
|------|-------|
| Workflow run | `36554803337` |
| Audit HEAD | `5c3505845386d12c01f2ea6b88377a4b004be59b` |
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
| `--apply` unconfirmed | exit `2` |
| `--apply` with confirm flags | exit `3` `BLOCKED_PENDING_API_CONFIRMATION` |

Source was fetched into `/tmp` and executed with `PYTHONPATH` inside `lathe_api`.
The live application tree was not checked out, rsynced, or restarted.

Hesabfa read was `item/getItems` only. Pagination fetched 3774 of 3774 reported
items across 38 pages. Unique remote `Code` count equals the fetch. No repeated
page and no duplicate remote `Code` were accepted.

## Counts

Population is non-deleted Karzar products (`6536`). `SCANNED` equals that population.

| Classification | Count |
|----------------|------:|
| `MAPPED` (local mapping present) | 3639 |
| `UNMAPPED` | 2887 |
| `LINK_EXISTING` | 10 |
| `MAPPED_ACTIVE` | 1007 |
| `RECONCILIATION_REQUIRED` (`mapped_inactive`) | 2629 |
| `MISSING_REMOTE_ITEM` | 0 |
| `AMBIGUOUS` | 3 |
| `PRICE_RISK` | 0 |
| `WOULD_ACTIVATE` | 0 |

`AMBIGUOUS` is 2 duplicate remote ProductCode groups plus 1 mapping code mismatch.
Those rows were classified and not repaired. They do not change the completed
population count.

`PRICE_RISK` counts fetched items whose `item/getItems` payload exposed a
non-zero buy or sell price. The count is 0. This PR did not save any existing item.

Mapped inactive items are a later, owner-gated correction. This scan did not
activate them.

## Files

| File | Role |
|------|------|
| `summary.json` | Machine-readable counters |
| `reconciliation.csv` | One row per non-deleted product |
| `ambiguous.csv` | Ambiguous identity rows |
| `errors.csv` | Error and missing-remote rows (header only) |
| `IDENTITY_PROBE.json` | Host, database, and read-only proof |
| `sha256sums.txt` | Digests of the files above and this README |

Columns are catalog identity and classification only: product id, SKU, mapping
presence, Hesabfa code, ProductCode, active flag, action, reason, and a
price-risk boolean. No customer fields.
