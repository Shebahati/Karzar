# Supplier Stock Authority

Independent commerce authority for Karzar public-sale activation.

```text
PRICE AUTHORITY  ≠  AVAILABILITY AUTHORITY
```

Never infer `AVAILABLE` from price, catalog inclusion, `is_active`, prior
`is_available`, or row existence.

This document is operational guidance for tooling under `scripts/catalog_target/`
and CLIs `validate_supplier_stock.py` / `map_supplier_stock.py`. It does **not**
set Canon-Lock Accepted policy by itself.

---

## 1. Canonical fields

| Field | Role |
|-------|------|
| `supplier` | Who supplied the file |
| `brand` | Canonical brand key (DASQUA, TERMA, …) |
| `source_date` | Authority date of the stock snapshot |
| `source_version` | Optional revision/label |
| `supplier_sku` | Optional supplier-side code |
| `manufacturer_sku` | Manufacturer / catalog SKU |
| `model` | Exact model identifier when SKU absent |
| `availability_status` | Textual stock state |
| `quantity` | Numeric sellable stock when semantics allow |
| `warehouse` | Optional location |
| `notes` | Free text (never treated as status without legend) |

### Mandatory for `SOURCE_AUTHORITY_VALID=YES`

1. `brand`
2. `manufacturer_sku` **or** a deterministic exact model identifier (`model`)
3. At least one of: `availability_status`, `quantity`
4. `source_date` present in-file **or** independently established and recorded in
   the source manifest (`source_date` / `received_at` policy)

---

## 2. Normalized availability statuses

```text
AVAILABLE
UNAVAILABLE
UNKNOWN
```

### Quantity (only when quantity = sellable stock)

| Quantity | Status |
|----------|--------|
| `> 0` | `AVAILABLE` |
| `= 0` | `UNAVAILABLE` |
| blank / non-numeric / negative | `UNKNOWN` (and `invalid_quantity` when non-blank invalid) |

If the source legend does **not** state that quantity is sellable stock, quantity
must not drive status → treat as insufficient semantics (`SOURCE_AUTHORITY_VALID=NO`
unless textual status is authoritative).

### Textual status (explicit only)

| Supplier value (examples) | Normalized |
|---------------------------|------------|
| موجود, available, in stock | `AVAILABLE` |
| ناموجود, نا موجود, out of stock, unavailable | `UNAVAILABLE` |
| blank / unclear / undocumented code | `UNKNOWN` |

Do **not** interpret arbitrary numeric codes without a documented legend.

### Forbidden inferences

Never map any of the following to `AVAILABLE`:

- `price > 0`
- product / row exists
- site `is_active=true`
- prior site `is_available=true`
- supplier catalogue inclusion

---

## 3. Freshness (stricter than price)

Configurable thresholds (defaults in code; do not silently change business policy):

| Class | Default stock age |
|-------|-------------------|
| `CURRENT_ENOUGH` | ≤ 14 days |
| `AGING_BUT_USABLE` | ≤ 45 days |
| `STALE` | > 45 days |
| `UNKNOWN` | no parseable `source_date` |

Stock freshness is intentionally stricter than price freshness. Thresholds are
CLI/config knobs — operators must set them explicitly for each intake.

---

## 4. Exact catalog matching

Priority:

1. `EXACT_MANUFACTURER_SKU`
2. `EXACT_NORMALIZED_SKU` — only brand-approved deterministic normalization
3. `EXACT_MODEL` — only when brand policy explicitly permits

Forbidden: fuzzy, substring, nearest SKU, visual inference.

Match outcomes:

```text
EXACT_MATCH
AMBIGUOUS
NOT_FOUND
DUPLICATE_SOURCE
SOURCE_CONFLICT
```

### DASQUA adapter (narrow)

Reviewed pack-suffix rule only:

```text
site  NNNN-NNNN
  ↔
source NNNN-NNNN-A
```

when the trailing segment is exactly `-A` (case-insensitive) and the base maps
**uniquely**. Do not extend to `-B`, multi-segment suffixes, or fuzzy stems.

Primary path remains conservative `normalize_sku` exact equality.

### TERMA adapter

- Map stock by exact SKU / approved exact model only.
- Do **not** use a stock file to repair price exceptions:
  - `CDA100-300` (duplicate price-source code)
  - `MA250H-200`, `MD710-25` (OCR-truncated price rows)
- Stock authority never invents `base_price`.

---

## 5. TERMA price policy (kept separate)

Treat independently:

```text
SOURCE_PRICE
SOURCE_UNIT_NORMALIZATION
KARZAR_SELLING_PRICE_POLICY
```

Observations that are **not** future APPLY policy:

- filename `+25درصد`
- unlabeled PDF `قیمت` column
- live site ≈ PDF/10 × 1.05 on many rows

Do **not** encode ×1.05 (or extra ×1.25) as automatic selling-price policy.
A TERMA sale-wave APPLY requires an explicit pricing-policy authority.

---

## 6. Future activation gates

A SKU may enter a sale-wave plan only if **all** hold:

1. Exact catalog identity
2. Authoritative price + valid positive proposed selling price
3. Fresh authoritative stock = `AVAILABLE`
4. `is_active=true` and `deleted_at IS NULL`
5. Sale-safe buyer-facing identity/content
6. No source conflict

First-wave presentation: prefer `primary_image_present`.

### DASQUA preference (after stock arrives)

From active + exact + price-ready + sale-safe (~235), prefer the ~51 image-present
subset first. Do not force cohort size beyond evidence.

### TERMA preference (after stock arrives)

From ~177 active + price-ready + sale-safe + image-acceptable, plus **explicit**
selling-price policy validation before APPLY.

Allowed future commerce mutations: `base_price`, `is_available` only.

---

## 7. Source authority manifest

Every accepted supplier file must record:

```text
source_id
brand
supplier
original_filename
sha256
received_at
source_date
authority_type   # PRICE | AVAILABILITY | PRICE_AND_AVAILABILITY
parser_version
normalization_policy_version
```

Enough metadata must exist to reproduce any future sale-wave plan.

---

## 8. Operational workflow (default deny)

```text
Supplier file
→ immutable source capture
→ SHA256
→ semantic validation
→ freshness validation
→ exact SKU mapping
→ UNKNOWN/conflict rejection
→ merge with independent price authority
→ candidate pool
→ reviewed sale allowlist
→ guarded APPLY (owner-authorized)
```

Fail closed at every step. No APPLY in stock standardization/intake tooling.

---

## 9. Templates & tools

| Artifact | Path |
|----------|------|
| Spec | `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md` |
| EN CSV | `data/templates/supplier_stock_template_en.csv` |
| FA CSV | `data/templates/supplier_stock_template_fa.csv` |
| XLSX | `data/templates/supplier_stock_template.xlsx` |
| Library | `scripts/catalog_target/supplier_stock.py` |
| Brand/source inventory adapters (exceptions only) | `scripts/catalog_target/brand_source_inventory_adapters.py` |
| Validate CLI | `scripts/validate_supplier_stock.py` |
| Map CLI | `scripts/map_supplier_stock.py` |
| Plan schema | `data/templates/sale_wave_plan_schema.csv` |
| Tests | `tests/test_supplier_stock_authority.py` |

Evidence scratch: `.local-scratch/supplier-stock-authority-standard/`.

---

## 10. Brand-source semantic adapters (Owner-confirmed exceptions)

**Generic rule is unchanged:** `price does not imply stock`.

The default validator must **not** treat `price > 0` as `AVAILABLE` for arbitrary
price lists or brands.

Owner may confirm **source-specific** business semantics that a particular Google
Drive file is an operational **supplier inventory list**, even without a separate
موجود/ناموجود column. Those exceptions are recorded here and in
`scripts/catalog_target/brand_source_inventory_adapters.py`. They are **not**
global policy.

| Adapter ID | Source (exact path) | Brand | Availability rule | Provenance |
|------------|---------------------|-------|-------------------|------------|
| `DASQUA_GOOGLE_DRIVE_INVENTORY_LIST` | `/home/shebahati/KaZar/Product and Data Complete/اندازه گیری/داسکوا/لیست قیمت داسکوا +10 درصد.pdf` | DASQUA only | valid positive supplier price row ⇒ `AVAILABLE`; zero / blank / invalid ⇒ not available for activation | Owner correction 2026-09-09 |
| `TERMA_GOOGLE_DRIVE_INVENTORY_LIST` | `/home/shebahati/KaZar/Product and Data Complete/اندازه گیری/ترما/لیست قیمت ترما +25درصد.pdf` | TERMA only | valid positive supplier price row ⇒ `AVAILABLE`; zero / blank / invalid / unresolved ⇒ not available for activation | Owner correction 2026-09-09 |

TERMA unresolved exclusions (inventory semantics must **not** repair these):

```text
CDA100-300
MA250H-200
MD710-25
```

### Selling price remains separate

```text
GOOGLE DRIVE SUPPLIER LIST  →  supplier availability authority (adapter above)
SHOPMILL                    →  current Karzar selling-price authority (Toman)
```

Do **not** use the supplier PDF price as controlling Karzar `base_price` when a
valid exact Shopmill customer price exists. Public-sale cohorts require the
intersection of supplier-available ∧ Shopmill-price-ready ∧ active ∧ sale-safe
(and preferred image readiness for Wave 1).

---

## 11. Versions

| Key | Value |
|-----|-------|
| `parser_version` | `supplier_stock/1.0.0` |
| `normalization_policy_version` | `supplier_stock_norm/1.0.0` |
| `brand_source_inventory_adapters` | `brand_source_inventory_adapters/1.0.0` |
