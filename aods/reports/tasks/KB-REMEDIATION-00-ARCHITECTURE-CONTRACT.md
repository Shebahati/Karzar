# Task record — KB-REMEDIATION-00 — Architecture Contract

| Field | Value |
|-------|-------|
| **NODE_ID** | KB-REMEDIATION-00-ARCHITECTURE-CONTRACT |
| **Prompt** | Prompt 00 — Create the remediation architecture contract |
| **Date** | 2026-08-02 |
| **Change class** | Documentation / audit only (C2 docs) |
| **Status** | COMPLETE — **READY FOR OWNER REVIEW** (not Board-Accepted) |
| **Authority** | Proposed SPEC only; does not claim Board acceptance |

## Allowlist honored

| Path | Action |
|------|--------|
| `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` | **Created** |
| `aods/reports/tasks/KB-REMEDIATION-00-ARCHITECTURE-CONTRACT.md` | **Created** (this file) |

No production code, tests, migrations, frontend, Accepted ADRs, or seed files modified.

## Inputs read

| Path | Role |
|------|------|
| `docs/architecture/karzar-knowledge-platform-master-architecture.md` | Bible invariants (Postgres SoR, P5–P6 dual-write gate, modular contexts) |
| `docs/architecture/adr/ADR-013-knowledge-edge-fact-storage.md` | Postgres overlay; no graph DB; no dual-write auth |
| `docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md` | PKE = `products.id` |
| `docs/architecture/specs/SPEC-knowledge-graph-model.md` | Edge statuses, provenance, soft-link migration |
| `docs/architecture/specs/SPEC-knowledge-graph-registry.md` | Relation vocabulary + KB-001 freeze |
| `docs/architecture/specs/SPEC-product-knowledge-entity-model.md` | PKE vs commerce; Facts/content model |
| `docs/architecture/specs/SPEC-property-dictionary-system.md` | Property/Fact/units; dual-write gated |
| `docs/architecture/specs/SPEC-industrial-taxonomy-model.md` | Knowledge dimensions ≠ second Category DAG |
| `app/api/endpoints/knowledge.py` | As-built public edges + admin sync |
| `app/crud/knowledge.py` | As-built `asserted\|published` visibility |
| `app/db/models/knowledge.py` | Edge table shape |
| `app/schemas/knowledge.py` | Response/counter schemas |
| `app/services/knowledge_edge_projector.py` | Projection/publish defaults |
| `tests/test_knowledge_edges.py` | As-built expectations |
| `frontend/Storefront/.../product-knowledge-rail.tsx` | Local blog rail (not API) |
| `frontend/admin-panel/.../knowledge-edges-browser.tsx` | Admin read-only browser |
| `project-management/progress/KNOWLEDGE_BASE_PROGRESS.md` | KB-001 progress context |

## Files changed

1. `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` (new)
2. `aods/reports/tasks/KB-REMEDIATION-00-ARCHITECTURE-CONTRACT.md` (new)

## Decisions recorded in the SPEC (Proposed)

1. **Public vs admin boundary:** Raw `GET /knowledge/edges` becomes super-admin-only; public uses resolved PKE read-model only.
2. **Publication:** `asserted` internal-only; `published` public; `rejected`/`deprecated` never public; article public edges require published article + non-future `published_at` + public target product.
3. **Compat:** Neighborhood remains temporarily but published-only, provenance-stripped, deprecated toward `GET .../knowledge`.
4. **Projection:** Scoped HTTP inline limits; full sync via durable Postgres job rows + CLI worker (batches, retry, locking, checkpoints, idempotency).
5. **Counters:** `scanned` + `created`/`updated`/`unchanged`/`deprecated`/`invalid_references`/`failed` replace opaque `edges_upserted`.
6. **Provenance minimum:** projection run, first-seen, last-verified, source artifact/version, actor, review/publish metadata, change reason.
7. **No dual-write** of `products.specifications` until a separate approved migration/import task.
8. **Identity / storage:** Keep `products.id` PKE key; Postgres only; no graph DB.
9. **Implementation sequence:** Prompts **01–14** enumerated in SPEC §12.
10. **Document status:** Proposed — owner review required; **not** Board-Accepted.

## Migrations

None in this task. SPEC §11 defines the future M1–M8 sequence for later prompts.

## Test commands / results

### Command 1 — citation gate

```bash
python3 aods/tools/aods_validate.py --gate citation
```

**Actual output:**

```text
AODS validation — 1 gate(s), base=origin/main
  SKIP  citation             no --pr-body supplied

RESULT: PASS — 0 new findings, 0 baselined
```

**Exit code:** `0`  
**Note:** Gate is contextual; Prompt 00 supplied no `--pr-body`, so it skips and the overall result is PASS.

**Supplemental (not required by Prompt 00):** With `/tmp/kb-remediation-00-pr-body.md`, citation **FAIL**s (15 CR-001 path findings) because this workspace’s git toplevel is `/home/moahmmad/Projects` and `Karzar-main/` is entirely untracked (`??`), so `resolves_on_base` cannot see in-tree paths. `origin/main` is also missing as a revision. No repair in allowlist can fix remote/base tracking; recorded under discovered-but-not-fixed.

### Command 2 — docs gate → substituted `links`

```bash
python3 aods/tools/aods_validate.py --gate docs
```

**Actual output:**

```text
usage: aods_validate.py [-h] ...
aods_validate.py: error: unknown gate 'docs'; try --list-gates
```

**Exit code:** `2`  
**Substitution:** `--list-gates` shows known gates: `registry`, `links`, `pmo`, `prompts`, `graph`, `naming`, `citation`, `allowlist`, `openapi`, `ingestion-boundary`. Closest non-mutating docs-quality gate: **`links`**.

```bash
python3 aods/tools/aods_validate.py --gate links
```

**Actual output:**

```text
AODS validation — 1 gate(s), base=origin/main
  PASS  links                0 checked

RESULT: PASS — 0 new findings, 0 baselined
```

**Exit code:** `0`
## Risks

| Risk | Note |
|------|------|
| Breaking anonymous `/edges` consumers | Intentional security fix; no anonymous grace period |
| Neighborhood asserted-article behavior change | Storefront currently uses blog JSON, not neighborhood API — lower immediate FE risk; tests must be rewritten |
| Owner may reject Proposed publication gates | Article auto-asserted remains; only public exposure tightens |
| Job/worker design not yet coded | Counters/limits are contract-level; Prompt 05–07 may need minor numeric tuning |
| Prompt pack 01–14 bodies not yet in-repo | Sequence defined here; later prompts must align or amend this SPEC via owner review |

## Discovered-but-not-fixed

1. Unauthenticated `GET /api/v1/knowledge/edges` exposes full provenance (`recorder`, `source_*`) — deferred to Prompt 01.
2. Public neighborhood/CRUD treats `asserted` as visible — deferred to Prompt 02.
3. Sync upsert always counts updates as changed; no `unchanged`/`invalid_references`/`failed` — deferred to Prompt 07.
4. Full-catalog sync runs inline in HTTP request — deferred to Prompt 05–06.
5. Storefront knowledge rail ignores knowledge API — deferred to Prompt 09.
6. Admin browser lacks status filters, resolved labels, review actions, history — deferred to Prompt 10.
7. No runtime Facts / property dictionary / evidence / taxonomy assignment tables — deferred to Prompts 11–13.
8. `edges_upserted` alias compatibility vs hard cut — owner may shorten 30-day window.
9. Workspace git toplevel is `/home/moahmmad/Projects` with `Karzar-main/` untracked; AODS `--gate citation --pr-body …` cannot resolve paths on merge base until this tree is a proper git checkout with remotes — out of Prompt 00 allowlist.

## Conclusion

**READY FOR OWNER REVIEW** — not ACCEPTED. Operator should inspect `SPEC-master-knowledge-base-remediation.md` before running Prompt 01.
