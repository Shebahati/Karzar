# URL Map — Karzar IA

**Status:** Proposed · Binding direction: **ADR-010** · Canon C3  
**Supersedes for PDP:** SEO constitution plural `/products/{slug}` row (stale)

---

## CURRENT → TARGET

| URL class | CURRENT | TARGET canonical | Redirect / notes | Indexable |
|-----------|---------|------------------|------------------|-----------|
| Product PDP | `/product/{id}` | **`/product/{slug}`** | **301** id→slug when shipped | Yes (active, non-deleted) |
| Product plural drift | — | **Not default** | Only if Board exception + dual redirects | — |
| Category Hub | **`/categories/{slug}`** (EXISTS) | Same (enhance) | No class change without RFC | Yes if non-empty / policy |
| Brand Hub | *absent* (filter `?brand=`) | **`/brands/{slug}`** | Filters remain PLP aids, not hubs | Yes for launched brands |
| Catalog PLP | `/catalog?...` | Same | Facet URLs **not** entity hubs | Conditional (avoid thin dupes) |
| Blog index | `/blog` | Transitional | Later Learning index | Yes |
| Article | `/blog/{slug}` | Guides path MAY evolve | 301 plan when renamed | Yes |
| Learning index | — | `/guides` or equiv (TARGET) | Provisional | Yes |
| Glossary | — | `/glossary/{term}` (TARGET) | — | Yes |
| Tool Class Hub | — | `/tools/{slug}` or `/classes/{slug}` (provisional) | Not EPIC 1 | Yes later |
| Comparison | — | `/compare/...` (TARGET) | — | Conditional |
| Standard | — | `/standards/{slug}` (TARGET) | — | Yes later |
| Application | — | `/applications/{slug}` (TARGET) | — | Yes later |
| Search results | catalog search UX | Same + future knowledge search | — | Usually noindex or carefully limited |
| Utilities | `/cart`,`/quote`,`/checkout/*`,`/account/*`,`/login` | Same | — | **noindex** |
| Static | `/about`,`/contact`,`/terms`,`/privacy` | Same | — | Yes |

---

## Rules

1. Canonical PDP MUST be singular **`/product/{slug}`** (ADR-010).  
2. Legacy **`/product/{id}`** MUST 301 to slug URL after cutover.  
3. Trailing slash policy SHOULD match existing Next.js convention site-wide (pick one; do not mix).  
4. No locale prefix assumed in v1 IA (FA primary site).  
5. Query params MUST NOT create unbounded indexable “hub” clones (`?brand=` is not `/brands/{slug}`).  
6. JSON-LD `@id` MUST equal canonical URL after EPIC 1 cutover.  
7. EPIC 1 URL work MUST NOT require Facts/KG tables.

---

## EPIC 1 minimal redirect matrix

| From | To | Type |
|------|----|------|
| `/product/{numericId}` | `/product/{slug}` | 301 |
| Internal cards/sitemap links using id | slug URLs | Update generators |
| `/brands/{slug}` | n/a (new) | 200 for launched brands |

---

## Open questions

- Exact Learning index path (`/guides` vs `/learn`).  
- Provisional Tool Class path — finalize in later RFC.  
- Whether empty category hubs stay noindex (Storefront already has empty-hub hygiene — preserve).
