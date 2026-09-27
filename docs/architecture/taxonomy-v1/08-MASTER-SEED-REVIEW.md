# Proposed Master Seed Review

**Subject:** `docs/architecture/specs/SPEC-industrial-taxonomy-master-seed.md` (**Proposed** — not Accepted)  
**Phase 1A verdict:** **Requires major amendment before any runtime load.**

---

## Overall

| Question | Answer |
|----------|--------|
| Still valid as-is? | **NO** |
| Requires amendment? | **YES** |
| Major outdated assumptions? | Readout-as-Type; Material-as-Type; Interface-as-Type |

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
| **CONSTITUTION RULE** | Knowledge Category not mandatory |
| **PROPOSED DIRECTION** | **PROPOSED AMENDMENT**; master seed should not require KC nodes |

---

## Usable fragments

- Domain/Family inventory sketches for metrology and cutting remain useful as **brainstorm input**.
- Commerce L1 bridge ideas (56/81/87 → metrology) remain observationally valid.
- Do **not** load seed into `knowledge_taxonomy_nodes` until amended and Board-reviewed.
