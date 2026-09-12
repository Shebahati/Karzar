# Logistics Authority

Independent package-dimension / shipping-class authority for Karzar parcel logistics.

```text
PRICE AUTHORITY  ≠  AVAILABILITY AUTHORITY  ≠  LOGISTICS AUTHORITY
```

Never infer package weight or package dimensions from:

- `base_price` / availability / `is_active`
- engineering `specifications.dimensions`
- product name, category, or brand defaults
- “typical” industrial sizes without an approved estimate record

This document is operational guidance for tooling under `scripts/catalog_target/`
and CLIs `validate_logistics_package.py` / `logistics_backfill.py` (validate-only).
It does **not** set Canon-Lock Accepted policy by itself.

Companion: [`docs/COMMERCE.md`](../COMMERCE.md) (Postex shipping),  
[`docs/integrations/postex/README.md`](../integrations/postex/README.md).

---

## 1. Canonical product fields (PR #311 / migration `i2j3k4l5m6n7`)

Storage units and names are those implemented on the Postex branch.
**Do not invent parallel `*_mm` or short `fragile`/`liquid` columns.**

| Catalog / DB field | Role | Null policy |
|--------------------|------|-------------|
| `shipping_class` | `parcel` \| `freight_only` | **NULL = UNKNOWN** (not reviewed). No server default. |
| `weight_grams` | Packaged unit weight | NULL = unknown |
| `package_length_cm` | Outer package length | NULL = unknown; if set must be `> 0` |
| `package_width_cm` | Outer package width | NULL = unknown; if set must be `> 0` |
| `package_height_cm` | Outer package height | NULL = unknown; if set must be `> 0` |
| `shipping_is_fragile` | Fragile handling flag | **NULL = UNKNOWN**; true/false only when reviewed |
| `shipping_is_liquid` | Liquid / spill flag | **NULL = UNKNOWN**; true/false only when reviewed |

Legacy rows after migration must remain NULL for class/fragile/liquid — never mass-assert `parcel` / `false`.

### Unit bridge for intake files

Authority **intake** CSVs may use millimetres for human measurement worksheets.
The validator converts to centimetres for storage alignment:

```text
package_*_cm = ceil(package_*_mm / 10)   # whole cm after ceil, matching package_builder
```

Grams stay grams. Do not store millimetres on `products`.

### Forbidden sources for package geometry

- `products.specifications` / engineering drawings as shipping L/W/H
- fabricating “fallback” boxes when data is missing
- copying one SKU’s package dims onto unrelated SKUs without source evidence

---

## 2. Source hierarchy

| Priority | Source class | Code | When allowed |
|----------|--------------|------|--------------|
| 1 | Manufacturer / official package specification | `OFFICIAL_MANUFACTURER` | Catalog datasheet, carton label, official packaging table |
| 2 | Supplier package data | `DISTRIBUTOR` | Supplier packing list with explicit package weight/dims |
| 3 | Manual Karzar measurement | `MANUAL_MEASUREMENT` | Physical measure of the sellable carton / sealed unit |
| 4 | Controlled estimation | `CONTROLLED_ESTIMATION` | **Only** with explicit Owner approval per SKU or approved cohort rule |

Every authority row must record `source` + `source_date`. Missing source → not READY.

---

## 3. Validation statuses

Per SKU / package row (independent of price and site availability):

| Status | Meaning |
|--------|---------|
| `UNKNOWN` | Classification / hazard facts not established (`shipping_class` NULL and/or hazards NULL with no usable package data) |
| `READY` | Explicit `parcel` + weight >0 + all dims >0 + fragile/liquid explicit + source provenance on intake |
| `INCOMPLETE` | Explicit `parcel` (or partial physical fields) but required package/hazard facts still missing |
| `INVALID` | Present values violate rules (non-positive, out of range, bad types, bad class) |
| `BLOCKED` | `freight_only` or policy/provider blocked as documented |

Mapping used by tooling:

```text
No usable shipping data     → UNKNOWN (and INCOMPLETE when partial)
Valid parcel package        → READY
Invalid / freight-only gate → BLOCKED (INVALID is the raw defect class; freight_only is BLOCKED for Postex parcel)
```

`freight_only` products are **not** logistics “READY” for Postex parcel quoting.
They are valid commerce SKUs that require freight / inquiry shipping outside Postex v1.

---

## 4. READY predicate (parcel)

A row is `READY` only if **all** of the following hold:

1. `shipping_class = parcel`
2. `weight_grams` is present and `> 0`
3. `package_length_cm`, `package_width_cm`, `package_height_cm` each present and `> 0`
4. `shipping_is_fragile` and `shipping_is_liquid` are explicit booleans (intake must not leave them blank)
5. `source` ∈ allowed source classes; `source_date` present
6. Values pass reasonable-range checks (see validator)
7. Optional offline box-fit check may still classify `DATA_READY_BUT_NO_POSTEX_BOX` — that is **not** catalog INVALID; it is a Postex capacity flag

`READY` never implies site purchasability. Purchasability remains:

```text
deleted_at IS NULL AND is_active AND is_available AND base_price IS NOT NULL
```

---

## 5. Migration / enablement boundary

| Action | Allowed in this foundation | Requires separate Owner order |
|--------|----------------------------|-------------------------------|
| Document authority + offline validate | Yes | — |
| Apply Alembic `i2j3k4l5m6n7` to production | No | Schema deploy / ops |
| Backfill `products` logistics columns | No | Category B APPLY + reviewed plan |
| Set `POSTEX_ENABLED=true` | No | Explicit enablement |
| Live Postex quote / parcel create | No | Explicit live authorization |

Schema add alone does **not** make the catalog Postex-ready. After migration,
existing products keep `shipping_class` / hazard flags as **NULL (UNKNOWN)**.
Do not treat NULL as parcel or as non-fragile/non-liquid.

### Alembic downgrade

After `shipping_quotes` / `shipments` rows exist in any persistent environment,
downgrading `i2j3k4l5m6n7` is **destructive** and is **not** an operational rollback.
Operational rollback is `POSTEX_ENABLED=false`. Schema rollback after real logistics
data exists must be forward-only unless explicitly Owner-authorized.

---

## 6. Provenance

PR #311 does **not** add provenance columns on `products`.

Until a future schema decision:

- Provenance lives in versioned authority files under `data/catalog-target/` (or `.local-scratch/` evidence during pilots)
- APPLY plans must carry `source` / `source_date` per SKU
- Runtime DB rows remain values-only; do not invent provenance by guessing

Status today: **NOT_TRACKED** on production product rows.

---

## 7. INSIZE pilot (plan only — do not execute)

| Item | Value |
|------|-------|
| Brand | INSIZE (`brand_id = 3`) |
| Scope | Current **purchasable** cohort only (production predicate), ~158 SKUs |
| Goal | Produce a validated logistics authority file; **no** Product UPDATE |
| Required output columns | `product_id`, `sku`, `weight_grams`, `package_length_cm`, `package_width_cm`, `package_height_cm`, `shipping_is_fragile`, `shipping_is_liquid`, `shipping_class`, `source`, `source_date`, `validation_status` |
| Exit for later APPLY | 100% of pilot purchasable rows `READY` **or** explicit `freight_only`/`BLOCKED` with Owner sign-off |

Do not shrink public availability to manufacture a READY cohort.

---

## 8. Related tooling

| Tool | Role |
|------|------|
| `scripts/validate_logistics_package.py` | Offline row validator → READY / INCOMPLETE / INVALID |
| `scripts/catalog_target/logistics_backfill.py` | CSV/XLSX → validated authority artifact (**no DB write**) |
| Future APPLY CLI | Out of scope until Owner authorizes Category B writer |

---

## 9. Safety invariants

- Logistics backfill must never write price, stock counts, or `is_available`
- Enrichment pipelines must not copy engineering dimensions into `package_*`
- `POSTEX_ENABLED` remains false until catalog readiness gate passes for the enabled cohort
