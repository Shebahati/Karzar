# IMG-01C — Final targeted corrections before first commit

**Status:** Draft — corrections complete; awaiting final human review  
**Branch:** `feat/image-discovery-pipeline`  
**Date:** 2026-08-02  
**Non-goals honored:** no commit/push/PR; no DB/Alembic; no Product/ProductImage; original `insize-100` untouched; no live TOSAG fetch

## Corrections

1. Governed `resolve_manifest_asset_path` (absolute/`..`/symlink/dir/missing)
2. `candidate_content_fingerprint` excludes batch provenance; multi-origin `candidate-provenance.*`
3. Non-empty consolidate output fail-closed without `--allow-replace`
4. Integrity failures → non-zero exit + `status=integrity_failure`
5. CSV source dedupe before role / max-images
6. Empty rejected provenance filled with governed fallbacks
7. Atomic `summary.json` on conflict/integrity paths
8. Contact sheet blocks non-http(s) href schemes
9. `high-reuse-assets.csv` (threshold = 8 SKUs / same-brand SHA)
10. Docs: offline asset/state regression ≠ live parser regression

## Evidence

- pytest `tests/test_image_discovery*.py`: 52 passed (37 prior + IMG-01C)
- Offline 100-SKU resume on `/tmp/insize-100-img01b` (asset/state only)

## Open

- Live TOSAG parser regression still pending network authorization
- First Git commit still requires human authorization
