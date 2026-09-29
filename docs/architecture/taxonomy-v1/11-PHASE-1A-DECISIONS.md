# Phase 1A Decisions (D1–D15)

**Status:** Steward review **APPROVED WITH AMENDMENTS** (2026-09-27)  
**Date:** 2026-09-27  
**Owner decision:** `13-STEWARD-DECISION-TX-OWNER-001.md` (`TX-OWNER-001`)  
**Note:** Accepted architecture SPECs/ADRs are **not** edited in place; amendments below remain Proposed for Board formalization.

---

## D1. What exactly is a Product Type?

**Answer:** The engineering class answering “what fundamentally IS this product?”, owning a versioned Property Definition schema, with at most one primary assignment per product.

**Evidence:** ADR-015; ETIM Product Class principle; Constitution §1.4  
**Class:** KARZAR-GOVERNANCE-DECISION + STANDARD-BACKED (structural)

---

## D2. Digital vs Vernier Caliper?

**Answer:** **Property** (`readout_type` / `display_type`) — **not** Product Type.  
**Exception:** none by default.

**Evidence:** ADR-015 Decision 7; live `GEN_CALIPER` Definition; PBT-1  
**Class:** KARZAR-GOVERNANCE-DECISION

---

## D3. Carbide vs HSS Drill?

**Answer:** **Property** (`cutting_material` / substrate) under Product Type **Twist Drill** (or appropriate drill PT).  
Master seed `type.drill.carbide|hss` is outdated.

**Class:** ENGINEERING-INFERENCE + ETIM-INSPIRED

---

## D4. BT vs HSK?

**Answer:** **Interface Property** (`taper_interface`) + Compatibility/size — **not** Product Type by themselves.  
Product Types are holding principles (ER Collet Chuck, Hydraulic Chuck, Shrink Fit, Arbor, …).  
Master seed `type.holder.bt|hsk` rejected as Types.

**Class:** ENGINEERING-INFERENCE

---

## D5. U-Drill 2D/3D/4D/5D separate types?

**Answer:** **No.** Same Product Type **Indexable Drill (U-Drill)**; L/D is **Property**.  
Commerce leaves MAY remain short-term (`KEEP_AS_CATEGORY` / prefer facet later).

**Class:** ENGINEERING-INFERENCE

---

## D6. When does geometry justify a new Product Type?

**Answer:** When geometry changes **working principle or engagement identity** and breaks a shared required schema (e.g. Square vs Ball Nose End Mill; Blade vs General Caliper).  
Mere size/tolerance/corner radius usually Property.  
Syntactic `property=value` alone does **not** force SAME_PRODUCT_TYPE — see PTST-1 “merely” guard.

**Class:** ENGINEERING-INFERENCE + OEM-BACKED

---

## D7. When does application justify a new Product Type?

**Answer:** Rarely. Application is secondary.  
**Exception:** When “application” is actually the product’s engineering function with distinct standards/schemas (Turning Insert vs Milling Insert).

**Class:** ISO-ALIGNED + KARZAR-GOVERNANCE-DECISION

---

## D8. Is Knowledge Category necessary?

**Answer:** **No — not mandatory.** **STEWARD-APPROVED** (2026-09-27). Gate 7 = **APPROVED**.

### STEWARD-APPROVED AMENDMENT (Accepted SPEC-industrial-taxonomy-model — formal Board edit pending)

```text
Knowledge Category is NOT a mandatory hierarchy level.

Target scientific hierarchy:
Domain
→ Family
→ optional nested Family
→ Product Type

Domain → Family → Knowledge Category → Product Type
must NOT be required.

Knowledge Category MAY remain available as an optional organizational
concept if a future use case genuinely requires it.
```

Do not alter runtime schema in Phase 1A. Do not mark Accepted SPECs amended in place yet.

---

## D9. What may Technical Classification contain?

**Answer:** Only reusable engineering groupings **not reducible** to a single `property=value` without losing structure.  
Default: Prefer Property.  
Forbidden: dumping material/interface/readout that are simple Properties.

### PROPOSED AMENDMENT

Clarify SPEC §3.5 examples so material/interface are **Property-first**, with Technical Class as optional overlay.

---

## D10. Immutable identifier model?

**Answer:** **Hybrid Wave 1** — internal DB surrogate (`id`) + immutable published code (`KZ.*` / grandfathered `GEN_CALIPER`).  
Labels/slugs/paths are not identity.  
Commerce requires `categories.code` / `KZ.CAT.*` (**SCHEMA_EXTENSION_REQUIRED** — later; not a Phase 1B blocker for design).

**Steward sequencing (Gate 8 = APPROVED FOR THIS SEQUENCING):**

```text
Phase 1B design KZ.CAT.* for live target categories
→ Freeze Current → Target mapping manifest
→ Later schema: categories.code nullable + UNIQUE
→ Backfill → validate → make mandatory for active
→ Importers: semantic code → runtime DB id
→ CI forbids new bare numeric category semantic dependencies
```

Opaque UUID/ULID is a **future optional** enhancement — **not** required before Phase 1B or initial Commerce migration.

---

## D11. Commerce Category vs Product Type?

**Answer:** Commerce = buyer navigation/SEO projection; Product Type = engineering truth.  
Commerce MAY project Property distinctions without creating Types (CCT-1).

---

## D12. HELICOIL terminology?

**Answer:** **Unchanged.**

```text
Preferred EN: Wire Thread Insert (Thread Repair Insert)
Preferred FA: اینسرت رزوه‌ای سیمی / فنر رزوه‌ای (steward pick one FA preferred)
Synonyms: هلی‌کویل, Helicoil, HELICOIL (trade)
Brand association: Böllhoff (when applicable)
```

HELICOIL is not the generic scientific concept. Components (spring / tap / kit) are related Types + relationships — not Domains.

---

## D13. Relationship to ECLASS / ETIM / ISO 13399?

**Answer:**

- ECLASS 16.0: **ECLASS-INSPIRED** (structure only; no licensed bulk data)
- ETIM: **ETIM-INSPIRED**
- ISO 13399: **ISO-ALIGNED** for cutting-tool semantics — **not** ISO-COMPLIANT

Crosswalk relations default to `CANDIDATE` until verified.

---

## D14. Which current Product Types are constitutionally questionable?

From `07-EXISTING-PRODUCT-TYPE-REVIEW.csv` (37 types):

| Class | Codes |
|-------|-------|
| CONSTITUTIONALLY_SOUND | 24 including GEN_CALIPER, micrometers, indicators, thread gauges, V_BLOCK, … |
| LIKELY_OVER_SPLIT | `DIGITAL_LEVEL` (vs `LEVEL`) |
| NAMING_ONLY_ISSUE | `INDICATING_CALIPER` |
| NEEDS_DOMAIN_REVIEW | 11 including feeler set/stock, several specialty calipers, shaft/thickness/taper gauges |
| LIKELY_UNDER_SPLIT | none flagged in current metrology-only set |

No production reassignment in 1A.

---

## D15. Is current Proposed Master Seed still valid?

**Answer:** **No as-is.** Requires amendment (see `08-MASTER-SEED-REVIEW.md`) before any load.  
Any Workshop / Hand Tools Domain proposal is **REJECTED** (`TX-OWNER-001`). Concepts mapping solely to that scope → `OUT_OF_SCOPE`.

---

## D16. Owner scope — Workshop / Hand Tools (`TX-OWNER-001`)

**Answer:** **REJECTED — OWNER SCOPE DECISION.**

```text
Workshop & Hand Tools is outside Karzar target scope.
No target Domain or Commerce L1.
No replacement catch-all (General Tools / Workshop Tools / Miscellaneous / سایر / …).
Scoped categories → DEPRECATE/REMOVE candidates.
Products genuinely in scope → CATALOG_EXIT.
Rehome forbidden by default.
Accessories under broad parents must be decomposed by product meaning — not mass-deleted.
```

**Approved by:** Owner / Taxonomy Steward · **Date:** 2026-09-27  
**APPLY:** Forbidden in Phase 1A.1 — Phase 1B manifests first; later deletion needs explicit APPLY authorization.

---

## Target Domains after Owner decision (Phase 1B)

1. Metrology & Inspection — اندازه‌گیری و بازرسی  
2. Cutting Tools — ابزارهای برشی  
3. Toolholding — ابزارگیر  
4. Workholding & Fixturing — گیرش قطعه و فیکسچر  
5. Industrial Machines & Equipment — ماشین‌آلات و تجهیزات صنعتی  
6. Thread Repair & Thread Inserts — تعمیر رزوه و اینسرت‌های رزوه  
7. Metalworking Fluids & Lubricants — سیالات فلزکاری و روانکارها  

---

## Proposed amendments to Accepted documents

| Target | Amendment | Steward status |
|--------|-----------|----------------|
| SPEC-industrial-taxonomy-model | Knowledge Category not mandatory; Technical Class Property-first clarification | Steward-approved for KC; Board formalization pending |
| SPEC-industrial-taxonomy-master-seed | Rewrite caliper/drill/holder type rows; mark Workshop/Hand/`dom.power` OUT_OF_SCOPE | Proposed doc — edit after Board |
| None applied in-place in Phase 1A / 1A.1 | Record only | — |

---

## Governance freeze

Roles, change gate, versioning, deprecation: Constitution §5–§7 and identity contract.  
CI rules: design-only list in Constitution / naming contract — **not implemented** in 1A.
