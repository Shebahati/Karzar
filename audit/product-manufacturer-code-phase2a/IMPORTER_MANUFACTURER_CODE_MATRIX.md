# Importer → manufacturer code matrix (Phase 2A)

No importer APPLY in this phase. Authority tiers per `PHASE-2A-MANUFACTURER-IDENTITY.md`.

| Importer | Current manufacturer identity source | Field name | Authority | Reliability | Exact canonical? | Phase 2C auto backfill? | Future code change? | Notes |
|----------|--------------------------------------|------------|-----------|-------------|------------------|-------------------------|---------------------|-------|
| INSIZE ShopMill | Reseller SKU + title | `sku`, `name` | 5 | Medium | No (not alone) | No | Yes — map official Order No. → canonical | Strong OEM catalogue exists offline; not wired as Tier 1 write |
| INSIZE official rebuild | Plan `official_model` | plan CSV / overlay | 1–3 (when OEM-linked) | High when official | Potentially | After explicit approval | Yes — controlled writer | Phase 2A reports readiness only |
| INSIZE PDF price list | PDF SKU | `sku` | 5–7 | Medium | No | No | Yes | SKU often equals OEM but not invariant |
| Mitutoyo | Row SKU + title | `sku`, `name` | 5–6 | Medium / risk | No | No | Yes — OEM Order No. outranks title | Reversed codes (e.g. 118-102 vs 102-118) critical |
| DASQUA | Catalog SKU | `sku` | 5 | Medium | No | No | Yes | Enrich writes tech specs, not OEM column |
| TERMA | Azarsanat import SKU/title | `sku`, `name`; `مدل`→`technical_specs.standard` | 5–6 | Low–medium | No | No | Yes | Model not top-level specs key |
| GUANGLU / GL | Price-list / catalog-target | PDF SKU | 5–7 | Low | No | No | Yes | Sparse catalog presence |
| ZCC.CT | Parse `manufacturer_code`/`model`/`part_number` | SourceProduct + sometimes `specs.model` | 4 | Medium–high for inserts | Not automatic | Tier-4 approval required | Yes — verify no destructive normalize | Field named manufacturer_code in source ≠ canonical Product field |
| SAN OU | `distributor_code` + enrich `model` | specs / reports | 4–5 | Medium | No | No | Yes — distributor ≠ OEM | Internal SO- ids are not OEM ordering codes |
| STC | ZCC parse pipeline (held/planned) | same as ZCC | 4 | Untested live | No | No | Yes | 0 live rows in Phase 0/1 snapshot |
| ASTPOWER / Azarsanat | Title `مدل` + SKU | `name`, `sku` | 6–7 | Low | No | No | Yes | TU-DR230 collision class |
| DCOIL | Catalog-target / PDF | SKU | 5–7 | Low | No | No | Yes | Sparse |
| Shams | Catalog-target | SKU | 5–7 | Low | No | No | Yes | Sparse |
| CSV seed | Opaque `specifications_json` | CSV columns | Unknown | Unknown | No | No | Yes — reject uncontrolled OEM write | Must not copy SKU→manufacturer_code |
| Admin create/edit | Manual name/SKU | ProductCreate/Update | N/A | N/A | No | No | Phase 2C controlled path | Phase 2A: manufacturer_code absent from write schemas |
| Generic product importer | Varies | Varies | ≤5 | Varies | No | No | Yes | Enforce canonical invariant at writer |

## Special reviews

### ZCC.CT
Source parse sets `manufacturer_code=model` and `part_number=manufacturer_key`. Live creates often omit model from specs or store truncated model with grade. Treat as Tier 4 structured source — **not** auto-canonical without authority review (hyphen/space/grade/chipbreaker handling).

### SAN OU
`distributor_code` is internal. Official `model` in enrich reports may be OEM-like but is not written as governed Product.manufacturer_code in Phase 2A.

### INSIZE
Many SKUs match official Order Nos. Still insufficient alone for `BACKFILL_EXACT`. Official catalogue / rebuild plan linkage required for Phase 2C.

### Mitutoyo
Do not trust title token order. OEM Order No. evidence must outrank legacy title formatting. Reversed pairs are `HOLD_IDENTITY_CONFLICT`.
