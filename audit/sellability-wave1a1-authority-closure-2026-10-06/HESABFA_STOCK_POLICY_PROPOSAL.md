# Hesabfa Stock Policy Proposal — Wave 1A.1 (UNPROVEN → proposal only)

## Current verdict

```text
HESABFA_STOCK_SEMANTICS_UNPROVEN
usable_for_future_APPLY=NO
```

Wave 1A read-only probe: 229/330 Tag-matched; 6 with Stock>0. No activation.

## Proposed Owner policy questions (not decisions)

1. **Sellable field:** Is `item.Stock` the sellable quantity, or must warehouse
   `GetQuantity` (with warehouse code) be used?
2. **Threshold:** Does `Stock > 0` authorize site `is_available=true`, or only
   inform warehouse widgets (currently forbidden on storefront)?
3. **Identity:** Tag=`karzar:{product_id}` vs ProductCode vs Code vs site SKU —
   which key is authoritative for APPLY allowlists?
4. **Conflict rule:** When supplier stock = UNAVAILABLE but Hesabfa Stock>0 (or
   inverse), which authority wins for public sale?
5. **Activation:** Hesabfa must remain **discovery-only** until Owner answers
   1–4 in writing; no Wave 1B APPLY via Hesabfa in this wave.

## Recommendation

Keep Hesabfa as secondary warehouse plane. Do not promote Stock→`is_available`
without an Accepted commerce decision. Supplier stock authority remains primary
for Wave 1B design brands that already have registered adapters.
