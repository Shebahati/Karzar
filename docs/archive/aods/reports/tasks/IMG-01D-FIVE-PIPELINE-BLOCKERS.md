# TASK-RECORD · IMG-01D

| Field | Value |
|-------|-------|
| Task ID | IMG-01D |
| Title | Close five independently reproduced blockers before first commit |
| Change class | C1 |
| Branch | `feat/image-discovery-pipeline` |
| Outcome | COMPLETE at authorship (historical: ready for review / no agent commit); **Final disposition: merged PR #198 @ f10cfff** |


## Final disposition

```text
Final disposition: merged in PR #198
Merge commit: f10cfff3ace2a00ef3a7403d5408e79e0b9b395b
Production execution: not approved
Live TOSAG parser validation: pending
```

## Independently reproduced defects

1. **Nested related false-positive** — regex `_UNRELATED_BLOCK` closed outer related at nested `</section>`; labeled SKU after inner close leaked into `subject_html` → false `sku_confirmed`.
2. **Replacement-output recognition** — any single marker (`assets/`, …) accepted; `--allow-replace` on `assets/unrelated.txt` alone succeeded and preserved unrelated data.
3. **Missing SHA** — `sha = manifest_sha or disk_sha` invented integrity evidence.
4. **Missing candidate_id** — treated as ordinary reject with `status=ok` / `integrity_failure_count=0`.
5. **Out-of-root symlink read** — `compare_runs` / globs followed `assets/link → /external/secret` and hashed the target.

## Implemented corrections

| Area | Change |
|------|--------|
| Structural parser | `sources/html_subject.py` — stdlib `HTMLParser` stack; suppress nested unrelated subtrees |
| Prior output | Coherent signature: manifest list + pipeline summary object + assets; unknown files fail; stale → `preexisting-stale-files.csv`, no delete |
| Manifest contract | `validate_source_manifest_row` — required fields, SHA hex, `cid:<64 hex>`, recomputed identity match |
| No-follow scans | `inspect_local_asset_nofollow` / `iter_local_asset_files` / inventory; applied to materialize, pending cleanup, classify, compare_runs, consolidate |
| Duplicate physical | `sha → all paths`; `duplicate-physical-assets.csv` + summary counters |
| Docs | `--allow-replace` policy + symlink/contract honesty; offline ≠ live parser |

## New tests

`tests/test_image_discovery_img01d.py` — nested related/heading/table/cross-sell/breadcrumb/malformed/main±unrelated SKU; allow-replace partial/unknown/stale/clean; missing/invalid SHA & candidate_id & identity fields; symlink no-follow for compare/materialize/classify/pending; duplicate physical report. Existing 52 tests retained (suite now 76).

## Remaining limitation

Offline 100-SKU Asset/state resume regression does **not** prove current live TOSAG page structure. Structural parser tests are local fixtures only.

## Non-goals honored

No commit/push/PR; no DB/Alembic/ProductImage; no live TOSAG; original `insize-100` untouched.
