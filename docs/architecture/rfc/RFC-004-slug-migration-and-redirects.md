# RFC-004 — Slug Migration & Redirects

## Metadata

| Field | Value |
|-------|-------|
| **ID** | RFC-004 |
| **Title** | Slug Migration & Redirects |
| **Status** | **Accepted** |
| **Authors** | SEO / Frontend (logical) |
| **Created** | 2026-07-29 |
| **Related ADRs** | ADR-010, ADR-002 |
| **Related Epics** | **EPIC 1** (first implementation epic) |
| **Related RFCs** | RFC-005 (hubs; parallel) |

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Binding plan for PDP slug migration + 301 redirects + canonical/JSON-LD alignment; EPIC 1 implementable without Facts. |

---

## 1. Summary

Migrate Product Detail Pages from **CURRENT** `/product/{id}` to **TARGET** `/product/{slug}` (singular), with **301** redirects from id URLs, canonical tags, and JSON-LD `@id` alignment — **without** Facts tables or dual-write. Reconcile stale plural `/products/{slug}` SEO constitution drift to singular (Canon C3).

## 2. Motivation / Problem

Slugs exist and are unique among active products (EPIC 0 dup slug **0**), but routing still uses numeric ids — burning SEO equity and blocking clean hubs linking. Constitution/docs that say `/products/{slug}` (plural) conflict with backlog/blueprint singular `/product/{slug}` and with less churn from `/product/{id}`.

## 3. Goals / Non-goals

**Goals:**  
- Ship `/product/{slug}` as canonical PDP.  
- 301 `/product/{id}` → `/product/{slug}`.  
- Canonical + breadcrumb + JSON-LD alignment.  
- Implementable in EPIC 1 with existing columns only.  

**Non-goals:**  
- Property Facts, KG, RAG.  
- Changing slug generation algorithm massively day-1.  
- Brand hubs (RFC-005).  
- Accepting plural `/products/` as TARGET.

## 4. Current State

- DB: `products.slug` unique; filled for actives.  
- Storefront: PDP by id path (as-built preference over stale IA docs — Canon C4).  
- Category hubs `/categories/{slug}` already exist.  
- Brand hubs absent.

## 5. Proposed Design

1. **Canonical pattern:** `/product/{slug}` (singular).  
2. **Redirect:** permanent 301 from `/product/{id}` when product resolvable; 404 if deleted per policy.  
3. **Legacy plural:** if any `/products/{slug}` links exist externally, 301 → singular `/product/{slug}` (do not keep plural as canonical).  
4. **Slug change policy:** rare; if changed, 301 old slug → new; audit.  
5. **API:** resolve by slug for storefront; id remains internal PK.  
6. **Sitemap / GSC:** submit singular URLs.  
7. **No Facts dependency.**

## 6. Alternatives Considered

| Option | Pros | Cons | Why not |
|--------|------|------|---------|
| A. Keep id URLs | Zero eng | SEO debt | Rejected ADR-010 |
| B. Plural `/products/{slug}` | Matches some docs | Extra churn from `/product/{id}` | Rejected Canon C3 |
| C. Singular `/product/{slug}` + 301 (chosen) | Minimal path churn | Doc cleanup | Selected |

## 7. Migration / Rollout Plan

| Phase | Work | Exit |
|-------|------|------|
| 0 | Inventory id URL references in FE/API/sitemaps | List |
| 1 | Dual resolve slug+id behind flag | QA |
| 2 | Canonical slug; enable 301 | Crawl sample 200 |
| 3 | Update internal links + JSON-LD | No id links in nav |
| 4 | Monitor GSC; remove flag debt | EPIC 1 exit |

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Broken bookmarks | 301 coverage tests |
| Duplicate content id+slug | Canonical tag |
| Slug collision | Already 0 dups; uniqueness SLO |
| Soft-deleted products | Consistent 404/410 policy |

## 9. Rollback Plan

- Feature flag: serve id URLs again; keep slug routes temporary 302/disable.  
- Reverse sitemap to id only if emergency (avoid if 301 already crawled — prefer fix-forward).  
- Compensating: restore prior route module from Git.

## 10. Security & Ingestion Boundary Impact

- No catalog enrichment required.  
- No production data writes for routing change.  
- Avoid open redirects: only resolve known product ids/slugs.

## 11. Observability / KPIs

- `url_slug_coverage` (already ~100% data)  
- `crawl_success_rate`, `index_rate`, `organic_ctr` (EPIC 1 bridge)  
- 301 hit count; 404 rate on old ids  
- Cite EPIC0 uniqueness baselines

## 12. Open Questions

1. 410 vs 404 for soft-deleted?  
2. Trailing slash policy?  
3. API versioning for slug resolve endpoint?  
4. Should admin preview links use slug immediately or remain id-based?

## 12a. EPIC 1 independence statement

This RFC is **intentionally Facts-free**. Engineers MUST NOT block slug routing on Property tables, dual-write flags, or Evidence. Success is measured by crawl/index/CTR KPIs and 301 correctness — not by technical_specs fill rate (still ~70% empty at EPIC 0 baseline).

## 12b. Test matrix (minimum)

| Case | Expect |
|------|--------|
| Active product id URL | 301 → `/product/{slug}` |
| Canonical slug URL | 200 + self canonical |
| Unknown id | 404 |
| Plural `/products/{slug}` if hit | 301 → singular |
| Soft-deleted | 404 or 410 per policy |
| Internal nav | No bare id PDP hrefs after phase 3 |

## 13. Decision Log

| Date | Decision | By | Note |
|------|----------|----|------|
| | | | |

## 14. References

- ADR-010, ADR-002  
- IA `url-map.md`  
- Canon C3  
- Epic KPI bridge EPIC 1  
- Storefront as-built over stale plural constitution
