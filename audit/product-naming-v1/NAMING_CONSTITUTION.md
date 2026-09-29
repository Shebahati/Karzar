# Karzar Product Naming Constitution v1

**Canonical SPEC:** [`../docs/architecture/specs/SPEC-product-naming-standard-v1.md`](../../docs/architecture/specs/SPEC-product-naming-standard-v1.md)

**Version id:** `karzar_product_naming_v1`  
**Phase:** 0/1 audit — Proposed (not Board-Accepted)

## Core grammar

```text
[Canonical Product Type] [Identity Qualifier(s)?] [Canonical Display Brand] کد [Manufacturer Code][، Primary Variant Attribute(s)?]
```

## Non-negotiables

1. Structured data → name (never the reverse as SoT).  
2. Default OEM display label is **`کد`**, not `مدل`.  
3. Preserve OEM manufacturer codes exactly.  
4. Product Type nouns — not commerce categories.  
5. HOLD > GUESS.  
6. No catalog APPLY / slug rewrite / SEO mutation in Phase 0/1.

## Companion artifacts

| Artifact | Path |
|----------|------|
| Brand display registry | `BRAND_DISPLAY_REGISTRY.csv` |
| PT naming profiles | `PRODUCT_TYPE_NAMING_PROFILES.csv` |
| Terminology registry | `NAMING_TERMINOLOGY_REGISTRY.csv` |
| Writer inventory | `PRODUCT_NAME_WRITERS.md` |
| Schema identity review | `SCHEMA_IDENTITY_REVIEW.md` |
| Census / proposals / HOLDs / SEO | `PRODUCT_NAMING_*.csv`, `SEO_IMPACT_REPORT.csv` |
| Engine prototype | `app/domain/product_naming.py` |
| Audit script | `scripts/audit_product_naming_v1.py` |
