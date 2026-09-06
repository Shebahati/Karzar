# Task record — AUD-KNOWLEDGE-FOUNDATION-001

| Field | Value |
|-------|-------|
| NODE_ID | AUD-KNOWLEDGE-FOUNDATION-001 |
| Archetype | AUD |
| Prompt | `aods/70-prompts/audit/AUD-repository-scan.prompt.md` |
| Date | 2026-07-30 |
| TASK_ID | NONE — CR-008 risk (knowledge foundation spans KB-001 + Canon/AODS + ingest; no dedicated PMO id) |
| Change class | C1 (evidence/report only) |
| Scope lock | Option A — Phases 1–7 as EVIDENCE inside audit report; no `MASTER_*` / `DOCUMENT_GOVERNANCE_MODEL.md` files created |
| Allowlist writes | `aods/reports/audits/AUD-KNOWLEDGE-FOUNDATION-001.md`, `aods/reports/tasks/AUD-KNOWLEDGE-FOUNDATION-001.md` |
| Decision ceiling | D0 |

## Inputs read

| Tier | Path | Depth |
|------|------|-------|
| T2 | `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` | SKIM (§1–3, catalog, governance) |
| T2 | `aods/registry/document-registry.yaml` | FULL parse (130 entries) |
| T1 | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` | FULL (§2–3 classes/ladder) |
| Scope | SCAN_SCOPE path set in audit report | Inventory commands + selective reads (Canon Lock, ingest policy, KNOWLEDGE-FLOW, Phase headers, product/content models, PMO) |

Forbidden-context exception: NO.

## Outputs

- Findings: `aods/reports/audits/AUD-KNOWLEDGE-FOUNDATION-001.md`
- This task record

## Validation notes

- Production/live DB product counts **not** queried (ADR-012) → Unknowns U1–U3; 5901 treated as claim.
- `aods_validate.py --gate links` and `--gate registry` run at VERIFY; paste in agent VERIFY block.
- Working tree had **pre-existing** dirty files under `project-management/` and prior `aods/reports/**` untracked artifacts; this node only **adds** the two AUD-KNOWLEDGE-FOUNDATION-001 paths.

## Status

COMPLETE (report-only; no subject files modified)
