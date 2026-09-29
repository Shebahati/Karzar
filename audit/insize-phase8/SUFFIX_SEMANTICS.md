# INSIZE 108A Suffix Semantics (Prompt 126)

Scope: **family-local**, derived only from observed DIGITAL specialty caliper tables in INSIZE 108A (artifact `insize-108a-catalogue-v1`). Do not generalize beyond cited families.

## Observed suffixes

| Suffix | Families where verified | OEM meaning (source-grounded) | Changes required V1 Facts? | Changes Product Type? | Notes |
|--------|-------------------------|-------------------------------|----------------------------|-----------------------|-------|
| *(none)* / bare code | 1122, 1169, 1176, 1178, 1520, 1530, 1120-500 | Base commercial code listed as its own row | N/A | N/A | Exact DB↔OEM match when present |
| **A** | 1120, 1121, 1123, 1161, 1183, 1185–1188 | Type A electronics / geometry class: typically preset buttons (on/off, set, mm/inch, preset ±); non-waterproof tables | Often yes vs B/*1 | No within same OEM section | Most specialty “bare DB SKU” maps toward A when sole non-WL code |
| **B** | 1120, 1121 | Type B: no preset (must add jaw width); different jaw dims; different range/accuracy | **YES** | No (same INTERNAL_* family) | Distinct Fact triad — blocks bare-SKU assertion unless excluded |
| **1** / **\*1** (e.g. 1120-1501) | 1120, 1121 | Alternate Type A jaw/geometry size for same nominal length | **YES** (range/accuracy) | No | Different measuring interval |
| **P** | 1120-150P, 1176-150P, 1178-300P, 1520-150P | IP67 / Type C waterproof class; often different buttons; sometimes different range | Sometimes (1178-300P range differs; 1120-150P same triad as A) | No | Optional-feature + sometimes Fact change |
| **WL** | Many digital families | Built-in wireless twin of a base/A row | **NO** for observed V1 triad | No | Same range/resolution/accuracy as paired non-WL code |
| **AWL** | A + WL | Type A + built-in wireless | **NO** vs matching **A** | No | Fact-equivalent to A for V1 |

## Family notes

### DIGITAL INSIDE GROOVE (1120) — pdf64/printed56
- Type A / B / C explicitly documented (button legends).
- A vs B vs *1 change range + accuracy.
- A vs AWL: identical metrology; wireless only.
- A vs P (1120-150): same 22–150 / ±0.04 triad; differs IP67 + Type C buttons.

### DIGITAL INSIDE POINT (1121) — pdf63/printed55
- Same A / B / *1 pattern as 1120; A/AWL fact-identical.

### DIGITAL INSIDE KNIFE-EDGE (1123) — pdf73/printed65
- Observed codes: 1123-150A/AWL, 1123-300A only (no B/*1/P in extract).
- A vs AWL fact-identical.

### EXTERNAL POINT / NECK (1185/1187) — pdf70/printed62
- Only *A / *AWL observed; identical triad.

### OFFSET / BLADE / POINT / TUBE / HOOK / INTERCHANGEABLE — various pages
- Where bare code exists (1122, 1169, 1530): exact match preferred.
- Where only *A/*AWL exist: V1 Facts identical across the pair.

## Rule of use

1. Never invent a global “A means X” across catalogues.
2. WL/AWL never change required V1 triad in verified tables → candidates for `RESOLVED_EQUIVALENT_FACTS`.
3. B / *1 / some P rows change Facts → remain `HOLD_MULTIPLE_FACT_SETS` unless positive evidence excludes them.
