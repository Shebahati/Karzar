# Search surface audit (Phase 2B)

## Before (main prior to 2B)

| Surface | Searched |
|---------|----------|
| Product.name | YES (single substring) |
| Product.sku | YES |
| Brand.name | YES |
| manufacturer_code | NO |
| Product Type | NO |
| Synonyms | NO |
| Multi-token cross-field | NO |

## After

| Surface | Searched |
|---------|----------|
| Product.name | YES (per token) |
| Product.sku | YES |
| Brand.name | YES |
| manufacturer_code | YES |
| ProductType code/FA/EN/slug | YES (EXISTS) |
| PT synonyms (active, PT-linked) | YES (EXISTS) |
| Multi-token | AND of per-token ORs |

Implementation: `app/utils/catalog_identity_search.py` → `app/crud/product.py`.
