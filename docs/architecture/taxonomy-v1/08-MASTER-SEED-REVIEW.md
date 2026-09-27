# Proposed Master Seed Review

**Subject:** `docs/architecture/specs/SPEC-industrial-taxonomy-master-seed.md` (**Proposed** — not Accepted)  
**Phase 1A verdict:** **Requires major amendment before any runtime load.**  
**Steward freeze:** Workshop / Hand Tools Domain **REJECTED** (`TX-OWNER-001`, 2026-09-27). Knowledge Category **not mandatory** (Steward-approved).

---

## Overall

| Question | Answer |
|----------|--------|
| Still valid as-is? | **NO** |
| Requires amendment? | **YES** |
| Major outdated assumptions? | Readout-as-Type; Material-as-Type; Interface-as-Type; any Workshop/Hand Tools Domain |
| Owner scope | Workshop & Hand Tools **OUT_OF_SCOPE** — no target Domain/L1 |

---

## Pattern findings

### 1. Digital / Vernier / Dial Caliper as Product Types

| Field | Content |
|-------|---------|
| **CURRENT** | `type.caliper.digital\|vernier\|dial` under `fam.calipers` |
| **PROBLEM** | Treats readout as engineering identity; conflicts ADR-015 Decision 7 and PTST-1/PBT-1 |
| **CONSTITUTION RULE** | Readout alone → Property; Family=Caliper; PT=GEN_CALIPER (+ geometry variants) |
| **PROPOSED DIRECTION** | Replace three types with Property Values / synonyms; keep geometry-based caliper PTs |

### 2. Carbide Drill / HSS Drill as Product Types

| Field | Content |
|-------|---------|
| **CURRENT** | `type.drill.carbide`, `type.drill.hss` |
| **PROBLEM** | Material encoded as Type → PT explosion; ETIM Feature principle violated |
| **CONSTITUTION RULE** | PTST-1 Q7 → SAME; Property `cutting_material` |
| **PROPOSED DIRECTION** | Single Twist Drill (and other drill PTs); material Property |

### 3. BT Holder / HSK Holder as Product Types

| Field | Content |
|-------|---------|
| **CURRENT** | `type.holder.bt`, `type.holder.hsk` |
| **PROBLEM** | Interface standard ≠ product identity |
| **CONSTITUTION RULE** | Property/TechClass `taper_interface`; PT = chuck/arbor holding principle |
| **PROPOSED DIRECTION** | Delete interface-as-type rows; add interface Property + Compatibility |

### 4. Technical classification examples in Accepted SPEC

| Field | Content |
|-------|---------|
| **CURRENT** | SPEC-industrial-taxonomy-model §3.5 lists material system & mounting interface as technical classification examples |
| **PROBLEM** | Easy to dump Properties into Technical Class |
| **CONSTITUTION RULE** | Prefer Property; Technical Class only if non-reducible |
| **PROPOSED DIRECTION** | **PROPOSED AMENDMENT** to Accepted SPEC prose clarifying Property-first default |

### 5. Knowledge Category level

| Field | Content |
|-------|---------|
| **CURRENT** | Domain → Family → Knowledge Category → Product Type |
| **PROBLEM** | Redundant with nested Family |
| **CONSTITUTION RULE** | Knowledge Category not mandatory — **STEWARD-APPROVED** |
| **PROPOSED DIRECTION** | Prefer Domain → Family (nestable) → Product Type; master seed must not require KC nodes |

### 6. Workshop / Hand Tools Domain — REJECTED (`TX-OWNER-001`)

| Field | Content |
|-------|---------|
| **CURRENT / IMPLIED** | Any Domain or L1 for Workshop & Hand Tools / ابزارهای کارگاهی و دستی; catch-alls; handheld-only expansion shells |
| **PROBLEM** | Owner has removed this scope from the Karzar catalog |
| **CONSTITUTION RULE** | **REJECTED — OWNER SCOPE DECISION**; no replacement catch-all; products → `CATALOG_EXIT` |
| **PROPOSED DIRECTION** | Do **not** introduce `dom.workshop` / Hand Tools Domain; mark sole-scope concepts `OUT_OF_SCOPE` |

#### Master-seed concepts — scope disposition

| concept_id | name_en | Disposition | Notes |
|------------|---------|-------------|-------|
| *(any proposed)* Workshop / Hand Tools Domain | — | **OUT_OF_SCOPE** / **REJECTED** | Must not appear in target taxonomy |
| `dom.power` | Power Tools | **OUT_OF_SCOPE** | Powered handheld / general workshop expansion — outside Owner catalog scope |
| `dom.safety` | Safety | **DEFERRED / OUT_OF_SCOPE for Phase 1B target Domains** | Not in frozen 7 Domains; do not use as Workshop catch-all |
| `dom.automation` | Automation | **DEFERRED** | Not in frozen 7 Domains |
| `dom.electrical` | Electrical | **DEFERRED / OUT_OF_SCOPE for Phase 1B target Domains** | Not in frozen 7 Domains |
| `app.workshop` | Workshop Measurement | **KEEP as Application** (metrology use-context) | **Not** a Hand Tools Domain — shop-floor measurement context only |

### 7. Target Domain set alignment

Master seed Domains must be rewritten to the Steward-frozen set of **seven** target Domains (Metrology, Cutting, Toolholding, Workholding, Machines, Thread Repair, Metalworking Fluids). Lubrication draft shell may map toward Metalworking Fluids & Lubricants — not Workshop.

---

## Usable fragments

- Domain/Family inventory sketches for metrology and cutting remain useful as **brainstorm input**.
- Commerce L1 bridge ideas (56/81/87 → metrology) remain observationally valid.
- Do **not** load seed into `knowledge_taxonomy_nodes` until amended and Board-reviewed.
- Do **not** invent a Workshop / Hand Tools Domain or catch-all L1 in any amendment.
