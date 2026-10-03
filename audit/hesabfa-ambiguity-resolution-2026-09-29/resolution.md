# Resolution — three Hesabfa identity cases

Read on 2026-09-29 from Production PostgreSQL (`transaction_read_only=on`) and a
complete Hesabfa `item/getItems` (3775/3775, 38 pages, duplicate remote `Code`
count 0). `DATABASE_WRITES=0`. `REMOTE_WRITES=0`. No mapping was updated.

| SKU | Local product | Prior issue | Remote candidates | Resolution | Correct Code | Future action |
|-----|---------------|-------------|-------------------|------------|--------------|---------------|
| `6112-1287` | 1627, جعبه راپورتر (گیج بلوک) — 0-1287mm, Dasqua | `duplicate_remote_product_code` | `000619`, `003620` | `UNRESOLVED` | — | `REMOTE_DUPLICATE_REVIEW` |
| `103-143` | 2297, میکرومتر ساده میتوتویو 175-150 میلی‌متر مدل 143-103, Mitutoyo | `duplicate_remote_product_code` | `003207`, `003457` | `UNRESOLVED` | — | `MANUAL_ACCOUNTING_REVIEW` |
| `4824-16` | 3685, شابلون ذوزنقه 1 - 12اینچ اینسایز مدل 4824-16, INSIZE | `mapping_code_mismatch` | mapped `000893` absent; ProductCode match `001287` | `RESOLVED` | `001287` | `LOCAL_MAPPING_UPDATE` |

`RECOMMENDATION != AUTHORIZATION`. None of these actions were applied.

## `6112-1287` — UNRESOLVED

Local mapping 595 stores Hesabfa code `000619` and product code `6112-1287`
for product 1627 only. `last_synced_at` is `2026-08-11T10:28:31.312320+00:00`.

| Code | Active | Name relation | nodeFamily | Local mapping owner |
|------|--------|---------------|------------|---------------------|
| `000619` | false | `exact_normalized` | کالا | product 1627, mapping 595 |
| `003620` | true | `different` | کالا : اندازه گیری : داسکوا(DASQUA) | none |

Code `000619` carries the Karzar title exactly. Code `003620` carries a
different trade title, راپورتر (گیج بلاک) 87 پارچه گرید 2 مدل 6112-1287, under
the Dasqua node that matches the local brand. Both use ProductCode `6112-1287`.
Neither code is owned by another Karzar product. SKU `6112-1287` belongs only
to product 1627.

Active state, code number, and price presence do not select a winner. The
exact title shows which item repeats the Karzar name. It does not show which
code holds warehouse quantity. Status: `UNRESOLVED_REMOTE_DUPLICATE`.

Additional evidence required: an accounting determination of which Hesabfa
code is the stock-bearing item for ProductCode `6112-1287`.

## `103-143` — UNRESOLVED

Local mapping 3150 stores Hesabfa code `003207` and product code `103-143`
for product 2297 only. `last_synced_at` is `2026-08-11T10:24:26.081348+00:00`.

| Code | Active | Name relation | nodeFamily | Local mapping owner |
|------|--------|---------------|------------|---------------------|
| `003207` | false | `exact_normalized` | کالا | product 2297, mapping 3150 |
| `003457` | true | `exact_normalized` | کالا : اندازه گیری : میتوتویو(MITUTOYO) | none |

Both remote names match the Karzar title exactly. The Mitutoyo node on
`003457` matches the local brand and is corroboration only. Neither code is
owned by another Karzar product. SKU `103-143` belongs only to product 2297.

Status: `UNRESOLVED_REMOTE_DUPLICATE`.

Additional evidence required: an accounting determination of which Hesabfa
code is the stock-bearing item for ProductCode `103-143`.

## `4824-16` — RESOLVED

Local mapping 869 stores Hesabfa code `000893` and product code `4824-16`
for product 3685 only. `last_synced_at` is `2026-07-28T09:35:31.638248+00:00`.

Code `000893` is absent from the complete item list, including a numeric-equal
comparison (`893` and `000893`). No second local mapping claims `000893`.

The only remote item with normalized ProductCode `4824-16` is:

| Code | Active | Name | nodeFamily | Local mapping owner |
|------|--------|------|------------|---------------------|
| `001287` | true | شابلون دنده ای ذوزنقه ای اینسایز (Insize) مدل 16-4824 | کالا : اندازه گیری : اینسایز(INSIZE) | none |

Normalized names differ. Shared catalog tokens are شابلون, ذوزنقه, اینسایز,
and model digits 4824/16. That corroborates the ProductCode. The decision uses
the unique ProductCode and the absence of mapped code `000893`. Code `001287`
is not owned by another Karzar product. SKU `4824-16` belongs only to product
3685.

Mapping classification: `STALE_CODE`. Correct current remote code: `001287`.
Stale local code: `000893`.

Future action, not executed:

```text
UPDATE hesabfa_item_mappings
SET hesabfa_code = '001287'
WHERE id = 869
  AND product_id = 3685
  AND sku = '4824-16'
  AND hesabfa_code = '000893'
  AND hesabfa_product_code = '4824-16';
```

## Ownership

No candidate produced `CODE_OWNED_BY_OTHER_PRODUCT` or
`PRODUCTCODE_USED_BY_OTHER_LOCAL_PRODUCT`. Counts are in `local_ownership.csv`.
Ownership is exact `hesabfa_code` string equality, which is the unique key on
`hesabfa_item_mappings`.
