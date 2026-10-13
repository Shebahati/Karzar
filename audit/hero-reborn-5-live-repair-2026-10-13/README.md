# Five-hero live regression repair evidence (#481 follow-up)

Read-only **production** probe (`live-probe.mjs`) captured before hotfix merge.

## Live defects measured (pre-fix)

| Viewport | Outer h | Hero h | Gap (px) | Note |
|----------|---------|--------|----------|------|
| 1920×1080 | 1080 | 920 | **+180** | Empty band under hero (fixed `100svh` wrapper) |
| 390×844 | 523 | 565 | **−21** | Hero taller than wrapper → overlap with next section |

`hero-design.json` on production: five slides `slide_h01`…`slide_h05`, dock `featuredOrder` 0–4 — no pack drift.

Post-fix verification: production-build local acceptance + re-run probe after deploy.
