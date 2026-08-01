---
id: SPEC-data-transformation-architecture
version: 0.1.0
status: Accepted
date: 2026-07-30
governing_parents:
  - docs/architecture/specs/SPEC-product-import-enrichment-playbook.md
  - docs/architecture/data-ingestion-policy.md
  - docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md
  - aods/40-artifacts/ARTIFACT-ARCHITECTURE.md
owner: Data Architect + Data Engineer
task_id: KB-001
---

# SPEC — Data Transformation Architecture

**Status:** **Accepted** (Architecture Board · ۱۴۰۵/۰۵/۱۰ · Mohammad Shebahati · Day-2 minute)  
**Purpose:** Mechanical architecture for supplier → production knowledge+commerce transforms  
**Extends:** Import & Enrichment Playbook (stages) + binding ingestion policy  
**Non-goals:** Script rewrites in this PR · production write authorization · weakening ADR-012

---

## 1. End-to-end pipeline

```text
Supplier data
    ↓
Raw deposit (SOURCE-DEPOSIT)
    ↓
Validation
    ↓
Normalization
    ↓
Entity resolution
    ↓
Classification
    ↓
Property mapping
    ↓
Fact creation
    ↓
Knowledge graph creation
    ↓
Human review
    ↓
Production (Category A local → controlled B)
```

Each arrow is a **versioned transform** with inputs/outputs, idempotency keys, and audit records.

---

## 2. Stage I/O contracts

| Stage | Input | Output | Fail mode |
|-------|-------|--------|-----------|
| Raw deposit | Vendor files/URLs | `data/imports/<vendor>/<collection>/` + README checksum | Reject undocumentable sources |
| Validation | Deposit + schema map | `valid_rows[]`, `quarantine[]` | Fail-closed on dest/host |
| Normalization | valid rows | Canonical field bag | Quarantine unparseable units |
| Entity resolution | Normalized bag | `match\|create\|review` decision | Never auto-merge fuzzy |
| Classification | Resolved entity | Category id + TaxonomyNode ids | Unknown → quarantine/unclassified |
| Property mapping | Source attrs | `(definition_id, raw_value)*` | Unmapped keys reported |
| Fact creation | Mapped attrs | Fact drafts `asserted` | No invent |
| Graph creation | Entity + class + docs | Edge drafts | Registry types only |
| Human review | Draft batch | Approved/rejected set | Tier gates |
| Production | Approved set | API writes + APPLY-REPORT | ADR-012 categories |

---

## 3. Mapping strategy

### 3.1 Mapping layers

| Layer | Artifact | Owner |
|-------|----------|-------|
| Source schema map | column/path → canonical field | Data eng |
| Brand alias map | string → `brand_id` | Catalog steward |
| Manufacturer alias map | string → `manufacturer_id` | PIM (UD-01) |
| Category rule map | keywords/OEM path → `category_id` | Taxonomy commerce |
| Taxonomy classify map | rules → TaxonomyNode concept_id | Knowledge steward |
| Property alias map | source key FA/EN → Definition key | Property steward |
| Unit map | symbol → canonical unit | Property steward |

All maps are **Git-versioned** (AODS `MAPPING-TABLE`). Runtime caches allowed; Git remains SoT for transform logic.

### 3.2 Property mapping algorithm

1. Lookup source key in alias table → `definition_id`.  
2. If miss → quarantine key (do not drop silently).  
3. Parse value with Definition datatype + unit map.  
4. Emit Fact draft with `source_id` = deposit ref + row locator.  
5. Optionally mirror into JSONB using **canonical keys only** (strangler), never invent defaults from `get_default_specifications()` empty strings as if measured.

### 3.3 Example

```text
Source: {"دقت": "±0.02mm", "SKU": "500-196-30"}
  → alias دقت → accuracy
  → parse quantity ± / 0.02 / mm
  → Fact(accuracy, 0.02 mm, qualifier=±, status=asserted)
```

---

## 4. Duplicate handling

| Detection | Action |
|-----------|--------|
| Duplicate SKU in batch | Keep first valid; quarantine rest |
| SKU matches DB, same Manufacturer+Model | Update enrich path |
| SKU matches DB, different Model | **High** halt |
| No SKU, Manufacturer+MPN match | Attach/enrich; assign SKU policy |
| Fuzzy name only | Review queue — never merge |
| Duplicate Document checksum | Reuse Document node |

Idempotency key per job: `hash(job_id + entity_business_key + stage + content_hash)`.

---

## 5. Provenance model

| Object | Provenance fields |
|--------|-------------------|
| Deposit | vendor, URL, retrieved_at, checksum, path |
| Row | deposit_id, row_number / OEM URL |
| Fact | source_id, recorder (job|user|ai), recorded_at, confidence |
| Edge | same + registry type version |
| Apply | git SHA, env, counts, ticket (Category B) |

AODS artifacts: `SOURCE-DEPOSIT`, `KNOWLEDGE-EXTRACT`, `DRY-RUN-REPORT`, `APPLY-REPORT`.

---

## 6. Rollback architecture

| Scope | Mechanism |
|-------|-----------|
| Category A local | Re-run compensating job; DB restore from local backup |
| Category B production | Mandatory pre-`backup_db.sh` restore point (ingestion policy) |
| Fact batch | Status flip to `deprecated` by `batch_id` |
| Edge batch | Soft deprecate by `batch_id` |
| Commerce create mistake | Soft-delete product; do not reuse SKU casually |

Every production job MUST declare Rollback in job header (policy §5).

---

## 7. Audit architecture

Minimum retained (no secrets in Git):

| Record | Content |
|--------|---------|
| Job definition | Script path, maps versions, flags |
| Run log | start/end UTC, env, base URL, operator |
| Stage metrics | counts in/out/quarantine |
| Sample diffs | before/after for N SKUs |
| Gate results | dry-run pass/fail |

---

## 8. Job types

| Job type | Stages included | May write price | May create product |
|----------|-----------------|-----------------|--------------------|
| `identity_import` | through Production | If commercial source declared | Yes scoped |
| `spec_enrich` | skip create; Facts+JSONB | No | No |
| `graph_project` | Graph+Review | No | No |
| `knowledge_draft` | Modules AI draft | No | No |
| `price_reconcile` | Validate→Normalize→Production commercial | Yes | No |
| `seo_enrich` | SEO stage | No | No |

---

## 9. Alignment to as-built scripts

| Script family | Transform home |
|---------------|----------------|
| `*_crawl.py` | Raw deposit producer |
| `*_import.py` | identity_import (formalize maps) |
| `*_enrich*.py` | spec_enrich |
| `seed_categories.py` | commerce taxonomy seed (not routine) |
| `ingestion_boundary.py` | Destination gate |
| Image importers | Media jobs (D16) — separate from Fact invent |

---

## 10. Human review integration

| Tier | Transform behavior |
|------|-------------------|
| Low | Auto apply after dry-run |
| Medium | Write `review_queue` rows; block publish status |
| High | Block Production stage until expert ack |

Review queue logical fields: entity_key, proposed_change, risk_tier, evidence_links, decision.

---

## 11. Requirements

| ID | Criterion |
|----|-----------|
| **XF-R1** | Full stage chain documented with I/O |
| **XF-R2** | Mapping layers Git-versioned |
| **XF-R3** | Duplicate rules explicit |
| **XF-R4** | Provenance on Facts/edges |
| **XF-R5** | Rollback per Category A/B |
| **XF-R6** | Does not weaken ADR-012 |
| **XF-R7** | Property mapping does not invent values |

---

## 12. Open questions

| ID | Question |
|----|----------|
| **XF-Q1** | Review queue in Postgres vs GitHub tickets for Medium batches? |
| **XF-Q2** | When to dual-write Facts while JSONB remains SoT? (Board gate) |
