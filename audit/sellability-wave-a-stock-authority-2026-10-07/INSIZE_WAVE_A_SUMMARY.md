# INSIZE Wave A Deep Summary

**Cohort:** 476 / 580 CURRENT_ONLY_AVAILABILITY  
**Canonical source bytes:** SHA256 `65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a`  
**Paths:** VPS preserve `/opt/karzar/preserve/insize-workbook-20261006/…` + local duplicate (byte-identical)

## Newest discovered stock source

| Candidate | SHA256 | Note |
|-----------|--------|------|
| `… افزایش 20 درصدی.xlsx` | `65a92337…` | Canonical for Wave A |
| `… دلار 300 هزار تومان - نهایی.xlsx` | `8324b2c1…` | Newer mtime (2026-10-07); **وضعیت map identical** (55265 codes, 0 disagreements) |
| Wave1A primary `(2).xlsx` | `8cecb478…` | Earlier family member |

No inventory authority with a **proven later document source date** was found. All remain `11 شهریور` filename family.

## Proven date?

```text
source_date = UNPROVEN
date proven = NO
freshness = UNKNOWN
SOURCE_AUTHORITY_VALID = NO
```

Filename `11 شهریور` alone is insufficient (Wave 1A.1 `SOURCE_YEAR_UNPROVEN` reconfirmed). OOXML `modified` / filesystem mtime are not accepted as source-year proof.

## Semantics

Header includes `CODE`, warehouse qty columns, and **`وضعیت`**.

| وضعیت | Normalized |
|-------|------------|
| موجود | AVAILABLE |
| نا موجود | UNAVAILABLE |

Workbook global: 255 موجود / 55011 نا موجود (of 55265 codes). Availability is taken from **وضعیت only** (not price).

## Identity matching (governed only)

| Match type | Count |
|------------|------:|
| EXACT_MANUFACTURER_SKU | 366 |
| EXACT_SKU | 66 |
| REGISTERED_INSIZE_TRAILING_A | 43 |
| NOT_FOUND | 1 |
| **Exact matched (any of above)** | **475** |

Trailing-A uses `insize_trailing_a_identity/1.0.0` on main only. No fuzzy / generic suffix stripping. N4120 / remaining-19 alias registries were **not** applied as unmerged informal rules.

## Normalized results (476)

| Class | Count |
|-------|------:|
| AVAILABLE | 10 |
| UNAVAILABLE | 465 |
| UNKNOWN | 1 |
| CONFLICT | 0 |

## Strict / aging candidates

| Set | Count |
|-----|------:|
| STRICT_AVAILABLE (CURRENT_ENOUGH) | **0** |
| AGING_AVAILABLE | **0** |

Blocker for the 10 AVAILABLE exact matches: **UNKNOWN_DATE** (cannot enter strict APPLY set).

## What prevents the remainder?

1. **Freshness / date** — entire INSIZE authority valid-for-APPLY blocked until source_date year proven or a dated fresh export arrives  
2. **Authoritative UNAVAILABLE** — 465 exact rows currently نا موجود in workbook (must not APPLY available)  
3. **1 NOT_FOUND** — no exact/trailing-A identity to workbook CODE  

## Fastest INSIZE unlock path

Obtain a **fresh** distributor inventory export with:

- manufacturer `CODE`
- `وضعیت` or proven sellable qty
- **explicit calendar source_date**

Then rematch the 476 with the same governed identity rules.
