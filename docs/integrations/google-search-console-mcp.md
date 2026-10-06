# Google Search Console read-only MCP

Karzar-owned MCP server for **read-only** Search Console, URL Inspection (indexed version), and CrUX field data. It runs as a **separate process** from `lathe_api` and does not use PostgreSQL or Redis.

## Architecture

```text
MCP client (ChatGPT / Cursor / other)
        |  Authorization: Bearer KARZAR_MCP_ACCESS_TOKEN
        v
127.0.0.1:8010  services/gsc_mcp  (Streamable HTTP `/mcp`)
        |  OAuth refresh (webmasters.readonly)
        v
Google APIs (Search Console, URL Inspection, CrUX)
```

Code lives under `services/gsc_mcp/`. Dependencies are pinned in `services/gsc_mcp/requirements.txt` (not the main backend `requirements.txt`).

## Google APIs and scope

| API | Use |
|-----|-----|
| Search Console API v3 | `Sites.list/get`, `searchAnalytics.query`, `Sitemaps.list/get` |
| URL Inspection API | `urlInspection/index:inspect` (indexed version only) |
| Chrome UX Report API | `records:queryRecord` (optional `CRUX_API_KEY`) |

OAuth scope (only):

```text
https://www.googleapis.com/auth/webmasters.readonly
```

**Not supported (by design):** sitemap submit/delete, site add/delete, request indexing, Indexing API, live URL test, Page Indexing aggregate API, generic Google proxy tools.

## MCP transport and ChatGPT connection

Doc authority checked during implementation (2026-10-01):

- [Model Context Protocol — transports](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) — Streamable HTTP is the remote transport; local default is `http://127.0.0.1:8010/mcp`.
- [OpenAI — MCP servers for ChatGPT](https://platform.openai.com/docs/guides/tools-remote-mcp) — remote MCP over HTTPS; Bearer token on requests is supported for secured servers.

**Recommended connection modes (Phase 1 — not activated in production):**

- **Option B (local):** ChatGPT / client via **Secure MCP tunnel** or SSH port-forward to `127.0.0.1:8010`, with `KARZAR_MCP_ACCESS_TOKEN`.
- **Option A (production target):** Authenticated HTTPS reverse proxy at `https://mcp.karzartools.com/mcp` (Nginx on the VPS) terminating TLS and forwarding to `127.0.0.1:8010`. See **Production deployment (owner-run)** below.

ChatGPT (Developer mode → MCP): add server URL, set authentication to Bearer token, scan tools, use in a chat. Exact UI labels may change; follow current OpenAI docs.

## Configuration

| Variable | Purpose |
|----------|---------|
| `GSC_SITE_URL` | Default property (`sc-domain:karzartools.com`) |
| `GSC_ALLOWED_ORIGINS` | URL allowlist for inspection / CrUX page URLs |
| `GOOGLE_GSC_CLIENT_ID` / `SECRET` / `REFRESH_TOKEN` | Google OAuth (never commit) |
| `CRUX_API_KEY` | Optional CrUX key (never commit) |
| `KARZAR_MCP_ACCESS_TOKEN` | MCP client Bearer secret (never commit) |
| `MCP_HOST` / `MCP_PORT` | Local default `127.0.0.1` / `8010`; Docker production uses `MCP_HOST=0.0.0.0` with host bind `127.0.0.1:8010` |
| `MCP_PUBLIC_BASE_URL` | Public MCP base, e.g. `https://mcp.karzartools.com` |

Placeholders only in repo; use secret storage in production.

## Google Cloud owner setup (one-time, manual)

Doc authority (OAuth bootstrap hardening, 2026-10-03):

- [OAuth 2.0 for desktop apps](https://developers.google.com/identity/protocols/oauth2/native-app) — loopback redirect, PKCE, system browser.
- [Using OAuth 2.0 to access Google APIs](https://developers.google.com/identity/protocols/oauth2) — token endpoint uses `application/x-www-form-urlencoded`.
- [Search Console API authorization](https://developers.google.com/webmaster-tools/v1/how-tos/authorizing) — readonly scope.

1. Select or create a Google Cloud project.
2. Enable **Google Search Console API**.
3. Configure the Google Auth consent screen if required.
4. Create an OAuth client ID with application type **Desktop app** (not deprecated OOB).
5. Download the client JSON locally (never commit).
6. Run local OAuth bootstrap (below); the system browser opens, you approve **only** `webmasters.readonly`, and the loopback callback completes automatically.
7. Credentials are written to `~/.config/karzar/gsc/credentials.json` with mode `0600`.
8. Copy refresh token (and client id/secret if used) into server secret storage for production MCP runtime env vars.
9. Optionally enable **Chrome UX Report API** and create an API key restricted to that API only.
10. Never paste secrets into GitHub, chat, or CI logs.

**No manual OOB copy/paste of authorization codes is required** for the default bootstrap flow.

## OAuth bootstrap (local only)

```bash
python -m services.gsc_mcp.bootstrap_oauth --credentials-file /path/to/client_secret_desktop.json
```

Optional: `--no-browser` prints the authorization URL instead of opening a browser.

Use `--print-refresh-token` only as an advanced option when copying directly into secret storage (warning: secret). It is not the normal path.

## Run locally

```bash
pip install -r services/gsc_mcp/requirements.txt
export PYTHONPATH=.
export KARZAR_MCP_ACCESS_TOKEN=...   # high-entropy
export GOOGLE_GSC_CLIENT_ID=...
export GOOGLE_GSC_CLIENT_SECRET=...
export GOOGLE_GSC_REFRESH_TOKEN=...
python -m services.gsc_mcp
curl -s http://127.0.0.1:8010/health
```

## Tests

```bash
pip install -r requirements-dev.txt -r services/gsc_mcp/requirements.txt
PYTHONPATH=. pytest tests/test_gsc_mcp_*.py -q
```

No real Google credentials required; HTTP is mocked.

## Docker

Build image (no secrets in context):

```bash
docker build -f services/gsc_mcp/Dockerfile -t karzar-gsc-mcp .
```

Compose overlay: `docker-compose.gsc-mcp.yml` (service `gsc_mcp`, container `karzar_gsc_mcp`). Host publish is **loopback only**: `127.0.0.1:8010:8010`. Inside the container the process listens on `MCP_HOST=0.0.0.0` and `MCP_PORT=8010`.

Env template (placeholders only): `deploy/staging/.env.gsc-mcp.template`.

## Production deployment (owner-run)

**This section documents steps the repository owner runs on the VPS after merge. Agents and CI must not execute deploy, DNS, certbot, or secret provisioning.**

### Never put secrets in

- Git / GitHub
- Cursor chat or prompts
- CI logs
- Docker image layers or build context

Required runtime secrets (VPS env file only):

| Variable | Notes |
|----------|--------|
| `GOOGLE_GSC_CLIENT_ID` | From OAuth client; desktop JSON does not need to be copied to VPS if id/secret/token are set |
| `GOOGLE_GSC_CLIENT_SECRET` | |
| `GOOGLE_GSC_REFRESH_TOKEN` | From local bootstrap |
| `KARZAR_MCP_ACCESS_TOKEN` | High-entropy Bearer for MCP clients, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

Optional: `CRUX_API_KEY` (CrUX API only).

File permissions: `chmod 600`, owned by the deployment user (example path `/etc/karzar/gsc-mcp.env`).

### Rotation (separate procedures)

- **MCP Bearer:** generate new token, update env file, `docker compose … up -d gsc_mcp` (recreate container), update clients.
- **Google refresh token:** re-run local `bootstrap_oauth` or revoke in Google Account → update env → recreate container.
- **OAuth client secret:** rotate in Google Cloud Console → update env → recreate container.
- **CrUX API key:** rotate in GCP → update env.

### MCP client timeouts (local / manual clients)

URL Inspection can take longer than default HTTP client read timeouts. If the MCP server succeeds but the client drops the SSE stream (~5s with some defaults), increase the **client** read timeout, for example:

```python
import httpx

timeout = httpx.Timeout(30.0, read=300.0)
```

Do not shorten Google upstream timeouts only to satisfy a short client timeout.

### Owner checklist

1. **DNS (manual):** `mcp.karzartools.com` → VPS public IP (no automation in repo).
2. **TLS (manual):** Let's Encrypt certificate for `mcp.karzartools.com` (e.g. certbot with Nginx).
3. **Secrets:** copy `deploy/staging/.env.gsc-mcp.template` to `/etc/karzar/gsc-mcp.env`, fill values, `chmod 600`.
4. **Build & start MCP only** (does not restart db/redis/app):

   ```bash
   cd /opt/karzar/Karzar   # or your deploy root
   git pull origin main
   docker compose -f docker-compose.gsc-mcp.yml --env-file /etc/karzar/gsc-mcp.env up -d --build gsc_mcp
   ```

5. **Loopback health:**

   ```bash
   curl -fsS http://127.0.0.1:8010/health
   ```

6. **Container:**

   ```bash
   docker ps --filter name=karzar_gsc_mcp
   docker inspect --format='{{.State.Health.Status}}' karzar_gsc_mcp
   ```

7. **Bearer MCP (loopback):** POST/stream to `http://127.0.0.1:8010/mcp` with `Authorization: Bearer <KARZAR_MCP_ACCESS_TOKEN>` (do not echo token in shell history; use env or prompt).

8. **Nginx:** install `deploy/staging/nginx/mcp.karzartools.com.conf.template` (adjust TLS paths), `nginx -t`, reload. Public URL: `https://mcp.karzartools.com/mcp`. Public `/health` is denied by template; use loopback health above.

9. **Public HTTPS smoke:** `curl -fsS -o /dev/null -w '%{http_code}\n' https://mcp.karzartools.com/mcp` (expect `401` without Bearer, not `502`).

### Rollback

1. Disable/remove Nginx site for `mcp.karzartools.com` and reload Nginx.
2. `docker compose -f docker-compose.gsc-mcp.yml --env-file /etc/karzar/gsc-mcp.env stop gsc_mcp` (or `down` for the MCP project only).
3. Leave `lathe_api`, Postgres, Redis, storefront, and admin untouched.

## MCP tools

Read-only tools: `gsc_list_properties`, `gsc_get_property`, `gsc_search_analytics`, `gsc_list_sitemaps`, `gsc_get_sitemap`, `gsc_inspect_url`, `crux_get_origin_field_data`, `crux_get_url_field_data`, `gsc_capabilities`, plus diagnostic `gsc_auth_probe`.

Search Analytics: row totals may not sum to property totals (privacy / limits). URL Inspection: **indexed version**, not live test.

## Rotation and revocation

- Rotate `KARZAR_MCP_ACCESS_TOKEN` in secret storage; restart the MCP process.
- Revoke Google refresh token in Google Account security or re-issue OAuth client secret and re-bootstrap.
- Rotate `CRUX_API_KEY` in Google Cloud Console; update server env.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `401` on `/mcp` | `KARZAR_MCP_ACCESS_TOKEN` and `Authorization: Bearer` header |
| `AUTH_NOT_CONFIGURED` | Google OAuth env vars |
| `CRUX_NOT_CONFIGURED` | `CRUX_API_KEY` optional |
| `PROPERTY_FORBIDDEN` | `GSC_SITE_URL` / foreign property flag |
| `URL_NOT_ALLOWED` | URL must match `GSC_ALLOWED_ORIGINS` |

## Limitations

- No Page Indexing aggregate API (UI export remains manual evidence).
- No Live URL Test via API.
- No request indexing or sitemap mutation.
- No brand/non-branded classification in the transport layer.
