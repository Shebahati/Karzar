# IMG-01E — Harden structured evidence and output roots

**Status:** done (Draft PR #198 follow-up commit)  
**Branch:** `feat/image-discovery-pipeline`  
**Depends:** IMG-01D

## Goal

Close the four hardening items declared on Draft PR #198 without expanding scope.

## Delivered

1. **Region-isolated structured evidence** — `html_subject.py` keeps subject vs unrelated meta/JSON-LD; adapter auto-accepts subject-region only.
2. **Atomic Product JSON-LD** — brand + requested SKU/MPN/productID must live on one Product object; cross-object mix and ambiguous multi-node sets reject.
3. **Symlinked governed/batch roots** — `lstat` no-follow validators on output root, `assets/`, `manifests/`, `review/`, `logs/`, metadata files, and batch roots; never open/hash through symlinks.
4. **Run output policy** — new run: absent or empty; `--resume` / `--force-refetch`: coherent prior + same `source_adapter` + no unknown/symlink roots.

## Non-goals (unchanged)

- No DB / Alembic / ProductImage
- No live TOSAG downloads in this task
- No Ready-for-Review / merge of #198
- No pilot binaries in Git

## Validation honesty

Offline 100-SKU asset/state resume on a **copy** of the preserved external pilot is not live TOSAG parser proof.

## IMG-01E-R1 (Resume identity contract)

Prior-output recognition and `load_previous_manifest` now call the shared `validate_source_manifest_row` on every Manifest row (same contract as Consolidation). Invalid `candidate_id` / identity / SHA / role rows reject the prior before Resume proceeds.
