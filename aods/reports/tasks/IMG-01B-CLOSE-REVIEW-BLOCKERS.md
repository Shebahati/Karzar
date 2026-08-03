# IMG-01B — Close human-review blockers before first commit

**Status:** Draft at authorship (historical) — implementation later merged; see Final disposition
**Branch:** `feat/image-discovery-pipeline`
**Date:** 2026-08-02
**Non-goals honored:** no commit/push/PR; no DB/Alembic; no Product/ProductImage; `insize-100` original not overwritten


## Final disposition

```text
Final disposition: merged in PR #198
Merge commit: f10cfff3ace2a00ef3a7403d5408e79e0b9b395b
Production execution: not approved
Live TOSAG parser validation: pending
```

## Summary

Closed IMG-01A review blockers: global candidate identity, safe filesystem naming, provenance, consolidation integrity + conflicts, cross-brand duplicates, referenced-asset run-state, atomic I/O + corrupt refuse, TOSAG subject evidence, bounded transport, single-flight concurrency, CLI/path validation, Pillow `getdata` deprecation.

## Evidence

- pytest `tests/test_image_discovery*.py`: 37 passed
- ruff: All checks passed
- PYTHONHASHSEED 0–9: see `/tmp/img01b-hashseed.txt`
- 100-SKU offline resume on `/tmp/insize-100-img01b` (schema-normalized copy of `insize-100`):
  - run1: accepted 100, rejected 0, unique 45, family 78, singleton_unverified 22, cross_brand 0
  - run2: semantic_manifest_stable true, asset_set_stable true, stale/missing 0

## Open

- Live TOSAG re-fetch may be connection-reset in restricted environments; resume reuses governed previous state when disk SHA matches.
- First Git commit still requires human authorization.
