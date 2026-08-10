# IMG-FAST-01B — Catalog-wide one-image discovery

**Node:** IMG-FAST-01B-ONE-IMAGE-DISCOVERY  
**Parent:** IMG-FAST-01  
**Status:** in_progress 85% (R2 complete — awaiting independent acceptance)  
**Branch:** `feature/img-fast-01b-one-image-discovery`  
**Draft PR:** #223

## Authority

- `docs/FAST_IMAGE_COVERAGE.md` (IMG-FAST-01B scope)
- Accepted IMG-FAST-01A seed SHA-256: `abbed4a4890d136ee48f767cf5450c6389524042a22c0b9dd172c1a9d0995016`
- ADR-012: no production DB/storage writes

## R1 Artifact (immutable — do not overwrite)

| Item | Path / value |
|------|----------------|
| Dir | `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B` |
| ZIP | `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B.zip` |
| ZIP SHA-256 | `260a60797d46f1a57a6c98017c8977bce23363f48c0fca18bf805a73e766341c` |
| Outcome | `green_exact=0` (WC SSL timeouts; metadata-only OFFICIAL lanes) |

## R2 Artifact

| Item | Path / value |
|------|----------------|
| Dir | `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B-R2` |
| ZIP | `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B-R2.zip` |
| ZIP SHA-256 | `a33f2edf276002743bdf5779dce4b502e8db7cb4975485f972712c5939742054` |
| Pilot | green_exact=34/100; domains abzarham.com + abzarmarket.com |
| Full | green_exact=204, yellow_review=67, unresolved=4437 (universe 4708) |
| Sources with green | `prior_artifact_reuse`, `abzarmarket_html`, `azarsanat_wc` |
| Domains with green | abzarham.com, abzarmarket.com, azarsanat.net |
| DB / ProductImage / deploy | all false / 0 |

## Deliverables

| Item | Path |
|------|------|
| CLI | `scripts/build_fast_image_coverage_discovery.py` |
| Package | `scripts/fast_image_coverage_discovery/` (multi-adapter: WC, HTML index, sitemap, prior reuse) |
| Tests | `tests/test_fast_image_coverage_discovery.py` (fixture-only; PYTHONHASHSEED 0..9) |

## Non-goals

- IMG-FAST-01C apply
- ProductImage / DB mutations
- Deploy / merge / Ready
- Overwriting R1 Artifact

## Verification

```bash
.venv/bin/python -m pytest tests/test_fast_image_coverage_discovery.py -q --noconftest
for i in 0 1 2 3 4 5 6 7 8 9; do PYTHONHASHSEED=$i .venv/bin/python -m pytest tests/test_fast_image_coverage_discovery.py -q --noconftest || exit 1; done
python3 aods/tools/aods_validate.py
```
