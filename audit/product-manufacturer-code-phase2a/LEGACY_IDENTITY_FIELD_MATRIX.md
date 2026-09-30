# Legacy identity field matrix (Phase 2A)

Rule: **legacy/source field ≠ canonical automatically.**  
Canonical field: `products.manufacturer_code` (nullable; NULL after Phase 2A migration).

| Field | Where used | Authority | Future role | Canonical? |
|-------|------------|-----------|-------------|------------|
| `products.manufacturer_code` | ORM / admin read (Phase 2A) | Tier 3 when non-null (verified) | Sole canonical OEM identity | **Yes** (when non-null) |
| `products.sku` | Commerce identity, search, imports | Karzar | Remain Karzar SKU | No |
| `products.slug` | URL / SEO | Karzar | Unchanged by naming | No |
| `products.name` | Display title | Mixed / legacy | Rename only in later phases | No |
| `specifications.manufacturer_code` | Rare / planned import payloads | Source-dependent | Evidence only until Phase 2C | No |
| `specifications.model` | ZCC live rows; some overlays | Source-dependent (often Tier 4) | Candidate evidence | No |
| `specifications.part_number` | ZCC parse / phase2 plans | Source-dependent | Candidate / SKU seed | No |
| `specifications.oem_model` | Audit overlays | Research | Candidate | No |
| `specifications.official_model` | INSIZE rebuild plan overlays | Near-OEM when from official rebuild plan | Candidate; Phase 2C research | No |
| `specifications.source_product_id` | ZCC / scrapers | Reseller/source | Traceability | No |
| `specifications.source_identity_key` | ZCC | Source composite key | Traceability | No |
| `specifications.distributor_code` | SAN OU | Distributor internal | Not OEM ordering code | No |
| `source_internal_sku` | Import manifests (not Product column) | Supplier | Matching only | No |
| Title `کد` / `مدل` tokens | Legacy names | Tier 6 | Audit candidate only | No |

Do not delete old fields. Do not mutate existing JSONB in Phase 2A.
