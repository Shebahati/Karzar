# Product 1789 — Owner-authorized Production brand repair APPLY

Immutable evidence for the Category B one-row Production repair:

```text
product_id 1789
brand_id NULL → 3 (INSIZE)
```

Owner authorization: «مرج کردم، تعمیر 1789 را انجام بدهیم»

## Safety

- No availability / price / activation / Hesabfa / deploy mutations
- Exactly 1 Product row, field `brand_id` only
- Exactly 1 `product_change_logs` row (`owner_authorized_brand_integrity_repair`)
- Sellable delta caused by repair = 0

## Tooling

`scripts/ops/product_1789_brand_repair_apply_once.py` — fail-closed; requires `--apply` and `--confirm-manifest-sha`.

Guarded rollback: `ROLLBACK.sql` (expects `brand_id=3` + identity guards).
