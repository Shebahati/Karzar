# TX-OWNER-001 — Remove Workshop / Hand Tools domain and all scoped catalog products

| Field | Value |
|-------|-------|
| **ID** | `TX-OWNER-001` |
| **Title** | Remove Workshop / Hand Tools domain and all scoped catalog products |
| **Phase** | 1A.1 Steward Freeze amendment |
| **Status** | **APPROVED** — authoritative for Phase 1B design drafting |
| **Approved by** | Owner / Taxonomy Steward |
| **Date** | 2026-09-27 |
| **Evidence class** | `KARZAR-GOVERNANCE-DECISION` |
| **Production APPLY** | **NO** — target-state law only; manifests in Phase 1B; deletion requires later explicit APPLY authorization |

---

## Decision

```text
Workshop & Hand Tools is outside Karzar target scope.
```

The following target Domain is **REJECTED** and must **not** exist in the target Karzar scientific taxonomy or as a target Commerce L1:

```text
Workshop & Hand Tools
ابزارهای کارگاهی و دستی
```

It must **not** be replaced by another generic catch-all such as:

```text
General Tools
Workshop Tools
Industrial Accessories
Miscellaneous Tools
Other Tools
ابزار عمومی
ابزار کارگاهی
لوازم جانبی عمومی
سایر
```

---

## Category consequence

```text
No target Domain or Commerce L1.
Existing scoped categories → REMOVE/DEPRECATE candidates.
```

For Phase 1B, any existing Commerce Category whose semantic scope belongs to Workshop Tools, Hand Tools, General Hand Tools, or Woodworking Tools must receive:

```text
TARGET_CATEGORY_DISPOSITION = REMOVE / DEPRECATE
OWNER_SCOPE_DECISION = YES
```

### Representative live categories (Phase 0B evidence — not exhaustive)

| category_id | name | path (abbrev) | live products (direct) | disposition |
|-------------|------|---------------|------------------------:|-------------|
| 157 | ابزار دستی | لوازم جانبی صنعتی › … | 0 (parent; 196 desc.) | `DEPRECATE_REMOVE` |
| 158 | ابزار دستی عمومی | … › ابزار دستی › … | 196 | `DEPRECATE_REMOVE` |
| 159 | ابزار چوبی | لوازم جانبی صنعتی › … | 0 (parent; 66 desc.) | `DEPRECATE_REMOVE` |
| 160 | ابزار آلات چوبی | … › ابزار چوبی › … | 66 | `DEPRECATE_REMOVE` |

---

## Product consequence

```text
Products genuinely belonging to this scope → CATALOG_EXIT.
```

```text
PRODUCT_DISPOSITION = CATALOG_EXIT
```

---

## Rehome

```text
Forbidden by default.
```

The only exception is:

```text
EXPLICIT FUTURE OWNER OVERRIDE
```

on a specific SKU/category. **No such override is currently granted.**

---

## Replacement catch-all

```text
Forbidden.
```

---

## Accessories ≠ Workshop Tools

Do **not** automatically delete legitimate industrial accessories merely because a current Category is broad or badly named.

Example: current `لوازم جانبی صنعتی` (154) must be **decomposed/analyzed** in Phase 1B.

| May remain (if product meaning fits) | Out of scope |
|--------------------------------------|--------------|
| Toolholding | General hand tools |
| Workholding | Generic workshop tools |
| Cutting Tools | Woodworking tools |
| Industrial Machines | |
| Metrology | |
| Thread Repair | |
| Metalworking Fluids | |

```text
current bad parent Category ≠ automatic product deletion
```

Classification must use actual descendant/product meaning.

---

## Explicit non-mutation (Phase 1A.1)

This decision defines the **TARGET STATE**. Phase 1A.1 must **not**:

```text
delete products
delete categories
disable products
change product category
create category
alter DB
deploy
```

Phase 1B produces exact manifests first. Later deletion needs its own explicit APPLY authorization.

---

## Related pack updates

- Constitution target Domains: seven in-scope Domains; Workshop marked `REJECTED — OWNER SCOPE DECISION`
- `09-REPRESENTATIVE-CATEGORY-TESTS.csv` — cats 157/158/159/160 annotated
- `08-MASTER-SEED-REVIEW.md` — Workshop Domain / sole-scope concepts `OUT_OF_SCOPE`
- `12-PHASE-1B-ENTRY-GATE.md` — Gate 9 approved; Ready for design drafting YES; APPLY NO
