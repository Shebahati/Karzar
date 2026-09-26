# Product Identity Equivalence Policy — RESOLVED_EQUIVALENT_FACTS

**Document type:** Knowledge governance policy  
**Status:** Current (binding for Knowledge Wave identity classification after merge)  
**Date:** 2026-09-26  
**Owner:** Platform Architect (knowledge)  
**Companions:** ADR-012, ADR-013, ADR-014, [`data-ingestion-policy.md`](./data-ingestion-policy.md), Wave Evidence locator contract (`pdf_page`, `printed_page`, `model`, `property`)

**Non-claim:** This document does **not** Accept a new ADR, invent a DB enum, or authorize Live writes by itself. It defines when required Facts may be asserted under unresolved OEM suffix identity.

---

## 1. Purpose

Allow safe governed ingestion when the exact OEM variant/suffix for a sellable DB SKU cannot be proven, but after evidence-based elimination every remaining plausible OEM identity shares the same Product Type and the same required Fact values under the active Product Type Definition.

The policy name is **RESOLVED_EQUIVALENT_FACTS**.

It exists so operators can ingest metrology Facts without falsely claiming exact OEM model identity.

---

## 2. Scope

Applies to:

- Product Type assignment planning
- Knowledge Wave allowlists / execute payloads
- Evidence locators and Wave `change_reason` / audit narrative
- Identity classification in audit/planning artifacts

Does **not** apply to:

- Commerce SKU rewriting
- Price, stock, availability, images, or category mutations
- Optional / suffix-sensitive properties unless independently resolved
- Claiming exact OEM suffix without proof

---

## 3. Terminology (identity vocabulary)

Governance vocabulary only. **No database enum or schema** is introduced by this policy.

| State | Meaning |
|-------|---------|
| **RESOLVED_EXACT** | Exactly one OEM model code is proven for the DB product. Evidence supports that single code. Locator `model` is that exact OEM code. |
| **RESOLVED_EQUIVALENT_FACTS** | Exact OEM suffix/variant is **not** proven. After bounded enumeration and positive narrowing, every remaining plausible OEM identity shares Product Type + identical required Facts under the Definition version used for ingestion. |
| **HOLD_MULTIPLE_FACT_SETS** | Remaining plausible OEM identities disagree on one or more required Facts (or cannot be reduced to an equivalent set). |
| **HOLD_PRODUCT_TYPE_AMBIGUITY** | Remaining plausible identities do not share one Product Type, or Product Type cannot be chosen without guessing. |
| **SOURCE_CONFLICT** | Authoritative sources contradict in a way that blocks safe required-Fact assertion (or identity evidence is mutually incompatible). |

Related planning labels (e.g. `HOLD_MULTIPLE_FACT_SETS_EXCLUDED_VARIANT`) describe **excluded OEM rows**, not live DB products.

### Product identity provenance vs Fact provenance

| Concern | Question answered | Must not be conflated with |
|---------|-------------------|----------------------------|
| **Product identity provenance** | Which OEM commercial variant(s) could this DB SKU be? | Fact values |
| **Fact provenance** | Which OEM table cell supports this required value? | Exact suffix proof |

**Permitted identity claim (example):**  
“DB SKU `1183-150` corresponds to the A/AWL fact-equivalent OEM family; exact suffix unresolved.”

**Forbidden identity claim:**  
“DB product is definitely `1183-150A`.”

**Permitted Fact claim:** only values identical across all residual candidates for each required membership.

---

## 4. Eligibility criteria (ALL required)

A product may be classified **RESOLVED_EQUIVALENT_FACTS** only if **all** of the following are true:

### A. Candidate set bounded

All plausible OEM variants are explicitly enumerated from authoritative source material (e.g. OEM catalogue table for that family/size).

### B. Positive narrowing exists

Evidence rules out non-equivalent variants. Acceptable evidence includes geometry, image characteristics, dimensions, button/layout features, structured legacy fields used only as **narrowing signals** (not technical authority), and original source metadata.

**A bare base SKU string alone is insufficient.**

When the authoritative OEM table for that size lists only fact-equivalent codes (e.g. `*A` and `*AWL`) and no multi-fact competitors appear in source, enumeration from that table **is** positive narrowing of the candidate universe — provided the audit records that enumeration.

### C. Same Product Type

Every remaining plausible variant belongs to the same governed Product Type.

### D. Same required Fact set

For every **required** membership in the **active** Product Type Definition used for ingestion, all remaining variants yield the same canonical value / unit / qualifier.

### E. Same evidence semantics

OEM source rows support those required Facts without selecting one unresolved suffix as if it were proven.

### F. No conflict

No remaining plausible variant creates a different required Fact, different Product Type, incompatible evidence, or contradictory identity evidence.

If any condition fails → remain **HOLD** (`HOLD_MULTIPLE_FACT_SETS`, `HOLD_PRODUCT_TYPE_AMBIGUITY`, or `SOURCE_CONFLICT` as applicable).

---

## 5. Disqualifying conditions / prohibitions

Explicitly prohibit:

1. Choosing the “most likely” suffix
2. Silently normalizing the DB SKU to an OEM suffix
3. Recording an exact model suffix as proven when it is not
4. Asserting optional wireless / data-output (or other suffix-controlled) attributes from suffix inference
5. Using legacy JSONB as technical authority for Fact values (OEM remains authoritative; legacy may only help **exclude** variants)
6. Widening Evidence beyond what the source supports
7. Using equivalent-facts classification when required Facts differ across residual candidates
8. Using category or title alone to resolve identity
9. Encoding Evidence `model` as a single unresolved suffix (e.g. `model=1183-150A`) as if exact

---

## 6. Evidence hierarchy

1. **OEM catalogue / authoritative artifact** (e.g. INSIZE 108A) — Fact values and candidate enumeration  
2. **Product image / physical markings** — identity narrowing  
3. **Source dimensions / button metadata / import attributes** — narrowing only  
4. **Legacy `products.specifications` JSONB** — narrowing / conflict detection only; **never** Fact authority  
5. **Category / marketing title** — non-authority for identity or Facts

---

## 7. Evidence locator rules

Wave Evidence validation requires locator keys:

`pdf_page`, `printed_page`, `model`, `property`

(see `REQUIRED_LOCATOR_KEYS` in knowledge wave evidence validation). Additional JSON keys are allowed without schema change.

### RESOLVED_EXACT

```json
{
  "pdf_page": 71,
  "printed_page": 63,
  "model": "1169-150",
  "property": "measurement_range"
}
```

`model` MUST be the proven exact OEM code.

### RESOLVED_EQUIVALENT_FACTS

Do **not** set `model` to a single unproven suffix.

Canonical convention (no schema migration):

```json
{
  "pdf_page": 72,
  "printed_page": 64,
  "model": "1183-150[A|AWL]",
  "model_candidates": "1183-150A|1183-150AWL",
  "identity_state": "RESOLVED_EQUIVALENT_FACTS",
  "property": "measurement_range"
}
```

| Field | Rule |
|-------|------|
| `model` | Family form `<base>[cand1\|cand2\|…]` using OEM suffix tokens **or** an equivalent non-deceptive family string. Must not look like a proven single OEM code when suffix is unresolved. |
| `model_candidates` | Pipe-separated **full** OEM codes for the residual set (order stable, lexicographic preferred). |
| `identity_state` | Literal `RESOLVED_EQUIVALENT_FACTS`. |
| `pdf_page` / `printed_page` | Exact OEM page supporting the Fact table/row set. |
| `property` | The Fact property being evidenced. |

The locator must still point at the exact OEM page/table that supports the Fact. Equivalence is about identity honesty, not about loosening page precision.

---

## 8. Wave `change_reason` / audit requirement

Any Wave (or SKU unit) that includes RESOLVED_EQUIVALENT_FACTS products MUST include recoverable narrative covering:

1. Exact DB SKU (and `product_id`)
2. Unresolved residual OEM candidate set
3. Why non-equivalent variants were excluded (or that OEM lists only the residual set)
4. Confirmation that all residual variants share required Facts under the Definition version used
5. Reference to the identity audit artifact (path + date/prompt id)

Example fragment:

> DB SKU 1183-150 (id 1834): residual OEM 1183-150A|1183-150AWL; exact suffix unresolved; OEM 108A pdf72 lists only A/AWL with identical V1 triad 0–150 / 0.01 / ±0.03; wireless/data_output not asserted; identity audit `audit/insize-phase8/PROMPT_126_RESULT.md` / Prompt 130 matrix.

---

## 9. Optional-property rule

If suffix ambiguity affects an optional property, that property **MUST NOT** be asserted unless independently resolved.

Example: A vs AWL may differ in wireless / data-output. While exact suffix remains unresolved, do **not** assert `data_output` (or similar) from suffix inference.

Required V1 Facts may proceed **only** because they are equivalent across the residual set.

---

## 10. Product Type Definition version dependency

An equivalent-facts decision is valid **only** relative to the Product Type Definition version used during ingestion.

Example: POINT_CALIPER Definition V1 requires only `measurement_range`, `resolution`, `accuracy`. A/AWL may be equivalent under V1. If Definition V2 makes `data_output` required, the prior equivalence decision is **insufficient** until re-evaluated.

### Re-evaluation triggers

Re-classify (do not silently reuse an old equivalent-facts decision) when:

- Required memberships of the Product Type Definition change
- The candidate identity set changes
- New OEM evidence appears
- A previously optional suffix-sensitive property becomes required
- Image or other narrowing evidence newly excludes one residual candidate (may upgrade to RESOLVED_EXACT) or re-opens conflict

**RESOLVED_EQUIVALENT_FACTS is not permanent universal identity resolution.**

---

## 11. Examples

### Exact (not this policy)

DB `1169-150` ↔ OEM `1169-150` on DIGITAL SMALL POINT CALIPERS → **RESOLVED_EXACT** → `model=1169-150`.

### Equivalent Facts (this policy)

DB `1183-150` ↔ residual OEM `1183-150A` | `1183-150AWL`, POINT_CALIPER V1 triad identical → **RESOLVED_EQUIVALENT_FACTS** → locator family form + `model_candidates`; do not claim A.

### Hold

DB bare SKU where residual OEM set still includes Type B / `*1` with different range/accuracy and no positive exclusion → **HOLD_MULTIPLE_FACT_SETS**.

---

## 12. Current INSIZE pilot cohort (after this policy)

First approved pilot after policy merge (ingestion is a **separate** governed Wave prompt — not authorized by this document alone):

| Field | Value |
|-------|--------|
| DB SKU | `1183-150` |
| product_id | 1834 |
| Product Type | `POINT_CALIPER` (exists; Def V1 triad) |
| Identity state | RESOLVED_EQUIVALENT_FACTS |
| Residual OEM | `1183-150A`, `1183-150AWL` |
| Required V1 Facts | 0–150 mm · 0.01 mm · ±0.03 mm (identical) |
| Optional excluded | wireless / data-output (suffix-sensitive) |
| Identity audit | `audit/insize-phase8/PROMPT_126_RESULT.md`, Prompt 130 compliance matrix |

Full 13-product compliance review: `audit/insize-phase12/EQUIVALENT_FACTS_POLICY_COMPLIANCE_MATRIX.csv` and `audit/insize-phase12/PROMPT_130_RESULT.md`.

---

## 13. Architecture decision (persistence)

**Persistent DB identity-mapping table: NOT REQUIRED YET.**

Recoverability / reproducibility at current scale (tens of specialty products) is provided by:

1. This policy document  
2. Identity audit artifacts + compliance matrix  
3. Wave `change_reason` narrative  
4. Evidence locators using the equivalence convention above  
5. Definition-version pinning already present on Facts / Waves  

### Future trigger for persistence

Introduce an explicit persistence layer (e.g. `product_source_identity` / OEM-alias table) when **any** of:

- Cohort scale reaches hundreds/thousands with repeated re-evaluation needs
- Definition-version remapping cannot be reconstructed from audit + Wave history alone
- Operators repeatedly need machine-enforceable identity state checks in CI/API

Until then, documentation + Evidence + Wave audit is sufficient. Do not pretend a DB table exists.

---

## 14. Non-goals

- Ingesting any product by merging this document
- Creating Product Types, Waves, Facts, or Evidence
- Rewriting SKUs or inventing OEM aliases in commerce
- Schema / enum / migration for identity states
- Expanding Definition V1 required fields
- Treating Prompt 126 “prefer locator model=\*A” notes as still valid — **superseded** by §7 of this policy

---

## 15. Related

- ADR-014 — PKE join = `products.id` (commerce SKU identity ≠ OEM model proof)
- ADR-013 — Evidence / Fact storage
- ADR-012 / data-ingestion-policy — write boundaries
- Prompt 126 identity audit (phase8)
- Prompt 130 formalization result (phase12)
