# Board Minute — ADR-015 Hybrid Product Type Classification Clarification

**Document ID:** `BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION`  
**Document type:** Board minute / clarification evidence  
**Status:** **Accepted** (this *is* the minute)  
**Version:** 1.0.0  
**Meeting identifier:** `AB-ADR-015-2026-08-02`  
**Date (Gregorian):** 2026-08-02  
**Date (Jalali):** ۱۴۰۵/۰۵/۱۱ (۱۱ مرداد ۱۴۰۵)  
**Board:** Karzar Architecture Board  
**Attendees:** محمد شباهتی — Mohammad Shebahati (Project Owner and sole Architecture Board member)  
**Quorum:** Satisfied — the sole Architecture Board member was present and exercised the project’s architecture decision authority.  
**Signed:** محمد شباهتی — Mohammad Shebahati (Project Owner / Architecture Board)  
**Decision:** **Option A — Accept Hybrid clarification**  
**Conditions:** None beyond the normative constraints recorded in this minute  
**Task:** KB-PT-00B  
**Parents:** ADR-015 · SPEC-canonical-product-type-model v0.1.1 · KB-PT-00 / KB-PT-00A · SPEC-industrial-taxonomy-model (Accepted) · ADR-013 · ADR-014

---

## Decision

**Accept the Hybrid Product Type classification architecture (Option A).**

| Field | Value |
|-------|-------|
| **Decision ID** | `AB-ADR-015-2026-08-02` / ADR-015 Hybrid clarification |
| **Outcome** | **Accepted — Option A** |
| **Conditions** | None beyond the normative constraints in this minute |
| **Effective** | Upon merge of the acceptance commit to `main` |
| **Does not authorize** | Graph database; JSONB↔Facts dual-write; bulk legacy JSONB migration; automatic Category→Product Type assignment; Product Type assignment backfill; runtime schema without normal Alembic/PR process |

---

## Question presented

How should the Wave-1 primary Product Type relationship coexist with the Accepted multi-dimensional industrial taxonomy classification model centered on `PRODUCT_CLASSIFIED_AS`?

---

## Documents reviewed

| Document | Path |
|----------|------|
| ADR-015 Hybrid Product Type | `docs/architecture/adr/ADR-015-product-type-engineering-classification.md` |
| Canonical Product Type SPEC | `docs/architecture/specs/SPEC-canonical-product-type-model.md` |
| Master KB remediation SPEC | `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` |
| Industrial Taxonomy Model | `docs/architecture/specs/SPEC-industrial-taxonomy-model.md` |
| Product Knowledge Entity Model | `docs/architecture/specs/SPEC-product-knowledge-entity-model.md` |
| ADR-013 / ADR-014 | `docs/architecture/adr/` |
| Canon Lock | `docs/architecture/CANON-LOCK.md` |

---

## Ballot

| Item | Vote | Disposition |
|------|------|-------------|
| Hybrid clarification Option A | **A** | Accept |
| Option B (taxonomy-only) | Rejected | — |
| Option C (defer) | Rejected | — |
| Option D (accept with conditions) | Not selected | Conditions = none beyond normative constraints below |

---

## Normative clarification (binding)

1. For Wave 1, `products.product_type_id` is the **primary** nullable engineering Product Type classification and provides deterministic Product Type lookup, Product Type Definition resolution, and validation applicability.
2. `PRODUCT_CLASSIFIED_AS` remains the governed mechanism for **secondary**, multi-dimensional, and future taxonomy classifications.
3. The direct FK and taxonomy classifications **MUST** resolve to the same governed Product Type identity and **MUST NOT** create duplicate Product Type entities or independent competing sources of truth.
4. `products.id` remains the Product Knowledge Entity identity (ADR-014). Product Type does not replace Product identity.
5. Commerce Category remains independent and commerce-only. Category changes do not automatically change Product Type; Product Type changes do not automatically change Category.
6. PostgreSQL remains the system of record (ADR-013). No graph database is introduced by this decision.
7. No JSONB↔Facts dual-write is authorized.
8. No bulk migration of legacy JSONB specifications is authorized.
9. No automatic Category-to-Product-Type assignment and no Product Type assignment backfill are authorized by this decision.
10. The exact taxonomy bridge is deferred to Prompt 13 and **MUST** preserve these identity and ownership constraints.

---

## Compatibility

| Authority | Effect of this minute |
|-----------|------------------------|
| ADR-013 | Preserved — Postgres SoR; no graph DB; no dual-write authorization |
| ADR-014 | Preserved — PKE = `products.id` |
| Industrial Taxonomy | Clarified/amended narrowly — primary Product Type MAY be materialized as nullable Product FK; secondary classifications remain taxonomy assignments; no duplicate identities; Prompt 13 owns bridge schema |
| Category | Remains commerce-only |
| Canonical Product Type SPEC | Remains Proposed implementation contract governed by Accepted ADR-015 |

---

## Canon Lock instruction

In the **same commit** as status upgrades:

1. Add Board Acceptance block **ADR-015 Hybrid Product Type Clarification** to `docs/architecture/CANON-LOCK.md`.
2. Add Accepted row for ADR-015.
3. Update ADR-015 status to **Accepted** with Board Acceptance table citing this minute.
4. Apply the narrow Industrial Taxonomy amendment authorized above.
5. Amend Master KB §12.1 so **KB-PT-01 may start** after this minute merges.

---

## Implementation sequence unblocked

**KB-PT-01** — Product Type core table + nullable `products.product_type_id` — is the next allowed implementation wave after this minute is on `main`.

Still gated thereafter: Prompt 11A / PT-W2 / Prompts 12–13 per Master KB §12.1 and SPEC-canonical-product-type-model §15.

---

## Dissent / conditions

None. Conditions beyond the normative constraints above: **none**.

---

## Signatures

| Role | Name |
|------|------|
| Architecture Board / Project Owner | محمد شباهتی — Mohammad Shebahati |

---

## Evidence

- This file
- Human Board decision supplied in Cursor conversation for KB-PT-00B (2026-08-02)
- ADR-015 status flip + Canon Lock row + taxonomy narrow amendment + Master KB gate update in the acceptance commit
- Registry class/status updates for Accepted minute and ADR-015

---

*End of Board minute.*
