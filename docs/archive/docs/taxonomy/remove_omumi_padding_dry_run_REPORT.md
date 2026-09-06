# Remove «عمومی» padding leaves — dry-run (staging API)

**Date:** 2026-07-26  
**API:** `https://api.karzartools.com/api/v1/categories/`  
**Script:** `scripts/remove_omumi_padding_leaves.py`  
**Staging apply:** **not applied** (VPS SSH timed out from this environment; use workflow after merge)

## Summary

| Metric | Value |
|--------|------:|
| Padding «عمومی» candidates | 23 |
| Planned deletes (move→parent) | 23 |
| Products to move (API rolled-up = direct for sole L3) | 1954 |
| Skips | 0 |
| Near-misses (left intact) | 1 |

All 23 candidates are **sole L3** children named `«Parent — عمومی»` under an L2 parent. No exact bare `عمومی`, no L1/L2 named عمومی, no non-sole cases on staging.

## Before → after samples

| Before | After | Products |
|--------|-------|--------:|
| ابزار انگشتی > انگشتی سرتخت کارباید > انگشتی سرتخت کارباید — عمومی | ابزار انگشتی > انگشتی سرتخت کارباید | 270 |
| قلاویز > قلاویز ماشینی صاف > قلاویز ماشینی صاف — عمومی | قلاویز > قلاویز ماشینی صاف | 255 |
| مته > مته کارباید(الماس) > مته کارباید(الماس) — عمومی | مته > مته کارباید(الماس) | 235 |
| دستگاه‌های صنعتی > دستگاه کُر گیری (کُر دریل) > … — عمومی | دستگاه‌های صنعتی > دستگاه کُر گیری (کُر دریل) | 199 |
| اینسرت > اینسرت تراش CNC > اینسرت تراش CNC — عمومی | اینسرت > اینسرت تراش CNC | 141 |

## Near-miss (not deleted)

| id | name | depth | products | why |
|----|------|------:|---------:|-----|
| 158 | ابزار دستی عمومی | 3 | 196 | Contains «عموم» but is a real merchandising leaf name, not padding pattern |

## Apply (after merge + Deploy Staging)

```bash
gh workflow run remove-omumi-padding.yml -f mode=dry-run
gh workflow run remove-omumi-padding.yml -f mode=apply
```

Or on VPS:

```bash
docker compose exec -T app python scripts/remove_omumi_padding_leaves.py --via-db
docker compose exec -T app python scripts/remove_omumi_padding_leaves.py --via-db --apply --confirm
```

Does **not** write price/stock. Megamenu collapse of sole «عمومی» remains as a UI safety net for leftovers. DELETE API also allows `target_category_id=parent` when the node is the sole child.
