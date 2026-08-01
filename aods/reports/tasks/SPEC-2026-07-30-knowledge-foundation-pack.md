# Task record — SPEC-2026-07-30-knowledge-foundation-pack

| Field | Value |
|-------|-------|
| **NODE_ID** | SPEC-2026-07-30-knowledge-foundation-pack |
| **ROLE** | Principal Data / Knowledge / IA / PIM Architect |
| **TASK_ID** | KB-001 (foundation prerequisite; IMPL not in scope) |
| **CHANGE_CLASS** | C2 (architecture specification) |
| **STATUS** | COMPLETE — four SPECs + pack README at `Proposed`; awaiting Board Accept (UD-06 / HC-01–HC-02 pattern) |
| **Date** | 2026-07-30 |
| **Base commit** | `2de8f39c4b43b56b8185aa181e915d16508f066f` (`main`) |

## Allow-list (this node)

- `docs/architecture/specs/**` (create)
- `docs/architecture/README.md` (index pointer only)
- `aods/registry/document-registry.yaml` (PROPOSED rows)
- `aods/reports/tasks/SPEC-2026-07-30-knowledge-foundation-pack.md` (this file)
- PMO mirrors for KB-001 progress/notes/`CHANGELOG.md`

## Forbidden (honored)

- No application code, Alembic, OpenAPI changes
- No Canon Lock Status→Accepted
- No MASTER_* documents
- No reads of quarantined hallucination sources (`frontend/AI_CONTEXT.md`, etc.)
- No dependency add/remove/upgrade
- No CONFLICT-REGISTER rewrites

## Outputs

1. `docs/architecture/specs/README.md` — Phase-1 analysis, decisions, dependency diagram, UD list, sequence
2. `docs/architecture/specs/SPEC-product-knowledge-entity-model.md`
3. `docs/architecture/specs/SPEC-industrial-taxonomy-model.md`
4. `docs/architecture/specs/SPEC-knowledge-graph-model.md`
5. `docs/architecture/specs/SPEC-product-import-enrichment-playbook.md`
6. Registry rows: `SPEC-PACK-README`, `SPEC-PKE-MODEL`, `SPEC-TAXONOMY-MODEL`, `SPEC-KG-MODEL`, `SPEC-IMPORT-PLAYBOOK`
7. PMO: KB-001 progress 20%; `KNOWLEDGE_BASE_PROGRESS.md`; `CHANGELOG.md`

## Conflicts surfaced (not silently resolved)

| ID | Handling |
|----|----------|
| CF-SPEC-01 | Taxonomy SPEC §1.3 — knowledge dimensions ≠ second commerce Category DAG |
| CF-SPEC-02 | Manufacturer ≠ Brand; UD-01 for migration of `brands` |
| CF-SPEC-03 | JSONB strangler; no dual-write ordered |
| CF-SPEC-04 | `specs/` interim vs reserved `domain/`/`pim/`/`knowledge-graph/` paths |
| CF-SPEC-05 | Prefer Accepted ADR-010 over stale Phase-1 CURRENT URL prose |

## Open questions for humans

See pack README UD-01…UD-08.

## Discovered but deliberately not fixed

- Phase-1 audit still says Brand Hub absent / id PDP — stale vs Wave-1 TARGET (left as HISTORICAL/PROPOSED evidence)
- `get_default_specifications()` measurement bias remains in code (out of scope)
- Soft `related_product_ids` not migrated (needs KB-001 IMPL after Accept)
- Missing historical ADR-001…009 packs not invented

## Verify

```bash
python3 aods/tools/aods_validate.py
```
