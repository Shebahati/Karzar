---
id: SPEC-product-import-enrichment-playbook
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/data-ingestion-policy.md
  - docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
  - docs/architecture/specs/SPEC-knowledge-graph-model.md
owner: Data Engineer + PIM Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
---

# SPEC — Product Import & Enrichment Playbook

**Status:** Proposed (not binding merge criteria until Architecture Board Accepts)  
**Document type:** Data pipeline / PIM operations specification  
**Non-goals:** Implementing importer code in this PR · authorizing production writes · weakening ADR-012 · inventing technical specs via AI

---

## 1. Purpose

Define the complete lifecycle of product data from raw inputs to production, so KarzarTools can grow an industrial knowledge platform with:

- Reproducible, auditable imports (Plane A SoT)
- Entity identity before enrichment
- Taxonomy + graph population
- AI assistance within strict limits
- Human-controlled accuracy for industrial claims

This playbook **extends** (does not replace) the binding ingestion policy.

---

## 2. Governing authority

| Source | Statement | Cite |
|--------|-----------|------|
| Ingestion policy | Versioned pipeline; Source/Destination/Owner/Validation/Audit/Rollback; Category A/B/C | `docs/architecture/data-ingestion-policy.md:21-58`, `:132-143` |
| ADR-012 | Category A local-only; fail closed on production for routine enrichment | `docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md:63-70` |
| Master Architecture P1–P2, P4–P5 | Measure before mutate; local enrichment; Evidence before generation; FA/EN before dual-write | Bible principles |
| AODS artifacts | SOURCE-DEPOSIT, KNOWLEDGE-EXTRACT, MAPPING-TABLE, DRY-RUN-REPORT, APPLY-REPORT | `aods/40-artifacts/ARTIFACT-ARCHITECTURE.md:74-79` |
| As-built importers | e.g. `scripts/mitutoyo_import.py`, `azarsanat_import.py`, enrichers, `data/imports/` | scripts + data tree |
| Boundary helper | `scripts/ingestion_boundary.py` fail-closed | ingestion policy remediations |

---

## 3. Pipeline overview

```text
RAW DATA
    ↓
VALIDATION
    ↓
NORMALIZATION
    ↓
ENTITY RESOLUTION
    ↓
CLASSIFICATION
    ↓
TECHNICAL ENRICHMENT
    ↓
KNOWLEDGE ENRICHMENT
    ↓
SEO ENRICHMENT
    ↓
HUMAN REVIEW
    ↓
PRODUCTION
```

Every stage **MUST** be skippable only when explicitly N/A (e.g. SEO-only touch-up still runs Validation + Review tier rules). Stages **MUST** emit machine-readable stage results for audit.

**Mandatory job header** (ingestion policy §5) still applies to the overall job: Source, Destination, Owner, Validation, Audit Trail, Rollback.

---

## 4. Stage specifications

### 4.1 RAW DATA

**Inputs (examples):**

| Source type | Examples in repo / ops | Trust default |
|-------------|------------------------|---------------|
| Supplier CSV | `data/imports/*.csv` | Medium — commercial fields may be OK; specs need verify |
| Manufacturer catalogs / leaflets | `data/imports/dasqua/`, Mitutoyo leaflets | High for OEM identity/specs **when checksummed** |
| PDFs | Price lists, catalogs | High for identity if OEM; Medium for OCR’d numbers |
| Existing database | Local baseline / production snapshot Category C | High for “what we sell”; not origin of knowledge long-term |
| Crawl JSONL | Mitutoyo/Shopmill crawls | Medium — treat as extract needing mapping |
| APIs | Admin API reads | Mirror of DB trust |
| AI drafts | Generated prose | **Untrusted** for Facts |

**Trusted vs not trusted:**

| Claim class | Trusted sources | Not trusted |
|-------------|-----------------|-------------|
| SKU existence / price intent | Controlled commercial feeds + human | Random web scrape without deposit |
| Model / MPN | OEM catalog PDF/CSV with SOURCE-DEPOSIT | AI inference |
| Technical specifications | OEM docs + measured Evidence | AI invention; competitor sites without license |
| Standards / certifications | OEM claim **plus** document Evidence for publish | AI; hearsay |
| Marketing prose | Human editorial; AI draft under review | Auto-publish AI |
| Availability / warehouse | Hesabfa / commerce systems | Knowledge pipelines |

**SOURCE-DEPOSIT required** for new external corpora: path under `data/imports/<vendor>/<collection>/`, checksum, vendor URL, retrieval date (AODS).

---

### 4.2 VALIDATION

Fail-closed checks before mutation:

| Check | Rule |
|-------|------|
| Schema / columns | Required columns present for declared source map |
| Encoding | UTF-8; Persian text not mojibake |
| SKU format | Non-empty; length ≤ as-built limit (50); trim |
| Duplicate rows in batch | Detect; abort or quarantine |
| Price type | Numeric if present; currency assumptions documented |
| Forbidden destination | Category A must not resolve production host without fail-closed env (ADR-012) |
| Allowlist | Brand/SKU scope when declared |
| Checksum | Input artifact matches deposit README |

**Outputs:** `valid_rows`, `quarantine_rows` with reasons. Quarantine **MUST NOT** silently drop without report.

---

### 4.3 NORMALIZATION

| Field | Normalization rules |
|-------|---------------------|
| **SKU** | Trim; preserve manufacturer separators unless map says otherwise; uppercase policy **per brand** (do not globally force case) |
| **Model numbers** | Trim; unify Unicode dashes; collapse internal whitespace; keep significant suffixes (ASX, IP67) |
| **Brand names** | Map aliases → canonical Brand (`مییتوتویو`/`Mitutoyo` → steward table); never create Brand from typo without review |
| **Manufacturer names** | Separate map from Brand (Entity SPEC); legal suffix normalization (`Co.`, `Corporation`) |
| **Persian / English names** | Store both when available; FA display name MUST NOT be machine-translated without review for publish |
| **Units** | Parse number + unit; convert to canonical unit per Definition dimension (mm vs in explicit); never drop unit |
| **Measurements** | Ranges as structured min/max; `±` tolerances as qualifier + magnitude |
| **Booleans** | Map yes/no/دارای/ندارد via dictionary |
| **Duplicate detection (intra-batch)** | Normalized Manufacturer+Model or SKU collision → quarantine |

Normalization **MUST** be deterministic and Git-versioned (`MAPPING-TABLE`).

---

### 4.4 ENTITY RESOLUTION

Decide: **new Product Knowledge Entity / Commerce Product** vs **match existing**.

#### Match ladder (highest confidence first)

| Rank | Rule | Action if match |
|------|------|-----------------|
| 1 | Active SKU exact match | Update path (enrich); do not create duplicate |
| 2 | Manufacturer ID + normalized MPN/Model exact | Link/enrich; SKU conflict → human |
| 3 | Brand ID + normalized Model exact **and** category family compatible | Candidate match → Medium review if SKU differs |
| 4 | Fuzzy similarity (name/trgm) above threshold | **Never auto-merge**; queue review |
| 5 | No match | Create new (if job allows creates) |

#### Create vs update policy

| Job type | May create products? | May update specs? | May update prices? |
|----------|----------------------|-------------------|--------------------|
| Identity import | Yes (scoped) | Only mapped OEM fields | Only if Source declared commercial |
| Spec enrich | No (unless allowlist miss = quarantine) | Yes mapped Definitions | **No** by default |
| Price reconcile | No | No | Yes scoped |
| Knowledge-only | No commerce create | Facts/modules/edges only | No |

**SKU conflict:** existing SKU with different Manufacturer+Model → **High** review halt (possible data corruption).

---

### 4.5 CLASSIFICATION

Assign:

1. Commerce Category (required for as-built `category_id` NOT NULL)
2. Primary Domain + Tool Family + Product Type (knowledge)
3. Application / Industry candidates (optional)

**Methods allowed:**

| Method | Auto-apply? |
|--------|-------------|
| Explicit source category map (Git rules) | Yes if map hit |
| Steward allowlist rules (e.g. Mitutoyo `CATEGORY_RULES` pattern) | Yes if unique hit |
| Spec Template inference from attributes | Suggest only |
| AI classification | Suggest → Medium review unless confidence ≥ threshold **and** within closed label set |

**MUST NOT** invent new Taxonomy nodes at runtime. Unknown class → quarantine or `unclassified` bucket for stewardship.

As-built illustration: `scripts/mitutoyo_import.py` keyword → `category_id` rules — pattern to formalize as versioned Classification Maps, not one-off script constants forever.

---

### 4.6 TECHNICAL ENRICHMENT

Map source attributes → Specification Definitions → Fact values.

| Allowed | Forbidden |
|---------|-----------|
| Copy OEM numeric specs with unit parse | Invent accuracy/resolution/range |
| Map FA/EN keys via dictionary to one Definition | Dual-write Facts to production before Board gate |
| Leave Fact empty when source missing | Fill defaults from `get_default_specifications()` as if measured |
| Mark Fact `asserted` + provenance | Publish compliance Facts without Evidence |

JSONB may still be written as operational store (Bible P6) **only** with mapped keys — prefer dictionary keys even inside JSONB to reduce chaos.

---

### 4.7 KNOWLEDGE ENRICHMENT

Create/update:

- Content modules (overview drafts, FAQ suggestions, …)
- Graph edges (similar, accessory candidates, article links)
- Document links when PDFs deposited
- Application/Industry suggestions

| AI may | AI must not |
|--------|-------------|
| Classify into **existing** taxonomy labels | Create fake standards/certifications |
| Draft overview / how-to / FAQ prose | Invent technical specification numbers |
| Suggest `PRODUCT_SIMILAR_TO` / accessories from rules | Invent prices or availability |
| Suggest internal links | Claim `PRODUCT_MEETS_STANDARD` as published |
| Flag missing Evidence | Bypass human review for High-risk |

Draft modules get `status=draft` and provenance `ai_draft`.

---

### 4.8 SEO ENRICHMENT

| Field | Rules |
|-------|-------|
| `slug` | Stable; follow existing uniqueness; RFC-004 redirect if change |
| `meta_title` / `meta_description` | Template from Brand + Type + Model; no keyword stuffing; no false claims |
| `short_description` | May use safe template from **published** Facts only (`docs/architecture/product-seo-descriptions-plan.md` spirit) |
| JSON-LD | Align `@id` to canonical URLs (ADR-010) when pages render |
| Hubs | Do not fabricate Brand/Category entities for SEO |

SEO stage **MUST NOT** invent Facts to make descriptions richer.

---

### 4.9 HUMAN REVIEW

#### Risk tiers

| Tier | Examples | Gate |
|------|----------|------|
| **Low** | Re-import identical checksum OEM row; projection-only edges from `category_id`/`brand_id`; slug unchanged meta template | Automatic apply on local Category A after dry-run green |
| **Medium** | New product create; AI classification; AI prose modules; fuzzy entity candidates; non-compliance edge suggestions | Human catalog steward review before apply (or before publish status) |
| **High** | Standards/certifications; accuracy/tolerance Facts; SKU identity conflicts; Manufacturer↔Brand splits; price changes outside commercial feed; Category B production | Domain expert / owner approval + ticket; Category B also needs backup per policy |

#### Approval levels vs publish

| Artifact | Low | Medium | High |
|----------|-----|--------|------|
| Commerce create/update (scoped) | Auto | Review | Expert |
| Fact `asserted` | Auto from OEM map | Review if AI/fuzzy | — |
| Fact `published` | — | Steward | Expert if metrology-critical or compliance |
| Edge `published` compliance | — | — | Expert + Evidence |
| AI prose module `published` | — | Steward (FA) | — |

**Proposed default (UD-08):** customer-facing FA prose from AI never auto-publishes.

---

### 4.10 PRODUCTION

| Environment | Rule |
|-------------|------|
| Local / Category A | Default destination `http://127.0.0.1:8000/api/v1` |
| Staging / controlled | Explicit Destination; still not casual |
| Production Category B | Ticket, backup, fail-closed env vars, APPLY-REPORT |
| Category C | Baseline dump/sync only — not enrichment substitute |

After apply:

1. Retain APPLY-REPORT (counts, errors, git SHA, job id).
2. Emit graph projection job if edges pending.
3. Rollback plan tested for Category B (backup restore or compensating job).

---

## 5. Cross-mapping: one new product journey

When importing a **new** product:

| Step | Spec | Action |
|------|------|--------|
| 1 | Entity | Determine identity (SKU / Manufacturer / Model); create PKE + Commerce Product link |
| 2 | Taxonomy | Assign commerce Category + Domain/Family/Type nodes |
| 3 | Graph | Create `PRODUCT_BRANDED_AS`, `PRODUCT_MANUFACTURED_BY` (if known), `PRODUCT_BELONGS_TO_CATEGORY`, `PRODUCT_CLASSIFIED_AS`, optional `USED_FOR` |
| 4 | Technical | Map OEM specs → Definitions/Facts (`asserted`) |
| 5 | Knowledge | Enqueue module drafts + similar/accessory suggestions |
| 6 | SEO | Slug + meta templates from known identity |
| 7 | Review | Tier by risk; publish Facts/modules when approved |
| 8 | Production | Category A apply → later controlled B if authorized |

---

## 6. AI control plane (summary)

```text
AI ALLOW:
  - classify into closed label sets
  - draft descriptions / FAQs / guides
  - suggest relationships
  - suggest missing-field tasks

AI DENY:
  - invent technical specifications
  - invent standards
  - invent certifications
  - invent prices
  - publish without review (Medium+)
  - write production catalog as Category A
```

---

## 7. Alignment with existing scripts (as-built → playbook)

| Script pattern | Playbook home |
|----------------|---------------|
| Crawl → JSONL → `*_import.py` | RAW → … → PRODUCTION (Category A) |
| `*_enrich*.py` leaflet merges | TECHNICAL (+ optional KNOWLEDGE) |
| `import_price_lists.py` / reconcile | Commercial path; skip knowledge invent |
| `seed_categories.py` | Taxonomy commerce seed (not routine enrich) |
| `publish_seo003_articles.py` | CMS Category B publisher — not product Fact invent |
| Image importers | Media track (D16 / catalog images plan) — out of knowledge Fact scope |

Scripts **SHOULD** evolve to declare stage hooks and reuse `ingestion_boundary.resolve_api_base()`; this SPEC does not rewrite them.

---

## 8. Requirements (testable)

| ID | Requirement | Criterion |
|----|-------------|-----------|
| **IMP-R1** | Full stage sequence documented | §3–§4 |
| **IMP-R2** | Trust model for sources | §4.1 |
| **IMP-R3** | Normalization rules for SKU/model/brand/units | §4.3 |
| **IMP-R4** | Entity resolution ladder | §4.4 |
| **IMP-R5** | AI allow/deny explicit | §4.7 + §6 |
| **IMP-R6** | Human review tiers | §4.9 |
| **IMP-R7** | Does not weaken ADR-012 | §4.10 + cites |
| **IMP-R8** | Cross-maps Entity/Taxonomy/Graph | §5 |
| **IMP-R9** | AODS deposit/extract artifacts referenced | §2 + §4.1 |
| **IMP-R10** | No uncontrolled free-text as Fact architecture | Technical stage uses Definitions |

---

## 9. Open questions

| ID | Question |
|----|----------|
| **IMP-Q1** | Similarity threshold numbers for fuzzy match? |
| **IMP-Q2** | Auto-create Brand when OEM feed introduces new brand string? (recommend: no) |
| **IMP-Q3** | Should Medium review be async job queue UI or PR-based for batch? |
| **UD-08** | Auto-publish policy for AI FA prose |

---

## 10. Success metrics (post-Accept, measurement — not vanity)

| Metric | Intent |
|--------|--------|
| % imports with SOURCE-DEPOSIT checksum | Provenance |
| % SKUs with Manufacturer resolved | Identity |
| % SKUs with primary Product Type | Classification |
| % Facts with provenance | Technical integrity |
| Zero Category A production host successes | Boundary |
| Quarantine rate trending explained | Quality |

EPIC 0-style scorecards remain Evidence; they do not authorize weakening this playbook.
