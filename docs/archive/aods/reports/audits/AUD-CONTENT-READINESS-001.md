# AUD-CONTENT-READINESS-001 — Content / catalog / KB readiness (Definition A)

**Node:** `AUD-CONTENT-READINESS-001`  
**Archetype:** AUD  
**Prompt:** `aods/70-prompts/audit/AUD-repository-scan.prompt.md`  
**Date:** 2026-07-30  
**Decision ceiling:** D0 (report only; no fixes)  
**Human scope lock:** Definition **A** — post-checkpoint content readiness = close `CAT-002` + `KB-001` phase-1 + quality of existing 24 articles + finish open EPIC-1 (`SEO-008`, `FE-002`) + catalog hygiene; **not** full knowledge platform / all-brand enrichment / head-term rank chase.

**SCAN_SCOPE (precise path set):**

| Area | Paths |
|------|-------|
| Storefront content JSON | `frontend/Storefront/content/**` |
| PMO status for open readiness tasks | `project-management/exports/tasks.json`, `progress/CONTENT_PROGRESS.md`, `progress/KNOWLEDGE_BASE_PROGRESS.md`, `sprints/SPRINT_05.md`, `CONTENT_CALENDAR.md`, `EXECUTIVE_SUMMARY.md` |
| Knowledge programme docs | `docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}*.md`, `docs/architecture/karzar-knowledge-platform-master-architecture.md` |
| EPIC-1 Brand Hub | `docs/architecture/information-architecture/epic1-ia-readiness.md`, `brand-hub-page-contract.md`, `docs/architecture/rfc/RFC-005-brand-hub-launch.md` |
| Ingestion policy (catalog writes) | `docs/architecture/data-ingestion-policy.md` |
| INSIZE / publish scripts (enumerate only) | `scripts/*insize*`, `scripts/*shopmill*`, `scripts/*seo003*` |
| As-built Article model (cite only) | `app/db/models/content.py` |
| OpenAPI article/brand surfaces | `openapi/v1.json` paths containing `article` or `brand` |

**Forbidden-context exception:** NO.

---

## 1. Measurement table

Every quantity below was produced by the listed command in this workspace on 2026-07-30.

| ID | Claim / quantity | Command | Observed output (summary) |
|----|------------------|---------|---------------------------|
| M01 | Tracked content files under Storefront content | `git ls-files 'frontend/Storefront/content/**' \| wc -l` | `4` |
| M02 | Articles in `articles.json` | `python3` load JSON → `len(articles)` | declared `count=24`, actual `24`, `published=24` |
| M03 | Articles with `<2` `related_product_ids` | same | `n=0`; distribution `{3: 24}` |
| M04 | Articles with `faq` block | same | `24` / `24` |
| M05 | Articles with placeholder cover image | `"placeholder" in cover_image` | `24` / `24` |
| M06 | Articles missing `/categories/` string in JSON | regex on article blob | `n=0` |
| M07 | Hub intros | `len(hubs)` vs `meta.count` | `15` hubs, `meta.count=15` |
| M08 | Hubs with `<3` links | count `links` | `hubs_lt3_links=[]` |
| M09 | Hub word counts (joined `paragraphs`) | word split | all in **150–226** (matches SEO-002 150–300w bar in PMO AC) |
| M10 | Knowledge Platform phase docs | `git ls-files 'docs/KNOWLEDGE_PLATFORM*'` + `wc -l` | **3** files; **1337** total lines |
| M11 | INSIZE/Shopmill-related scripts | `git ls-files 'scripts/*' \| rg -i 'insize\|shopmill'` | **6** paths |
| M12 | SEO-003 scripts | `git ls-files` match `*seo003*` | `generate_seo003_articles.py`, `publish_seo003_articles.py` |
| M13 | All `scripts/*.py` | `git ls-files 'scripts/*.py' \| wc -l` | `42` |
| M14 | All tracked under `scripts/` | `git ls-files 'scripts/*' \| wc -l` | `66` |
| M15 | PMO tasks total / todo / done | parse `tasks.json` | `n_tasks=28`, `todo=4`, `done=24`, `as_of=2026-07-30` |
| M16 | Open task IDs | same | `CAT-002`, `KB-001`, `SEO-008`, `FE-002` |
| M17 | Open task hours sum | sum `hours` on todo | **86** (20+30+24+12) |
| M18 | Storefront `/brands` app routes | `git ls-files 'frontend/Storefront/src/app/brands/**' \| wc -l` | **0** |
| M19 | Storefront blog routes | `git ls-files …/app/blog/**` | `blog/page.tsx`, `blog/[slug]/page.tsx` present |
| M20 | OpenAPI article+brand paths | keys in `openapi/v1.json` with `article` or `brand` | **8** paths (articles public+CMS, brands list/slug/id/logo) |
| M21 | `pdf_catalog_url` in product components | `rg` under `components/product/` | **no hits** |
| M22 | `pdf_catalog_url` elsewhere in Storefront src | `rg` | type + `mock-data.ts` only (field exists; UI slot not observed in product components) |

### Reproducibility commands (copy-paste)

```bash
git ls-files 'frontend/Storefront/content/**' | wc -l
python3 -c 'import json; from pathlib import Path; d=json.loads(Path("frontend/Storefront/content/blog/articles.json").read_text()); print(d["count"], len(d["articles"]), sum(1 for a in d["articles"] if a.get("is_published")))'
python3 -c 'import json; from pathlib import Path; h=json.loads(Path("frontend/Storefront/content/hubs/intros.json").read_text()); print(len(h["hubs"]), h.get("meta",{}).get("count"))'
git ls-files 'docs/KNOWLEDGE_PLATFORM*'; wc -l docs/KNOWLEDGE_PLATFORM*.md
git ls-files 'scripts/*' | rg -i 'insize|shopmill' | wc -l
python3 -c 'import json; t=json.load(open("project-management/exports/tasks.json")); print(len(t["tasks"]), [x["id"] for x in t["tasks"] if x["status"]=="todo"])'
git ls-files 'frontend/Storefront/src/app/brands/**' | wc -l
```

---

## 2. Classification table (registry)

| Path | Registry class | Registry status | Notes |
|------|----------------|-----------------|-------|
| `frontend/Storefront/content/blog/articles.json` | **UNREGISTERED** | — | Primary article authoring artifact in-repo; not in `document-registry.yaml` |
| `frontend/Storefront/content/hubs/intros.json` | **UNREGISTERED** | — | Same |
| `project-management/CONTENT_CALENDAR.md` | PLAN | current | |
| `project-management/exports/tasks.json` | (registered PLAN/GENERATED family — PMO) | — | Machine SoT for task status |
| `docs/KNOWLEDGE_PLATFORM_PHASE1_ARCHITECTURE_AUDIT.md` | PROPOSED | proposed | |
| `docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md` | PROPOSED | proposed | |
| `docs/KNOWLEDGE_PLATFORM_PHASE3_IMPLEMENTATION_ROADMAP.md` | PROPOSED | proposed | |
| `docs/architecture/karzar-knowledge-platform-master-architecture.md` | CANON | accepted | Orientation / Bible; does **not** alone authorise I0 implementation without Board slice |
| `docs/architecture/information-architecture/epic1-ia-readiness.md` | CANON | accepted | EPIC-1 must/must-not |
| `docs/architecture/information-architecture/brand-hub-page-contract.md` | PROPOSED | proposed | Awaits HC-01 |
| `docs/architecture/rfc/RFC-005-brand-hub-launch.md` | CANON | accepted | Launch sequencing |
| `docs/architecture/data-ingestion-policy.md` | CANON | binding | Catalog write rules |

**Proposed GOV follow-up (do not act here):** register the two content JSON files (class `GENERATED` or `PLAN` — human chooses) so validators see them.

---

## 3. Claim verification

| ID | Claim | Source | Check | Verdict |
|----|-------|--------|-------|---------|
| C01 | 24 SEO-003 articles in content store | `REPOSITORY-AUDIT.md:69` | M02 | **CONFIRMED** |
| C02 | 15 hub intros | `REPOSITORY-AUDIT.md:69` | M07–M09 | **CONFIRMED** |
| C03 | SEO-003 done / 24 published / ≥2 products / FAQ | `CONTENT_PROGRESS.md:20-34`; calendar all `[x]` | M02–M06 | **CONFIRMED** for JSON artifact DoD fields measured; **UNVERIFIABLE** for “Live CMS == JSON” without API/DB access (G-07) |
| C04 | Open tasks only CAT-002 + KB-001 | `REPOSITORY-AUDIT.md:176` | M16 | **CONTRADICTED** — current open set is **four**: also `SEO-008`, `FE-002` (`tasks.json` 2026-07-30). Audit text is stale relative to Sprint 05 Board wave. |
| C05 | KB-001 deferred / ~10% | `KNOWLEDGE_BASE_PROGRESS.md:5-17`; `tasks.json` | progress=10, status=todo, revisit 2026-09-23 | **CONFIRMED** as PMO status |
| C06 | CAT-002 deferred INSIZE #90 | `tasks.json` CAT-002 notes | status=todo progress=15 | **CONFIRMED** as PMO status; **UNVERIFIABLE** live PR #90 state (`gh` network failed this run) |
| C07 | “Knowledge platform کامل” not realistic for checkpoint | `EXECUTIVE_SUMMARY.md:33-34` | Definition A explicitly excludes full platform | **CONFIRMED** as PLAN authority for scheduling |
| C08 | Brand Hub SPEC Proposed; IMPL blocked HC-01 Q1–Q5 | `brand-hub-page-contract.md:4-15`, `:157-165`; `SPRINT_05.md:14-16` | M18 = 0 brand routes | **CONFIRMED** |
| C09 | G-01 Brand Hub page spec missing | `REPOSITORY-AUDIT.md:281` | Contract file now exists as **Proposed** | **PARTIALLY SUPERSEDED** — structure drafted; thresholds still open (Q1–Q5). Treat as **SPEC-ready, not Accepted**. |
| C10 | G-07 Content authority JSON vs CMS | `REPOSITORY-AUDIT.md:287` | Dual stores still present (JSON + `/api/v1/cms/articles`) | **CONFIRMED still open** (no SoR doc found in scope) |
| C11 | Article model has `related_product_ids` JSONB | `app/db/models/content.py:43` | read model | **CONFIRMED** — product links are list-of-ids, **not** a queryable knowledge graph |
| C12 | FE-002 “partial UI affordances” | `tasks.json` FE-002 notes | M21–M22 | **UNVERIFIABLE / WEAK** — `pdf_catalog_url` typed + mocked null; **no** product-component render found. Accessories hits are nav/category imagery, not PDP relation slot. |

---

## 4. Enforcement table

| Rule / expectation | Documented where | Enforced by | Finding |
|--------------------|------------------|-------------|---------|
| Local-only routine ingestion | ADR-012 + data-ingestion-policy | `aods_validate.py --gate ingestion-boundary` (gate registered) | **Documented + gated** (gate exists in validator; this node did not re-run full gate matrix beyond §11) |
| PMO living sync | `.cursor/rules/pmo-living-system.mdc` | Process / Cursor rule; no machine gate proving mirror sync | **Documented, weakly enforced** |
| Brand Hub must not invent thin-hub policy | `brand-hub-page-contract.md` + CR-014 | Human HC-01; IMPL forbidden until Accepted | **Documented; human-enforced** |
| SEO-003 article DoD (≥2 products, FAQ) | CONTENT_CALENDAR / task AC | No CI test found asserting JSON DoD in this scan | **Documented; content-artifact currently meets fields; unenforced in CI** |
| Knowledge graph links queryable | KB-001 AC | No graph tables/endpoints observed in Article model | **Documented AC; unimplemented** |
| Content JSON vs CMS precedence | (missing — G-07) | Nothing | **Undocumented; unenforced** |
| Register content JSON in document-registry | registry completeness | `aods_validate --gate registry` may allow via globs | **UNREGISTERED artifacts** |

---

## 5. Gaps (expected for Definition A, missing or incomplete)

| Gap ID | Gap | Blocks |
|--------|-----|--------|
| G-A1 | No Storefront `/brands/[slug]` route (M18=0) | `SEO-008` |
| G-A2 | Brand Hub Q1–Q5 unanswered; contract `Proposed` | HC-01 → SEO-008 IMPL |
| G-A3 | ORM Brand has no long description column (cited in contract) | Hub blurb strategy (Q3) |
| G-A4 | KB-001: no queryable article↔product↔category graph beyond `related_product_ids` list | Knowledge readiness A |
| G-A5 | Knowledge Phase docs are PROPOSED; I0 not started (Phase1 status narrative) | KB-001 implementation slice choice |
| G-A6 | CAT-002 INSIZE content fill still todo 15%; ≥200 SKU QA unmet in PMO | Catalog readiness A |
| G-A7 | All 24 article covers are placeholders | Content quality bar beyond SEO-003 checkbox |
| G-A8 | FE-002 PDF CTA + accessories slot not evidenced in product components | EPIC-1.7 |
| G-A9 | G-07 JSON vs CMS SoR still unspecified | Publish/drift risk for articles |
| G-A10 | Live product count / enrichment coverage not measurable without DB | Catalog hygiene evidence |

---

## 6. Unknowns

| U# | Unknown | What would resolve it |
|----|---------|------------------------|
| U1 | Whether CMS DB article rows match `articles.json` 1:1 on live/staging | Local API dump or admin export; decide G-07 |
| U2 | GSC index / CTR for 24 articles | Search Console export (outside git) |
| U3 | GitHub PR #90 current state | `gh pr view 90` with working network |
| U4 | How many INSIZE SKUs already have content-safe fields filled | Local DB query / dry-run report artifact |
| U5 | Active product count today (audit cites ~5901 baseline) | `SELECT count(*)` on local/staging DB — **not estimated here** |
| U6 | Which brands are Wave-1 priority for hubs | Board list (RFC-005 waves) + inventory of brands with slug+meta+logo |
| U7 | How many products have non-null `pdf_catalog_url` and accessory relations | DB/API sample |
| U8 | Whether any knowledge-graph tables exist outside `content.py` Article | Broader `app/db/models` + alembic scan (out of this node’s full-read budget; not asserted) |

---

## 7. Definition A — readiness snapshot (inferred from measurements)

| Pillar | PMO task | Tracked status | Evidence posture |
|--------|----------|----------------|------------------|
| Articles (checkpoint set) | SEO-003 | **done** | JSON DoD fields **CONFIRMED**; covers all placeholders; live CMS sync **UNVERIFIABLE** |
| Category hubs | SEO-002 | **done** | 15 hubs, words≥150, links≥3 **CONFIRMED** |
| Catalog INSIZE fill | CAT-002 | **todo 15%** deferred revisit 2026-09-23 | Scripts exist; apply not done in PMO |
| Knowledge graph seed | KB-001 | **todo 10%** deferred | Docs PROPOSED; Article links are ID lists only |
| Brand Hub | SEO-008 | **todo 15%** blocked HC-01 | SPEC Proposed; **0** FE routes |
| PDP PDF + accessories | FE-002 | **todo 10%** | Type field exists; UI slot **not observed** |
| **Tracked remaining hours** | — | — | **86h** open-task estimate (not wall-clock) |

**Observed:** Checkpoint content KPI (24 articles + hubs) is met in-repo.  
**Inferred:** “آمادگی کامل” under Definition A is **not** met; remaining critical path is EPIC-1 blockers + deferred CAT/KB + content hardening (covers, SoR, PDF data).

---

## 8. What the human must prepare (inputs — not invented by agents)

### 8.1 Decisions (Board / HC)

1. **HC-01 freeze Brand Hub** — answer **Q1–Q5** in `brand-hub-page-contract.md:161-165`; then set status Accepted (Board only).  
2. **Lift or keep deferral** for `CAT-002` / `KB-001` before 2026-09-23 revisit (PMO/Board). Definition A assumes they **will** be executed.  
3. **G-07** — declare SoR: Git JSON vs CMS DB after publish (write a short POLICY/PLAN note).  
4. **KB-001 slice** — which Phase-1 relations are in-scope for “phase-1 seed” (articles↔products↔categories only vs more). Cite PROPOSED docs; do not invent schema.

### 8.2 Content / assets to supply

| # | Artifact | Needed for |
|---|----------|------------|
| H1 | Priority brand list (Wave membership) with approved Persian display names | SEO-008 |
| H2 | Brand intro blurbs **if Q3=A** (authored like hubs) — one short paragraph each; **no invented specs** | SEO-008 |
| H3 | Brand logos (SVG/PNG rights-cleared) **if Q5=Required** | SEO-008 |
| H4 | Real editorial cover images for 24 articles (replace placeholders) | Article quality |
| H5 | INSIZE source package / Shopmill crawl outputs already used by scripts + QA checklist for ≥200 SKUs | CAT-002 |
| H6 | Product PDF/datasheet URLs or files for priority SKUs (`pdf_catalog_url`) | FE-002 |
| H7 | Accessory / related-SKU pairs (or honest empty policy confirmation) | FE-002 |
| H8 | Optional: GSC CSV for the 24 article URLs | Measurement, not ship-blocker |

### 8.3 Operational authorisations

| # | Checkpoint | Why |
|---|------------|-----|
| O1 | **HC-09** before any staging/production catalog write for CAT-002 | ADR-012 / ingestion boundary |
| O2 | Confirm target API is local/`127.0.0.1` for routine enrich | Same |
| O3 | HC-06/07 for merges that deploy (same-VPS residual awareness) | Deploy topology |

---

## 9. Proposed follow-up nodes (do not execute in this AUD)

| Order | Node | Archetype | Purpose |
|------:|------|-----------|---------|
| 1 | `DOC-FULL-CONTENT-READINESS-PLAN-001` | DOC/GOV | Write step-by-step MD plan from this audit (user-requested deliverable) under `project-management/` + registry if needed |
| 2 | Human **HC-01** | Human | Freeze Brand Hub Q1–Q5 |
| 3 | `IMPL-frontend-route` SEO-008 | IMPL | `/brands/[slug]` after Accepted |
| 4 | `IMPL-frontend-route` / component FE-002 | IMPL | PDF CTA + accessories slot |
| 5 | `KNOW-catalog-ingest` CAT-002 | KNOW | INSIZE content-safe fill, local only |
| 6 | `SPEC` then `IMPL` KB-001 | SPEC→IMPL | Graph seed; avoid second taxonomy |
| 7 | `GOV` register content JSON + close stale REPOSITORY-AUDIT open-task claim | GOV | Registry + audit freshness |
| 8 | Optional content QA node | DOC/TEST | Replace placeholder covers; verify CMS sync |

**Recommended execution order for Definition A (logical dependency):**  
HC-01 → SEO-008 + FE-002 (parallel after unblocked) → CAT-002 (HC-09) → KB-001 (depends SEO-003 already done) → content hardening (covers, G-07) → plan/PMO close.

---

## 10. Conflict / stale notes (propose only)

| Item | Proposal |
|------|----------|
| `REPOSITORY-AUDIT.md:176` open-task list stale | GOV/DOC refresh evidence row — append note; do not silently rewrite history elsewhere |
| CR-014 still OPEN | Remains until HC-01 + SEO-008; SPEC file exists |
| UNREGISTERED content JSON | Registry add via GOV |

---

## 11. Line quotation checks (sed)

```
sed -n '69p' aods/10-repository-intelligence/REPOSITORY-AUDIT.md
# | Content store | `frontend/Storefront/content/` — `blog/articles.json` (24 SEO-003 articles), `hubs/intros.json` (15 hub intros). **JSON, not MDX.** |

sed -n '176p' aods/10-repository-intelligence/REPOSITORY-AUDIT.md
# | Open tasks | `CAT-002` (INSIZE fill, 15%), `KB-001` (knowledge graph, 10%) — both **deliberately deferred** to after 2026-09-22 |

sed -n '33,34p' project-management/EXECUTIVE_SUMMARY.md
# بله برای: … ۲۴ مقاله … / خیر برای: … knowledge platform کامل …

sed -n '161p' docs/architecture/information-architecture/brand-hub-page-contract.md
# | Q1 | Minimum active product count to **publish** a hub? | …
```
