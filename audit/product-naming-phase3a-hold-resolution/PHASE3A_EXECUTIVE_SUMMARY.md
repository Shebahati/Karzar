# Phase 3A HOLD resolution — executive summary

- Standardized persisted (Phase 2F): **47**
- Remaining HOLD: **1303**
- Total governed cohort: **1350**

## Reason reconciliation

- `HOLD_MISSING_PRODUCT_TYPE`: 778
- `HOLD_OEM_SEMANTIC_EVIDENCE_MISSING`: 330
- `HOLD_PRODUCT_TYPE_NAMING_POLICY`: 101
- `HOLD_MISSING_VARIANT_FACT`: 58
- `HOLD_VARIANT_POLICY_UNDEFINED`: 31
- `HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT`: 3
- `HOLD_OWNER_CANONICAL_TITLE_REVIEW`: 1
- `HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT`: 1

## Projected unlockability

- `DIRECT_UNLOCK`: 1
- `MULTI_STEP_UNLOCK`: 14
- `OWNER_DECISION_REQUIRED`: 143
- `SOURCE_EVIDENCE_REQUIRED`: 1040
- `TWO_STEP_UNLOCK`: 105

## Waves

- `WAVE_3B_GOVERNANCE_QUICK_WINS`: rows=132 expected_unlock=1 cumulative=48 priority=P0
- `WAVE_3C_VARIANT_FACTS`: rows=58 expected_unlock=0 cumulative=48 priority=P1
- `WAVE_3D_INSIZE_OEM_EVIDENCE`: rows=330 expected_unlock=0 cumulative=48 priority=P2
- `WAVE_3E_INSIZE_MISSING_PT`: rows=156 expected_unlock=0 cumulative=48 priority=P2
- `WAVE_3F_DASQUA_PT`: rows=396 expected_unlock=0 cumulative=48 priority=P2
- `WAVE_3G_TERMA_PT`: rows=226 expected_unlock=0 cumulative=48 priority=P2
- `WAVE_3H_MANUAL_EXCEPTIONS`: rows=5 expected_unlock=0 cumulative=48 priority=P3

## Top clusters

- `oem:B1_NO_IDENTITY_REGISTRY_ENTRY:no_identity_registry_entry`: 87 (WAVE_3D_INSIZE_OEM_EVIDENCE)
- `naming_policy:GEN_CALIPER`: 65 (WAVE_3B_GOVERNANCE_QUICK_WINS)
- `missing_pt:DASQUA:A6_NO_AUTHORITATIVE_SOURCE:prefix:1804`: 32 (WAVE_3F_DASQUA_PT)
- `missing_pt:INSIZE:A6_NO_AUTHORITATIVE_SOURCE:prefix:4129`: 28 (WAVE_3E_INSIZE_MISSING_PT)
- `missing_pt:DASQUA:A6_NO_AUTHORITATIVE_SOURCE:prefix:1310`: 25 (WAVE_3F_DASQUA_PT)
- `variant_fact:PIN_GAUGE:nominal_size`: 25 (WAVE_3C_VARIANT_FACTS)
- `missing_pt:DASQUA:A6_NO_AUTHORITATIVE_SOURCE:prefix:2220`: 23 (WAVE_3F_DASQUA_PT)
- `missing_pt:DASQUA:A6_NO_AUTHORITATIVE_SOURCE:prefix:5333`: 23 (WAVE_3F_DASQUA_PT)
- `missing_pt:TERMA:A6_NO_AUTHORITATIVE_SOURCE:prefix:MA250H`: 23 (WAVE_3G_TERMA_PT)
- `oem:B2_ACCESSORY_ONLY_OCCURRENCE:FEELER GAUGE ROLLS`: 22 (WAVE_3D_INSIZE_OEM_EVIDENCE)
- `oem:B5_OEM_SOURCE_NOT_EXTRACTED:no_primary_product_occurrence`: 19 (WAVE_3D_INSIZE_OEM_EVIDENCE)
- `variant_policy:level_variant_policy_pending_owner`: 19 (WAVE_3B_GOVERNANCE_QUICK_WINS)
- `oem:B4_EXACT_OCCURRENCE_BUT_HEADING_NOT_GOVERNED:TWO POINTS/THREE POINTS INTERNAL MICROMETERS`: 17 (WAVE_3D_INSIZE_OEM_EVIDENCE)
- `variant_fact:THREAD_RING_GAUGE:nominal_size`: 17 (WAVE_3C_VARIANT_FACTS)
- `missing_pt:INSIZE:A6_NO_AUTHORITATIVE_SOURCE:prefix:4139`: 17 (WAVE_3E_INSIZE_MISSING_PT)

## Historical missing brand row

Identified product_id `1789` manufacturer_code `1114-150` hold `HOLD_PRODUCT_TYPE_NAMING_POLICY` with empty HOLD CSV brand field; name/audit indicate INSIZE. This explains 101 HOLD_PRODUCT_TYPE_NAMING_POLICY vs 100 branded-INSIZE rows in surface brand tallies.

## Read-only proof

- DB mutation SQL executed: 0
- Product / ProductType / KB / policy / OEM authority mutations: 0
- Phase 2F names mutated: 0
- Deploy: no
