# Hesabfa (حسابفا) Level-4 integration

## Scope (locked product decisions)

| Concern | Direction |
|---------|-----------|
| Catalog & prices | **Site is source of truth** — do not push catalog/prices site→Hesabfa as primary |
| Stock / warehouse counts | **Hesabfa only** — site never stores or displays numeric stock; only **موجود / ناموجود** (`is_available`) |
| Item shells | **Site → Hesabfa** create/upsert on product save + backfill (`ProductCode` = site `sku`, stock left at **0**) |
| Contacts | One Hesabfa contact **per customer** (create/link on demand by phone) |
| Inquiry / proforma | **Not synced** |
| Sale invoice | Created in Hesabfa **after payment verify** (hook wired; skipped while `HESABFA_TEST_MODE=true`) |
| Admin metrics | **No Hesabfa numbers in admin** — website paid sales / availability only; never sales-summary or stock from Hesabfa |
| Categories | **Not synced** by default — shop IA ≠ accounting `nodeFamily`; match products by SKU only |

## Environment variables (VPS / `.env`)

Set these on the API host only (Compose env file or `/opt/karzar/.deploy-secrets`). **Never commit real keys.**

```bash
HESABFA_ENABLED=true
HESABFA_API_KEY=...
HESABFA_LOGIN_TOKEN=...
HESABFA_BASE_URL=https://api.hesabfa.com/v1
HESABFA_TIMEOUT_SECONDS=15
# true = invoice writes skipped; item push still allowed
HESABFA_TEST_MODE=true
# Admin must never consume Hesabfa reads (sales totals, stock, etc.)
HESABFA_ADMIN_READS_ENABLED=false
HESABFA_CURRENCY_UNIT=rial
HESABFA_CURRENCY_CODE=IRR
```

### Staging checklist

1. Add vars to API container on VPS `195.177.255.198`.
2. `alembic upgrade head` (hesabfa tables + `products.is_available`).
3. Keep `HESABFA_TEST_MODE=true` until verified.
4. Keep `HESABFA_ADMIN_READS_ENABLED=false` (default).
5. `POST /api/v1/hesabfa/items/push` to backfill site products (qty 0).
6. Zero any leftover `products.stock_quantity` from older Hesabfa pulls (`scripts/clear_hesabfa_pulled_stock.py`).
7. When gateway live: `HESABFA_TEST_MODE=false`.

## Admin API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/hesabfa/status` | Enabled / configured / test mode / `admin_reads_enabled` |
| POST | `/api/v1/hesabfa/mappings/sync` | Match site `sku` ↔ Hesabfa `ProductCode` |
| POST | `/api/v1/hesabfa/items/push` | Create/upsert site products in Hesabfa (stock 0) |
| POST | `/api/v1/hesabfa/stock/sync` | **Deprecated no-op** — Hesabfa→site quantity pull disabled |
| GET | `/api/v1/hesabfa/sales-summary` | **Website paid sales only** — Hesabfa fields always null |

## What admin must NOT show

- Hesabfa total sales / invoice counts
- Warehouse quantities or inventory value pulled from Hesabfa
- Any other Hesabfa-sourced metric widgets

Dashboard keeps **فروش وبسایت (پرداخت‌شده)** from local orders only.

## Inventory policy

- Warehouse counts: **Hesabfa only**.
- Site: `is_available` boolean. Storefront shows **موجود** / **ناموجود**.
- Do **not** import `GetQuantity` into the site (worker removed; `/stock/sync` is a no-op).
- Product create/update pushes Hesabfa item shell at qty 0 when integration is enabled.
- Legacy `stock_quantity` column is kept at `0` (cleared after older pulls).

## Categories

Hesabfa `item/save` supports `nodeFamily`, but site categories are **not synced** (shop IA ≠ accounting folders). Match by SKU only.

## Payment hook

`verify_order_payment` → `maybe_create_invoice_after_payment`. Failures never roll back payment. `HESABFA_TEST_MODE=true` → skip with status `skipped`.

## Invoice money / tax

Karzar `OrderItem.unit_price` is the **final customer-facing gross** (same meaning as
`Product.base_price` for payment). Hesabfa sale invoice lines are tax-exclusive in
the public plugin contract:

```text
line_total = unitPrice × quantity − discount + tax
invoice_total ≈ Σ(line_total) + freight
```

Evidence (official WooCommerce Hesabfa plugin `ssbhesabfa`):

| Field | Plugin meaning |
|-------|----------------|
| `UnitPrice` | WooCommerce line `subtotal / quantity` (net of line tax) |
| `Discount` | `subtotal − total` |
| `Tax` | absolute `subtotal_tax` |
| `Freight` | `shipping_total + shipping_tax` |

### Current Karzar fail-safe (accounting tax unproven)

`product.tax_percent` / snapped `OrderItem.tax_percent` is **not** proven to be
authoritative embedded-VAT metadata (create/admin default `9` vs ORM/DB `0`;
imports often omit an intentional accounting choice). Inventing a net/tax split
from that field would misclassify VAT while the customer already paid the gross.

Until Owner/accounting confirms the metadata:

| Field | Karzar behavior |
|-------|-----------------|
| `unitPrice` | Full gross (paid) unit amount in Hesabfa money |
| `tax` | `0` |
| `freight` | `shipping_customer_cost` (0 for `receiver_due`) |
| `discount` | `0` |

This keeps:

```text
Σ(unitPrice × quantity) + freight == order.estimated_total
```

(within currency conversion), without claiming a VAT breakdown.

### Future Owner-gated inclusive extraction

Helper `_inclusive_net_unit_and_tax` implements:

1. Convert gross unit toman → Hesabfa money (`rial` = ×10 integer; `toman` = 0.01).
2. `gross_line = gross_unit × quantity`.
3. `net_line = round(gross_line / (1 + tax_percent/100))` (`ROUND_HALF_UP`).
4. `net_unit = floor(net_line / quantity)` to the currency quantum (keeps `tax >= 0`).
5. `tax = gross_line − net_unit × quantity`.

Enable only after Owner confirms `tax_percent` means VAT already included in
`base_price`. Never send `unitPrice = gross` together with `tax = gross × rate`
(that double-counts tax).
