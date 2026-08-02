# TASK-RECORD · KB-PT-00

| Field | Value |
|-------|-------|
| Task ID | KB-PT-00 |
| Title | Establish Canonical Product Type architecture contract |
| Change class | C5 — Governance-affecting |
| Role executed as | R-SYS-ARCH |
| Prompt | `aods/70-prompts/spec/SPEC-feature-contract.prompt.md` (allowlist expanded by owner-approved kickoff) |
| Base commit | `26d27946a63171900f32914f67161a6eb8a3d5b2` (`origin/main` = PR #192 Master KB merge) |
| Branch | `docs/kb-pt-00-canonical-product-type-contract` |
| Attempts | 1 |
| Outcome | COMPLETE — Proposed contract ready for owner review; no runtime implementation |

## Task metadata

- **Priority:** P0
- **Dependency:** KB-REMEDIATION-00C (Master KB architecture contract on main)
- **Status:** done / progress 100 (artifacts complete; **owner review remains required**; Board Accept not claimed)
- **Non-goals honored:** no DB models, Alembic, runtime backend/frontend/tests, seeding, assignment, JSONB migration, dual-write, commit/push/merge/deploy/PR, Board Accept claim

## Owner architecture direction (recorded, not Board-Accepted)

- Category = commerce/navigation only
- Product Type = first-class engineering classification SoT
- Category MUST NOT remain permanent Product Type substitute
- Specification applicability/validation ultimately from Product Type Definition
- Product Type is aggregate root + bounded profiles (not God Object; not label-only)
- `products.id` remains PKE identity; Product Type classifies
- Legacy JSONB stays until separate approved cutover; no bulk conversion; no dual-write
- No graph DB; PostgreSQL SoR

## Repository inputs read

| Input | Use |
|-------|-----|
| `docs/architecture/karzar-knowledge-platform-master-architecture.md` | Category ≠ Tool Class; dual-write gates |
| ADR-013 / ADR-014 | Postgres overlay; PKE = `products.id` |
| `SPEC-master-knowledge-base-remediation.md` | Sequencing amend target (was v0.3.0) |
| SPEC KG model/registry, PKE, Property Dictionary, Industrial Taxonomy | Classification / Facts / dual-write / taxonomy norms |
| `CANON-LOCK.md`, `docs/ARCHITECTURE.md` | Canon status; layering |
| `app/db/models/product.py`, `spec_template_service.py`, alembic history | As-built Category template proxy; no ProductType |
| Admin/Storefront spec forms & PLP filters | Category-template + JSONB dependency |
| `aods/registry/document-registry.yaml`, PMO `tasks.json`, ADR numbering | Conventions |
| External evidence | Owner-provided INSIZE/DASQUA summaries (not repository facts) |

## External evidence summary (owner-provided; not repo facts)

- INSIZE separates Calipers / Depth / Height; Digital/Dial/Vernier are readout technologies; many variants are attributes/profiles; resolution ≠ accuracy (1108 examples).
- DASQUA distinguishes readout commercially; engineering function includes general-purpose, depth, groove, disk-brake, specialty — orthogonal to readout.

## As-built findings

| Finding | Status | Cite |
|---------|--------|------|
| `products.product_type` / ProductType | **Absent** | `app/` / `alembic/` zero matches |
| `products.category_id` required FK | Present | `product.py` |
| Spec templates | Category `spec_template_key` + in-code registry | `spec_template_service.py` |
| Property Dictionary / Facts / taxonomy tables | Absent | models/alembic |
| `products.specifications` JSONB | Present operational SoT | `product.py` |
| Knowledge overlay | `knowledge_edges` only (KB-001 freeze) | ADR-013 as-built |
| PLP filters | Category template + JSONB paths | catalog endpoints / jsonb_filters |
| Product comparison feature | Absent | Storefront |

## Decisions made

1. **Hybrid architecture (ADR-015 Option D):** first-class Product Type + nullable `products.product_type_id` + taxonomy participation; secondary CLASSIFIED_AS retained.
2. Reject Category-as-proxy (A) and taxonomy-only primary (B) for Wave-1 primary classification.
3. Readout = orthogonal controlled profile (`digital`/`dial`/`vernier`).
4. Initial Calipers Product Type seed (6 types) marked non-exhaustive.
5. Attribute membership requiredness: required/optional/conditional/forbidden.
6. Definition lifecycle: draft/active/retired; integer versions Wave 1.
7. Category↔Product Type mapping deferred for Wave 1; never owns assignment.
8. FK delete: restrictive + lifecycle retirement.
9. Legacy JSONB Phases 0–3; no dual-write; no bulk migration.
10. Master KB **v0.3.0 → v0.4.0** with preserved decision log + §12.1 Prompt 11 gate.
11. Next free ADR = **ADR-015** (011 reserved; do not reuse).

## Alternatives rejected

| Option | Reason |
|--------|--------|
| A Category proxy | Contradicts Canon separation + owner direction |
| B Taxonomy-only primary | Insufficient deterministic Wave-1 product FK/validation |
| C FK-only without taxonomy | Incomplete vs Accepted multi-dim taxonomy |

## Exact files changed

1. `docs/architecture/specs/SPEC-canonical-product-type-model.md` — **created**
2. `docs/architecture/adr/ADR-015-product-type-engineering-classification.md` — **created**
3. `docs/architecture/adr/README.md` — index ADR-015 Proposed
4. `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` — **v0.4.0** amendment
5. `aods/reports/tasks/KB-PT-00-CANONICAL-PRODUCT-TYPE-CONTRACT.md` — this record
6. `aods/registry/document-registry.yaml` — register SPEC + ADR-015; fix Master KB `on_main: true`
7. `project-management/exports/tasks.json` — add KB-PT-00 done/100
8. `project-management/CHANGELOG.md`
9. `project-management/DONE.md`
10. `project-management/KANBAN_BOARD.md`
11. `project-management/progress/KNOWLEDGE_BASE_PROGRESS.md`

## ADR number chosen and why

**ADR-015** — next free in-repo ADR after 010/012/013/014. ADR-011 remains reserved historical and was not reused.

## Master KB version change

**0.3.0 → 0.4.0** — Product Type architecture amendment + Prompt 11–13 gate; prior 00/00A/00B/00C history preserved in §0.4 decision log and prior task reports.

## Prompt sequencing amendment

- Prompts 01–10 may proceed when independent of Product Type; must not introduce Category-owned permanent future templates.
- Prompts 11–13 blocked until Canonical Product Type SPEC owner-reviewed, ADR-015 reviewed, and Product Type runtime + Definition ownership approved.
- Insertion waves: KB-PT-01+ / PT-W1…PT-W4 before Prompt 11. Prompt pack **not** renumbered.

## Migration waves

PT-W0 (this task) → PT-W1 nullable FK → PT-W2 Definition/membership → PT-W3 assignment/ambiguity → PT-W4 read-only JSONB validation → PT-W5 Property/Facts/Evidence → PT-W6 pilot → PT-W7 optional cutover.

## Non-negotiables preserved

- `products.id` PKE identity (ADR-014)
- No graph DB (ADR-013)
- No dual-write / no bulk JSONB migration
- No Board Accept claim
- No runtime paths in this task
- Category remains single commerce tree (no second Category DAG)

## Open questions

1. Board clarification of Hybrid primary FK vs Accepted taxonomy CLASSIFIED_AS-centric wording
2. Wave-1 readout persistence shape (column vs profile association)
3. Specialty Caliper promotion criteria from pilot evidence
4. Knowledge Steward role vs super-admin for Definition activation

## Validation commands

| Command | Exit | Checked | Result |
|---------|------|---------|--------|
| `git diff --check` | 0 | — | PASS |
| `git diff --name-only` (+ untracked) | 0 | 11 paths | PASS — allowlist only |
| `python3 aods/tools/aods_validate.py --gate links` | 0 | 249 | PASS |
| `python3 aods/tools/aods_validate.py --gate registry` | 0 | 249 | PASS |
| `python3 aods/tools/aods_validate.py --gate pmo` | 0 | 33 | PASS |
| `python3 aods/tools/aods_validate.py --gate naming` | 0 | 1042 | PASS |
| ADR/document lint (`--gate docs`) | — | — | **SKIP** — gate does not exist in `aods_validate.py --list-gates` |

### Targeted content greps (PASS)

- Proposed status present on SPEC, ADR-015, Master KB
- Board acceptance not granted / `not_granted`
- `products.id` remains PKE identity
- Product Type is **not** Category
- `product_type_id` initially nullable
- no dual-write / no bulk JSONB migration
- Prompt 11 / §12.1 gate present in Master KB
- required/optional/conditional/forbidden
- accuracy and resolution distinct

### Skipped gates

- ADR-specific lint / `--gate docs` — not available (SKIP, not claimed as pass)
- Dependency installs for unrelated gates — not performed

## Mirror limitation

GENERATED CSV/printable PMO exports were **not** hand-edited (no official in-repo generator) — same limitation documented under KB-REMEDIATION-00C.

## Remaining blockers (updated by KB-PT-00A)

- Owner review of SPEC v0.1.1 + ADR-015 (required for Prompt 11A gate items)
- **Architecture Board Hybrid clarification minute** — **mandatory** before KB-PT-01 (owner direction insufficient to supersede Accepted Canon)
- Human commit / PR / merge of this branch (agent MUST NOT push/merge)
- KB-PT-01 runtime **governance-blocked** until Board minute exists

## Human next steps (updated by KB-PT-00A)

1. Owner-review SPEC-canonical-product-type-model v0.1.1 + ADR-015
2. Architecture Board minute clarifying Hybrid primary FK vs secondary `PRODUCT_CLASSIFIED_AS` (see ADR-015 required statements)
3. Commit and open PR when ready (human)
4. Only after Board minute + merge: **KB-PT-01** (PT-W1 core + nullable FK only)
5. Then Prompt **11A** (definitions/aliases/units only) → PT-W2 → Prompts 12–13

## Rollback

Docs-only: discard branch or supersede Proposed docs. No schema/runtime to roll back.

---

## Final owner-review corrections (KB-PT-00A)

Appended 2026-08-02. Does not rewrite the historical KB-PT-00 body above. Detail: `aods/reports/tasks/KB-PT-00A-OWNER-REVIEW-CORRECTIONS.md`.

| # | Correction applied |
|---|--------------------|
| 1 | Sequencing: Prompt **11A** (Property Definitions + aliases + Units) **before** PT-W2 Attribute Membership |
| 2 | Prompt 11A MUST NOT create `knowledge_spec_templates` / `knowledge_template_properties` |
| 3 | Prompt 12/13 blocked until PT-W2 Definition/membership ownership implemented and approved |
| 4 | Board clarification **mandatory** before KB-PT-01; owner direction alone cannot supersede Accepted Canon |
| 5 | Hierarchy examples non-duplicative: Domain=Dimensional Metrology; Tool Family=Sliding Measuring Instruments; Product Family=Calipers; Type=General-purpose Caliper |
| 6 | PT-W1: **no** readout persistence; vocabulary concept retained for PT-W2+ |
| 7 | PT-W1: **no** Product Type catalogue seed; Specialty inactive until pilot; **no** assignment backfill |
| 8 | Minimum PT-W1 runtime contract recorded; PK SQL type deferred to KB-PT-01 inspection |
| 9 | Taxonomy linkage deferred to Prompt 13; PT-W1 creates no taxonomy nodes |
| 10 | Early-wave admin = existing super-admin pattern until Steward ADR |
| Versions | SPEC **0.1.0 → 0.1.1**; Master KB **0.4.0 → 0.4.1**; ADR-015 remains **Proposed** |
