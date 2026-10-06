# Hesabfa Semantics Report — Wave 1A

## Scope

Read-only `item/getItems` pagination against live Hesabfa from API container
`lathe_api` on host `srv5944957438`. No `item/save`, no stock writes, no mapping
mutations. `HESABFA_ENABLED=true`, `HESABFA_TEST_MODE=true`.

## Observed fields

Hesabfa items expose numeric `Stock` (example sample items and Tag=`karzar:{id}`
matches). `item/GetQuantity` for ProductCode-style codes returned empty lists in
this probe (filter/code semantics not relied upon).

## Cohort coverage

| Metric | Value |
| --- | ---: |
| Wave 0 targets | 330 |
| Tag-matched Hesabfa items | 229 |
| Matched with Stock > 0 | 6 |
| Unmatched targets | 101 |

## Policy (current main)

From `docs/HESABFA.md` / `docs/COMMERCE.md`:

- Site inventory is binary `is_available` (موجود / ناموجود).
- Warehouse numeric stock lives only in Hesabfa.
- `POST /hesabfa/stock/sync` is a deprecated no-op — site does not store warehouse quantities.
- Admin must not display Hesabfa stock widgets.

## Verdict

`HESABFA_STOCK_SEMANTICS_UNPROVEN`

Observed `Stock` values are evidence only. They are **not** accepted as
Wave 1B APPLY authority for flipping `is_available` without an Owner decision
that defines:

1. Which Hesabfa quantity field is sellable stock (item.Stock vs warehouse GetQuantity).
2. Warehouse code / multi-warehouse rules.
3. Exact identity key (Tag vs ProductCode vs Code vs site sku).
4. Whether Stock>0 ⇒ site AVAILABLE is authorized commerce policy.

Wave 1A does **not** promote Hesabfa Stock into `future_apply_candidate=YES`.
