# KarZar Production Deployment Guide (Technical)

**Date:** 18 July 2026  
**Stacks:** `Karzar-main` (FastAPI + Postgres + Redis) · `karzar-frontend` (Storefront + admin-panel, Next.js)

---

## 1. Target topology

```text
                    ┌─────────────────────┐
   Clients ──TLS──► │ Nginx / Caddy       │
                    └─────────┬───────────┘
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
   shop.example.com   admin.example.com   api.example.com
      :3000 Next           :3001 Next         :8000 API
                                               │
                                    ┌──────────┴──────────┐
                                    ▼                     ▼
                               Postgres 15              Redis 7
```

**Why split hosts:** clean CORS, isolated admin surface, independent caching/CDN later.

---

## 2. Capacity baseline

| Environment | vCPU | RAM | Disk | Notes |
|-------------|------|-----|------|-------|
| Staging | 2 | 4 GB | 40 GB SSD | Docker + two Next processes |
| Production (small) | 4 | 8 GB | 80 GB+ SSD | Headroom for image uploads + PG |
| Production (growth) | split API/DB | 16 GB+ | managed disk + object storage | Move media off local disk |

---

## 3. Server bootstrap

1. Ubuntu 22.04/24.04 LTS, unattended security updates.  
2. Create deploy user; SSH keys only; disable password auth.  
3. UFW: allow `22/tcp`, `80/tcp`, `443/tcp`; deny others inbound.  
4. Install: Docker Engine + Compose plugin, Nginx, Certbot, Node.js **20** LTS, `git`.  
5. Optional: fail2ban, automatic `docker image prune` timer.

---

## 4. Backend deployment (`Karzar-main`)

### 4.1 Compose

Use production-capable compose (`docker-compose.yml` + staging/prod overlay). Services: `app`, `db` (Postgres 15), `redis` (7). Prefer `APP_SERVER=gunicorn` with workers sized to vCPU (`2×CPU+1` as starting point).

### 4.2 Environment (critical production values)

| Variable | Production expectation |
|----------|------------------------|
| `DEBUG` | `False` |
| `APP_ENV` | `production` / `staging` |
| `SECRET_KEY` | cryptographically random ≥32 chars |
| `OTP_DEV_ECHO` | `False` |
| `ALLOW_PUBLIC_REGISTER` | `False` unless product requires it |
| `ENABLE_API_DOCS` | `False` publicly (or VPN-only) |
| `ENABLE_METRICS` | `True` only if scraped privately |
| `CORS_ORIGINS` | Exact shop + admin HTTPS origins |
| `TRUSTED_HOSTS` | API hostname(s) |
| `ENFORCE_HTTPS` | `True` behind TLS terminator |
| `PAYMENT_PROVIDER` | `zarinpal` (+ merchant id) |
| `SMS_PROVIDER` | `kavenegar` (+ API key/sender/template) |
| `PAYMENT_*_URL` | Public shop HTTPS callback/success/failure |
| `ADMIN_STEP_UP_PIN` | Strong, rotated, secret-managed |
| `POSTGRES_*` / `REDIS_*` | Strong passwords; internal network only |
| `INITIAL_SUPER_ADMIN_*` | Bootstrap once; change immediately |

Never commit real `.env`. Mode `600` on server file.

### 4.3 Rollout commands (illustrative)

```bash
cd /opt/karzar/Karzar-main
cp .env.staging.example .env   # then edit secrets
docker compose -f docker-compose.yml -f docker-compose.staging.yml pull
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build
curl -fsS https://api.example.com/health
curl -fsS https://api.example.com/ready
```

Migrations: follow project entrypoint (`docker-entrypoint`) — confirm alembic/auto-migrate behavior before first prod boot.

### 4.4 Persistence & backups

- Named volumes for Postgres data and uploaded files (`/static/uploads` or equivalent).  
- Daily `pg_dump` to off-box storage; weekly restore drill.  
- Redis: ephemeral OK if used for throttle/cache; do not rely on it as sole durable store.

---

## 5. Frontend deployment (`karzar-frontend`)

### 5.1 Build-time env

Both apps:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1
NEXT_PUBLIC_USE_MOCK=false
```

These are **baked into the client bundle** — rebuild after any API host change.

### 5.2 Build & run

```bash
cd Storefront && npm ci && npm run build && npm run start -- --port 3000
cd admin-panel && npm ci && npm run build && npm run start -- --port 3001
```

Process manager recommendation: **PM2** ecosystem file or systemd units with restart-on-failure and log rotation.

Optional hardening: enable Next `output: 'standalone'` and run the standalone server artifact (smaller runtime footprint).

### 5.3 Resource caps

Set `NODE_OPTIONS=--max-old-space-size=1536` (or similar) per app on small VPS to avoid unbounded heap growth under traffic spikes.

---

## 6. Reverse proxy (Nginx)

### 6.1 Requirements

- Terminate TLS at Nginx.  
- Forward `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`.  
- Raise `client_max_body_size` on API (image uploads), e.g. `20m`.  
- WebSocket not required for current apps; keep HTTP/1.1 proxy buffering defaults unless SSE is added later.

### 6.2 Security headers (API + admin especially)

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header Referrer-Policy strict-origin-when-cross-origin always;
```

Optional admin IP allowlist:

```nginx
allow 203.0.113.10;
deny all;
```

### 6.3 TLS

Certbot (`certbot --nginx`) per hostname; auto-renew timer verified with `systemctl status certbot.timer`.

---

## 7. Recommended tooling

| Concern | Tool |
|---------|------|
| Process supervision (Next) | PM2 or systemd |
| Containers | Docker Compose |
| TLS | Certbot or Caddy |
| Uptime | Uptime Kuma / Better Stack |
| Metrics | Prometheus scrape `/metrics` (private network) |
| Logs | Docker json-file limits → Loki/Grafana later |
| CI | GitHub Actions: `tsc`, lint, `next build` |
| Secrets | Server env files / Doppler / Vault (not git) |
| Object media (later) | S3-compatible + CDN |

---

## 8. Security checklist (must)

1. Disable `OTP_DEV_ECHO`, mock payments, public Swagger in production.  
2. Rotate `SECRET_KEY`, DB password, step-up PIN, SMS/payment keys.  
3. CORS allowlist exact HTTPS origins only.  
4. Redis required for production throttles (`DEBUG=False` path).  
5. Separate admin hostname; prefer MFA at VPN/SSO edge if available.  
6. Keep step-up PIN out of frontend bundles and public docs.  
7. Patch OS + images monthly; watch CVEs for Postgres/Redis/Node.  
8. Backup + restore test before go-live.  
9. Rate-limit sensitive routes at Nginx as defense-in-depth (OTP/contact already throttled in app).  
10. Do not expose Postgres/Redis ports on public interface.

---

## 9. Smoke test plan

| Step | Expect |
|------|--------|
| `GET /ready` | 200, DB+Redis ok |
| Storefront home | Hero/products from live API |
| OTP login | SMS delivered; no `dev_code` in response |
| Purchase checkout | Gateway redirect + verify callback |
| Inquiry checkout | Tracking code without payment |
| Admin login | Password auth |
| Step-up action | PIN → destructive succeeds + audit row |
| Image upload | Served via API static/uploads URL over HTTPS |

---

## 10. Rollback

- Frontend: keep previous PM2/systemd release directory; symlink swap.  
- Backend: `docker compose` previous image tag; DB migrations must be backward-compatible or have down scripts before relying on auto-migrate.

---

## 11. Related docs

| Doc | Path |
|-----|------|
| Persian summary | `docs/deploy/DEPLOYMENT_fa.md` |
| FE-ahead API needs | `docs/gaps/01-fe-ahead-be-needed-en.md` |
| Unused BE APIs | `docs/gaps/02-be-exists-fe-should-use-en.md` |
| Local stack (no secrets) | `LOCAL_STACK_ACCESS.md` |
| Integration notes | `INTEGRATION_RUNTIME_NOTES.md` |

---

*This guide assumes single-VPS Compose deployment. For multi-node Kubernetes/ECS, keep the same env/security invariants and replace process/proxy sections accordingly.*
