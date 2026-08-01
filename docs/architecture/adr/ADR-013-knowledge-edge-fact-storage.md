# ADR-013 — Knowledge Edge / Fact Storage (Postgres Overlay)

## Status
Accepted

### Board Acceptance (Knowledge Foundation Day 2)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۱۰ (2026-08-01) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | [`../../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md`](../../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md) |
| **Ballot** | UD-05 **A** |
| **Scope** | Wave-1 knowledge graph edges and governed Facts store as Postgres relational tables (overlay). No graph engine for KB-001. |

## Date
2026-08-01

## Deciders
Architecture Board (Mohammad Shebahati) · Platform Architect

## Context
Knowledge Graph SPECs (`SPEC-knowledge-graph-model.md`, `SPEC-knowledge-graph-registry.md`, `SPEC-domain-model.md`) define typed edges and Facts as a **logical overlay** on commerce SoR. Storage choice was Board-open as **UD-05**. Soft JSON arrays (`related_product_ids`, free-form accessories) remain transitional debt until projectors write typed edges.

**Problem:** Without a storage ADR, KB-001 IMPL cannot choose between pure Postgres tables vs introducing a graph engine.

## Decision Drivers
- Preserve commerce SoR (products / brands / categories / articles)
- Operability on existing Postgres stack
- Provenance and audit on edges/Facts
- KB-001 freeze scope (three projection edges only first)
- Must not weaken ADR-012

## Considered Options

### Option A — Postgres relational edge + fact tables only (Chosen)

Add overlay tables in the same database; query via SQL/ORM; no separate graph DB in wave-1.

**Pros:** Fits modular monolith; backup/restore with SoR; simplest ops.  
**Cons:** Multi-hop graph queries less convenient than a graph engine.  
**Risks:** Premature optimization pressure toward Neo4j/etc. — deferred by this ADR.

### Option B — Postgres now + optional graph engine later (explicit non-goal for KB-001)

Same as A for wave-1; document future hybrid as allowed only by a later Board ADR.

**Pros:** Leaves door open.  
**Cons:** Temptation to scope-creep KB-001.  
**Risks:** Agents cite “optional later” as permission to add engine now.

### Option C — Defer storage decision

**Pros:** None for delivery.  
**Cons:** Blocks DDL and KB-001.  
**Risks:** Spec-only forever.

## Decision
1. **Wave-1 MUST store knowledge edges and Facts in Postgres relational tables** in the primary application database (overlay — not a replacement for commerce SoR tables).
2. **KB-001 MUST NOT introduce a graph database / engine.** A future hybrid engine requires a **new** Board ADR; Option B’s “later” is **not** an implementation license.
3. Edge rows MUST be typed per Accepted `SPEC-knowledge-graph-registry.md` and carry provenance sufficient for audit (source, confidence/review state as defined in SPECs).
4. This ADR **MUST NOT** authorize dual-write from JSONB `technical_specs` into Facts — that remains a **separate Board gate**.
5. This ADR **MUST NOT** weaken ADR-012 (ingestion boundary) or ADR-010 (URL contract).
6. Schema changes still require normal Alembic PR + review; this ADR alone does **not** ship migrations.

## Consequences
### Positive
- Unblocks KB-001 edge table design citing Canon
- Keeps ops model unified

### Negative / residual
- Deep multi-hop analytics may need future Board revisit
- JSONB strangler continues until dual-write gate

## Related
- UD-05 · KB-001 scope freeze · `SPEC-knowledge-graph-model.md` · `SPEC-knowledge-graph-registry.md` · ADR-014
