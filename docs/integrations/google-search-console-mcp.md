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
- **Option A (later):** Authenticated HTTPS reverse proxy (e.g. `mcp.karzartools.com`) terminating TLS and forwarding to the container.

ChatGPT (Developer mode → MCP): add server URL, set authentication to Bearer token, scan tools, use in a chat. Exact UI labels may change; follow current OpenAI docs.

## Configuration

| Variable | Purpose |
|----------|---------|
| `GSC_SITE_URL` | Default property (`sc-domain:karzartools.com`) |
| `GSC_ALLOWED_ORIGINS` | URL allowlist for inspection / CrUX page URLs |
| `GOOGLE_GSC_CLIENT_ID` / `SECRET` / `REFRESH_TOKEN` | Google OAuth (never commit) |
| `CRUX_API_KEY` | Optional CrUX key (never commit) |
| `KARZAR_MCP_ACCESS_TOKEN` | MCP client Bearer secret (never commit) |
| `MCP_HOST` / `MCP_PORT` | Default `127.0.0.1` / `8010` |

Placeholders only in repo; use secret storage in production.

## Google Cloud owner setup (one-time, manual)

1. Select or create a Google Cloud project.
2. Enable **Google Search Console API**.
3. Configure OAuth consent screen if required.
4. Create OAuth client (desktop or web with `http://127.0.0.1:8765/oauth/callback` for bootstrap).
5. Run local OAuth bootstrap (below) and sign in with the Google account that has access to `sc-domain:karzartools.com`.
6. Store refresh token in server secret storage (not git).
7. Optionally enable **Chrome UX Report API** and create an API key restricted to that API only.
8. Never paste secrets into GitHub, chat, or CI logs.

## OAuth bootstrap (local only)

```bash
export GOOGLE_GSC_CLIENT_ID=...
export GOOGLE_GSC_CLIENT_SECRET=...
python -m services.gsc_mcp.bootstrap_oauth
# Or write to ~/.config/karzar/gsc/credentials.json (mode 0600)
```

Use `--print-refresh-token` only when you will copy the value directly into secret storage (warning: secret).

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

## Docker (dormant)

Build only (no deploy in Phase 1):

```bash
docker build -f services/gsc_mcp/Dockerfile -t karzar-gsc-mcp .
```

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
