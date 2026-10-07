# ROOT-CAUSE RECONCILIATION

**Snapshot:** 2026-10-07T10:16:05Z  
**Identity equation:** `SELLABLE (717) + NON_SELLABLE (5819) = LIVE (6536)` ✓

## Blocker populations → root-cause classes

### INACTIVE (`is_active=false`): 4951

| Class | Count | Notes |
|-------|------:|-------|
| `INACTIVE_SOURCE_UNKNOWN` | 3419 | No ProductChangeLog / policy evidence for why inactive |
| `INACTIVE_MISSING_COMMERCIAL_DATA` | 1237 | Inactive and missing image and/or commercial price |
| `INACTIVE_IDENTITY_UNCERTAIN` | 295 | Missing/partial manufacturer_code or brand identity |
| **Sum** | **4951** | Residual unexplained: **0** |

`SHOULD_CONSIDER_ACTIVATION` for all inactive rows in this freeze: `UNKNOWN` (no Owner allowlist applied in this audit).

### UNAVAILABLE (`is_available=false`): 2780

| Class | Count | Authority |
|-------|------:|-----------|
| `NO_AUTHORITY` | 2780 | No current proven supplier stock authority attached in-DB for this freeze |
| **Sum** | **2780** | Residual: **0** |

Freshness: `UNKNOWN` for all. Hesabfa `last_stock` captured as supporting evidence only (`HESABFA_STOCK_SEMANTICS=UNPROVEN`).

Of these, **580** are one-blocker `UNAVAILABLE` only (active+priced+imaged).

### UNPRICED (`base_price IS NULL OR <= 0`): 1610

| Class | Count |
|-------|------:|
| `PRICE_SOURCE_MISSING` | 820 |
| `PRICE_LEGACY_NULL` | 790 |
| **Sum** | **1610** |

Zero-price commercial invalids: none beyond the unpriced set in this freeze (`technically_price_non_null == priced == 4926`).

### IMAGE_MISSING (no qualifying non-placeholder image): 5072

| Class | Count |
|-------|------:|
| `IMAGE_ROW_MISSING` | 5072 |
| **Sum** | **5072** |

No placeholder-only residual split in this freeze (all image-blocked rows had zero qualifying URLs; primary status recorded per row in the matrix).

## Blocker combination reconciliation → LIVE

| Combination | Count |
|-------------|------:|
| `INACTIVE+IMAGE_MISSING` | 3038 |
| `INACTIVE+UNAVAILABLE+UNPRICED+IMAGE_MISSING` | 1524 |
| `NONE` (sellable) | 717 |
| `UNAVAILABLE` | 580 |
| `INACTIVE+UNAVAILABLE+IMAGE_MISSING` | 292 |
| `UNAVAILABLE+IMAGE_MISSING` | 217 |
| `INACTIVE+UNAVAILABLE` | 82 |
| `UNAVAILABLE+UNPRICED` | 71 |
| `INACTIVE+UNAVAILABLE+UNPRICED` | 14 |
| `INACTIVE+UNPRICED+IMAGE_MISSING` | 1 |
| **Sum** | **6536** |

## Blocker-count distribution

| Blockers | Count |
|---------:|------:|
| 0 | 717 |
| 1 | 580 |
| 2 | 3408 |
| 3 | 307 |
| 4 | 1524 |
| **Sum** | **6536** |

## Classification coverage

| Metric | Value |
|--------|------:|
| Non-sellable | 5819 |
| Fully classified (deterministic classes) | 2400 |
| Partially classified (`INACTIVE_SOURCE_UNKNOWN` present) | 3419 |
| Silent/unlabeled residual | 0 |
| Coverage (labeled) | 100% |

Unknown is represented as explicit taxonomy (`INACTIVE_SOURCE_UNKNOWN`, `NO_AUTHORITY`), not silence.
