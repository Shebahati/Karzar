# Schema Identity Review — Manufacturer Code for Naming v1

**Status:** Proposed (Phase 0/1) — **not** Board-Accepted; no Alembic in this phase  
**Parents:** ADR-014 · PRODUCT_IDENTITY_EQUIVALENCE_POLICY · SPEC-product-naming-standard-v1 §3  
**Non-claim:** Does not authorize schema migration, production APPLY, or Canon Lock merge.

---

## 1. As-built (verified)

| Concern | Evidence | Finding |
|---------|----------|---------|
| Commerce PKE join | ADR-014 Accepted — Wave-1 PKE = `products.id` (1:1) | Sellable SKU identity is already stable |
| OEM manufacturer code column | `app/db/models/product.py` — Product has `sku`, `slug`, `name`, `specifications` JSONB; **no** `manufacturer_code` | No first-class OEM ordering/designation field |
| Specs JSONB | `products.specifications` (default factory in model) | Uncontrolled; importers may stash `model`, `source_identity_key`, etc. |
| Identity equivalence policy | `docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md` | Governs Fact assertion under unresolved OEM suffix; does **not** introduce a DB enum or persistent OEM mapping table |
| Search | `app/crud/product.py` name/sku/brand ILIKE | Cannot search a dedicated manufacturer_code column today |

**Conclusion:** OEM identity for titles today is reconstructed from title text, SKU heuristics, and ad-hoc JSONB keys — evidence-only, not schema.

---

## 2. Options for naming v1

| Option | Shape | Pros | Cons |
|--------|-------|------|------|
| **A — `products.manufacturer_code`** (nullable String) | First-class column (+ optional evidence metadata later) | Matches import pipelines that already carry OEM codes; simplest path for `build_product_name_v1`; searchable later | One primary code only; multi-issuer aliases need care |
| **B — `product_identifiers` table** | `(product_id, identifier_type, value, issuer, is_primary, evidence…)` | Superior when secondary codes / multi-issuer aliases proliferate | Heavier migration; premature if most SKUs have one OEM code |
| **C — KB-only identity** | Facts / knowledge nodes only | Reuses knowledge stack | Insufficient alone for commerce title generation at write time |

---

## 3. Recommendation

**Choose Option A for Naming Standard v1 schema work (Phase 2 proposal).**

Rationale:

1. Naming engine requires a stable OEM token (`کد {manufacturer_code}`) with OEM-native preservation — a nullable column is the lowest-risk SoR field on the commerce product.
2. ADR-014 already locks PKE join to `products.id`; manufacturer_code is **commerce-adjacent identity**, not a competing PKE key.
3. PRODUCT_IDENTITY_EQUIVALENCE_POLICY continues to govern **when Facts may be asserted** under unresolved suffixes; it does not block a nullable primary OEM code column for titles when `RESOLVED_EXACT` (or an explicitly held code for display).
4. Keep JSONB `specs.model` as **legacy evidence only** — do not treat uncontrolled JSONB as authority for APPLY.

**Path to Option B:** When secondary identifiers (distributor internal SKU, alternate catalogue numbers, grade-as-separate-id) exceed what a single column + evidence notes can hold, introduce `product_identifiers` with `is_primary` pointing at the same value currently in `manufacturer_code`, then keep the column as a denormalized primary for naming/search or migrate fully under a follow-on ADR.

---

## 4. Phase 0/1 stance

- Audit candidates may propose manufacturer_code from evidence (`specs.model`, overlays, title `مدل`/`کد`, brand-native SKU patterns) with confidence tags.
- **Heuristics must not auto-write** identity to production (SPEC §3 authority tiers).
- No Alembic in this PR/phase; this document is the schema intent record only.

---

## 5. Related cites

- `docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md` — PKE = `products.id`
- `docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md` — RESOLVED_EXACT / EQUIVALENT_FACTS; no new identity enum
- `docs/architecture/specs/SPEC-product-naming-standard-v1.md` §3 — Option A now, Option B when scale requires
- `app/db/models/product.py:172-177` — current columns (`sku`, `slug`, `name`; no manufacturer_code)
