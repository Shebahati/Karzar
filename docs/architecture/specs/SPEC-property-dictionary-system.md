---
id: SPEC-property-dictionary-system
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-domain-model.md
  - app/services/spec_template_service.py
owner: Property Steward + PIM Architect
task_id: KB-001
---

# SPEC — Property Dictionary System

**Status:** Proposed  
**Purpose:** Governed technical specification system (Property → Template → Fact)  
**Non-goals:** Enabling JSONB dual-write · dropping JSONB · AI inventing values · DDL in this PR

---

## 1. Why this exists

As-built specs are uncontrolled JSONB with measurement-biased defaults (`app/db/models/product.py:49-68`) and in-code admin templates (`app/services/spec_template_service.py`). Bible **P5–P6** require FA/EN mapping before Facts dual-write and keep JSONB operational until approved migration.

This SPEC defines the **target governed system** and the strangler path from today’s keys.

---

## 2. Core constructs

```text
Specification Definition (Property)
        │
        ├── included in → Specification Template (per family/type)
        │
        └── valued as → Specification Fact (on PKE)
                              │
                              └── supported by → Evidence / Document
```

| Construct | One-line |
|-----------|----------|
| **Property / Definition** | Meaning of an attribute (`accuracy`) |
| **Template** | Which Properties apply to a Caliper vs Insert |
| **Fact** | Product + Property + Value + Unit + Evidence |
| **Unit** | Canonical code in a dimension |
| **Alias** | FA/EN labels and legacy JSON keys mapping to one Definition |

---

## 3. Property Definition

### 3.1 Attributes

| Field | Required | Description |
|-------|----------|-------------|
| `definition_id` | Yes | Stable opaque ID |
| `key` | Yes | Canonical snake_case English key (`measurement_range`) |
| `data_type` | Yes | See §5 |
| `unit_dimension` | MAY | `length`, `angle`, `mass`, `dimensionless`, … |
| `default_unit` | MAY | e.g. `mm` |
| `label_en` | Yes | English display |
| `label_fa` | Yes | Persian display |
| `description_en/fa` | MAY | Steward help text |
| `validation` | Yes | Rules object (§6) |
| `enum_values` | If enum | Closed list with FA/EN labels |
| `comparable` | Yes | Whether usable in product compare |
| `filterable` | Yes | PLP facet candidate |
| `customer_facing` | Yes | If false, ops-only |
| `version` | Yes | SemVer of definition semantics |
| `status` | Yes | `draft` \| `active` \| `deprecated` |
| `steward` | SHOULD | Role/owner |
| `supersedes` | MAY | Prior definition_id |

### 3.2 Example Definitions (seed candidates)

| key | label_fa | label_en | type | unit | Notes |
|-----|----------|----------|------|------|-------|
| `measurement_range` | بازه اندازه‌گیری | Measurement range | range | mm | Shared metrology |
| `resolution` | تفکیک‌پذیری | Resolution | number | mm | Shared |
| `accuracy` | دقت | Accuracy | quantity | mm | Often ± qualifier |
| `display_type` | نوع نمایش | Display type | enum | — | vernier/dial/digital |
| `data_output` | خروجی داده | Data output | boolean | — | |
| `protection_rating` | درجه حفاظت | IP rating | enum | — | IP54/IP65/IP67 |
| `material` | جنس | Material | enum/string | — | Shared many families |
| `standard_ref` | استاندارد مرجع | Reference standard | string | — | Links Standard node preferred |
| `spindle_type` | نوع اسپیندل | Spindle type | enum | — | Micrometer-specific |
| `insert_shape` | شکل اینسرت | Insert shape | enum | — | Insert-specific |
| `cutting_diameter` | قطر برش | Cutting diameter | number | mm | End mill / drill |
| `shank_diameter` | قطر شفت | Shank diameter | number | mm | |
| `flute_count` | تعداد لبه | Flute count | integer | — | |
| `coating` | پوشش | Coating | enum | — | TiN, TiAlN, … |
| `taper_interface` | رابط مخروطی | Taper interface | enum | — | BT40, HSK-A63, … |

---

## 4. Templates

### 4.1 Template attributes

| Field | Description |
|-------|-------------|
| `template_id` / `key` | Stable (`caliper_digital`, `micrometer_outside`, `insert_turning`, `tool_holder_bt`) |
| `applies_to_node_ids` | Taxonomy family/type nodes |
| `properties[]` | Ordered list of `{definition_id, required, sort_order, group}` |
| `version` / `status` | Governance |
| `strangler_legacy_key` | Maps from as-built `spec_template_key` when 1:1 |

### 4.2 Illustrative templates

#### Caliper Template (`caliper`)

Required/should: `measurement_range`, `resolution`, `accuracy`, `display_type`  
Optional: `data_output`, `protection_rating`, `material`, `standard_ref`

#### Micrometer Template (`micrometer`)

Shared: `measurement_range`, `resolution`, `accuracy`  
Specific: `spindle_type`, `anvil_type`, `flatness`

#### Insert Template (`insert`) — strangler from as-built `insert`

`insert_shape`, `insert_size`, `grade`, `coating`, `chipbreaker`, `application_material`

#### Tool Holder Template (`tool_holder`) — strangler from `insert_holder`

`taper_interface`, `gauge_length`, `clamping_type`, `coolant_through`

#### End Mill / Drill — strangler from `end_mill` / `drill`

`cutting_diameter`, `shank_diameter`, `flute_count`, `coating`, `material`, `overall_length`

### 4.3 Inheritance

1. Templates **compose** Definitions (shared IDs) — do not copy attributes.  
2. Child type templates MAY **extend** family templates (add properties; MUST NOT redefine shared Definition semantics).  
3. Category walk-up today (`spec_template_service` resolve) stranglers to: Type node → Family template → Domain default.

---

## 5. Datatype system

| data_type | Value shape | Example |
|-----------|-------------|---------|
| `boolean` | true/false | `data_output=true` |
| `integer` | int | `flute_count=4` |
| `number` | decimal | `resolution=0.01` |
| `quantity` | `{magnitude, qualifier?}` | `{magnitude: 0.02, qualifier: "±"}` |
| `range` | `{min, max}` | `{min: 0, max: 150}` |
| `enum` | enum code | `display_type=digital` |
| `string` | short text | free codes when enum not ready |
| `string_array` | list | button labels |
| `ref_standard` | standard_id | preferred over free string |
| `ref_document` | document_id | |

**MUST NOT** store units inside free-text values for comparable properties (`"0.01mm"` as opaque string is transitional debt).

---

## 6. Units

| Dimension | Canonical | Allowed aliases (normalize to canonical) |
|-----------|-----------|------------------------------------------|
| length | `mm` | `mm`, `میلی‌متر`; convert `in`/`"` with explicit conversion flag |
| angle | `deg` | `°`, `degree` |
| mass | `g` | `kg` convert |
| dimensionless | `1` | — |
| hardness | steward-defined | HRC, HV — no silent convert |

Rules:

1. Facts store **canonical unit**.  
2. Display MAY localize unit labels FA/EN.  
3. Cross-unit compare requires conversion table version pin.

---

## 7. Validation rules

| Rule class | Examples |
|------------|----------|
| type | value matches data_type |
| required | template marks required → block publish |
| min/max | magnitude within bounds |
| enum membership | code ∈ enum_values |
| unit compatibility | unit ∈ dimension |
| range order | min ≤ max |
| regex | SKU-like codes |
| mutual exclusion | steward-defined |

Validation runs at: import TECHNICAL stage, admin save, publish transition.

---

## 8. Localization (FA/EN)

Bible **P5**: FA and EN keys that mean the same concept MUST map to one Property.

| Mechanism | Rule |
|-----------|------|
| Labels | `label_fa` / `label_en` on Definition |
| Aliases | `aliases[]` include legacy JSON keys: `accuracy`, `دقت`, `range`, `بازه اندازه‌گیری` |
| Mapping table | Git `MAPPING-TABLE` per vendor (AODS artifact) |
| Customer UI | FA primary; EN secondary |
| Canonical key | Always English snake_case — never Persian as `key` |

`top:*` operational residue keys **MUST NOT** become customer-facing Properties (AODS mapping guidance).

---

## 9. Fact model

| Field | Required | Notes |
|-------|----------|-------|
| `fact_id` | Yes | |
| `entity_id` | Yes | PKE |
| `definition_id` | Yes | |
| `value` | Yes | Per datatype |
| `unit` | If dimensioned | Canonical |
| `qualifier` | MAY | ±, approx, max |
| `status` | Yes | asserted/published/disputed/deprecated |
| `source_id` | Yes for asserted+ | Provenance |
| `evidence_ids` | For publish of critical Facts | accuracy, standards |
| `recorded_at` / `recorder` | Yes | |
| `confidence` | MAY | AI suggestions |

**Publish policy:** Metrology-critical Facts (`accuracy`, `resolution`, tolerances) and any compliance-linked Fact **SHOULD** require Evidence before `published` (align Bible P4). Empty is honest.

---

## 10. Versioning & governance

| Change type | Process |
|-------------|---------|
| Add Property | Steward PR; status draft → active |
| Rename label | Allowed without new version |
| Change semantics/datatype/unit | New Definition version; migrate Facts; deprecate old |
| Remove Property | Deprecate; keep Facts readable |
| Template edit | Version bump; dry-run on sample SKUs |
| Dual-write JSONB↔Facts | **Board gate only** (Canon Lock §3 — not authorized here) |

Dictionary lives Git-first (YAML/JSON seed) until tables Accepted via ADR/RFC.

---

## 11. Strangler from as-built templates

| Legacy `spec_template_key` | Target template key | Notes |
|----------------------------|---------------------|-------|
| `measurement` | `caliper` / family split later | Over-broad today — seed Types refine |
| `insert` | `insert` | |
| `insert_holder` | `tool_holder` | |
| `end_mill` | `end_mill` | |
| `drill` | `drill` | |
| `default` | `industrial_default` | material/standard/coating |

Legacy JSON keys map via aliases → Definitions; unread keys quarantine in import reports.

---

## 12. AI rules (property scope)

| Allowed | Forbidden |
|---------|-----------|
| Suggest Definition for unknown source key | Invent numeric Fact values |
| Suggest template classification | Publish Facts |
| Draft FA labels for steward review | Collapse distinct concepts into one key without review |

---

## 13. Requirements

| ID | Criterion |
|----|-----------|
| **PD-R1** | Definition / Template / Fact separated |
| **PD-R2** | Datatypes + units specified |
| **PD-R3** | FA/EN alias → one Definition |
| **PD-R4** | Shared Definitions across templates |
| **PD-R5** | Version/deprecate rules |
| **PD-R6** | Strangler from `spec_template_service` keys |
| **PD-R7** | Dual-write not authorized by this SPEC |

---

## 14. Open questions

| ID | Question |
|----|----------|
| **UD-03** | Seed scope: metrology-only vs all L1 domains first? |
| **PD-Q1** | Hardness / grade systems — separate dimension pack? |
| **PD-Q2** | Store dictionary in DB at v1 or Git-seeded read model? |
