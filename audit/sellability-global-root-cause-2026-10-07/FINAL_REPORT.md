# KARZAR GLOBAL SELLABILITY ROOT-CAUSE AUDIT — FINAL REPORT

**Status:** COMPLETE (read-only)  
**Snapshot UTC:** 2026-10-07T10:16:05Z  
**origin/main:** `076fb45cc2be7b71b169295508361b8336950ee8`  
**Host / DB:** `srv5944957438` / `lathe_postgres` / `karzar_staging` / volume `karzar_postgres_data`  
**Alembic:** `u4v5w6x7y8z9`  
**transaction_read_only:** `on` (proven)  
**SELLABILITY_MUTATION_AUTHORIZED:** **NO**

---

## Executive answers (required)

### 1. How many Products are sellable right now?

**717**

### 2. How many are non-sellable?

**5819** (`717 + 5819 = 6536` live)

### 3. For every non-sellable Product, do we know why?

**Yes at blocker level (100%).** Every live product has a matrix row with exact blocker set.  
Root-cause taxonomy: **2400** fully deterministic; **3419** carry explicit `INACTIVE_SOURCE_UNKNOWN` (classified residual, not silent). Availability gaps are uniformly `NO_AUTHORITY` (2780). No unlabeled residual.

### 4. How many have 1 / 2 / 3 / 4 blockers?

| Blockers | Count |
|---------:|------:|
| 0 (sellable) | 717 |
| 1 | 580 |
| 2 | 3408 |
| 3 | 307 |
| 4 | 1524 |

One-blocker breakdown: **ONLY_AVAILABILITY = 580**; ONLY_ACTIVE/PRICE/IMAGE = **0**.

### 5. What are the largest root-cause classes?

1. `IMAGE_ROW_MISSING` — 5072  
2. `INACTIVE_SOURCE_UNKNOWN` — 3419  
3. `NO_AUTHORITY` (availability) — 2780  
4. `INACTIVE_MISSING_COMMERCIAL_DATA` — 1237  
5. `PRICE_SOURCE_MISSING` — 820  
6. `PRICE_LEGACY_NULL` — 790  
7. `INACTIVE_IDENTITY_UNCERTAIN` — 295  

### 6. How many could become sellable immediately using evidence already available?

**0 additional** (`EVIDENCE_COMPLETE_UPPER_BOUND = 717`).  
No AUTO_SAFE immediate unlock candidates: stock/price/image authorities were **not** proven attached in-DB for this freeze.

### 7. Fastest safe path to the first +100 Sellable?

Obtain a **fresh INSIZE supplier stock authority** (exact manufacturer_code / governed trailing-A / alias registries only). Target ≥100 of the **476** INSIZE `CURRENT_ONLY_AVAILABILITY` SKUs that the source marks AVAILABLE. Then Owner-authorize a narrow APPLY. Do **not** infer from price or Hesabfa.

### 8. Fastest safe path to +500 Sellable?

Same path at brand scale: INSIZE (476) + ASTPOWER (53) + SAN OU (24) + Dasqua (22) only-availability cohort = **575** candidates. Gain materializes only where sources say AVAILABLE and Owner authorizes APPLY. Upper bound if all AVAILABLE: **~+575** toward ~1292 sellable.

### 9. Which suppliers/sources are blocking the most Products?

| Brand | ONLY_AVAILABILITY needing stock source |
|-------|----------------------------------------:|
| INSIZE | 476 |
| ASTPOWER | 53 |
| SAN OU | 24 |
| Dasqua | 22 |
| TERMA | 4 |
| Mitutoyo | 1 |

See `SELLABILITY_SOURCE_REQUIRED.csv`. Broader catalog gaps are image (5072) and inactive (4951) but those are not one-blocker unlocks.

### 10. Which Owner decisions unlock the most Products?

1. Authorize fresh **INSIZE** stock source use → up to **+476**  
2. Authorize **ASTPOWER / SAN OU / Dasqua** stock sources → up to **+99** combined  
3. Policy on archival 4-blocker set (1524) — usually **keep non-sellable**  
4. Hesabfa stock-semantics study before any Hesabfa-driven availability  

See `SELLABILITY_OWNER_DECISIONS_REQUIRED.csv`.

### 11. Which fixes can be automated safely?

**None as AUTO_SAFE today.**  
580 rows are `AUTO_AFTER_SOURCE_AUTHORITY` (availability enable **after** valid stock authority). Image/price automation requires exact source inventories not attached in this freeze.

### 12. Which Products should NOT be made sellable?

- **1524** four-blocker `INACTIVE+UNAVAILABLE+UNPRICED+IMAGE_MISSING` classified `ARCHIVAL_CATALOG` / `F8_INTENTIONALLY_NOT_FOR_SALE` unless Owner overturns  
- Any product with unresolved identity conflict / duplicate manufacturer identity within brand  
- Anything lacking proven stock authority (do not flip `is_available` from price)

### 13. Recommended execution order after this audit?

1. Wave A — acquire/validate stock authorities for the 580 only-availability cohort (INSIZE first)  
2. Wave D — Owner-authorized availability APPLY for source-AVAILABLE subset only  
3. Wave F — identity/integrity cleanup (`AVAILABLE_INACTIVE` / `AVAILABLE_NO_IMAGE` debt)  
4. Waves B/C — image/price sources for multi-blocker long tail  
5. Wave E — inactive policy (never mass-activate)  
6. Wave G — archival long tail  

Details: `REMEDIATION_WAVE_PLAN.md`.

---

## Safety proof

| Control | Value |
|---------|-------|
| Production Product mutation | NO |
| Database mutation | NO (`SET TRANSACTION READ ONLY` → `transaction_read_only=on`) |
| Hesabfa mutation | NO |
| Deployment | NO |
| HESABFA_STOCK_SEMANTICS | UNPROVEN (supporting evidence only) |

## Contract

See `CODE_SELLABILITY_CONTRACT.md`. Historical and current SELLABLE definitions align (commercial `base_price > 0`). Cart technically accepts non-null zero; audit does not.

## Global census

```text
live=6536  active=1585  available=3756  priced=4926
imaged=1464  visible=1368  sellable=717  non_sellable=5819
```

## Historical 330

```text
still_live=330  now_sellable=1  still_only_availability=329  new_blockers=0
```

## Upper bounds

| Bound | Value |
|-------|------:|
| SELLABLE_NOW | 717 |
| EVIDENCE_COMPLETE_UPPER_BOUND | 717 |
| SOURCE_REFRESH_UPPER_BOUND | 1297 |
| OWNER_DECISION_UPPER_BOUND | 1297 |
| THEORETICAL_UPPER_BOUND (excl. archival 1524) | 5012 |

## Data integrity (systemic)

| Finding | Count | Severity |
|---------|------:|----------|
| AVAILABLE_INACTIVE | 3039 | HIGH (flag true while inactive) |
| AVAILABLE_NO_IMAGE | 3039 | HIGH |
| AVAILABLE_UNPRICED | 1 | HIGH |

No mutation performed to correct these.

## Brand focus (availability authority)

All focus brands: **authority_exists=NO** for this freeze (`BRAND_AVAILABILITY_AUTHORITY.csv`).

## Artifacts

Directory: `audit/sellability-global-root-cause-2026-10-07/`  
Universe rows: 6536  
Matrix rows: 6536  
See `SHA256SUMS.txt`.
