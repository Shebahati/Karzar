# PROMPT 130 RESULT — Formalize RESOLVED_EQUIVALENT_FACTS Governance

**STATUS:** READY_FOR_POLICY_MERGE  
**DATE:** 2026-09-26  
**MODE:** Governance / repository change only — **no** Live catalog or KB mutation  
**Branch:** `docs/kb-equivalent-facts-governance`  
**Base:** `origin/main` @ `76ef7b254396e4c742c634d4c81837d5eacaa4f8`

## POLICY DECISION

Formalize durable governance policy:

**RESOLVED_EQUIVALENT_FACTS**

Canonical document:

[`docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md`](../../docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md)

| Topic | Decision |
|-------|----------|
| Identity states | RESOLVED_EXACT · RESOLVED_EQUIVALENT_FACTS · HOLD_MULTIPLE_FACT_SETS · HOLD_PRODUCT_TYPE_AMBIGUITY · SOURCE_CONFLICT (vocabulary only; no DB enum) |
| Eligibility | A–F all required (bounded candidates, positive narrowing, same PT, same required Facts, same evidence semantics, no conflict) |
| Definition-version dependency | Equivalence is valid only for the Definition version used at ingestion; re-evaluate on required-membership change |
| Optional-property rule | Suffix-sensitive optionals (e.g. wireless/data_output) MUST NOT be asserted while suffix unresolved |
| Locator rule | Keep required keys; for equivalent-facts use `model=<base>[A\|AWL]`, `model_candidates=<fullA>\|<fullAWL>`, `identity_state=RESOLVED_EQUIVALENT_FACTS` — never `model=<unproven single suffix>` |
| Supersedes | Prompt 126 note to “prefer locator model=\*A” for equivalent cases |

## PILOT (do not ingest in this prompt)

| Field | Value |
|-------|--------|
| SKU | **1183-150** |
| Product ID | **1834** |
| Residual OEM | 1183-150A \| 1183-150AWL |
| Product Type | POINT_CALIPER (already live; Def V1 triad) |
| Required facts equivalent | YES — 0–150 / 0.01 / ±0.03 (OEM pdf72/printed64) |
| Optional excluded | wireless / data-output |
| Policy eligible | **YES** |
| Ingested here | **NO** |

Reconfirmed against Prompt 126 matrix + OEM page semantics: catalogue lists only A/AWL for this size; triad identical; exact suffix unresolved.

## COHORT REVIEW (13 equivalent-facts products)

Source: Prompt 126 product-level classifications, re-checked against `SKU_IDENTITY_MATRIX.csv` evidence columns (not label-only).

| Result | Count |
|--------|------:|
| Reviewed | **13** |
| POLICY_ELIGIBLE | **13** |
| Returned to HOLD | **0** |

| product_id | SKU | Proposed PT | Residual | Eligible |
|-----------:|-----|-------------|----------|----------|
| 1795 | 1120-150 | INTERNAL_GROOVE_CALIPER | A\|AWL | POLICY_ELIGIBLE |
| 1796 | 1120-200 | INTERNAL_GROOVE_CALIPER | A\|AWL | POLICY_ELIGIBLE |
| 1797 | 1120-300 | INTERNAL_GROOVE_CALIPER | A\|AWL | POLICY_ELIGIBLE |
| 1799 | 1121-150 | INTERNAL_POINT_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1835 | 1185-150 | EXTERNAL_GROOVE_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1839 | 1187-150 | EXTERNAL_GROOVE_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1801 | 1123-150 | INSIDE_KNIFE_EDGE_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1827 | 1161-150 | TUBE_THICKNESS_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1834 | 1183-150 | POINT_CALIPER | A\|AWL | POLICY_ELIGIBLE (**pilot**) |
| 1836 | 1186-150 | OFFSET_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1837 | 1186-200 | OFFSET_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1838 | 1186-300 | OFFSET_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |
| 1840 | 1188-150 | BLADE_CALIPER | A\|AWL | POLICY_ELIGIBLE (PT pending) |

Full row detail: [`EQUIVALENT_FACTS_POLICY_COMPLIANCE_MATRIX.csv`](./EQUIVALENT_FACTS_POLICY_COMPLIANCE_MATRIX.csv).

Narrowing quality varies (image/geometry vs catalogue-only A/AWL enumeration) but all 13 meet A–F under this policy. None were returned to HOLD.

## ARCHITECTURE

| Question | Answer |
|----------|--------|
| Persistent identity table required? | **NO** (not yet) |
| Reason | Current scale is tens of specialty SKUs; recoverability via policy + audit matrix + Wave `change_reason` + Evidence locator convention + Definition pinning on Facts/Waves is sufficient |
| Future persistence trigger | Hundreds/thousands scale; Definition remaps not reconstructable from audit/Wave history; need machine-enforceable identity state in CI/API |

Verdict path: documentation/audit based — **not** IDENTITY_ARCHITECTURE_REQUIRED.

## FILES CHANGED

| Path | Role |
|------|------|
| `docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md` | Canonical POLICY |
| `audit/insize-phase12/PROMPT_130_RESULT.md` | This result (EVIDENCE) |
| `audit/insize-phase12/EQUIVALENT_FACTS_POLICY_COMPLIANCE_MATRIX.csv` | 13-product matrix |
| `audit/insize-phase8/PROMPT_126_RESULT.md` | Identity audit authority (commit for recoverability) |
| `audit/insize-phase8/SKU_IDENTITY_MATRIX.csv` | Candidate/exclusion evidence |
| `audit/insize-phase8/SUFFIX_SEMANTICS.md` | Family-local suffix semantics |
| `audit/insize-phase8/READY_SPECIALTY_PRODUCTS.csv` | Exact-ready companion from Prompt 126 |
| `aods/registry/document-registry.yaml` | Register new markdown |

Runtime code / Alembic / OpenAPI: **unchanged**.

## VALIDATION

| Gate | Result |
|------|--------|
| AODS full (registry / links / naming / ingestion-boundary) | **PASS** |
| OpenAPI | SKIP locally (fastapi not installed in this shell; unchanged surface — no API edit) |
| Ingestion-boundary (standalone) | **PASS** |

## SAFETY

| Check | Result |
|-------|--------|
| Live DB writes | NONE |
| Product writes | NONE |
| Fact / Evidence writes | NONE |
| Wave mutations | NONE |
| JSONB writes | NONE |
| Deploy | NO |
| Migration | NO |
| 1183-150 ingested | NO |
| Specialty Wave created | NO |

## VERDICT

**READY_FOR_POLICY_MERGE**

STOP. Do not merge in-agent unless human orders. Do not ingest 1183-150. Do not create specialty Waves.
