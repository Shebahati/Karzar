# REMEDIATION WAVE PLAN (DESIGN ONLY — NO APPLY)

**Authority:** Owner must separately authorize any wave.  
**This audit:** `SELLABILITY_MUTATION_AUTHORIZED = NO`

Data-driven order (not the template letter order):

## Recommended execution order

### Wave A — Fresh stock authority for CURRENT_ONLY_AVAILABILITY (580)

| Field | Value |
|-------|-------|
| Products | 580 (INSIZE 476, ASTPOWER 53, SAN OU 24, Dasqua 22, TERMA 4, Mitutoyo 1) |
| Expected sellable gain | Up to **+580** if sources classify AVAILABLE; lower if UNAVAILABLE/UNKNOWN |
| Risk | High if inferred without `SOURCE_AUTHORITY_VALID=YES` |
| Required authority | Supplier stock files per `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md` |
| Owner decision | Authorize source acquisition + use; brand-by-brand |
| Automation readiness | `AUTO_AFTER_SOURCE_AUTHORITY` only — never AUTO_SAFE today |
| Dependencies | Exact identity already present for this cohort |

**Fastest path to +100:** INSIZE stock source covering ≥100 of the 476 only-availability SKUs that map AVAILABLE.

**Fastest path to +500:** INSIZE (476) + ASTPOWER (53) + SAN OU (24) stock authorities with AVAILABLE outcomes (575 theoretical if all AVAILABLE).

### Wave B — Image imports for multi-blocker cohorts (not one-blocker)

| Field | Value |
|-------|-------|
| Products | 5072 image-missing (0 are ONLY_IMAGE) |
| Expected sellable gain | **0 immediate** alone — always co-blocked today |
| Risk | Medium (wrong image / identity mismatch) |
| Required authority | Exact manufacturer_code/SKU image inventories |
| Owner decision | Source allowlists per brand |
| Automation readiness | Possible `AUTO_SAFE` only after exact match + Owner allowlist |
| Dependencies | Must combine with active/price/stock waves |

### Wave C — Price authority imports

| Field | Value |
|-------|-------|
| Products | 1610 unpriced (0 are ONLY_PRICE) |
| Expected sellable gain | **0 immediate** alone |
| Risk | High commercial if wrong price |
| Required authority | Brand price lists; exact mfr code |
| Owner decision | Price policy / FX / margin |
| Automation readiness | `AUTO_AFTER_SOURCE_AUTHORITY` |
| Dependencies | Identity OK; never equate price to availability |

### Wave D — Availability APPLY after Wave A sources validated

| Field | Value |
|-------|-------|
| Products | Subset of Wave A where source says AVAILABLE |
| Expected sellable gain | Equals validated AVAILABLE count |
| Risk | Critical — false AVAILABLE harms customers |
| Required authority | Validated Wave A manifests |
| Owner decision | Explicit Wave D APPLY authorization |
| Automation readiness | Scripted map only after Owner APPLY |
| Dependencies | Wave A complete; Hesabfa remains UNPROVEN |

### Wave E — Inactive policy review

| Field | Value |
|-------|-------|
| Products | 4951 inactive |
| Expected sellable gain | Indirect only |
| Risk | High if mass-activated |
| Required authority | Owner commercial policy |
| Owner decision | Required for every activation class |
| Automation readiness | `OWNER_DECISION` / `NOT_RECOMMENDED` for auto-activate |
| Dependencies | Image+price+stock for candidates; exclude archival 1524 |

### Wave F — Identity / data-integrity repairs

| Field | Value |
|-------|-------|
| Products | `INACTIVE_IDENTITY_UNCERTAIN` 295; integrity `AVAILABLE_INACTIVE` 3039; `AVAILABLE_NO_IMAGE` 3039 |
| Expected sellable gain | Unlocks later waves; not direct sellable |
| Risk | Medium–high (duplicates, wrong brand) |
| Required authority | Governed INSIZE identity registries; brand rules |
| Owner decision | Alias / duplicate canonical choices |
| Automation readiness | Deterministic identity rules only where already governed |
| Dependencies | Before commercial activation of affected rows |

### Wave G — Multi-blocker long tail + archival

| Field | Value |
|-------|-------|
| Products | 1524 four-blocker archival; other 2–3 blocker mixes |
| Expected sellable gain | Long-tail; treat 1524 as F8 unless Owner overturns |
| Risk | Low if left alone; high if force-sold |
| Required authority | Full commercial stack |
| Owner decision | Keep as reference/archival? |
| Automation readiness | Not recommended |
| Dependencies | Waves A–F |

## Explicit non-waves

- No Production UPDATE SQL in this pack.
- No Wave 1B APPLY.
- No Hesabfa stock-driven availability until semantics PROVEN.
