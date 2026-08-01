# ADR-014 — Product Knowledge Entity Identity (Wave-1)

## Status
Accepted

### Board Acceptance (Knowledge Foundation Day 2)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۱۰ (2026-08-01) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | [`../../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md`](../../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md) |
| **Ballot** | UD-02 **A** |
| **Scope** | Wave-1 Product Knowledge Entity (PKE) stable link identity = commerce `products.id` (1:1). |

## Date
2026-08-01

## Deciders
Architecture Board (Mohammad Shebahati) · Domain / PIM Architect

## Context
`SPEC-product-knowledge-entity-model.md` separates **Commerce Product** (SKU offer) from **Product Knowledge Entity** (meaning). Identity scheme was Board-open as **UD-02**. Bible principle: identity before intelligence.

**Problem:** Implementing overlay tables/APIs without a stable PKE key causes fork risk (UUID now vs reuse product id later).

**Non-claim:** This ADR does **not** invent or Accept reserved historical `ADR-002` text (not in this repository). It is a **new in-repo** wave-1 decision.

## Decision Drivers
- 1:1 SKU↔meaning is true for current catalog reality
- Minimize migration cost for KB-001
- Keep commerce SoR authoritative for sellable identity
- Allow future 1:N (packs / multi-SKU families) without lying today

## Considered Options

### Option A — PKE link = `products.id` (1:1) (Chosen for wave-1)

Knowledge overlay rows reference `products.id` as the stable join key for the sellable SKU’s knowledge entity.

**Pros:** Zero new identity namespace; matches as-built catalog; simplest projectors.  
**Cons:** Awkward if later one knowledge entity spans many SKUs.  
**Risks:** Treating `products.id` as ontological forever — mitigated by explicit revisit clause.

### Option B — New UUID `knowledge_entity_id` from day one

**Pros:** Cleaner future 1:N.  
**Cons:** Extra join everywhere; migration of soft links; premature for wave-1.  
**Risks:** Dual identifiers confuse enrichment scripts.

### Option C — Defer

Blocks KB-001 identity columns and edge endpoints.

## Decision
1. **Wave-1 MUST use `products.id` as the Product Knowledge Entity join key** (1:1 commerce SKU ↔ PKE projection).
2. Knowledge overlay tables/APIs that attach meaning to a sellable SKU **MUST** reference `products.id` (or a column proven to equal it), not invent a parallel public product id.
3. **1:N SKU packs / family entities** are **out of scope** for KB-001; introducing a separate `knowledge_entity_id` namespace requires a **future Board ADR** (or amendment minute), not silent schema drift.
4. Manufacturer ≠ Brand split (**UD-01**) remains **deferred** and MUST NOT be smuggled into identity work.
5. This ADR **MUST NOT** weaken ADR-010, ADR-012, or ADR-013.

## Consequences
### Positive
- Unblocks KB-001 edge rows keyed by product id
- Aligns article↔product soft links migration path

### Negative / residual
- Future pack/family modeling needs an explicit identity ADR later

## Related
- UD-02 · `SPEC-product-knowledge-entity-model.md` · `SPEC-domain-model.md` · ADR-013 · KB-001
