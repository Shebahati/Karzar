# Phase 2A — Canonical Manufacturer Identity

**Status:** Proposed infrastructure (schema + governance). Not a rename APPLY.  
**Parent:** [`SPEC-product-naming-standard-v1.md`](../SPEC-product-naming-standard-v1.md)  
**AODS:** `PRODUCT-NAMING-V1-PHASE-2A-MANUFACTURER-IDENTITY`

---

## 1. Definition

`products.manufacturer_code` is the **exact verified manufacturer-issued** ordering, designation, catalogue, model, part, or variant code that identifies the product within the manufacturer’s catalog.

Examples: `1108-150`, `500-196-30`, `DCMT11T312-XM YBC203`, `WNMG080408-PM`, `K11-315MM`, `GM-4E-D8.0`.

It is **not** Karzar SKU, `source_internal_sku`, `source_product_id`, slug, product name, reseller internal code, or a heuristic candidate.

---

## 2. Canonical vs candidate identity

| Layer | Meaning | May populate `products.manufacturer_code`? |
|-------|---------|---------------------------------------------|
| Canonical | Verified OEM identity (Tier 1–3 authority) | Yes (Phase 2C controlled writer only) |
| Candidate | Audit/extracted/source evidence | **No** — CSV, JSONB, manifests only |

`extract_manufacturer_code_candidates()` returns candidates only. It never implies governance.

---

## 3. Null semantics

| Value | Meaning |
|-------|---------|
| `NULL` | Canonical OEM identity unset / unverified |
| non-null | **Verified canonical manufacturer identity** |

Non-null **must not** mean probable, regex-extracted, SKU-copied, title-parsed, or reseller-only.

After Phase 2A migration, all existing rows remain `NULL` (zero backfill).

---

## 4. Evidence / authority requirements

Future automatic backfill (Phase 2C) should normally require Tier 1–3:

1. OEM manufacturer catalogue / official product page  
2. Authorized distributor / official national representative  
3. Karzar already-verified structured identity with evidence  

Tier 4 (structured supplier import) needs explicit source-specific approval.  
Tier 5–7 (reseller title, legacy parse, SKU-only) must not auto-write canonical identity.

---

## 5. SKU non-equivalence

SKU is Karzar commerce identity. Manufacturer code is OEM identity. They may coincide for some rows; that is **not** an invariant.

Forbidden:

```text
product.manufacturer_code = product.sku
UPDATE products SET manufacturer_code = sku
```

---

## 6. Exact-format preservation

Preserve authoritative OEM form. Do not automatically uppercase/lowercase, Persianize digits, strip hyphens/dots/spaces/slashes, or collapse designation segments. Harmless outer whitespace trim is allowed only at a controlled write boundary.

---

## 7. Uniqueness policy

**No** `UNIQUE(manufacturer_code)` and **No** `UNIQUE(brand_id, manufacturer_code)` in Phase 2A.

Phase 0/1 observed at least `ASTPOWER` + `TU-DR230` candidate collision. Uniqueness waits until collision audit is resolved.

---

## 8. Collision policy

Collisions are audited, not auto-resolved. Do not merge products or pick a winner in Phase 2A. See `audit/product-manufacturer-code-phase2a/MANUFACTURER_CODE_COLLISIONS.csv`.

---

## 9. Write policy

- `ProductCreate` / `ProductUpdate`: **no** `manufacturer_code` field.  
- First canonical writer deferred to **Phase 2C**.  
- Any future writer must require verified source, reason, actor, and must call `record_product_change(..., field_name="manufacturer_code", ...)`.

---

## 10. Audit policy

`product_change_logs` already supports field-level diffs. When a canonical writer lands (Phase 2C), every change must log `field_name=manufacturer_code`, old/new, reason, actor, timestamp.

---

## 11. Future Phase 2C backfill rules

- Prefer `BACKFILL_EXACT` only with Tier 1–3 evidence.  
- Insufficient alone: SKU looks correct, title `مدل`/`کد`, regex, `specifications.model`, reseller page, source internal SKU.  
- No production APPLY in Phase 2A.

---

## 12. Naming confidence relationship

`build_product_name_v1` HIGH confidence requires **both**:

- `product_type_governed=True`
- `manufacturer_code_governed=True` (and non-empty code)

Either false → HIGH forbidden (max MEDIUM). Candidates from `extract_manufacturer_code_candidates()` never set governance.

---

## Indexes (Phase 2A)

| Index | Columns | Unique | Supported query | Reason |
|-------|---------|--------|-----------------|--------|
| `ix_products_manufacturer_code` | `manufacturer_code` | false | exact OEM lookup / collision scan | Phase 2C readiness |
| `ix_products_brand_id_manufacturer_code` | `brand_id`, `manufacturer_code` | false | brand-scoped OEM lookup | collision audit |

---

## Search gap (documented; not implemented here)

Current catalog search: `name`, `sku`, `Brand.name` (`app/crud/product.py`).  
Manufacturer-code search is required before rename APPLY (Phase 2B/2E). Out of Phase 2A scope.

---

## Alembic

Revision `u4v5w6x7y8z9` — additive nullable column + non-unique indexes; no DML.
