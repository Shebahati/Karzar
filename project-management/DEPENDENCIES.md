# Dependencies

## Task dependencies
See `diagrams/dependencies.mmd` and each task `deps`.

## System dependencies
- [ ] PostgreSQL + Redis (runtime)
- [ ] Hesabfa stock sync (qty SoT)
- [ ] VPS self-hosted runner `karzar-vps`
- [ ] Zarinpal / payment provider
- [ ] SMS OTP provider

## Soft dependencies
- [ ] Google Search Console
- [ ] Analytics (CWV field data)

## Release-window dependencies (REL-001)
- [ ] CI + deploy workflow health on `main`
- [ ] Access to logs/monitoring for first 30 minutes post-deploy
- [ ] Named release owner and named rollback owner
- [x] SEC-001 hygiene gate (closed 2026-07-27; residual R8 dep advisories)
