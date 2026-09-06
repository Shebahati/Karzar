# AUD-KNOWLEDGE-FOUNDATION-001 — Knowledge Architecture Foundation Audit (Option A)

**Node:** `AUD-KNOWLEDGE-FOUNDATION-001`  
**Archetype:** AUD  
**Prompt:** `aods/70-prompts/audit/AUD-repository-scan.prompt.md`  
**Date:** 2026-07-30  
**Decision ceiling:** D0 (report only; no fixes; no new master files created)  
**Human scope lock:** Option **A** — all Phase 1–7 deliverables as **EVIDENCE + recommendations** inside this report; do **not** create `DOCUMENT_GOVERNANCE_MODEL.md` / `MASTER_*.md` as binding or Proposed files in this node.  
**TASK_ID:** NONE — CR-008 risk (spans `KB-001`, catalog/import governance, Canon/AODS authority; no single PMO task owns “knowledge foundation programme”).  
**Base:** `origin/main` fetch 2026-07-30; working tree on `main` at merge-base `2de8f39c4b43b56b8185aa181e915d16508f066f`.

**Forbidden-context exception:** NO (quarantined paths inventoried via registry/`git ls-files` only; contents not read as truth).

---

## SCAN_SCOPE (precise path set)

| Area | Paths measured |
|------|----------------|
| Authority / registry | `aods/10-repository-intelligence/AUTHORITY-MODEL.md`, `REPOSITORY-AUDIT.md`, `CONFLICT-REGISTER.md`, `aods/registry/document-registry.yaml` |
| Process knowledge flow | `aods/90-governance/KNOWLEDGE-FLOW.md`, `aods/AODS-CHARTER.md` |
| Canon / IA / SEO / ingest | `docs/architecture/CANON-LOCK.md`, `karzar-knowledge-platform-master-architecture.md`, `data-ingestion-policy.md`, `adr/ADR-010*`, `adr/ADR-012*`, `rfc/RFC-004*`, `rfc/RFC-005*`, `information-architecture/**`, `product-seo-descriptions-plan.md` |
| Knowledge programme (Proposed) | `docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` |
| Catalog ops docs | `docs/SEED_IMPORT.md`, `docs/SCRIPTS.md`, `docs/CATALOG_IMAGES_PLAN.md`, `docs/taxonomy/**` |
| As-built product/content models | `app/db/models/product.py`, `app/db/models/content.py` |
| API surface counts | `openapi/v1.json` |
| Import artifacts (counts) | `data/imports/**` CSV/JSON summaries; `scripts/*{seed,import,enrich,crawl,taxonomy,insize,dasqua,mitutoyo,shopmill,seo}*` |
| Storefront entity routes | `frontend/Storefront/src/app/{product,brands,categories}/**` |
| Content store | `frontend/Storefront/content/blog/articles.json`, `hubs/intros.json` |
| PMO | `project-management/EXECUTIVE_SUMMARY.md`, `progress/KNOWLEDGE_BASE_PROGRESS.md`, `exports/tasks.json` |
| Prior related evidence | `aods/reports/audits/AUD-CONTENT-READINESS-001.md` (if present in tree) |

**Out of scope for mutation:** all of the above (read-only). **Out of scope for full-line reads:** entire `docs/audits/**` bulk (registry allow-glob); quarantined docs; production DB/API.

---

## 0. Executive diagnosis (observed → inferred)

### Observed

1. The repository already has a **machine-enforced document authority system**: `AUTHORITY-MODEL.md` + `document-registry.yaml` (130 registered documents; class histogram below) and Canon Lock Wave-1 Accepted rows on `origin/main`.
2. **Knowledge Platform intent** exists as: one **Accepted** orientation bible (`karzar-knowledge-platform-master-architecture.md`) plus three **PROPOSED** phase docs (2010 lines combined with bible) that still say “awaiting approval” / design-only (`OI-KF-04`).
3. **As-built catalog** is commerce-first: `Product` / `Brand` / `Category` / JSONB `specifications` / soft links `Article.related_product_ids` — **no** `knowledge` OpenAPI paths, **no** Alembic files matching knowledge/graph tables.
4. **Ingestion governance** is strong on paper (`data-ingestion-policy.md`, ADR-012, `KNOWLEDGE-FLOW.md`) but several **cited companion packs are ABSENT** from this Git tree (`DOCUMENT_GOVERNANCE.md`, EPIC0 executive summary, baseline migration ops docs, enterprise KG/PIM packs — Canon Lock §3).
5. **Product census** is a **frozen claim of 5901** repeated across Canon/IA/bible; this audit **could not** verify live DB or production website counts (ADR-012 / no prod query). Import **artifacts** under `data/imports/` measure far smaller subsets (e.g. `all_products.csv` = 1251 data rows; Dasqua+INSIZE only).
6. EPIC-1 URL surfaces **exist in Storefront tree** (`/product/[slug]`, `/brands/[slug]`, `/categories/[slug]`), contradicting stale Phase-1 “`/product/{id}` only / no brand routes” claims.

### Inferred (labelled)

- KarzarTools is **not documentation-poor**; it is **documentation-overgoverned in process** and **under-specified in product-as-knowledge-entity**. Creating eight new `MASTER_*` filenames *as* Level-0 authority would **duplicate and risk contradicting** Accepted AODS/Canon — the governing architecture to follow is **extend Canon + fill missing Domain/KG/PIM packs**, not invent a parallel constitution.
- Readiness for a Grainger/RS/Mitutoyo-class Knowledge Base is **foundation-incomplete**: authority + URL/IA + ingestion policy exist; **product entity model, industrial taxonomy SoT, KG overlay schema, provenance store, and verified product baseline** do not.

---

## 1. Measurement table

Every quantity below was produced by the listed command in this workspace on 2026-07-30.

| ID | Claim / quantity | Command | Observed output (summary) |
|----|------------------|---------|---------------------------|
| M01 | Tracked markdown files | `git ls-files '*.md' \| wc -l` | **203** |
| M02 | `docs/**/*.md` | `git ls-files 'docs/**/*.md' \| wc -l` | **56** |
| M03 | `docs/*.md` (top-level glob as listed by git) | `git ls-files 'docs/*.md' \| wc -l` | **79** (includes nested matches under docs/) |
| M04 | `docs/architecture/**/*.md` | `git ls-files 'docs/architecture/**/*.md' \| wc -l` | **13** |
| M05 | `aods/**/*.md` | `git ls-files 'aods/**/*.md' \| wc -l` | **45** |
| M06 | `project-management/**/*.md` | `git ls-files 'project-management/**/*.md' \| wc -l` | **23** |
| M07 | `frontend/**/*.md` | `git ls-files 'frontend/**/*.md' \| wc -l` | **17** |
| M08 | `scripts/*.py` | `git ls-files 'scripts/*.py' \| wc -l` | **42** |
| M09 | All tracked under `scripts/` | `git ls-files 'scripts/*' \| wc -l` | **66** |
| M10 | Alembic version files | `git ls-files 'alembic/versions/*.py' \| wc -l` | **27** |
| M11 | ORM model modules | `git ls-files 'app/db/models/*.py'` | **8** files (`product`, `content`, `commerce`, `user`, `platform`, `hesabfa`, `base`, `__init__`) |
| M12 | Registry document entries parsed | Python parse of `document-registry.yaml` `  - id:` blocks | **130** |
| M13 | Registry class histogram | same | POLICY 37, CANON 22, PLAN 22, REFERENCE 20, EVIDENCE 11, HISTORICAL 8, CONTRACT 3, PROPOSED 3, QUARANTINED 3, GENERATED 1 |
| M14 | Knowledge programme files | `git ls-files 'docs/KNOWLEDGE*' 'docs/architecture/karzar-knowledge*'` | **4** paths |
| M15 | Knowledge programme + bible line counts | `wc -l docs/KNOWLEDGE_PLATFORM_PHASE*.md docs/architecture/karzar-knowledge-platform-master-architecture.md` | 337+632+373+668 = **2010** |
| M16 | OpenAPI paths / schemas | `python3` load `openapi/v1.json` | **82** paths, **115** schemas |
| M17 | OpenAPI paths containing `product` / `brand` / `knowledge` | same | productish **20**, brandish **4**, knowledge **[]** |
| M18 | Import/enrich/seed-related scripts | `git ls-files 'scripts/*.py' \| rg -i 'seed\|import\|enrich\|crawl\|taxonomy\|insize\|dasqua\|mitutoyo\|shopmill\|seo'` | **30** |
| M19 | `all_products.csv` data rows | `csv.reader` | **1251** (+header); brands Dasqua 909 + INSIZE 342; **1** duplicate SKU in file |
| M20 | Other import CSVs | same | `insize_products.csv` **342**; `dasqua_products.csv` **909**; `products_not_imported.csv` **187** |
| M21 | Dasqua catalog summary export | read `data/imports/dasqua/catalog_2025/summary.json` | `exported` **727**; match matched **343** / unmatched **123** / conflict **9**; `apply` false |
| M22 | Dasqua `site_export.csv` lines | `wc -l` | **728** (incl. header ⇒ ~727) |
| M23 | Articles / hubs in content JSON | load JSON | articles **24**/24; hubs **15** |
| M24 | Storefront entity routes present | `git ls-files …/app/{product,brands,categories}/**` | `product/[slug]/page.tsx`, `brands/[slug]/page.tsx`, `categories/[slug]/page.tsx` **present** |
| M25 | PMO tasks open | parse `tasks.json` | open: **CAT-002** `in_progress` 75; **KB-001** `todo` 10 (n_tasks=28) |
| M26 | User-requested master filenames in git | `git ls-files` each | **all ABSENT** (12 names + `docs/architecture/DOCUMENT_GOVERNANCE.md`) |
| M27 | Canon “not in this repo” companion packs cited by ingestion policy / bible | `git ls-files --error-unmatch` | **ABSENT:** `DOCUMENT_GOVERNANCE.md`, `specification-data-flow.md`, `docs/operations/database-baseline-migration-plan.md`, `docs/audits/production-to-development-synchronization-strategy.md`, `docs/audits/EPIC0-executive-summary.md`, `docs/prompts/karzar-enterprise-architecture-prompts.md` |
| M28 | Alembic knowledge/graph hits | `git ls-files alembic/versions/*.py \| xargs rg -l -i 'knowledge\|entity_graph\|kg_'` | **none** |
| M29 | Key authority paths resolve on `origin/main` | `git cat-file -e origin/main:<path>` | OK for AUTHORITY-MODEL, CANON-LOCK, data-ingestion-policy, KNOWLEDGE-FLOW |
| M30 | Taxonomy docs under `docs/taxonomy` | `git ls-files 'docs/taxonomy/**'` | **1** file: `remove_omumi_padding_dry_run_REPORT.md` (EVIDENCE) |

### Reproducibility commands (copy-paste)

```bash
git ls-files '*.md' | wc -l
git ls-files 'docs/architecture/**/*.md' | wc -l
git ls-files 'scripts/*.py' | wc -l
python3 -c 'import json;d=json.load(open("openapi/v1.json"));print(len(d["paths"]),len(d["components"]["schemas"]),len([p for p in d["paths"] if "knowledge" in p.lower()]))'
git ls-files 'docs/KNOWLEDGE*' 'docs/architecture/karzar-knowledge*'
wc -l docs/KNOWLEDGE_PLATFORM_PHASE*.md docs/architecture/karzar-knowledge-platform-master-architecture.md
python3 -c 'import csv;from pathlib import Path;r=list(csv.DictReader(Path("data/imports/all_products.csv").open(encoding="utf-8-sig")));print(len(r))'
git ls-files 'frontend/Storefront/src/app/product/**' 'frontend/Storefront/src/app/brands/**' 'frontend/Storefront/src/app/categories/**'
python3 -c 'import json;t=json.load(open("project-management/exports/tasks.json"));print([(x["id"],x["status"],x["progress"]) for x in t["tasks"] if x["status"]!="done"])'
```

---

## 2. Classification table (registry) + user classes A–G

### 2.1 AODS registry (authoritative machine classes)

| Path | Registry class | Status | Rank | Notes |
|------|----------------|--------|------|-------|
| `docs/architecture/CANON-LOCK.md` | CANON | accepted | 1 | Binding index |
| `docs/architecture/karzar-knowledge-platform-master-architecture.md` | CANON | accepted | 1 | Orientation bible; does **not** alone authorise I0 coding |
| `docs/architecture/adr/ADR-010-seo-url-contract.md` | CANON | accepted | 1 | PDP/Brand URL |
| `docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md` | CANON | accepted | 2 | Local-only routine ingest |
| `docs/architecture/rfc/RFC-004-slug-migration-and-redirects.md` | CANON | accepted | 1 | |
| `docs/architecture/rfc/RFC-005-brand-hub-launch.md` | CANON | accepted | 1 | |
| `docs/architecture/information-architecture/*` (primary pack) | CANON | accepted | 1 | IA + epic1 + url-map + brand-hub contract |
| `docs/architecture/data-ingestion-policy.md` | CANON | binding | 2 | Catalog write rules |
| `docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` | PROPOSED | proposed | 99 | Design context only |
| `aods/10-repository-intelligence/AUTHORITY-MODEL.md` | POLICY | accepted | 6 | Process authority ladder (AODS) |
| `aods/90-governance/KNOWLEDGE-FLOW.md` | POLICY | accepted | 6 | Provenance / transform pipeline |
| `aods/AODS-CHARTER.md` | POLICY | accepted | 6 | Process constitution |
| `docs/SEED_IMPORT.md` | POLICY | stale | 6 | Seed workflow; registry flags stale |
| `docs/SCRIPTS.md` | POLICY | current | 6 | |
| `docs/CATALOG_IMAGES_PLAN.md` | PLAN | current | 7 | Authorized image plan (CR-019) |
| `docs/architecture/product-seo-descriptions-plan.md` | PLAN | current | 7 | |
| `docs/API_CONTRACT.md` | CONTRACT | current | 5 | |
| `docs/ARCHITECTURE.md` | REFERENCE | current | 8 | |
| `project-management/EXECUTIVE_SUMMARY.md` | PLAN | current | 7 | Schedule only |
| `docs/taxonomy/remove_omumi_padding_dry_run_REPORT.md` | EVIDENCE | current | 9 | |
| `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` | EVIDENCE | current | 9 | Partially stale vs 2026-07-30 board closes |
| `docs/GO_LIVE_EXECUTION_PLAN.md` | HISTORICAL | stale | 10 | Forbidden context for agents |
| `docs/FRONTEND_IMPLEMENTATION_GUIDE.md` | QUARANTINED | quarantined | 999 | Forbidden context |
| User `MASTER_*.md` / `DOCUMENT_GOVERNANCE_MODEL.md` | — | — | — | **ABSENT** (M26) |

### 2.2 Mapping user classes A–G → AODS (do not invent a second ladder)

| User class | Meaning in this audit | Maps to AODS class(es) | What agents should trust |
|------------|----------------------|------------------------|---------------------------|
| **A** Master authority | Binding “what is correct” | `CANON` (+ human Rank 0) | Canon Lock rows + ADRs/RFCs/IA/ingest policy |
| **B** Strategic | Vision / sequencing intent | `CANON` bible (orientation) + `PLAN` (when) + `PROPOSED` strategy | Bible for direction; PMO for schedule; Phases 1–3 **not** merge criteria |
| **C** Architectural | Structures / contracts of design | `CANON` ADR/RFC/IA + `PROPOSED` KP phases | Accepted architecture only |
| **D** Implementation | How code/API/schema behave | Plane C code + `CONTRACT` OpenAPI + Developer Standards (`CANON`) | Code for as-built; OpenAPI for interface; standards for PR shape |
| **E** Operational | How to run pipelines/ops | `POLICY` | Ingestion policy, KNOWLEDGE-FLOW, OPERATIONS, SEED_IMPORT (note stale) |
| **F** Reference | Orientation | `REFERENCE` | Correct when contradicted by A–E |
| **G** Obsolete / archive | Do not instruct | `HISTORICAL` + `QUARANTINED` | Never as requirements |

**Finding (inferred):** User-requested `DOCUMENT_GOVERNANCE_MODEL.md` would be a **duplicate of** `AUTHORITY-MODEL.md` + `CANON-LOCK.md`. Creating it as Level-0 without HC-14 is a governance defect.

---

## 3. Claim verification

| ID | Claim | Source | Check | Verdict |
|----|-------|--------|-------|---------|
| C01 | Active products **5901** (EPIC 0 freeze) | Bible control table; IA baseline; ingestion policy | No DB/`SELECT` run (ADR-012) | **UNVERIFIABLE** in this node — treat as **frozen claim**, not measured 2026-07-30 census |
| C02 | Catalog scale ~5901 in REPOSITORY-AUDIT | `REPOSITORY-AUDIT.md` §2.3 | Same | **UNVERIFIABLE** live; **CONFIRMED** as repeated documentation claim |
| C03 | OpenAPI ~81 paths | `REPOSITORY-AUDIT.md` §2.1 | M16 = **82** | **CONTRADICTED** (stale audit number; delta +1) |
| C04 | Knowledge platform Phases “awaiting approval” | Phase headers 2026-07-22 | Registry PROPOSED; `OI-KF-04` | **CONFIRMED** — still not Board-Accepted for I0 |
| C05 | Phase 1: PDP `/product/{id}` only; no brand entity routes | Phase1 `:73-76` | M24 routes exist; ADR-010 Accepted | **CONTRADICTED** as as-built (doc stale relative to EPIC-1 delivery) |
| C06 | No knowledge API | Phase1 verdict | M17 knowledge paths `[]` | **CONFIRMED** |
| C07 | No KG / knowledge tables | Phase1; Canon §3 packs absent | M28 none; models lack knowledge graph entities | **CONFIRMED** for overlay tables |
| C08 | Article↔product soft links only | `content.py` `related_product_ids` JSONB | Read model `:43` | **CONFIRMED** — not a queryable graph |
| C09 | Versioned pipeline is SoT for product transforms | `data-ingestion-policy.md` §2 | Policy text; companion `DOCUMENT_GOVERNANCE.md` ABSENT (M27) | **CONFIRMED** as binding policy intent; **gap** in cited companions |
| C10 | KB-001 eligible / ~10% | EXECUTIVE_SUMMARY; KNOWLEDGE_BASE_PROGRESS; tasks.json | M25 todo 10; progress notes need SPEC before IMPL | **CONFIRMED** as PLAN status |
| C11 | CAT-002 open enrichment | tasks.json | M25 in_progress 75 | **CONFIRMED** as PLAN |
| C12 | Content articles 24 / hubs 15 | Prior AUD-CONTENT + remeasure | M23 | **CONFIRMED** for JSON artifact |
| C13 | `all_products.csv` ≈ full catalog | filename implication | M19 = 1251 Dasqua+INSIZE only | **CONTRADICTED** if read as full SoT — subset artifact |
| C14 | Image import paused (Phase docs) vs CATALOG_IMAGES_PLAN | Phase3 vs CR-019 | Registry PLAN current for images plan | **CONFLICT already decided** — CR-019 Option A; Phase pause superseded-for-now |
| C15 | AODS pack “PROPOSED” example in AUTHORITY-MODEL §2 table | AUTHORITY-MODEL `:40` example cell | Registry marks AODS docs POLICY accepted | **TENSION** — example cell stale vs Board acceptance 2026-07-30; classes still valid |

---

## 4. Enforcement table

| Rule / expectation | Documented where | Enforced by | Finding |
|--------------------|------------------|-------------|---------|
| Document class / forbidden context | AUTHORITY-MODEL + registry | `aods_validate.py --gate registry` (+ prompts) | **Documented + gated** |
| Local-only routine ingestion | ADR-012 + data-ingestion-policy | `--gate ingestion-boundary` | **Documented + gated** (full matrix not re-run beyond VERIFY links/registry) |
| Provenance for every DB fact | KNOWLEDGE-FLOW | Partial; `OI-KF-01` no provenance store | **Documented; weakly enforced** |
| Agent claims not persisted | KNOWLEDGE-FLOW §2 | Process / HC; no DB trigger observed | **Documented; human-enforced** |
| Canon-only merge criteria | CANON-LOCK | PR review + citation rules; CI aods job | **Documented; partially gated** |
| Knowledge graph links queryable | KB-001 AC | None (no tables/API) | **Documented AC; unimplemented** |
| Industrial taxonomy master | Expected by industrial KB mission | Only seed script + one dry-run EVIDENCE | **Missing master; unenforced** |
| Product entity knowledge layers | Bible / Phase2 aspirational | JSONB bag + CMS soft links | **Partial technical/commercial only** |
| Live product census freshness | Bible 5901 | No continuous measured baseline artifact in-repo | **Claim frozen; unenforced refresh** |
| Content JSON vs CMS SoR | G-07 (prior audit) | Nothing in this scope | **Undocumented precedence** (still open) |

---

## 5. Gap list

| ID | Expected foundation artifact | Observed | Severity |
|----|------------------------------|----------|----------|
| G01 | Single binding document governance (user `DOCUMENT_GOVERNANCE_MODEL`) | **Exists as** `AUTHORITY-MODEL` + `CANON-LOCK` + registry — **not** as user filename | Low if mapped; **High** if duplicated |
| G02 | Master Product Entity Model (conceptual, DB-independent) | **ABSENT** as dedicated Accepted/Proposed master; fields only in ORM + default JSONB | **Critical** for KB |
| G03 | Master Industrial Taxonomy SoT | **ABSENT**; category tree via `seed_categories.py`; one dry-run report | **Critical** |
| G04 | Master Knowledge Graph model (nodes/edges) | Phase2 **PROPOSED** only; Canon §3 says Domain/KG/PIM packs **not in repo** | **Critical** |
| G05 | Master Product Import Strategy (end-to-end) | Split across ingest policy + SEED_IMPORT (stale) + KNOWLEDGE-FLOW + 30 scripts | **High** — need one Proposed master that **defers** to ADR-012 |
| G06 | Master SEO Entity Strategy | Partial: ADR-010 + IA + SEO description plan; no unified entity SEO master | Medium |
| G07 | Cited packs in ingest policy / bible | **ABSENT** (M27) | High (broken citations / inventability trap) |
| G08 | Machine provenance store | `OI-KF-01` open | High |
| G09 | Verified current product census | 5901 claim UNVERIFIABLE here | High for migration baseline choice |
| G10 | `/api/v1/knowledge/*` | None | Expected until Board accepts I0 |
| G11 | Queryable article↔product↔category graph | JSONB ids only | Blocks KB-001 DoD |
| G12 | User-named MASTER files | All ABSENT by design of Option A | N/A — recommendations in §8–§12 |

---

## 6. Unknowns

| ID | Unknown | What would determine it |
|----|---------|-------------------------|
| U1 | Current **production** active product count | Category C / HC-09 measured export — not estimated here |
| U2 | Current **local/staging** DB product/brand/category counts | `SELECT count(*)` on authorised local DB |
| U3 | Website public product count (indexable) | Crawl or Storefront sitemap analysis against live host (ops), not inferred from CSV |
| U4 | Spec completeness % today (bible cites ~70% empty technical_specs) | Re-run baseline quality report against measured DB; EPIC0 summary file ABSENT |
| U5 | Whether Phases 1–3 are intended for Board Acceptance or lapsed | Architecture Board minute (`OI-KF-04`) — HC-02 |
| U6 | Licensing of supplier catalogue images | Legal / `OI-KF-02` |
| U7 | Whether `all_products.csv` is still used as import input or archival | Script invocation evidence + owner |
| U8 | Live CMS article set == JSON 24 | API/DB compare (prior G-07) |
| U9 | Full brand list beyond Dasqua/INSIZE in production | DB brand table dump |
| U10 | Exact residual open CRs after 2026-07-30 closes | Board close lines vs skill memory; conflict register living — do not invent OPEN set without dated read of full register decisions |

---

## 7. Phase 2 recommendation — Document Authority System (do **not** create parallel file)

**Recommendation:** Treat the following as the **Document Governance Model** (conceptual). A future GOV/SPEC node may add a short **pointer** doc if humans want the user filename — but it must **cite and defer** to existing Accepted sources, not redefine Rank 0–10.

### Recommended hierarchy (aligned to AODS, not replacing it)

| User LEVEL | Role | Existing SoT | May authorise code? |
|------------|------|--------------|---------------------|
| **0** | Constitution / process law | Human operator Rank 0; `AODS-CHARTER`; Board minutes | Process only |
| **1** | Vision / platform strategy | `karzar-knowledge-platform-master-architecture.md` (CANON orientation) + EXECUTIVE_SUMMARY (PLAN when) | Orientation / schedule |
| **2** | IA / data / product entity / taxonomy / ontology | IA pack (CANON); **missing** Product Entity + Taxonomy + KG masters (to be PROPOSED→Accepted) | After Board Accept |
| **3** | Technical implementation | ADR/RFC Accepted; OpenAPI CONTRACT; Alembic; code | Yes within Canon |
| **4** | Operational procedures | data-ingestion-policy, KNOWLEDGE-FLOW, OPERATIONS, SEED_IMPORT | Ops |
| **5** | Drafts / analysis | PROPOSED phases, audits EVIDENCE, agent prose | **Never** alone |

### Conflict resolution (binding today)

Per `AUTHORITY-MODEL.md` §3: lowest rank number that speaks to the question wins; code is Plane C (as-built vs ought); silent picking forbidden → CONFLICT-REGISTER.

### How future documents are created / approved

1. Draft as `PROPOSED` (or EVIDENCE if audit).  
2. Register in `document-registry.yaml` (GOV node).  
3. Architecture Board minute + Canon Lock row for `CANON` (HC-02 / HC-14).  
4. Agents cite `path:line` on `origin/main` only.

**Agents must trust:** Canon Lock Accepted/Binding → ADR/RFC/IA/ingest → OpenAPI/code for as-built → PMO for schedule → audits as evidence only. **Never** quarantined docs.

---

## 8. Phase 3 — Master document map (recommended; files **not** created this node)

| Recommended master (user name) | Purpose | Scope | Authority target | Owner | Inputs | Outputs | Related systems | Existing stand-in |
|--------------------------------|---------|-------|------------------|-------|--------|---------|-----------------|-------------------|
| MASTER_PROJECT_CONSTITUTION | What may bind work | Process + merge criteria | CANON index | Board | Board minutes | Canon Lock rows | AODS, PMO | **`CANON-LOCK.md` + `AODS-CHARTER.md`** — do not fork |
| MASTER_KNOWLEDGE_ARCHITECTURE | Platform shape | KG overlay, modules, non-goals | CANON orientation / future Domain pack | Platform Architect | Bible + Phase2 | I-slice specs | FastAPI, CMS, search | **Bible CANON** + Phase2 PROPOSED |
| MASTER_INFORMATION_ARCHITECTURE | Routes, page types, hubs | Public URL + indexation | CANON | FE+SEO Architect | IA pack, ADR-010 | Route contracts | Storefront | **IA pack** |
| MASTER_PRODUCT_ENTITY_MODEL | Product as knowledge entity | Layers §9 | PROPOSED→CANON | Product Data Architect | ORM, OpenAPI, industrial practice | Schema RFC + enrichment contracts | PIM-like overlay, PDP | **MISSING — highest priority new Proposed** |
| MASTER_INDUSTRIAL_TAXONOMY | Category/tool class SoT | Depth, naming, templates | PROPOSED→CANON | Taxonomy owner | `seed_categories`, dry-runs | Taxonomy RFC + migration jobs | Categories API | **MISSING** (script ≠ master) |
| MASTER_KNOWLEDGE_GRAPH_MODEL | Nodes/edges/query | Articles, products, brands, standards, applications | PROPOSED→CANON | Knowledge Engineer | Phase2, KB-001 AC | Alembic I-slice + API | CMS, SEO internal links | **MISSING in-repo pack** (Canon §3) |
| MASTER_PRODUCT_IMPORT_STRATEGY | Pipeline SoT | Raw→production | POLICY/CANON ingest + Proposed playbook | Backend + Knowledge | ADR-012, KNOWLEDGE-FLOW, SEED_IMPORT | Pipeline runbooks | `scripts/`, `data/imports/` | **Partial — needs unifying Proposed playbook** |
| MASTER_SEO_ENTITY_STRATEGY | Entity SEO | URL, JSON-LD, linking, hubs | CANON SEO + Proposed expansion | SEO | ADR-010, IA, SEO plans | Entity SEO checklist | Storefront, sitemap | **Partial** |
| DOCUMENT_GOVERNANCE_MODEL | Authority UX for humans | Classes, conflicts | POLICY pointer | Doc Architect | AUTHORITY-MODEL | Optional thin alias | Registry validator | **Use AUTHORITY-MODEL; optional alias later** |
| KNOWLEDGE_BASE_READINESS_REPORT | Maturity gate | Prerequisites | EVIDENCE | Auditor | This audit | Go/No-Go | PMO | **This report §11** |
| NEXT_90_DAYS_KNOWLEDGE_FOUNDATION_PLAN | Sequencing | 12 weeks | PLAN | PMO | This audit + EXEC summary | Sprint tasks | tasks.json | **This report §12** |

---

## 9. Phase 4 — Product Entity Architecture (conceptual; database-independent)

**Observed as-built core** (`app/db/models/product.py`): identity (sku, slug, name), classification (category_id, brand_id), commercial (base_price, original_price, is_available, stock_quantity deprecated for UX, tax, weight), technical bag (`specifications` JSONB default with technical_specs/features/dimensions/optional_accessories), SEO columns (meta_*), media (ProductImage, pdf_catalog_url), soft delete / is_active.

**Missing as first-class knowledge** (inferred from absence): educational narratives, selection guides, common mistakes, standards entities, applications, comparisons, FAQ entity, related educational content edges, manufacturer vs brand distinction, model-number identity separate from SKU, product family, tool class ontology beyond category tree.

### Recommended conceptual entity: `ProductKnowledgeEntity`

#### Identity Layer
- Product display name (locale fa-IR primary)
- Manufacturer (org)
- Brand (market face; may equal manufacturer)
- Model number (manufacturer code)
- SKU (commerce unique among active)
- Slug (SEO identity; ADR-010)
- Product family / series
- Product type / tool class

#### Classification Layer
- Category path (≤3 depth — seed rule)
- Industrial taxonomy codes (external + internal)
- Spec template key (exists: `Category.spec_template_key`)
- Intended industry / use-class tags (knowledge, not only nav)

#### Technical Layer
- Structured properties from governed dictionary (not free JSON forever)
- Dimensions, accuracy, range, resolution, material, standards, compatibility, accessories
- Evidence links (PDF page, manufacturer URL) — provenance required (KNOWLEDGE-FLOW)

#### Knowledge Layer
- What it is / how it works / where used / how to select / common mistakes
- Comparisons (entity edges, not HTML blobs only)
- FAQ
- Related educational content (articles, hubs)

#### Commercial Layer
- Price, availability (`is_available` binary on site), supplier refs
- Hesabfa owns numeric warehouse stock (Canon/domain invariant)
- **Enrichment must not write** price/stock (ADR-012 / skill invariants)

#### SEO Layer
- Canonical URL `/product/{slug}`
- Meta title/description
- JSON-LD Product/Offer/Breadcrumb `@id` agreement
- Internal links to brand/category/article hubs
- Entity relationships for topical authority

**Rule:** Commerce tables remain SoR for sellable state; knowledge overlay **references** product ids — Phase1/2 recommendation (PROPOSED) aligns; do not replace `products` table.

---

## 10. Phase 5 — Product import strategy (recommendation)

### 10.1 Current product situation (measured vs claimed)

| Source | Count | Authority |
|--------|------:|-----------|
| Documentation freeze “active products” | **5901** | Claim (UNVERIFIABLE here) |
| `data/imports/all_products.csv` | **1251** | K-DERIVED artifact (Dasqua+INSIZE only) |
| Dasqua site export / summary | **~727** exported | Pipeline evidence; apply=false in summary |
| `products_not_imported.csv` | **187** | Deficiency ledger |
| Live website / production DB | **?** | Unknowns U1–U3 |
| OpenAPI / ORM | Schema only | Not a census |

### 10.2 Data quality problems (observed / inferred)

- **Baseline ambiguity:** docs say 5901; import CSVs are brand subsets → risk of wrong “source of truth” choice.
- **Duplicate SKU** in `all_products.csv` (1) → entity resolution required.
- **Dasqua match conflicts** (9) / large unmatched sets in summary.json.
- **Empty technical_specs** historically claimed ~70% (bible) — **UNVERIFIABLE** now (U4); EPIC0 summary ABSENT.
- **Dual content stores** (JSON articles vs CMS) — precedence undocumented.
- **SEED_IMPORT** registry status **stale** while still POLICY.
- **30** import/enrich scripts → operational sprawl without single playbook.

### 10.3 Answers (strategic)

1. **SoT for product transforms:** Versioned Data Pipeline + Git (ingestion policy §2) — **not** ad-hoc Admin, **not** production API for routine work (ADR-012). Production DB is operational store after deploy, not authoring origin.
2. **Baseline for migration:** Prefer **measured local baseline dump of production catalog** (Category C, HC-09) as **temporary census**, then converge to pipeline — **do not** treat `all_products.csv` as full catalog. Website scrape is last resort and competitor-class constraints apply for third-party sites.
3. **Migration:** Inventory → normalize SKUs → entity resolution (SKU/brand/model) → Category A local dry-run → human review → controlled apply; never silent prod writes.
4. **Normalization:** Unicode/Persian digits, brand aliases, category depth ≤3, slug rules per RFC-004, specs via property dictionary (future) not free-text invent.
5. **Brands:** `brands` table SoR for site brand hubs (RFC-005); manufacturer org may be future node; do not invent hub thin-policy beyond Accepted contract.
6. **Categories:** Taxonomy master (G03) must govern `seed_categories` / remediation scripts; avoid second taxonomy (KB-001 AC).
7. **Missing specs:** Only `K-EXT-PRIMARY` (or corroborated secondary) numerics; AI = proposal (`K-AGENT-CLAIM`) until validator/HC.
8. **AI enrichment:** Allowed to propose descriptions/mappings; forbidden to invent specs/prices/stock; competitor text/images never (KNOWLEDGE-FLOW matrix).
9. **Human approval:** HC-09 for Category B/C; dry-run reports mandatory; Board for schema/Canon.

### 10.4 Pipeline (align to KNOWLEDGE-FLOW; user stages)

```text
Raw Product Data (PDF/CSV/API export)
    ↓  Validation (schema, required keys, environment Category A/B/C)
    ↓  Normalization (SKU, brand, units, slugs)
    ↓  Entity Resolution (match existing product ids; conflict queue)
    ↓  Technical Enrichment (specs with provenance; no commerce keys)
    ↓  Knowledge Enrichment (educational fields as Proposed → review)
    ↓  SEO Enrichment (meta, links; ADR-010 compliant)
    ↓  Human Review (HC)
    ↓  Production Database (controlled deploy path — not laptop→prod API)
```

**Playbook file:** recommend future Proposed `docs/architecture/MASTER_PRODUCT_IMPORT_STRATEGY.md` (or under `docs/architecture/` naming per NAMING-CONVENTIONS) that **normatively defers** to ADR-012 + data-ingestion-policy + KNOWLEDGE-FLOW.

---

## 11. Phase 6 — Knowledge Base readiness

### Maturity (inferred scale 0–5)

| Dimension | Level | Evidence |
|-----------|------:|----------|
| Document authority | **4** | AODS + Canon + registry gates |
| Public IA / SEO URL | **3–4** | ADR-010 Accepted; routes present; hub content exists |
| Commerce catalog | **4** | Mature ORM/commerce |
| Product-as-knowledge model | **1** | JSONB + soft links only |
| Taxonomy governance | **1** | Script + one report |
| KG overlay | **0** | No tables/API |
| Ingestion discipline | **3** | Policy+gates; provenance store missing; script sprawl |
| Content graph (KB-001) | **1** | 24 articles linked by ids; not queryable graph |
| **Overall KB readiness** | **~1.5 / 5** | **Not ready** for Knowledge Base implementation slices that assume Domain/KG/PIM packs |

### Critical blockers

1. **B-KB-01** Missing Accepted (or even drafted-in-repo) Product Entity Model + KG model + Taxonomy masters (Canon §3 explicit absence).  
2. **B-KB-02** Unverified product census vs conflicting CSV subsets.  
3. **B-KB-03** `OI-KF-04` — Phases 1–3 approval state unresolved.  
4. **B-KB-04** Provenance store absent (`OI-KF-01`).  
5. **B-KB-05** KB-001 SPEC missing (“Phase-1 graph slice still needs SPEC before IMPL” — KNOWLEDGE_BASE_PROGRESS).  
6. **B-KB-06** Broken/absent citations to DOCUMENT_GOVERNANCE / EPIC0 / ops baseline packs (inventability hazard).

### Recommended order (before KB implementation)

1. Authority hygiene (map masters → existing Canon; optional pointer doc) — GOV  
2. Measure census (local baseline) — AUD/ops HC-09  
3. SPEC Product Entity Model + Taxonomy + KG edges — SPEC HC-01  
4. Board Accept slices onto Canon Lock — HC-02  
5. Import playbook Proposed — SPEC/DOC  
6. KB-001 SPEC then IMPL (graph seed without second taxonomy)  
7. Only then Phase3 I0-style knowledge modules

---

## 12. Phase 7 — Next 90 days (PLAN recommendation; not PMO write)

Assumes Option A complete; human may copy into PMO via separate GOV-pmo-sync.

| Week | Focus | Tasks | Exit criteria |
|-----:|-------|-------|---------------|
| 1 | Document cleanup (authority) | Publish this audit; Board triage G01/G07; decide `OI-KF-04`; **no** parallel constitution | Minute on Phases + citation repair list |
| 2 | Authority establishment | GOV: registry notes cleanup; optional thin governance pointer deferring to AUTHORITY-MODEL | Agents cite one ladder only |
| 3–4 | Master creation (Proposed) | SPEC: Product Entity Model; Taxonomy SoT outline; KG edge list for articles↔products↔categories↔brands | HC-01 drafts frozen |
| 5 | Product entity modeling | Map ORM/OpenAPI → entity layers; gap matrix | Traceability table path:line |
| 6 | Taxonomy | Extract tree from seed/DB; define naming + template keys; no DAG | Taxonomy Proposed v0 |
| 7 | Import pipeline design | Unifyة playbook aligning user pipeline to KNOWLEDGE-FLOW; inventory 30 scripts | Playbook Proposed |
| 8 | First complete product modeling | Pick **one** SKU family (e.g. one INSIZE series); fill all layers with provenance; human review | Gold exemplar Accepted as template |
| 9–10 | KB-001 SPEC + thin IMPL prep | Spec queryable links; **no** second taxonomy; tests from SPEC | HC-01 on KB-001 spec |
| 11–12 | KB implementation gate | If blockers B-KB-01…05 cleared: implement graph seed slice only; else HALT and extend foundation | Queryable links DoD **or** explicit defer |

**Priority order (user list) — confirmed:** cleanup → authority → masters → entity model → taxonomy → import design → exemplar product → KB impl.

**Non-goals in 90 days:** full Mitutoyo-scale ontology; head-term SEO vanity; production enrich-by-default; replacing commerce schema.

---

## 13. Complete document authority map (condensed inventory)

### A / CANON (trust for correctness)

CANON-LOCK; Architecture bible; ADR-010/012; RFC-004/005; IA pack (incl. brand-hub contract); Developer Standards; data-ingestion-policy; git-development-workflow.

### B / Strategic

Bible (orientation); EXECUTIVE_SUMMARY / PMO (when); KNOWLEDGE_PLATFORM phases (**PROPOSED only**).

### C / Architectural

Accepted ADR/RFC/IA; Phase2 target architecture (**PROPOSED**).

### D / Implementation

`app/**`, `alembic/**`, `openapi/v1.json`, API_CONTRACT/CHANGELOG, frontend routes, Developer Standards.

### E / Operational

KNOWLEDGE-FLOW; OPERATIONS; HESABFA; SEED_IMPORT (stale); SCRIPTS; CATALOG_IMAGES_PLAN; ingest scripts under policy.

### F / Reference

README, ARCHITECTURE.md, FRONTEND_INTEGRATION, app READMEs.

### G / Obsolete / quarantine

HISTORICAL: GO_LIVE_EXECUTION_PLAN, BACKEND_CHANGES, FRONTEND_HANDOVER, audits v1 (forbidden bulk), etc.  
QUARANTINED: `frontend/AI_CONTEXT.md`, `frontend/BACKEND_NON_COMPLIANCE.md`, `docs/FRONTEND_IMPLEMENTATION_GUIDE.md`.  
Stale-as-built claims inside otherwise useful PROPOSED Phase1 URL section (C05).

---

## 14. Exact recommended next steps (human)

1. **Accept this report as EVIDENCE** (no code).  
2. **HC-02 / Board:** resolve `OI-KF-04` (Phases 1–3 Accept vs lapse vs supersede).  
3. **HC-09 / ops:** measure real product census on authorised DB; record baseline artifact.  
4. **Open SPEC nodes** (separate allowlists): Product Entity Model, Industrial Taxonomy, KG edge model, Import playbook — all `PROPOSED`, registered, Canon-deferred.  
5. **Do not** create a competing `DOCUMENT_GOVERNANCE_MODEL` with new Rank 0–5 that ignores AODS.  
6. **GOV-pmo-sync:** optionally add PMO task “Knowledge foundation programme” to clear CR-008 NONE, and link KB-001 behind SPEC.  
7. **Only after** SPEC+HC-01: implement KB-001 graph seed.

---

## 15. Proposed follow-up nodes

| Finding | Node type | HC |
|---------|-----------|-----|
| G01/G07 citation & governance pointer | GOV / DOC | HC-02 if Canon touch |
| G02 Product Entity Model | SPEC | HC-01 |
| G03 Taxonomy master | SPEC | HC-01 |
| G04 KG model | SPEC | HC-01 |
| G05 Import playbook | SPEC / DOC | HC-01 |
| U1–U3 census | AUD / ops | HC-09 |
| OI-KF-04 phase approval | GOV Board | HC-02 |
| KB-001 implementation | SPEC then IMPL/TEST | HC-01 then HC-05–07 |
| Registry stale notes (CR-001 comment in YAML header) | GOV | — |
| Append conflict if Board wants formal CR for Phase1 URL staleness | GOV append-only | HC-03 |

---

## 16. Relation to AUD-CONTENT-READINESS-001

Prior node measured content JSON DoD and Definition A checkpoint readiness. This node **does not supersede** it; it widens scope to **knowledge architecture foundation**. Where counts overlap (24 articles, 15 hubs), remeasured **CONFIRMED** (M23). Brand routes: prior audit reported 0 brand app routes; this tree now has `brands/[slug]/page.tsx` (M24) — **do not merge the two audits silently**; treat as time-separated measurements.
