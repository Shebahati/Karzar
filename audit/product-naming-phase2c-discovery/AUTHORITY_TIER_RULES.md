# Phase 2C — Manufacturer identity authority tiers

Discovery-only. No Product writes. SKU ≡ OEM is never a universal rule.

## Canonical manufacturer code

The exact verified manufacturer-issued ordering / catalogue / model / part /
variant designation for that commercial/technical product variant, preserving
OEM formatting (case, hyphens, dots, slashes, meaningful spaces, suffixes).

## Tiers

| Tier | Authority | Can yield `BACKFILL_EXACT` alone? |
|------|-----------|----------------------------------|
| 1 | OEM primary (official catalogue, product page, price list, technical PDF, OEM API) | Yes |
| 2 | Official authorized channel (appointed distributor / importer catalogue) | Yes |
| 3 | Strong local primary (Karzar-owned supplier workbook mapped to OEM numbers; verified invoice) | Yes |
| 4 | Weak secondary (marketplace, retailer, SEO page, title, SKU heuristic, legacy field) | **No** |

## `BACKFILL_EXACT` requirements (all)

1. Candidate is exact and unambiguous  
2. Evidence is Tier 1–3 with registry linkage  
3. Evidence maps to this product/variant  
4. No unresolved conflicting stronger evidence  
5. Formatting preserved exactly  
6. Brand identity known  
7. No unresolved brand+OEM duplication ambiguity  

Product Type is **not** required for OEM-column backfill readiness, but is tracked
separately for rename readiness.

## Other primary states

- `MANUAL_REVIEW` — strong evidence needs human interpretation  
- `HOLD_WEAK_EVIDENCE` — Tier 4 only  
- `HOLD_IDENTITY_CONFLICT` — competing candidates (e.g. title vs SKU)  
- `HOLD_MISSING` — no plausible OEM identity  
- `HOLD_BRAND_AMBIGUOUS` — brandless / brand unclear  
- `HOLD_DUPLICATE_IDENTITY` — brand + candidate collision across products  
- `REVIEW_EXISTING_CANONICAL` — non-null `manufacturer_code` without Tier 1–3 provenance  

These states are mutually exclusive for primary classification and must reconcile
to the non-deleted population.
