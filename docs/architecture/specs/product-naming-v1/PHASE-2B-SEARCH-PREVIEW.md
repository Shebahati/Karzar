# Phase 2B — Search Safety & Admin Naming Preview

**Status:** Proposed infrastructure. No rename APPLY. No manufacturer_code backfill.  
**Parent:** [`SPEC-product-naming-standard-v1.md`](../SPEC-product-naming-standard-v1.md)  
**Prerequisite:** Phase 2A (`products.manufacturer_code`, Alembic `u4v5w6x7y8z9`)

---

## 1. Search surfaces

Each query token is matched (ILIKE, escaped) against:

| Surface | Source |
|---------|--------|
| Product name | `products.name` |
| SKU | `products.sku` |
| Manufacturer code | `products.manufacturer_code` (null skipped) |
| Brand | `brands.name` via relationship |
| Product Type code / FA / EN / slug | `product_types.*` via `product_type_id` |
| PT synonyms | `knowledge_taxonomy_nodes.synonyms` (see §4) |

Not searched: description, short_description, specifications JSONB, Facts, SEO fields.

## 2. Token semantics

```text
AND( OR(surfaces match token_i) for each whitespace token )
```

Cross-field examples: `اینسایز 1108-150`, `ZCC DCMT`, `الماس DCMT` (synonym + OEM).

## 3. Normalization

Display tokens: Arabic `ي/ك` → Persian `ی/ک`; Arabic-Indic digits → Western; whitespace collapse.  
OEM codes in storage are never rewritten. Case-insensitive match via ILIKE.

## 4. Synonym source & contract

- Table: `knowledge_taxonomy_nodes`
- Require (all):
  - `status = active`
  - `node_type = product_type` (canonical taxonomy type; **not** assignment role `product_type_bridge`)
  - `dimension = family` (matches `knowledge_taxonomy_service` node_type→dimension map)
  - `product_type_id = Product.product_type_id` and Product PT FK non-null
- Synonyms JSON: only **top-level array string elements** are searchable
  - PostgreSQL: `jsonb_array_elements` + `jsonb_typeof(elem) = 'string'`
  - SQLite tests: `json_each` + `type = 'text'`
  - object / nested array / number / bool / null elements → ignored
  - non-array legacy value → no match, query does not fail
- Unrelated PT synonyms and wrong `node_type` must not match.

## 5–6. Product Type & manufacturer-code search

Via FK `products.product_type_id` and EXISTS (no row multiplication). Manufacturer code uses Phase 2A indexes.

## 7. Governance context

```python
NamingGovernanceContext(
  product_type_governed,
  manufacturer_code_governed,
  brand_display_governed,
  naming_profile_governed,
  variant_facts_governed,
  identity_qualifiers_governed,
)
```

## 8. HIGH confidence contract

HIGH only if every input used in the generated title is governed:

- Product Type FK governed  
- `manufacturer_code` governed (non-null column = verified)  
- Brand display registry status GOVERNED/APPROVED/CANONICAL  
- Naming profile GOVERNED (not `generic.v1`)  
- Used variant facts evidenced/published  
- Used identity qualifiers governed when present  

## 9. Naming-profile resolution

`resolve_naming_profile_v1(ProductType.code)` → mapped profile or `generic.v1` + `PROFILE_MISSING`. Never guesses from `Product.name`.

## 10. Variant fact governance

Facts appearing in the title (e.g. measurement range) require published KB Fact evidence for HIGH. Title/heuristic extraction is never injected into persisted preview.

## 11. Preview endpoint

```text
GET /api/v1/products/{id}/naming-preview
```

Auth: super-admin. Read-only. Inputs: persisted PT, brand, manufacturer_code, published Facts, registries. Null OEM → HOLD (no title parse).

## 12. Admin UX

Panel «نام استاندارد کارزار»: current/proposed name, PT, brand, OEM (read-only), profile, state, confidence, blockers. **No Apply / Rename button.**

## 13. No-apply guarantee

Zero Product.name / slug / SKU / manufacturer_code writes from preview or search.

## 14. Known limitations

- Brand Display Registry mostly `PROPOSED`/`NEEDS_GOVERNANCE` → HIGH rare until brands governed  
- Synonym coverage depends on active PT-linked taxonomy nodes  
- Census for OEM backfill still PARTIAL (Phase 2A)  
- No candidate-preview POST in this PR  

## 15. Prerequisites for later phases

- **2C:** controlled OEM backfill (Tier 1–3) — blocked by PARTIAL census / BACKFILL_EXACT=0  
- **2D:** full naming dry-run with real PT + OEM  
- **2E:** owner-authorized RENAME_SAFE HIGH apply + SEO plan  
