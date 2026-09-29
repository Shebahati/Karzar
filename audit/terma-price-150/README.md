# TERMA +50% Price Update — 2026-09-26

## Authorization

Owner-authorized increase of current TERMA `base_price` by exactly **50%**.

This was a Category B catalog mutation scoped to one brand and one mutable
field. It is **complete**. Do not rerun any historical APPLY for this event.

## Scope

| Item | Value |
|------|-------|
| Brand | `TERMA \| ترما` |
| `brand_id` | `5` |
| Affected live products | `312` |
| Mutable field | `base_price` **only** |

Not in scope: `original_price`, availability, active flags, stock, SKU/slug/name,
images, Hesabfa, Postex, deploy, or any other brand.

## Execution result

**STATUS:** `APPLIED`

Formula:

```text
new_base_price = quantize(old_base_price × 1.50, 0.01)
```

Results (authoritative read-only verification):

| Check | Result |
|-------|--------|
| `product_change_logs` rows (`field_name=base_price`, reason below) | **312** |
| Distinct product IDs | **312** |
| Formula matches (`new = round(old×1.50, 2)`) | **312 / 312** |
| Current DB `base_price` = logged `new_value` | **312 / 312** |
| Duplicate product mutations | **0** |
| Live TERMA products | **312** |
| Priced TERMA products | **312** |

Change-log reason string (exact):

```text
TERMA +50% owner-authorized price update 2026-09-26
```

Post-apply cohort aggregates:

| Metric | Value |
|--------|-------|
| minimum `base_price` | `929250.00` |
| maximum `base_price` | `441000000.00` |
| sum `base_price` | `13537661250.00` |

## Verification

Production identity (CR-011 live; historic names):

| Probe | Value |
|-------|-------|
| Host | `srv5944957438` |
| DB container | `lathe_postgres` |
| Database | `karzar_staging` |
| Volume | `karzar_postgres_data` |
| Transaction mode | `BEGIN READ ONLY` / `transaction_read_only=on` |

Evidence file: [`VERIFY_REPORT.json`](./VERIFY_REPORT.json)  
Identity probe: [`VERIFY_IDENTITY_PROBE.json`](./VERIFY_IDENTITY_PROBE.json)

Additional checks:

- External API (`https://api.karzartools.com`) returned the new prices for sampled TERMA SKUs (including change-log IDs).
- Storefront PDPs (`https://karzartools.com/product/<slug>`) returned HTTP 200 with matching SKU and price digits for sampled visible products.
- VPS loopback API verification in the temporary read-only workflow failed in a **non-mutating** way; external API verification was used successfully instead.

Interpretation recorded in the verify report: `DB_APPLY_CONFIRMED`.

## Incident note

GitHub Actions workflow run **`36244999947`** (`TERMA Price +50% APPLY`) showed
**FAILURE** even though the database transaction had already **COMMITTED**.

What that means operationally:

1. Actions job status alone was **not** sufficient to determine catalog state.
2. A later **READ-ONLY** verification (same production identity, `BEGIN READ ONLY`)
   confirmed 312/312 change logs and 312/312 live price matches.
3. From repository evidence: the container-side mutate path completed inside
   `lathe_api`, while host-side post-processing for the Actions step appears to
   have failed afterward (annotations included host `python3` missing → exit
   **127** during report pretty-print / artifact handling). That host failure
   does **not** roll back a committed Postgres transaction.

Follow-up (do **not** address in this audit PR): catalog APPLY runners should
treat “mutation COMMIT before workflow-critical host post-verification” as a
generic hazard — prefer fail-closed reporting that cannot mask a committed
write, without re-executing mutations.

## Final status

```text
TERMA_PRICE_150_APPLY_OK
```

## Safety

- Do **not** rerun the historical TERMA +50% APPLY.
- Do **not** reintroduce a push-triggered one-shot production APPLY workflow for this event.
- The update is already complete; this directory is audit preservation only.
