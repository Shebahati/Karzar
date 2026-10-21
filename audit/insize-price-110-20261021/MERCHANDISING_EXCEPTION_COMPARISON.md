# Two-product merchandising exception comparison (TOMAN)

Values are taken directly from `products.base_price` and `products.original_price` (no conversion).

## 1944 — `3203-1506`

| Field | Current | Proposed |
|--------|--------:|---------:|
| `base_price` | 44,038,500 | 48,442,350 (+10% ROUND_HALF_UP) |
| `original_price` | 47,100,000 | **NULL** |
| Derived discount % | 6.50% | none |
| Storefront display | discounted (sale below compare-at) | no compare-at / no strikethrough promo |

## 3639 — `S3-2824`

| Field | Current | Proposed |
|--------|--------:|---------:|
| `base_price` | 49,929,000 | 54,921,900 (+10% ROUND_HALF_UP) |
| `original_price` | 53,400,000 | **NULL** |
| Derived discount % | 6.50% | none |
| Storefront display | discounted | no compare-at |

Authorized exception IDs are fixed in `AUTHORIZED_ORIGINAL_PRICE_NULL_EXCEPTIONS`; cohort size remains **206**.
