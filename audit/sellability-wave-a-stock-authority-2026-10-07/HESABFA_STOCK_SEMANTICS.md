# Hesabfa Stock Semantics — Wave A (read-only)

**Cohort:** frozen CURRENT_ONLY_AVAILABILITY (580)  
**Queried:** YES (read-only Production `hesabfa_item_mappings`)  
**Mapped rows:** 478 / 580  
**Mutation:** NO

## Question

What does Hesabfa `Stock` / `last_stock` mean operationally for Karzar?

## Evidence

| Source | Finding |
|--------|---------|
| `docs/HESABFA.md` | Warehouse counts are **Hesabfa-only**; site never stores/displays numeric stock; site uses binary `is_available` |
| `docs/COMMERCE.md` / Canon | Site availability is binary; warehouse counts are Hesabfa-only |
| Mapping table | `hesabfa_item_mappings.last_stock`, `last_synced_at` present |
| Official Hesabfa API notes in docs | Stock is not an `item/save` field; opening quantity is a separate fiscal method |
| Supplier stock policy | `PRICE AUTHORITY ≠ AVAILABILITY AUTHORITY`; Hesabfa not listed as storefront availability authority unless semantics proven |

## Classification

```text
HESABFA_STOCK_SEMANTICS = UNPROVEN
```

Not proven to be any of:

- physical on-hand sellable stock
- available-to-promise
- warehouse sellable quantity with Karzar-compatible legend

Observed `last_stock` values are **supporting evidence only**.

## Usable as availability authority?

```text
NO
```

Wave A does **not** set `normalized_availability` from Hesabfa Stock.

See `HESABFA_COHORT_RECONCILIATION.csv` (`usable_as_availability_authority=NO` for all rows).
