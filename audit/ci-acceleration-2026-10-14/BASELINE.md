# CI baseline (2026-10-14)

Source: GitHub Actions history (`Backend CI`, `Frontend CI`), successful runs sample n≈18–25 per job.

## Backend CI (seconds)

| Job | median | p95 | workflow timeout (min) |
|-----|--------|-----|------------------------|
| Classify changes | 15 | 15 | 5 |
| aods | 28 | 44 | 10 |
| lint | 57 | 68 | 10 |
| test | 790 | 833 | 25 |

## Frontend CI (seconds)

| Job | median | p95 | workflow timeout (min) |
|-----|--------|-----|------------------------|
| Classify changes | 13.5 | 15 | 5 |
| storefront | 78 | 91 | 10 |
| admin-panel | 49 | 61 | 10 |
| storefront-e2e | 181 | 198 | 10 |

Timeouts use ~1.35× p95 wall time plus margin (see workflow `timeout-minutes`).

`origin/main` at capture: `ec6ed4d55c10284ab4a0661a6ed9a2cd352bb833`.
