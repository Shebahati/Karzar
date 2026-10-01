# Gate A — Post-deploy acceptance (Phase 2B)

## Runtime identity

| Claim | Evidence | Proven live? |
|-------|----------|--------------|
| Expected Phase 2B merge SHA | `dc16270ae045bf4cef6ffd40cdc041596ec508a6` | Anchor |
| Last successful Deploy Staging | GitHub Actions run `36824461331` on runner `karzar-vps` / machine `srv5944957438` | Yes (deploy logs) |
| Package / FE images | `karzar-shop:sha-dc16270…`, `karzar-admin:sha-dc16270…`, `EXPECTED_SHA=dc16270…`, smoke `DEPLOY_FE_SMOKE_OK` | Yes (deploy logs) |
| Later deploy after 36824461331 | None (as of audit capture) | Yes (gh run list) |
| Live `docker inspect` / `git rev-parse` in `/opt/karzar` | Blocked — cloud VM has no SSH keys; TCP/22 to VPS times out; Task API cannot place agent on private worker `hp-g2-450` | **No** |
| Live Alembic / APP_ENV / volume names | Same blocker | **No** |

**Observed runtime SHA (live container):** `UNPROVEN`  
**Best deploy-log SHA with no superseding deploy:** `dc16270ae045bf4cef6ffd40cdc041596ec508a6`

## Live HTTP acceptance (public)

See `GATE_A_LIVE_ACCEPTANCE.json`.

- API `/ready` + `/health` → 200, database/redis ok  
- Storefront `/` → 200  
- Admin `/login` → 200  
- Identity search (name/SKU/brand) → functional  
- Multi-token AND-of-OR + negative impossible token → functional  
- Normalization `كولیس`≡`کولیس` → 186=186  
- Escaping `%` / `\` → totals 0, no 500  
- `on_sale` ∩ search (اینسایز=385, داسکوا=0) → intersection semantics  
- `sort=id_asc` pagination → ordered, disjoint pages  
- Sitemap index + children → 200 XML, no `Invalid sort key`  
- Naming preview unauth → 401 (contract present; zero-write not DB-proven without admin token)  
- Admin UI source (repo) exposes `نام استاندارد کارزار`, read-only OEM, no Apply/Rename controls  

## Sitemap build warning classification

- **Original symptom:** Docker build log during deploy packaging:  
  `[sitemap] cohort=product_count generation failed … Invalid sort key`  
- **Current live result:** `/sitemap.xml` and all child locs HTTP 200, XML, product shards populated  
- **Classification:** `TRANSIENT PRE-BACKEND-SWAP BUILD WARNING`  
- **Evidence:** warning occurred while building FE images against then-running API before backend swap; post-deploy public sitemaps succeed; live `id_asc` returns 200

## Result

`POST_DEPLOY_ACCEPTANCE = PASS_WITH_LIMITATIONS`

### Limitations

1. Live container SHA / Alembic / APP_ENV / DB volume not inspectable from this cloud agent  
2. SQL non-deleted baseline + `manufacturer_code` null/non-null counts unavailable (no SSH/psql)  
3. Authenticated naming-preview zero-write not proven (staging admin credentials not available to this VM; unauth=401)  
4. Live synonym sample data absent — implementation verified in `app/utils/catalog_identity_search.py` (`jsonb_array_elements` + `jsonb_typeof = 'string'`)  
5. manufacturer_code search: **CAPABILITY PRESENT / DATA NOT YET POPULATED** via public payloads (field admin-only / null)
