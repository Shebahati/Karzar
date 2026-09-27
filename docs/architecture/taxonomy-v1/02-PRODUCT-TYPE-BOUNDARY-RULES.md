# Product Type Boundary Rules

**Status:** Proposed design (Phase 1A)

---

## 1. Product Type creation criteria

A new Product Type **SHOULD** exist when products differ in a **material** way on one or more of:

- engineering function
- physical / measurement working principle
- fundamental geometry that **defines** identity (not mere size)
- required property schema (many meaningless or contradictory properties if merged)
- applicable specialist standards treating them as distinct classes
- workpiece interaction mode (for cutting items)

A new Product Type **SHOULD NOT** exist merely for different:

brand · series · model · size · range · diameter · length · material · coating · grade · accuracy value · resolution value · interface **size** · thread size · flute count · tooth count · color · pack qty · origin · stock · price

### Exception criteria (allowed splits despite “should not”)

Create / keep a Product Type when **all** hold:

1. Specialist standard or strong OEM technical taxonomy treats them as different classes; **and**
2. Core mandatory properties diverge (different dimensions/units/evidence); **and**
3. Merging would force `NOT_APPLICABLE` on a large share of required properties; **and**
4. Domain Steward records `TCR-1` with evidence.

---

## 2. KARZAR PRODUCT TYPE SPLIT TEST — PTST-1

Apply **in order**. Stop at first decisive terminal rule.

| Step | Question | If YES | If NO |
|------|----------|--------|-------|
| Q1 | Fundamentally different engineering **functions**? | Continue | lean SAME |
| Q2 | Fundamentally different physical / measurement **principles**? | Continue | — |
| Q3 | Materially different **required property schema**? | Continue | — |
| Q4 | Geometry difference **defines identity** (not size/tolerance)? | Continue | — |
| Q5 | Authoritative technical standard treats as different classes/types? | Strong NEW signal | — |
| Q6 | Combining makes required properties meaningless or heavily conditional? | Strong NEW signal | — |
| Q7 | Distinction is merely a **value of an existing Property**? | **SAME_PRODUCT_TYPE** (terminal) | — |
| Q8 | Distinction is merely **Application/context**? | **SAME_PRODUCT_TYPE** (terminal) | — |
| Q9 | Distinction is merely **interface/compatibility size or standard family** without holding-principle change? | Prefer Property/TechClass; usually **SAME** holder PT | — |
| Q10 | Distinction is marketing / brand / series / trade vocabulary? | **SAME_PRODUCT_TYPE** (terminal) | — |

### Deterministic decision rule

```text
IF Q7 OR Q8 OR Q10 = YES → SAME_PRODUCT_TYPE
ELSE IF Q9 = YES AND Q1–Q4 all NO → SAME_PRODUCT_TYPE
   (represent as Property / Compatibility / Technical Class)
ELSE IF (Q1 OR Q2) AND (Q3 OR Q6) → NEW_PRODUCT_TYPE
ELSE IF Q5 AND (Q3 OR Q4 OR Q6) → NEW_PRODUCT_TYPE
ELSE IF Q4 AND Q3 → NEW_PRODUCT_TYPE
ELSE IF any of Q1–Q6 YES but evidence thin → NEEDS_DOMAIN_REVIEW
ELSE → SAME_PRODUCT_TYPE
```

No numeric scoring. Evidence class MUST be recorded (`STANDARD-BACKED` / `OEM-BACKED` / `ENGINEERING-INFERENCE` / `KARZAR-GOVERNANCE-DECISION`).

---

## 3. KARZAR PROPERTY BOUNDARY TEST — PBT-1

| Case | Verdict | Rationale | Evidence class |
|------|---------|-----------|----------------|
| Digital vs Vernier Caliper | **Property** `readout_type` | Same measuring function/jaw geometry family; schema shared; ADR-015 forbids readout as PT | KARZAR-GOVERNANCE-DECISION + ENGINEERING-INFERENCE |
| Digital vs Dial Caliper | **Property** `readout_type` | Same as above | same |
| General-purpose vs Blade Caliper | **Product Type** | Jaw/blade geometry changes measurement capability + schema emphasis | ENGINEERING-INFERENCE (aligns with live `BLADE_CALIPER`) |
| Outside vs Inside Micrometer | **Product Type** | Different measuring contacts/principles of application | ENGINEERING-INFERENCE + OEM-BACKED |
| Digital Level vs Level | **Property** (default) | Same instrument class; readout/electronics — see review of live over-split | KARZAR-GOVERNANCE-DECISION |
| Carbide vs HSS Drill | **Property** `cutting_material` / substrate | Same twist-drill function; material is characteristic | ETIM-like Feature principle + ENGINEERING-INFERENCE |
| Square vs Ball Nose End Mill | **Product Type** | End geometry defines machining engagement identity | ENGINEERING-INFERENCE + OEM-BACKED |
| 2D vs 3D vs 4D vs 5D U-Drill | **Property** `length_ratio` / L/D class | Same indexable drill identity; performance ratio | ENGINEERING-INFERENCE |
| BT40 vs BT50 holder | **Property** `taper_size` (+ Compatibility) | Size within BT family | ENGINEERING-INFERENCE |
| BT vs HSK holder | **Property / Technical Class** `taper_interface` — **not** Product Type by itself | Interface standard ≠ holding principle; PT = chuck/arbor kind | ENGINEERING-INFERENCE |
| Mechanical vs Hydraulic Vise | **Property** `actuation` | Same machine-vise identity; actuation method | ENGINEERING-INFERENCE |
| Turning vs Milling Insert | **Product Type** | Distinct cutting-item systems, geometries, ISO insert conventions | ISO-ALIGNED (ISO 13399 cutting item) + OEM-BACKED |
| Positive vs Negative Insert | **Property** / geometry attribute | Rake/clearance system within insert type | ENGINEERING-INFERENCE |
| Coated vs Uncoated Insert | **Property** `coating` | Consumable characteristic | ENGINEERING-INFERENCE |
| 3-flute vs 4-flute End Mill | **Property** `flute_count` | Same end-mill type | ENGINEERING-INFERENCE |
| Through-coolant vs non | **Property** `coolant_delivery` | Feature within drill/end-mill type | ENGINEERING-INFERENCE |
| Metric vs Imperial thread gauge | **Property** `thread_standard` / unit system | Same gauge type | ENGINEERING-INFERENCE |

---

## 4. Case study — Calipers

**Live Product Type:** `GEN_CALIPER` (General-purpose Caliper)  
**Active Definition properties (Phase 0B):** `measurement_range`, `resolution`, `accuracy`, `data_output`, `material`, `standard_ref`

**Constitution rule (freeze):**

> Readout mechanism alone (**digital / vernier / dial**) **DOES NOT** create a Product Type.

**Qualified exception:** none by default. If a “caliper” variant changes jaw geometry or measuring principle so the shared Definition becomes incoherent → separate Product Type (already seen: `BLADE_CALIPER`, groove/point variants).

**Against Proposed master seed:** `type.caliper.digital|vernier|dial` as Product Types are **outdated** — treat as Property Values / synonyms.

**INSIZE 1108 pilot:** Compatible with `GEN_CALIPER` + readout/Facts — do not explode types per display.

---

## 5. Case study — Cutting tools (ISO-ALIGNED)

Conceptual stack (ISO 13399-inspired vocabulary — **not** claiming full conformity):

| Concept | Karzar home |
|---------|-------------|
| Cutting item (indexable insert) | Family Inserts → Product Types by process/system |
| Tool item / tool body | Product Types (holders for inserts, solid tools) |
| Adaptive item | Toolholding Product Types / Compatibility |
| Assembly | Relationship / kit (`PART_OF`) |
| Solid cutting tool | End mill / twist drill Product Types |

### Inserts

| Candidate | Verdict |
|-----------|---------|
| Turning Insert | **Product Type** |
| Milling Insert | **Product Type** |
| Grooving / Parting Insert | **Product Type** (or sub-type under parting system — Domain review if schema shared) |
| Threading Insert | **Product Type** |
| Drilling Insert | **Product Type** (for indexable drill inserts) |
| shape, clearance, tolerance, chipbreaker, grade, coating, substrate, corner radius, hand, size | **Properties** |

### End mills

| Candidate | Verdict |
|-----------|---------|
| Square End Mill | **Product Type** |
| Ball Nose End Mill | **Product Type** |
| Corner Radius End Mill | **NEEDS_DOMAIN_REVIEW** (often variant of square with `corner_radius` Property) |
| Chamfer Mill | **Product Type** |
| Taper End Mill | **Product Type** |
| Roughing End Mill | **Property** `profile` / tooth form **or** PT if schema diverges strongly |
| carbide/HSS, coating, flutes, helix, diameters, lengths | **Properties** |

### Drills

| Candidate | Verdict |
|-----------|---------|
| Twist Drill | **Product Type** |
| Center Drill | **Product Type** |
| Indexable Drill (U-Drill) | **Product Type** |
| Annular Cutter | **Product Type** |
| Step Drill | **Product Type** |
| Gun Drill / Spade Drill | **Product Type** |
| HSS / carbide / cobalt / 2D–5D / coolant / diameter / point angle | **Properties** (or Technical Class only if multi-property system) |

---

## 6. Case study — Toolholding

| Candidate | Verdict |
|-----------|---------|
| ER Collet Chuck | **Product Type** (holding principle) |
| Hydraulic Chuck | **Product Type** |
| Shrink Fit Holder | **Product Type** |
| Shell / Face Mill Arbor | **Product Type** |
| Boring Bar Holder | **Product Type** |
| VDI Toolholder | **Product Type** *or* interface Property on lathe toolholder PT — **NEEDS_DOMAIN_REVIEW** |
| Pull Stud | **Product Type** (adaptive accessory item) + Compatibility |
| Collet | **Product Type** (consumable adaptive) + Compatibility |
| BT / HSK / SK / CAT as names | **Property** `taper_interface` (+ size) — **not** Product Type alone |
| Master seed `type.holder.bt` / `type.holder.hsk` | **REJECT as Product Types** |

---

## 7. Case study — Workholding

| Candidate | Verdict |
|-----------|---------|
| Machine Vise | **Product Type** |
| Precision Vise | Often **Property** `precision_class` on Machine Vise — review |
| Hydraulic / Mechanical / Pneumatic Vise | **Property** `actuation` |
| 3-Jaw / 4-Jaw Chuck | **Product Type** (or jaw-count Property on Lathe Chuck PT — prefer PT split if markets/schemas differ) |
| Collet Chuck (workholding) | **Product Type** |
| Rotary Table | **Product Type** |
| V-Block | **Product Type** (live `V_BLOCK`) |
| Clamp | Family/Type by clamp kind |

**Actuation** defaults to Property, not Product Type.

---

## 8. Property-schema principle

> Products that share fundamental engineering identity and can be described by the **same core Property Definition** SHOULD share the same Product Type.

**Split when merging causes:** many meaningless properties · different mandatory dimensions · different standards · different working principles · different geometry models · different evidence requirements.
