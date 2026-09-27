# Commerce Category Rules

**Status:** Proposed design (Phase 1A)

---

## 1. Job of Commerce Category

Commerce Category exists for:

- customer navigation
- merchandising
- SEO category hubs (`/categories/{slug}` — ADR-010)
- commercial discovery
- purchase-oriented grouping

It is **not** the canonical engineering definition (ADR-015).

### Permitted projections

Commerce **MAY** expose buyer-useful distinctions that are **Properties** at the engineering layer, e.g.:

- HSS Drills / Carbide Drills
- Digital Calipers
- BT Holders / HSK Holders
- U-Drill 2D…5D

**Constraint:** Every product in such a Category MUST still carry (when classified) a correct **Product Type** that does **not** depend on that projection alone.

### Uncontrolled-tree constraints

1. Depth ≤ 3; products only on selectable leaves (depth 2|3).
2. No cycles; unique `(parent_id, name)`.
3. Every Category MUST have immutable `category_code` once schema lands (Phase later).
4. Imports MUST map via `category_code` or stewarded mapping table — **not** bare integer PK (governance; schema later).
5. Catch-all leaves («عمومی») are debt; CCT-1 → prefer remove after reassignment.
6. Megamenu groups L1 roots only; does not invent ontology.
7. Renames/moves require redirect impact review (`CATEGORY_SLUG_REDIRECTS` / SEO Reviewer).

---

## 2. KARZAR COMMERCE CATEGORY TEST — CCT-1

Evaluate candidate Category C:

| Factor | Ask |
|--------|-----|
| Search intent | Do buyers seek C by name? |
| Catalog scale | Is assortment large enough that a hub helps (soft signal, not hard min)? |
| Buyer vocabulary | Is the label established in market FA/EN? |
| Filter discoverability | Would a facet on parent suffice? |
| SEO entity value | Stable hub worth indexing? |
| Merchandising need | Needed for megamenu/path clarity? |
| Future assortment | Likely to grow? |

### Result vocabulary

| Result | Meaning |
|--------|---------|
| `KEEP_AS_CATEGORY` | Valid commerce node |
| `BETTER_AS_FACET` | Prefer filter on parent hub |
| `BETTER_AS_PRODUCT_TYPE` | Distinction is engineering identity (rare for Category-only proposals) |
| `BETTER_AS_APPLICATION` | Use-context tag |
| `BETTER_AS_SYNONYM` | Alias of another Category/Type |
| `NOT_ENOUGH_EVIDENCE` | Defer |

**No hard minimum product count** as scientific truth. Empty selectable leaves are SEO-toxic (Phase 0: empty hubs 404) — operationally avoid publishing empty indexable hubs.

---

## 3. Relationship to scientific Domains

Live L1 roots (15) are **not** Domains. Mapping examples (illustrative):

| Live L1 | Domain projection |
|---------|-------------------|
| اندازه گیری دقیق / CNC / آزمایشگاهی | Metrology (Applications split CNC vs Lab) |
| ابزار اینسرتی + اینسرت | Cutting Tools |
| ابزار انگشتی / مته / قلاویز | Cutting Tools |
| ابزارگیر | Toolholding |
| ابزار گیرشی | Workholding |
| دستگاه‌های صنعتی | Industrial Machines |
| لوازم جانبی صنعتی | Often Facet/Accessories — tighten |
| هلی‌کویل L1 leaves | Fastening & Thread Repair (and fix selectable depth) |

Phase 1B will disposition all 138 nodes under CCT-1 + PTST-1.
