# ADR-010 — SEO URL Contract

## Status
Accepted

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Binding SEO/URL contract for EPIC 1: singular `/product/{slug}`, 301 from id, Brand Hub `/brands/{slug}`; no Facts dependency. |

## Date
2026-07-29

## Deciders
Architecture Board (**Accepted** ۱۴۰۵/۰۵/۰۷ · Mohammad Shebahati) · SEO owner · Frontend lead · Catalog consult

## Context
CURRENT: PDP `/product/{numericId}`; slugs exist in DB unused. Category hubs `/categories/{slug}` exist. Brand hubs absent. SEO constitution target table lists plural `/products/{slug}` — conflicts with backlog/blueprint singular `/product/{slug}` (Canon C3). EPIC 0 recommends slug routing + brand hubs as highest ROI without Facts tables.

**Problem:** Without a binding URL contract, EPIC 1 fragments across plural/singular and filter-as-hub anti-patterns.

## Decision Drivers
- SEO permanence
- Redirect correctness
- EPIC 1 implementability without schema/Facts
- Consistency with ADR-002 (slug = public identity)
- Avoid thin duplicate URLs

## Considered Options
### Option A — Keep id URLs forever

No slug migration.

**Pros:** No redirect work.

**Cons:** Wastes slug data; weak semantics.

**Risks:** Long-term SEO debt.
### Option B — Plural `/products/{slug}` as canonical

Follow SEO constitution table literally.

**Pros:** Matches one stale doc.

**Cons:** Breaks continuity from `/product/{id}`; dual patterns.

**Risks:** Redirect matrix complexity.
### Option C — Singular `/product/{slug}` + hubs (Chosen)

Align backlog/blueprint; 301 from id; brand hubs new; categories stay.

**Pros:** Minimal path churn; EPIC1-ready.

**Cons:** Must supersede plural constitution row.

**Risks:** Slug collisions if governance weak.

## Decision
1. Canonical public product URL MUST be **`/product/{slug}`** (singular `product`).
2. Legacy **`/product/{id}`** MUST **301** to the canonical slug URL when slug routing ships.
3. The SEO constitution row listing **`/products/{slug}`** (plural) is **stale relative to backlog/blueprint** and is **superseded by this ADR** unless Architecture Board explicitly accepts plural later **and** documents redirects from `/product/{id}` and any singular/plural variants.
4. Brand hubs MUST use **`/brands/{slug}`** (TARGET; not present today). Launch sequencing SHOULD follow EPIC 0 priority brands: ASTPOWER, INSIZE, Dasqua, Chumpower, Mitutoyo, SAN OU (RFC-005).
5. Category hubs: CURRENT **`/categories/{slug}`** is affirmed; TARGET is **enhance-in-place** unless an RFC introduces a replacement class.
6. JSON-LD `@id` and breadcrumbs MUST align to canonical URLs after cutover.
7. This ADR **unblocks EPIC 1** and MUST NOT require Facts tables, Property dual-write, or Knowledge Graph runtime.
8. Unbounded indexable faceted URLs MUST NOT be treated as entity hubs.

## Rejected Alternatives
Rejected forever-id URLs (A). Rejected plural-as-default without Board exception (B).

## Consequences
### Positive
- Clear EPIC 1 contract
- Aligns ADR-002 slug identity
- Preserves existing category hub equity

### Negative / Trade-offs
- Implementation + sitemap/card updates required
- Constitution docs need banner/note of supersession

### Follow-up work required
- RFC-004 Slug Migration & Redirects
- RFC-005 Brand Hub Launch
- Prompt 4 IA url-map
- EPIC 1 implementation
- Prompt 11 PR checklist citations

## Compliance & Gates
Non-compliant: shipping slug PDP without 301 from id; inventing `/products/{slug}` as silent default; requiring Facts for URL work. Gate: none beyond normal PR review — intentionally EPIC1-ready.

## References
- `docs/architecture/karzar-knowledge-platform-master-architecture.md`
- `docs/roadmap/knowledge-platform-execution-backlog.md`
- `docs/constitution/seo-architecture-constitution.md`
- `docs/architecture/karzar-knowledge-platform-blueprint.md`
- `docs/audits/EPIC0-executive-summary.md`
- `docs/audits/catalog-baseline-completeness-report.md`

## Acceptance Self-Check
- [x] Decision is implementable without guessing
- [x] Alternatives recorded
- [x] No schema migration ordered by this ADR alone
- [x] No contradiction with ingestion policy
- [x] EPIC 0 facts not falsified
