# IMG-01A — Generic multi-brand image-discovery engine

**Node:** IMG-01A
**Archetype:** KNOW
**Prompt:** `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md`
**Change class:** C2
**Task ID:** IMG-01A (CR-008 Option C)
**Branch:** `feat/image-discovery-pipeline`
**Status:** Draft at authorship (historical) — implementation later merged; see Final disposition
**Date:** 2026-08-02


## Final disposition

```text
Final disposition: merged in PR #198
Merge commit: f10cfff3ace2a00ef3a7403d5408e79e0b9b395b
Production execution: not approved
Live TOSAG parser validation: pending
```

## Goal

Refactor IMG-01 into a brand-agnostic discovery engine plus `insize_tosag` adapter before the first commit. Preserve external `insize-100` pilot assets. No DB / Alembic / ProductImage / commit.

## Related

- IMG-01 — initial INSIZE pilot + pipeline intent
- External evidence: `/home/moahmmad/Projects/Karzar-image-pilot/insize-100/`

## Outcome

- Refactor to generic engine + `insize_tosag` adapter complete
- Tests: 20 passed; PYTHONHASHSEED 0–9 all pass
- aods_validate links/registry/pmo/naming: PASS
- 100-SKU resume: accepted 100 / unique 45 / rejected 0; second unchanged run reports `asset_set_stable` + `semantic_manifest_stable`
- PMO: IMG-01 + IMG-01A registered (CR-008 C)
- **Stop before commit**
