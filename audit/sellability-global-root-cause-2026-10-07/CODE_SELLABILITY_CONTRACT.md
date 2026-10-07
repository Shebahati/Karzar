# CODE SELLABILITY CONTRACT

**Snapshot:** 2026-10-07T10:16:05Z  
**Code base:** `origin/main` `076fb45cc2be7b71b169295508361b8336950ee8`  
**Mutation:** none

## HISTORICAL_AUDIT_CONTRACT

```text
LIVE       = deleted_at IS NULL
ACTIVE     = LIVE AND is_active = true
AVAILABLE  = LIVE AND is_available = true
PRICED     = LIVE AND base_price IS NOT NULL AND base_price > 0
IMAGED     = EXISTS ≥1 qualifying non-placeholder ProductImage
VISIBLE    = LIVE AND is_active AND IMAGED
SELLABLE   = VISIBLE AND is_available AND PRICED
```

## CURRENT_CODE_CONTRACT

Authoritative storefront visibility (`app/utils/public_catalog.py`):

| Predicate | Code behavior |
|-----------|----------------|
| Soft-delete | `deleted_at IS NULL` required for public lists/PDP |
| Active | `is_active = true` required (`storefront_public_product_filters`) |
| Image gate | When `STOREFRONT_HIDE_IMAGELESS_PRODUCTS=true` (default), require non-placeholder image URL via `public_image_exists_clause` |
| Materialization | `STOREFRONT_REQUIRE_MATERIALIZED_IMAGES` defaults to `DEBUG`; production path does not require on-disk materialization for this audit’s IMAGED definition |
| Availability | `is_available` is **not** a list/PDP visibility filter; it partitions ranking (`availability_rank_clause`) and blocks commercial sellability |
| Purchase price | `cart_service.py`: purchase lane rejects only `base_price is None` |

### Definitions used by THIS audit (CURRENT CODE + commercial safety)

```text
LIVE       = deleted_at IS NULL
ACTIVE     = LIVE AND is_active = true
AVAILABLE  = LIVE AND is_available = true
PRICED / COMMERCIAL_PRICE_VALID =
             LIVE AND base_price IS NOT NULL AND base_price > 0
TECHNICALLY_ACCEPTED_BY_CODE =
             LIVE AND base_price IS NOT NULL
             (cart accepts zero/negative; audit does NOT call them sellable)
IMAGED     = ≥1 ProductImage with non-empty URL and not matching
             placeholder ILIKE token set in public_catalog._PLACEHOLDER_ILIKE_TOKENS
VISIBLE    = LIVE AND ACTIVE AND IMAGED
             (matches storefront public filters when image hide is on)
SELLABLE   = VISIBLE AND AVAILABLE AND COMMERCIAL_PRICE_VALID
```

## code/audit discrepancy

| Topic | Discrepancy | Audit choice |
|-------|-------------|--------------|
| Zero/negative `base_price` | Cart accepts non-null zero; historical audit required `> 0` | **Commercial PRICED (`> 0`)** for SELLABLE |
| `is_available` vs visibility | Code allows unavailable products on storefront lists (ranked lower) | SELLABLE still requires AVAILABLE |
| Hesabfa stock | Mapping/`last_stock` exist; semantics **UNPROVEN** | Not used as availability authority |

**Fresh census used CURRENT CODE CONTRACT with commercial price rule.** Historical Wave 0/1A used the same SELLABLE definition; counts are directly comparable.

## Placeholder tokens (IMAGED)

Synced with `app/utils/public_catalog.py`:

`placeholder`, `woocommerce-placeholder`, `no-image`, `no_image`, `noimage`, `default-image`, `default_image`, `default-product`, `default_product`, `karzar-editorial`, `/images/placeholders/`

## Availability authority (policy)

`docs/catalog/SUPPLIER_STOCK_AUTHORITY.md`:

```text
PRICE AUTHORITY ≠ AVAILABILITY AUTHORITY
```

Exact SKU / manufacturer_code match only. No fuzzy match. Hesabfa stock not authority until semantics PROVEN.
