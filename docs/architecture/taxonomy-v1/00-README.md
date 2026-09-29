# Karzar Taxonomy V1 — Phase 1A Design Pack

**Status:** Design (Proposed) — not Accepted Canon  
**Phase:** 1A — Scientific Taxonomy Constitution + Stable Identity Contract  
**Steward review:** **APPROVED WITH AMENDMENTS** (2026-09-27) — see `13-STEWARD-DECISION-TX-OWNER-001.md`  
**Date:** 2026-09-27  
**Safety:** READ-ONLY against Production; no catalog/taxonomy APPLY; no deploy  

This pack **defines the law** for future taxonomy work. It does **not** disposition all 138 live Commerce Categories (that is Phase 1B). Accepted SPECs/ADRs are **not** edited in place; Steward-approved amendments are recorded here as Proposed until Board formalization.

## Authoritative inputs

| Source | Role |
|--------|------|
| `SPEC-industrial-taxonomy-model.md` (Accepted) | Multi-dimensional taxonomy model |
| `ADR-015` (Accepted) | Product Type hybrid primary FK; readout orthogonality |
| `ADR-010` (Accepted) | SEO URL contract for `/categories/{slug}` |
| Phase 0B audit (`audit/taxonomy-phase0b/` on branch `cursor/taxonomy-phase0b-db-census-a062`) | Observational Production evidence only |
| Public ECLASS 16.0 / ETIM / ISO 13399 principles | Structural inspiration — **ISO-ALIGNED / INSPIRED**, not licensed bulk copy |

## Pack contents

| File | Purpose |
|------|---------|
| `01-TAXONOMY-CONSTITUTION-V1.md` | Normative entity definitions |
| `02-PRODUCT-TYPE-BOUNDARY-RULES.md` | PTST-1, PBT-1, case studies |
| `03-COMMERCE-CATEGORY-RULES.md` | CCT-1, merchandising constraints |
| `04-STABLE-IDENTITY-CONTRACT.md` | Immutable identity model |
| `05-NAMING-AND-SYNONYM-CONTRACT.md` | FA/EN/code/synonym/trade-name rules |
| `06-EXTERNAL-STANDARDS-ALIGNMENT.md` | ECLASS/ETIM/ISO 13399 posture + crosswalk |
| `07-EXISTING-PRODUCT-TYPE-REVIEW.csv` | Review of 37 live Product Types |
| `08-MASTER-SEED-REVIEW.md` | Critique of Proposed master seed |
| `09-REPRESENTATIVE-CATEGORY-TESTS.csv` | ~25 live Category analyses |
| `10-ARCHITECTURE-GAP-MATRIX.csv` | Support status per constitutional rule |
| `11-PHASE-1A-DECISIONS.md` | D1–D15 + proposed amendments |
| `12-PHASE-1B-ENTRY-GATE.md` | Gate before 138-category disposition |
| `13-STEWARD-DECISION-TX-OWNER-001.md` | Owner scope: Workshop/Hand Tools removed |
| `taxonomy-constitution-v1.yaml` | Machine-readable constitution |

## Non-goals (Phase 1A)

- No Production DB write, Category mutation, Product reassignment, PT mutation
- No Knowledge Taxonomy population, Alembic, SEO redirect change, import APPLY
- No exhaustive disposition of all 138 live Categories
- No modification of Accepted SPECs/ADRs in place (amendments recorded as **PROPOSED**)

## How to read

1. Start with `01-TAXONOMY-CONSTITUTION-V1.md` and `11-PHASE-1A-DECISIONS.md`.
2. Apply tests from `02` / `03` to any disputed concept.
3. Steward review of Phase 1A is **APPROVED WITH AMENDMENTS** — Phase 1B design drafting may begin when explicitly authorized; do **not** auto-start Phase 1B; do **not** Production APPLY.
