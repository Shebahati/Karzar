# SPEC — Karzar Product Naming Standard v1

**Document type:** Architecture / governance specification (implementation-grade)  
**Status:** **Proposed** (Phase 0/1 audit — not Board-Accepted; do not treat as Canon Lock merge criteria alone)  
**Version:** `karzar_product_naming_v1`  
**Date:** 2026-09-28  
**Parents:** ADR-014 · ADR-015 · SPEC-product-knowledge-entity-model · SPEC-canonical-product-type-model · PRODUCT_IDENTITY_EQUIVALENCE_POLICY · SPEC-product-import-enrichment-playbook · ADR-010  
**Non-claim:** This SPEC does **not** authorize catalog APPLY, schema migration to production, slug changes, SEO mutation, or Board Acceptance.

---

## 1. Purpose

Establish a **single deterministic** customer-facing product display-name grammar for the Karzar industrial catalog.

Long-term direction:

```text
Structured Data → Product Name
```

Not:

```text
Product Name → infer structured data
```

Pipeline:

```text
STRUCTURED PRODUCT IDENTITY
+ CANONICAL PRODUCT TYPE
+ CANONICAL BRAND DISPLAY
+ MANUFACTURER CODE
+ APPROVED IDENTITY QUALIFIERS
+ APPROVED PRIMARY VARIANT ATTRIBUTE(S)
        ↓
KARZAR NAMING ENGINE (karzar_product_naming_v1)
        ↓
CANONICAL PRODUCT DISPLAY NAME  (products.name)
```

---

## 2. Terminology

| Term | Meaning | Notes |
|------|---------|-------|
| **SKU** | Karzar internal commerce identity | Used across site/Hesabfa matching; must **not** change semantics in naming work |
| **slug** | Public PDP URL token | Generated on create; **must not** auto-change when `name` changes (see §15) |
| **name** | Canonical customer-facing display title | Free string today; target of this standard |
| **manufacturer_code** | Exact OEM ordering / designation / catalogue / variant code | Identity field; preserve authoritative form |
| **model / part_number / ordering_code / designation** | OEM-side synonyms for identity tokens | May map into `manufacturer_code` or typed identifiers; do not collapse casually |
| **source_internal_sku / source_product_id** | Upstream reseller/system IDs | Evidence only; not display identity |
| **Product Type (PT)** | Engineering classification noun (`product_types`) | ADR-015; **not** commerce category |
| **Brand** | Commerce brand facet | May store bilingual `EN \| FA` in one `brands.name` string today |
| **identity qualifier** | Optional PT-adjacent token required for identity (e.g. digital vs dial when not in PT) | Profile-governed |
| **primary variant attribute** | Buyer-critical distinguishing fact (range, Ø, thread, capacity, volume) | Profile-governed; omit noise |
| **meta_title** | SEO title | Separate concern; falls back to `name` today |

Do **not** treat SKU ≡ manufacturer_code ≡ model ≡ slug ≡ name.

---

## 3. Identity model

### 3.1 As-built (verified)

| Concern | Current state | Cite |
|---------|---------------|------|
| `products.name` | Free `String(255)`, required | `app/db/models/product.py` |
| Create validation | Non-empty strip only | `app/schemas/product.py` |
| Update | May change `name`; **does not** regenerate `slug` | `app/crud/product.py` |
| Manufacturer code column | **Absent** on Product ORM | — |
| Specs JSONB | Uncontrolled; may hold `model`, ranges, etc. | `products.specifications` |
| Product Type FK | Nullable `product_type_id` | ADR-015 |
| Brand bilingual | Convention `EN \| FA` in single `name` | `split_bilingual_label` / `display_brand_name` |
| Persistent OEM mapping table | **Not required yet** per identity policy | `PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md` |

### 3.2 Recommended architecture (Phase 2 proposal — not applied here)

**Recommendation: Option A now, Option B when scale requires it.**

| Option | Shape | Verdict |
|--------|-------|---------|
| **A** | Nullable `products.manufacturer_code` (+ optional evidence metadata later) | **Recommended for v1** — matches import pipelines already carrying OEM codes; simplest path to naming |
| **B** | `product_identifiers(product_id, identifier_type, value, issuer, is_primary, evidence…)` | Superior when multi-issuer aliases / secondary codes proliferate |
| **C** | KB-only identity | Insufficient alone for commerce title generation; reuse Facts for variant attrs |

Authority tiers for manufacturer identity:

1. OEM technical catalogue / official product page  
2. Official / authorized national distributor  
3. Karzar verified structured data  
4. Reliable reseller catalog  
5. Legacy imported title  
6. Heuristic inference (**must not auto-write identity**)

Heuristics may propose audit candidates only.

---

## 4. Naming grammar

Default Persian storefront grammar:

```text
[Canonical Product Type]
[Identity Qualifier(s), only when required]
[Canonical Display Brand]
کد
[Manufacturer Code]
[، Primary Variant Attribute(s), only where useful]
```

Conceptual order:

```text
Product Type → identity qualifier → brand → manufacturer code → ≤ few buyer-critical attributes
```

Example:

```text
کولیس دیجیتال اینسایز کد 1108-150، 0–150 میلی‌متر
```

Forbidden opposite patterns:

- Marketing stuffing  
- Bilingual brand dump (`INSIZE | اینسایز …`)  
- Universal `مدل` before OEM code  
- Category breadcrumb as title  

### 4.1 `کد` vs `مدل`

Use Persian label **`کد`** as the default generic display label before the OEM identifier.

Do **not** universally use `مدل`. OEMs use Code / Order No. / Catalogue No. / Part Number / Designation / Model interchangeably; `کد` is the Karzar display abstraction. Structured fields retain OEM semantics.

---

## 5. Brand display rules

Do not insert raw `Brand.name` when it is a bilingual storage label.

Conceptual fields (registry / future schema):

| Field | Role |
|-------|------|
| `identity_name` | Stable brand key (usually Latin trademark) |
| `display_name_fa` | Persian storefront form |
| `display_name_en` | Latin form |
| `preferred_product_title_form` | `fa` \| `en` \| `mixed` |

Reuse as-built helpers for interim splitting: `app/utils/seo_descriptions.split_bilingual_label` / `display_brand_name`.

Per-brand override: Latin trademark may remain in titles when overwhelmingly canonical (e.g. **ZCC.CT**). Registry: `audit/product-naming-v1/BRAND_DISPLAY_REGISTRY.csv` (proposed).

---

## 6. Product Type rules

- Titles use **Product Type** nouns, never commerce category paths.  
- One canonical customer-facing Persian term per PT; alternatives are **synonyms** (taxonomy node `synonyms` / search index — not stuffed into `name`).  
- Do not silently mutate PT rows in Phase 0/1.  
- If PT FK missing or Persian label unsuitable → `HOLD_MISSING_PRODUCT_TYPE` / `HOLD_TERMINOLOGY_GOVERNANCE`.

---

## 7. Manufacturer code policy

Manufacturer code is an **identity** field.

Preserve authoritative form. Do **not** casually:

- remove hyphens / dots  
- convert `/` to `-`  
- collapse meaningful spaces  
- strip grade / chipbreaker / suffixes  
- Persianize digits  
- uppercase/lowercase without OEM evidence  

OEM identity preservation **outranks** cosmetic uniformity.

Display always: `کد {manufacturer_code}` with the code in OEM-native Latin form.

---

## 8. Variant attribute policy

### Include (when profile requires)

- measurement range  
- nominal diameter / thread size  
- capacity  
- length class / flute count (only if variant-defining)  
- interface / collet system (toolholding)  
- package volume (fluids)

### Exclude by default

- accuracy, resolution, IP rating  
- material, DIN/ISO callouts (unless sole distinguisher)  
- country, warranty, delivery, stock, price  
- marketing adjectives  

Max variant attributes: profile-defined (usually 1; rarely 2).

---

## 9. Units and typography

| Case | Form |
|------|------|
| Numeric range | en dash `–` → `0–150 میلی‌متر` |
| Multiplication | `×` → `M6×1` |
| Diameter | `Ø8 میلی‌متر` |
| Degrees | `60°` |
| Volume | `1 لیتر`, `5 لیتر` |
| Digits in display attrs | Latin digits in v1 (deterministic; OEM-native) |
| Digits in OEM codes | Always OEM-native Latin |
| Decimal separator | `.` for technical magnitudes in v1 |
| Micron | `µm` or governed unit dictionary label |
| Inch | Prefer metric primary; imperial only when identity-defining |

Unit wording must align with Property Dictionary / unit dimensions where Facts exist.

---

## 10. Forbidden content

Canonical `name` must not contain:

**Marketing / quality claims:** بهترین، حرفه‌ای، با کیفیت / باکیفیت، اصل، اورجینال، اصل چین، ویژه، پرفروش، ارزان، فوق‌العاده، تضمینی، قیمت ویژه  

**Commerce state:** موجود، ناموجود، ارسال فوری، تخفیف، فروش ویژه  

**SEO stuffing:** خرید، قیمت، فروش، کارزار (and equivalents) inside `name`  

Also avoid: duplicated brand/code/range/category, raw source breadcrumbs, store names, HTML entities, invisible Unicode (normalize), Arabic `ي`/`ك` in Persian display segments.

---

## 11. Synonym policy

- One canonical FA term in the title.  
- Synonyms live in taxonomy / search (Knowledge Taxonomy `synonyms` JSONB), **not** in `name`.  
- Example: canonical `اینسرت تراشکاری`; synonyms `الماس تراشکاری`, `الماس`, `Turning Insert`.  
- Do not build a duplicate knowledge system for synonyms.

---

## 12. Search implications

**As-built search** (`app/crud/product.py`): `Product.name`, `Product.sku`, `Brand.name` only.

Not searched today: manufacturer_code column (absent), PT names, KB synonyms.

Naming standard must **not** reduce discoverability by stuffing. Future search/index should cover:

- brand FA/EN aliases  
- manufacturer_code  
- PT name + synonyms  
- primary variant tokens  

Phase 0/1: report gap only; no search rewrite.

---

## 13. SEO implications

`resolve_meta_title(meta_title, name)` → `meta_title` else `name` else `محصول`  
(Backend + storefront PDP).

Therefore renaming `name` changes effective SERP title whenever `meta_title` is null/blank.

Rules:

- Keep `name` technical and stable.  
- Put commercial SEO phrases in governed `meta_title` / description pipelines — **not** in `name`.  
- Phase 0/1: quantify impact only (`SEO_IMPACT_REPORT.csv`).

---

## 14. Import rules

```text
source.name          → evidence only (Tier 4–5)
manufacturer_code
brand
product_type
facts / primary attrs
        → naming engine
        → canonical Karzar name
```

Missing required identity → **HOLD** (do not invent title).

Writer inventory: `audit/product-naming-v1/PRODUCT_NAME_WRITERS.md`.

---

## 15. Admin rules

Preferred UX (future):

```text
Product Type + Brand + Manufacturer Code + structured facts
        ↓
Canonical Name Preview (system-generated)
```

**Recommended mode: B** — system-generated name + privileged override with reason/actor/time/version.

Mode A (fully locked) is too rigid for industrial edge cases.  
Mode C (free text + lint) preserves today’s drift.

Slug: create-time only; rename must **not** auto-change slug without separate SEO migration approval.

`NAME_CHANGE_CAUSES_SLUG_CHANGE = NO` (verified on current `main`).

---

## 16. Override governance

Future fields (or audit log reuse):

| Field | Purpose |
|-------|---------|
| `name_override` | Explicit non-engine title |
| `name_override_reason` | Human justification |
| `name_override_actor` | Attributable user |
| `name_override_at` | Timestamp |
| `naming_standard_version` | e.g. `karzar_product_naming_v1` |

Overrides must be explicit, attributable, reasoned, auditable. No hidden code exceptions.

---

## 17. Versioning

- Engine/rules tagged `karzar_product_naming_v1`.  
- Audit rows and future product metadata record which version produced a name.  
- Rule changes require a new version id; do not silently rewrite the catalog under “latest”.

---

## 18. Migration states

Every product ends in exactly one primary state:

| State | Meaning |
|-------|---------|
| `EXACT` | Current name already satisfies v1 |
| `RENAME_SAFE` | Deterministic proposal possible (confidence HIGH/MEDIUM/LOW) |
| `HOLD_MISSING_BRAND` | No reliable brand |
| `HOLD_MISSING_MANUFACTURER_CODE` | Required OEM identity missing |
| `HOLD_MISSING_PRODUCT_TYPE` | Cannot determine canonical noun safely |
| `HOLD_MISSING_VARIANT_ATTRIBUTE` | Required distinguisher unavailable |
| `HOLD_IDENTITY_CONFLICT` | Sources disagree |
| `HOLD_TERMINOLOGY_GOVERNANCE` | PT/noun exists but FA canonical unresolved |
| `MANUAL_REVIEW` | Cannot safely auto-classify |

Confidence for `RENAME_SAFE`:

- **HIGH** — PT governed, brand known, OEM code exact, required facts evidenced, no conflicts, profile deterministic → only HIGH eligible for eventual automatic rename wave  
- **MEDIUM / LOW** — human review required  

**HOLD > GUESS.** Structured authoritative identity > source title. OEM identity > cosmetic uniformity.

---

## 19. Examples

| Family | Proposed form |
|--------|----------------|
| Digital caliper | `کولیس دیجیتال اینسایز کد 1108-150، 0–150 میلی‌متر` |
| Outside micrometer | `میکرومتر خارج‌سنج دیجیتال اینسایز کد 3105-25، 0–25 میلی‌متر` |
| Turning insert | `اینسرت تراشکاری ZCC.CT کد DCMT11T312-XM YBC203` |
| Self-centering chuck | `سه‌نظام منظم سانو کد K11-315MM، 315 میلی‌متر` |
| Thread repair insert | `اینسرت ترمیم رزوه {Brand} کد {…}، M6×1` |

Concrete catalog before/after samples live in `audit/product-naming-v1/PRODUCT_NAMING_SUMMARY.md`.

---

## 20. Non-goals

Naming Standard v1 does **not** itself:

- change pricing, availability, inventory, or Hesabfa mappings  
- change categories or redesign taxonomy  
- invent technical facts or infer identity from images  
- rewrite descriptions or SEO copy automatically  
- change URLs / slugs  
- merge duplicates  
- translate / Persianize OEM codes  
- replace Product Type governance  
- authorize production APPLY or deploy  

---

## 21. Phased API / enforcement (proposal only)

| Phase | Behavior |
|-------|----------|
| A | Audit-only (this phase) |
| B | Warning / lint on create-update |
| C | Canonical name preview in admin |
| D | Server-side canonical generation default |
| E | Governed manual override |

Do not make breaking ProductCreate rejection in Phase 0/1.

---

## 22. Naming engine API (design)

Module path (prototype allowed): `app/domain/product_naming.py`

```python
build_product_name_v1(*, product_type, brand, manufacturer_code, facts, naming_profile) -> NamingResult
lint_product_name_v1(...)
compare_product_name_v1(...)
```

Properties: deterministic, pure where practical, testable, evidence-aware, no network/AI/DB writes, no fuzzy identity guessing.

Profiles: governed rows (`profile_code`, `product_type_code`, `title_pattern`, `brand_policy`, `manufacturer_code_required`, `primary_variant_fact_keys`, `unit_policy`, `max_variant_attributes`, `version`) — see `PRODUCT_TYPE_NAMING_PROFILES.csv`.

---

## 23. Exit gate (Phase 0/1)

Complete when constitution, writer inventory, census, proposals/HOLDs, brand/PT/terminology registries, identity schema review, search/SEO reports, collisions, dry-run artifacts, and draft PR exist — with **zero** catalog mutation and **zero** deploy.

**STOP** after Phase 0/1. Owner approval required before Phase 2A–2E.
