# EPIC 1 IA Readiness

**Status:** **Accepted** (Wave-1) · Actionable for frontend/SEO leads  
**Depends on:** ADR-010 (**Accepted**), ADR-002, this IA pack  
**Does NOT require:** Facts tables, Property dual-write, Knowledge Graph runtime

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Checklist of what EPIC 1 MUST implement on the IA slice. |

---

## What EPIC 1 MUST implement (IA slice)

| # | Deliverable | IA reference |
|---|-------------|--------------|
| 1 | Route PDP at `/product/{slug}` | url-map, page-type PDP |
| 2 | 301 `/product/{id}` → slug | url-map |
| 3 | Update cards, breadcrumbs, sitemap to slug | linking, schema |
| 4 | JSON-LD `@id` / BreadcrumbList use canonical slug URL | layer Schema + SEO |
| 5 | Ship Brand Hub `/brands/{slug}` for priority brands | nav, page-type |
| 6 | Expose Brand meta needed for hubs (API/product surface as required by impl) | Entity Layer |
| 7 | Render PDF CTA + accessories slot (honest empty OK) | Relation Layer, ADR-008 |
| 8 | Preserve/enhance Category Hub `/categories/{slug}` | affirm CURRENT |

---

## What EPIC 1 MUST NOT wait for

- Tool Class hubs  
- Glossary / Standards / Applications  
- Graph-typed relations  
- Vector search  
- FA/EN Property dictionary completion  
- Evidence corpus fullness (but empty Document slot still shows)

---

## Engineering acceptance (IA)

- [ ] Hitting old id URL returns 301 to slug  
- [ ] Canonical link / JSON-LD `@id` match slug URL  
- [ ] At least one priority Brand Hub returns 200 with product list  
- [ ] Category Hub still works  
- [ ] PDP shows document + accessory regions  
- [ ] No new indexable thin facet “hubs” introduced as Brand substitutes  

---

## KPIs (names; formulas Prompt 9/15)

- URL coverage (% active products reachable by slug URL)  
- Redirect success rate (id→slug)  
- Crawl/index of PDP + Brand hubs  
- Organic CTR (post-launch monitor)

---

## Risks

| Risk | Mitigation |
|------|------------|
| Slug collision / change | ADR-002 stability; redirect on change |
| Plural `/products/` drift | ADR-010 singular only |
| Brand hub thin content | Launch with meta + PLP; deepen later |
| Sitemap omission | Explicit EPIC 1 task |

---

## Next after EPIC 1 (IA)

Prompt 5 KG (Relation storage) · Content Layer guides migration · Tool Class hubs · Search Layer depth (Prompt 14)
