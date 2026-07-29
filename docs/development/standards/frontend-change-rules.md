# Frontend Change Rules

**Status:** Proposed · Storefront / SEO

---

## URL & SEO (EPIC 1)

- Canonical PDP: **`/product/{slug}`** (singular) — Canon C3 / ADR-010 / RFC-004.  
- 301 from `/product/{id}`; do not adopt plural `/products/{slug}` as TARGET.  
- Brand hubs: **`/brands/{slug}`** (RFC-005) when shipping hubs.  
- Prefer **as-built storefront** over stale IA constitution on conflicts (Canon C4).  
- JSON-LD `@id` / breadcrumbs follow singular slug URLs.  
- Honest empty: PDF CTA and accessories regions remain visible even if empty.

## Branding / IA budget

When touching landing/marketing surfaces, follow existing brand system; do not invent purple-glow generic AI layouts. Product/catalog pages preserve established patterns.

## Specs display

- Do not render OperationalMetadata `top:*` as customer technical specs.  
- FA labels are display; raw keys are not Approved Properties until mapped.  
- Do not claim AI-citeable content without Evidence (ADR-009).

## Performance (principles)

- Avoid premature micro-opts; measure before heavy memoization unless team React Compiler guidance says otherwise.  
- Images: respect primary/gallery rules; don’t fake multi-image UI density.

## Citations

URL/SEO PRs cite ADR-010 and RFC-004/005. Meaning changes cite Domain/ADR.
