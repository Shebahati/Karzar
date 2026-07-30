---
id: SPEC-industrial-taxonomy-master-seed
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
  - scripts/seed_categories.py
  - project-management/DECISIONS.md
owner: Information Architect + Domain Architect
task_id: KB-001
---

# SPEC — Industrial Taxonomy Master Seed

**Status:** Proposed  
**Purpose:** Initial multi-dimensional taxonomy architecture (nodes + bridges)  
**Critical:** This does **NOT** replace commerce `categories`. Megamenu remains presentation over L1 (**D1**).

Node IDs below are **logical concept IDs** for design/seed files — not database serials.

---

## 1. Seed principles

1. Dimensions from Taxonomy Model: `domain`, `family`, `application`, `industry`, `technical`.  
2. Single parent within dimension (no DAG categories).  
3. FA primary labels; EN for PIM/OEM alignment.  
4. Bridge map to as-built commerce L1 where known (`scripts/seed_categories.py`).  
5. Future domains (Safety, Automation, …) included as **draft** shells for expansion without schema redesign.  
6. Spec templates referenced by key from Property Dictionary SPEC.

---

## 2. Domain dimension

| concept_id | name_fa | name_en | slug | parent | status | synonyms | description | related_templates |
|------------|---------|---------|------|--------|--------|----------|-------------|-------------------|
| `dom.root` | ابزار صنعتی | Industrial Tools | industrial-tools | — | active | — | Root pillar | — |
| `dom.measurement` | اندازه‌گیری | Measurement | measurement | `dom.root` | active | metrology, اندازه‌گیری دقیق | Dimensional & related metrology | `caliper`, `micrometer` |
| `dom.cutting` | ابزار برشی | Cutting Tools | cutting-tools | `dom.root` | active | machining tools | Material removal tools | `insert`, `end_mill`, `drill` |
| `dom.toolholding` | ابزارگیر | Toolholding | toolholding | `dom.root` | active | tool holders | Spindle/interface holders | `tool_holder` |
| `dom.workholding` | گیرش قطعه | Workholding | workholding | `dom.root` | active | fixturing | Workpiece holding | `industrial_default` |
| `dom.power` | ابزار قدرتی | Power Tools | power-tools | `dom.root` | draft | — | Powered handheld/industrial | — |
| `dom.safety` | ایمنی | Safety | safety | `dom.root` | draft | PPE | Safety equipment | — |
| `dom.automation` | اتوماسیون | Automation | automation | `dom.root` | draft | — | Sensors/actuators/automation | — |
| `dom.electrical` | الکتریکی | Electrical | electrical | `dom.root` | draft | — | Electrical tools/instruments | — |
| `dom.lubrication` | روانکاری | Lubrication | lubrication | `dom.root` | draft | — | Lubrication systems | — |
| `dom.machines` | دستگاه‌های صنعتی | Industrial Machines | industrial-machines | `dom.root` | active | — | Machines & apparatus | — |

---

## 3. Family dimension — Measurement

Parent domain: `dom.measurement`

| concept_id | name_fa | name_en | slug | parent | status | synonyms | description | related_templates |
|------------|---------|---------|------|--------|--------|----------|-------------|-------------------|
| `fam.dim` | اندازه‌گیری ابعادی | Dimensional Measurement | dimensional-measurement | `dom.measurement` | active | — | Linear/geometric dimensional tools | — |
| `fam.calipers` | کولیس | Calipers | calipers | `fam.dim` | active | کولیس ورنیه, vernier | Caliper family | `caliper` |
| `type.caliper.vernier` | کولیس ورنیه | Vernier Caliper | vernier-caliper | `fam.calipers` | active | — | Scale vernier | `caliper` |
| `type.caliper.dial` | کولیس ساعتی | Dial Caliper | dial-caliper | `fam.calipers` | active | — | Dial display | `caliper` |
| `type.caliper.digital` | کولیس دیجیتال | Digital Caliper | digital-caliper | `fam.calipers` | active | digimatic | Electronic display | `caliper` |
| `fam.micrometers` | میکرومتر | Micrometers | micrometers | `fam.dim` | active | micrometer | Micrometer family | `micrometer` |
| `type.micrometer.outside` | میکرومتر خارجی | Outside Micrometer | outside-micrometer | `fam.micrometers` | active | — | External measurement | `micrometer` |
| `fam.height_gauges` | ارتفاع‌سنج | Height Gauges | height-gauges | `fam.dim` | active | — | Height measurement | `caliper` |
| `fam.indicators` | اندیکاتور | Indicators | indicators | `fam.dim` | active | dial indicator, شیطانک | Dial/test indicators | `measurement_indicator` |
| `fam.gauge_blocks` | گیج بلوک | Gauge Blocks | gauge-blocks | `fam.dim` | active | gage block, راپورتر | Reference blocks | `industrial_default` |
| `fam.depth` | عمق‌سنج | Depth Gauges | depth-gauges | `fam.dim` | active | — | Depth measurement | `caliper` |
| `fam.bore` | بورگیج | Bore Gauges | bore-gauges | `fam.dim` | active | سیلندر | Internal diameter | `micrometer` |

---

## 4. Family dimension — Cutting Tools

Parent domain: `dom.cutting`

| concept_id | name_fa | name_en | slug | parent | status | synonyms | description | related_templates |
|------------|---------|---------|------|--------|--------|----------|-------------|-------------------|
| `fam.inserts` | اینسرت | Inserts | inserts | `dom.cutting` | active | کاربید اینسرت | Indexable inserts | `insert` |
| `type.insert.turning` | اینسرت تراش | Turning Insert | turning-insert | `fam.inserts` | active | — | Turning | `insert` |
| `type.insert.milling` | اینسرت فرز | Milling Insert | milling-insert | `fam.inserts` | active | — | Milling | `insert` |
| `fam.end_mills` | انگشتی | End Mills | end-mills | `dom.cutting` | active | endmill | End mill family | `end_mill` |
| `type.endmill.square` | انگشتی سرتخت | Square End Mill | square-end-mill | `fam.end_mills` | active | — | Flat end | `end_mill` |
| `type.endmill.ball` | انگشتی سرگرد | Ball Nose End Mill | ball-nose-end-mill | `fam.end_mills` | active | بال نوز | Ball nose | `end_mill` |
| `fam.drills` | مته | Drills | drills | `dom.cutting` | active | — | Drill family | `drill` |
| `type.drill.carbide` | مته کارباید | Carbide Drill | carbide-drill | `fam.drills` | active | الماس | Solid carbide | `drill` |
| `type.drill.hss` | مته HSS | HSS Drill | hss-drill | `fam.drills` | active | کبالت | HSS/Co | `drill` |
| `fam.taps` | قلاویز | Taps | taps | `dom.cutting` | active | — | Threading taps | `industrial_default` |
| `fam.u_drill` | یو-دریل | U-Drills | u-drills | `dom.cutting` | active | — | Indexable drills | `drill` |

---

## 5. Family dimension — Toolholding & Workholding

| concept_id | name_fa | name_en | slug | parent | status | synonyms | description | related_templates |
|------------|---------|---------|------|--------|--------|----------|-------------|-------------------|
| `fam.holders_milling` | ابزارگیر فرز | Milling Toolholders | milling-toolholders | `dom.toolholding` | active | — | CNC milling holders | `tool_holder` |
| `type.holder.bt` | کولت/هولدر BT | BT Holders | bt-holders | `fam.holders_milling` | active | — | BT interface | `tool_holder` |
| `type.holder.hsk` | هولدر HSK | HSK Holders | hsk-holders | `fam.holders_milling` | active | — | HSK interface | `tool_holder` |
| `fam.holders_turning` | ابزارگیر تراش | Turning Toolholders | turning-toolholders | `dom.toolholding` | active | — | Lathe holders | `tool_holder` |
| `fam.insert_holders` | هولدر اینسرتی | Insert Holders | insert-holders | `dom.cutting` | active | — | Bodies for inserts | `tool_holder` |
| `fam.workholding_general` | گیرش عمومی | General Workholding | general-workholding | `dom.workholding` | draft | — | Vices, clamps | `industrial_default` |

---

## 6. Application dimension (cross-cutting)

| concept_id | name_fa | name_en | slug | parent | status | synonyms | description |
|------------|---------|---------|------|--------|--------|----------|-------------|
| `app.root` | کاربردها | Applications | applications | — | active | — | Root |
| `app.qc` | کنترل کیفیت | Quality Control | quality-control | `app.root` | active | QC | Incoming/final QC |
| `app.cnc_insp` | بازرسی CNC | CNC Inspection | cnc-inspection | `app.root` | active | — | In-process machining inspection |
| `app.workshop` | اندازه‌گیری کارگاهی | Workshop Measurement | workshop-measurement | `app.root` | active | — | Bench/shop floor |
| `app.calibration` | کالیبراسیون | Calibration Lab | calibration-lab | `app.root` | active | — | Lab calibration |
| `app.turning` | تراشکاری | Turning | turning | `app.root` | active | — | Lathe operations |
| `app.milling` | فرزکاری | Milling | milling | `app.root` | active | — | Milling operations |
| `app.drilling` | سوراخ‌کاری | Drilling | drilling | `app.root` | active | — | Hole making |
| `app.welding_fab` | جوش و ساخت | Welding Fabrication | welding-fabrication | `app.root` | draft | — | Future |

---

## 7. Industry dimension

| concept_id | name_fa | name_en | slug | parent | status | synonyms | description |
|------------|---------|---------|------|--------|--------|----------|-------------|
| `ind.root` | صنایع | Industries | industries | — | active | — | Root |
| `ind.automotive` | خودرو | Automotive | automotive | `ind.root` | active | — | Auto manufacturing/QC |
| `ind.aerospace` | هوافضا | Aerospace | aerospace | `ind.root` | active | — | Aerospace |
| `ind.steel` | فولاد و فلزات | Steel & Metals | steel-metals | `ind.root` | active | — | Metals |
| `ind.oil_gas` | نفت و گاز | Oil & Gas | oil-gas | `ind.root` | active | — | Energy |
| `ind.machine_mfg` | ماشین‌سازی | Machine Manufacturing | machine-manufacturing | `ind.root` | active | — | Machine builders |
| `ind.medical` | تجهیزات پزشکی | Medical Device | medical-device | `ind.root` | draft | — | |
| `ind.education` | آموزش | Education & Training | education | `ind.root` | draft | — | |

---

## 8. Technical classification (examples)

| concept_id | name_fa | name_en | slug | parent | status | notes |
|------------|---------|---------|------|--------|--------|-------|
| `tech.root` | طبقه فنی | Technical Class | technical | — | active | |
| `tech.accuracy_class` | کلاس دقت | Accuracy Class | accuracy-class | `tech.root` | draft | Bind to Property enums later |
| `tech.power_source` | منبع انرژی | Power Source | power-source | `tech.root` | draft | manual/battery/electric |
| `tech.taper` | مخروط ابزار | Taper Interface | taper-interface | `tech.root` | active | Prefer Property `taper_interface` when facet |

Prefer **Properties** for filterable technical attributes when a Definition exists; use technical nodes for navigation groupings that are not single properties.

---

## 9. Commerce Category bridge (not duplication)

Map as-built L1 roots → knowledge Domains (assignment bridge only):

| Commerce L1 (`seed_categories.py`) | id | Knowledge domain |
|------------------------------------|----|------------------|
| ابزارگیر | 1 | `dom.toolholding` |
| ابزار اینسرتی | 2 | `dom.cutting` (+ holders) |
| اینسرت | 3 | `dom.cutting` / `fam.inserts` |
| ابزار انگشتی | 4 | `dom.cutting` / `fam.end_mills` |
| مته | 5 | `dom.cutting` / `fam.drills` |
| قلاویز | 6 | `dom.cutting` / `fam.taps` |
| ابزار گیرشی | 8 | `dom.workholding` |
| دستگاه‌های صنعتی | 9 | `dom.machines` |
| اندازه گیری دقیق | 56 | `dom.measurement` |
| CNC اندازه گیری | 81 | `dom.measurement` |
| اندازه گیری آزمایشگاهی | 87 | `dom.measurement` |

Leaf commerce categories continue to merchandise PLPs. Knowledge Types are assigned in parallel during Classification stage.

**MUST NOT** create a second storefront Category tree from this seed.

---

## 10. SEO usage of seed

| Node status | Indexable hub? |
|-------------|----------------|
| Commerce Category (existing) | Yes — `/categories/{slug}` |
| Domain / Family / Type | No until UD-04 |
| Application / Industry | No until UD-04 |
| `draft` domains | Never public |

---

## 11. Expansion procedure reminder

Adding Lubrication products later: activate `dom.lubrication`, add families, bind templates, extend classification maps — **no DDL for taxonomy shape**.

---

## 12. Requirements

| ID | Criterion |
|----|-----------|
| **SEED-R1** | Domains include Measurement, Cutting, Toolholding, Workholding, Safety, Automation, Electrical, Lubrication |
| **SEED-R2** | Measurement families include Calipers, Micrometers, Height Gauges, Indicators |
| **SEED-R3** | Cutting families include Inserts, End Mills, Drills |
| **SEED-R4** | Each node has concept_id, FA/EN, slug, parent, dimension, synonyms, description, templates where applicable |
| **SEED-R5** | Explicit non-replacement of commerce categories |
| **SEED-R6** | Bridge table to existing L1 ids |

---

## 13. Open questions

| ID | Question |
|----|----------|
| **TX-Q1** | Collapse commerce L1 measurement roots (56/81/87) under one Domain bridge only? |
| **SEED-Q1** | Exact Persian marketing names vs OEM EN for Type slugs? |
