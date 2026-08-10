# IMG-FAST-01B — Catalog-wide one-image discovery

**Node:** IMG-FAST-01B-ONE-IMAGE-DISCOVERY  
**Parent:** IMG-FAST-01  
**Status:** in_progress  
**Branch:** `feature/img-fast-01b-one-image-discovery`

## Authority

- `docs/FAST_IMAGE_COVERAGE.md` (IMG-FAST-01B scope)
- Accepted IMG-FAST-01A seed: `abbed4a4890d136ee48f767cf5450c6389524042a22c0b9dd172c1a9d0995016`
- ADR-012: no production DB/storage writes

## Deliverables

| Item | Path |
|------|------|
| CLI | `scripts/build_fast_image_coverage_discovery.py` |
| Package | `scripts/fast_image_coverage_discovery/` |
| Tests | `tests/test_fast_image_coverage_discovery.py` (fixture-only) |
| External artifact | `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B` |
| ZIP | `/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B.zip` |

## Non-goals

- IMG-FAST-01C apply
- ProductImage / DB mutations
- Deploy

## Verification

```bash
.venv/bin/python -m pytest tests/test_fast_image_coverage_discovery.py -q --noconftest
python3 aods/tools/aods_validate.py
```
