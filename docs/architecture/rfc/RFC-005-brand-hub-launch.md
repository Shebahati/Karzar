# RFC-005 — Brand Hub Launch

## Metadata

| Field | Value |
|-------|-------|
| **ID** | RFC-005 |
| **Title** | Brand Hub Launch |
| **Status** | **Accepted** |
| **Authors** | SEO / Content (logical) |
| **Created** | 2026-07-29 |
| **Related ADRs** | ADR-010, ADR-002 |
| **Related Epics** | **EPIC 1** |
| **Related RFCs** | RFC-004 (PDP slugs; parallel/sequenced) |

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Binding plan for Brand Hub `/brands/{slug}` MVP; no Facts/KG/dual-write required. |

---

## 1. Summary

Launch first-class Brand Hub pages at **`/brands/{slug}`** with SEO meta exposure via API, internal linking from PDP/category, and a phased brand wave order from EPIC 0 brand intelligence — **without** requiring Facts, dual-write, or Knowledge Graph tables. Unbranded products (**288**) remain valid without a fake “Generic” brand.

## 2. Motivation / Problem

Brand hubs are **absent** today (filters only). EPIC 0 shows uneven brand richness; priority industrial brands (ASTPOWER, INSIZE, Dasqua, Chumpower, Mitutoyo, SAN OU) concentrate SEO and enrichment ROI. Brand `meta_*` fields exist in DB but API/storefront exposure is weak — hubs cannot rank without meta + indexable URLs. EPIC 1 can ship hubs on commerce data alone.

## 3. Goals / Non-goals

**Goals:**  
- Route `/brands/{slug}` listing products for that brand.  
- Expose brand meta_title/description (and future OG) via API.  
- Wave launch: priority brands first, then long tail.  
- Honest empty slots (no fake density).  
- Compatible with RFC-004 singular product URLs.  

**Non-goals:**  
- Facts/Evidence-powered hub modules as launch blocker.  
- Inventing brands for unbranded SKUs.  
- Full knowledge compare on hub day-1.  
- Production enrichment to inflate brand content.

## 4. Current State

- `brands` table with slug/meta fields (as-built).  
- Products optional `brand_id`; unbranded **288** (4.88%).  
- No `/brands/{slug}` storefront route.  
- Category hubs `/categories/{slug}` exist — pattern reference.  
- Avg quality **58.33**; hubs must not claim Spec-Ready catalog-wide.

## 5. Proposed Design

### URL & IA

- Canonical: `/brands/{slug}`  
- PDP links to brand hub when `brand_id` set.  
- Breadcrumb: Home → Brands → {Brand} → Product (when applicable).  
- No `/brand/` singular confusion; plural collection + slug resource.

### API

- Public brand retrieve by slug including meta scalars.  
- Paginated product list filtered by brand_id; respect `is_active` / not deleted.  
- Do not require Approved Facts in payload for EPIC 1.

### Content

- Hub hero: brand name as primary signal; one short supporting blurb from brand description/meta if present.  
- Product grid commerce-first.  
- Optional “specs sparse” honesty — do not invent datasheets (PDF=0 baseline).

### Launch waves (EPIC 0 priority)

| Wave | Brands (canonical spellings) | Rationale |
|------|------------------------------|-----------|
| 1 | ASTPOWER, INSIZE, Dasqua | Volume / enrichment focus |
| 2 | Chumpower, Mitutoyo, SAN OU | Metrology / industrial priority |
| 3 | Remaining branded catalog | Long tail |
| — | Unbranded | No hub membership; PDP ok |

Exact ordering within wave may adjust from `brand-intelligence-baseline.md` without inventing new census numbers here.

### SEO

- Unique meta per brand; fallback templates if empty.  
- Sitemap entries per launched wave.  
- Canonical self-referential hub URLs.

## 6. Alternatives Considered

| Option | Pros | Cons | Why not |
|--------|------|------|---------|
| A. Filters-only forever | Cheap | Weak SEO | Rejected blueprint |
| B. Wait for Facts | Rich modules | Blocks EPIC 1 | Rejected |
| C. Fake Generic brand | 100% coverage | Lies | Forbidden ADR-002 |
| D. Phased `/brands/{slug}` (chosen) | ROI waves | Partial launch | Selected |

## 7. Migration / Rollout Plan

| Phase | Work | Exit |
|-------|------|------|
| 0 | API meta exposure + empty route stub | Contract tests |
| 1 | Wave 1 hubs live + internal links | Crawl 200 |
| 2 | Wave 2 | Indexation watch |
| 3 | Wave 3 + sitemap complete | EPIC 1 brand KPI |
| 4 | Later: Knowledge modules when Facts exist | Separate epic |

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Thin meta content | Templates + Content backlog; don’t block route |
| Brand slug collisions | DB uniqueness; audit |
| Cannibalizing category pages | Distinct intent; IA linking rules |
| Claiming Spec-Ready hubs | DQ honesty; commerce-first grid |

## 9. Rollback Plan

- Feature flag hide `/brands/*` (404 or redirect to home/search).  
- Revert sitemap brand URLs.  
- No data migration to undo — routes only.  
- Compensating: restore prior nav without brand links.

## 10. Security & Ingestion Boundary Impact

- No Category B enrichment required for launch.  
- Content edits via normal admin/local policy.  
- Do not scrape production to “fill” brand blurbs as undocumented bulk.

## 11. Observability / KPIs

- Brand hub `crawl_success_rate`, `index_rate`, `organic_ctr` (EPIC 1)  
- `brand_coverage` among products (baseline branded ≈95.12%)  
- Wave completion checklist  
- Cite EPIC0 unbranded **288** — not a defect to force to zero for hub launch

## 12. Open Questions

1. `/brands` index page in wave 1 or later?  
2. Brand logo asset requirements?  
3. Multi-brand OEM/distributor display names?

## 13. Decision Log

| Date | Decision | By | Note |
|------|----------|----|------|
| | | | |

## 14. References

- ADR-010, ADR-002  
- IA navigation / url-map  
- `docs/audits/brand-intelligence-baseline.md`  
- EPIC0 executive summary  
- RFC-004
