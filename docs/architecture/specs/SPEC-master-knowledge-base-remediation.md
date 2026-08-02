---
id: SPEC-master-knowledge-base-remediation
version: 0.1.0
status: Proposed
date: 2026-08-02
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/architecture/adr/ADR-013-knowledge-edge-fact-storage.md
  - docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md
  - docs/architecture/specs/SPEC-knowledge-graph-model.md
  - docs/architecture/specs/SPEC-knowledge-graph-registry.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-property-dictionary-system.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
owner: Platform Architect + Knowledge Architect (author) · Owner review required
task_id: KB-REMEDIATION-00
pack: docs/architecture/specs/README.md
---

# SPEC — Master Knowledge Base Remediation Architecture Contract

**Status:** **Proposed — owner review required**  
**Document type:** Implementation contract (Plane B)  
**Authority:** This document does **not** claim Board acceptance. It MUST NOT be treated as Accepted Canon until an Architecture Board minute upgrades it.  
**Non-goals of this SPEC file:** Code · Alembic · tests · frontend · editing Accepted ADRs · dual-write authorization · graph database introduction · inventing a parallel public product ID.

---

## 0. Purpose & as-built baseline

### 0.1 Purpose

Define the **single implementation contract** for remediating the KB-001 knowledge edge overlay into a **secure, governed Master Knowledge Base** so later tasks (Prompts 01–14) do not invent API, publication, projection, provenance, or storage behavior.

### 0.2 As-built baseline (preserve meaning; remediate gaps)

| Area | As-built | Cite |
|------|----------|------|
| Storage | Postgres `knowledge_edges` overlay; no Facts table | `app/db/models/knowledge.py:40-102` · ADR-013 |
| Freeze types | `PRODUCT_BELONGS_TO_CATEGORY`, `PRODUCT_BRANDED_AS`, `ARTICLE_EXPLAINS_PRODUCT` | `knowledge.py:29-34` · registry §5 |
| PKE identity | Join key = `products.id` | ADR-014 |
| Public reads | Unauthenticated `GET /edges`, `GET /products/{id}/neighborhood` return full edge rows including provenance | `app/api/endpoints/knowledge.py:26-95` · `app/schemas/knowledge.py:21-48` |
| Visibility | CRUD defaults to `asserted` \| `published` | `app/crud/knowledge.py:11-12` |
| Category/brand status | `published` if product `is_active` and not soft-deleted; else `asserted` | `knowledge_edge_projector.py:31-35` |
| Article status | Always project `asserted` | `knowledge_edge_projector.py:168-183` |
| Sync | Synchronous admin `POST /projections/sync`; empty scope = full catalog | `knowledge.py:98-115` · `schemas:51-55` |
| Counters | `products_scanned`, `articles_scanned`, `edges_upserted`, `edges_deprecated` only | `schemas:58-63` |
| Upsert truth | Update path always counted as changed (`True`) | `knowledge_edge_projector.py:77-83` |
| Storefront rail | Local blog JSON `related_product_ids`; not knowledge API | `product-knowledge-rail.tsx:14-21` |
| Admin browser | Read-only list via `GET /edges`; type filter; shows provenance | `knowledge-edges-browser.tsx:26-95` |

### 0.3 Non-negotiable invariants

1. **Modular monolith layer direction:** `endpoints → services → crud → models`. Knowledge remediation MUST NOT introduce cross-layer imports that invert this.
2. **PostgreSQL remains commerce + knowledge storage.** No graph database / engine (ADR-013).
3. **`products.id` is the Wave-1 Product Knowledge Entity identity.** No parallel public product ID namespace (ADR-014).
4. **Never weaken** authentication, authorization, publication-state filtering, provenance, auditability, or DB integrity to make tests pass.
5. **No dual-write** of `products.specifications` JSONB ↔ Facts until a **separate** Board-approved migration/import task (Bible P5–P6 · ADR-013 Decision 4 · SPEC-property-dictionary PD-R7).

---

## 1. Public versus admin API boundary

### 1.1 Surface classes

| Class | Audience | AuthN/AuthZ | May expose |
|-------|----------|-------------|------------|
| **Public knowledge** | Storefront / anonymous / customer | None or session; no admin role required | Published knowledge read-models only (§1.3, §8) |
| **Admin stewardship** | Admin panel / operators | Authenticated **super-admin** (same gate as today’s sync: `get_current_super_admin`) unless a later Accepted ADR introduces a narrower Knowledge Steward role | Raw edges, all statuses, provenance, audit, review actions, jobs |
| **Projection control** | Operators / CLI | Super-admin for HTTP; CLI worker uses ops credentials / process identity (§5) | Sync requests, job status, counters |

### 1.2 Raw edge listing is admin-only

| Endpoint (target) | Rule |
|-------------------|------|
| `GET /api/v1/knowledge/edges` | **MUST** require super-admin. Anonymous and non-admin callers receive `401` (no/invalid auth) or `403` (authenticated non-admin). |
| Future `GET /api/v1/knowledge/edges/{edge_id}` | Admin-only if introduced. |
| Any endpoint returning `KnowledgeEdgeResponse` (full row) | Admin-only. |

**Deprecation of as-built public listing:** While unauthenticated listing exists, it is a **security defect**, not a supported public contract. Remediation Prompt 01 MUST close anonymous access in the same change that introduces the public read-model (§8). A compatibility shim that continues to return full rows to anonymous clients is **forbidden**.

### 1.3 Public responses — publication & field redaction

Public knowledge responses **MUST**:

1. Include only knowledge with public-eligible publication state (§2).
2. **Never** expose internal recorder / source / audit fields, including at minimum: `recorder`, `source_kind`, `source_ref`, `recorded_at` (as audit stamp), `confidence` (internal), `notes`, projection-run IDs, actor IDs, change reasons, review metadata.
3. Use **resolved public DTOs** (§8), not ORM-shaped `KnowledgeEdgeResponse`.

Admin responses **MAY** expose the full edge row plus provenance extensions (§7).

### 1.4 Security matrix (normative)

| Operation | Anon | Customer | Super-admin |
|-----------|------|----------|-------------|
| `GET .../products/{product_id}/knowledge` (public PKE read-model) | Yes (published only) | Yes | Yes |
| `GET .../edges` (raw) | No | No | Yes |
| `GET .../edges` with `status=asserted\|rejected\|deprecated` | No | No | Yes |
| Review / publish / reject edge | No | No | Yes |
| `POST .../projections/sync` (scoped) | No | No | Yes |
| Enqueue full-catalog projection job | No | No | Yes |
| `GET` projection job status | No | No | Yes |
| Property dictionary / Facts admin CRUD | No | No | Yes (when tables exist) |
| Public Facts (customer-facing) | Published Facts only | Published Facts only | Yes |

---

## 2. Publication semantics

Statuses remain the Accepted vocabulary: `asserted` \| `published` \| `rejected` \| `deprecated` (SPEC-knowledge-graph-model §7 · `EDGE_STATUSES`).

### 2.1 Global visibility rules

| Status | Internal (admin) | Public |
|--------|------------------|--------|
| `asserted` | Visible | **Never** |
| `published` | Visible | **Yes**, subject to type-specific gates below |
| `rejected` | Visible | **Never** |
| `deprecated` | Visible | **Never** |

**Remediation delta:** As-built public visibility of `asserted` (`crud/knowledge.py:_visible_statuses`) is **non-compliant** with this contract and MUST be removed from all public query paths.

### 2.2 `PRODUCT_BELONGS_TO_CATEGORY`

| Rule | Norm |
|------|------|
| Projection source | `products.category_id` |
| Auto status | `published` iff commerce product is active and not soft-deleted; else `asserted` (preserve projector intent) |
| Public | Edge `status=published` **and** target category exists and is commerce-public per existing category public rules |
| Cardinality | N:1 as-built; stale targets deprecated by reconciliation (§4) |

### 2.3 `PRODUCT_BRANDED_AS`

| Rule | Norm |
|------|------|
| Projection source | `products.brand_id` |
| Auto status | Same commerce publish-with-product rule as category |
| Public | Edge `status=published` **and** target brand exists |
| Missing brand | No edge created; prior brand edge deprecated when `brand_id` cleared |

### 2.4 `ARTICLE_EXPLAINS_PRODUCT`

| Rule | Norm |
|------|------|
| Projection source | `articles.related_product_ids` |
| Default projection status | `asserted` (internal candidate) — preserve wave-1 default |
| Auto-publish | **Forbidden** from projection alone |
| Steward publish | Super-admin review action MAY set `published` only when **all** public gates hold at transition time |
| **Public article edge gates** (all required) | (1) edge `status=published`; (2) article `is_published=true`; (3) article `published_at` is not in the future (server clock UTC); (4) target product is a **public target product** (§2.5) |
| If any gate fails at read time | Omit from public response (do not error the whole PDP knowledge payload) |
| If steward attempts publish while gates fail | `409` with error code `ARTICLE_EDGE_NOT_PUBLISHABLE` and details naming failed gates |

### 2.5 Public target product

A product is a **public target product** iff:

1. Row exists in `products`.
2. `deleted_at IS NULL`.
3. `is_active = true`.
4. It is eligible for existing public product read APIs (same filters Storefront already uses for PDP; remediation MUST NOT invent a weaker filter).

### 2.6 Rejected & deprecated

- `rejected`: steward decision; retained for audit; never public; projection MUST NOT overwrite `rejected` back to `asserted`/`published` without an explicit steward re-open action.
- `deprecated`: reconciliation/lifecycle; never public; soft state — rows are not hard-deleted by projection.

---

## 3. Endpoint plan, schemas, deprecation, errors

### 3.1 Backward-compatible plan

| Phase | Behavior |
|-------|----------|
| **T0 (as-built)** | `GET /edges`, `GET /products/{id}/neighborhood`, `POST /projections/sync` |
| **T1 (Prompt 01–03)** | Lock raw `/edges` to admin; add public PKE read-model; keep neighborhood path but change its **response schema and visibility** |
| **T2 (compatibility window)** | Documented period (default **30 days** after T1 merge to `main`, or until owner shortens) during which clients MUST migrate |
| **T3** | Remove legacy public field shapes only after Storefront + Admin consumers updated |

### 3.2 Endpoint inventory (target)

#### Admin — raw edges

```http
GET /api/v1/knowledge/edges
```

Query (preserve + extend): `edge_type`, `from_type`, `from_id`, `to_type`, `to_id`, `status`, `skip`, `limit` (1–500).  
Response: `KnowledgeEdgeListResponse` (full rows + later provenance extensions).  
Auth: super-admin.

#### Admin — review actions (new)

```http
POST /api/v1/knowledge/edges/{edge_id}/review
```

Body:

```json
{
  "action": "publish" | "reject" | "reopen_asserted" | "deprecate",
  "change_reason": "string (required, min 3 chars)"
}
```

Effects: status transition per §2; write review metadata (§7).  
Errors: `404 EDGE_NOT_FOUND`, `409 INVALID_STATUS_TRANSITION`, `409 ARTICLE_EDGE_NOT_PUBLISHABLE`, `422` validation.

#### Public — Product Knowledge read-model (new; preferred Storefront contract)

```http
GET /api/v1/knowledge/products/{product_id}/knowledge
```

Auth: public.  
`product_id` = commerce `products.id` (ADR-014).  
Response: `PublicProductKnowledgeResponse` (§8).  
If product is not a public target product: `404 PRODUCT_NOT_FOUND` (do not leak existence of inactive SKUs beyond existing public product behavior — align with products public GET).

#### Legacy neighborhood (compat)

```http
GET /api/v1/knowledge/products/{product_id}/neighborhood
```

| Rule | Norm |
|------|------|
| Auth | Remains public |
| Visibility | **Published-only** (no `asserted`) |
| Schema | **MUST NOT** return admin fields (`recorder`, `source_*`, etc.) |
| Shape | Prefer embedding the same resolved objects as §8 (`category`, `brand`, `articles`) rather than raw edge rows |
| Deprecation | Response header `Deprecation: true` + `Link` to `/knowledge` successor; OpenAPI mark deprecated; remove after compatibility window |

Breaking change note: removing `asserted` articles from neighborhood **is intentional** and required for security/publication honesty. Tests that expected asserted articles on public neighborhood MUST be rewritten to admin or publish-path tests.

#### Projection sync (admin)

```http
POST /api/v1/knowledge/projections/sync
```

Body:

```json
{
  "product_ids": [1, 2] | null,
  "article_ids": [3] | null,
  "mode": "inline" | "enqueue"
}
```

| Mode | Rule |
|------|------|
| `inline` (default for scoped) | Allowed only when scope is **bounded** (§5.1). Returns `ProjectionSyncResponse` with §6 counters. |
| `enqueue` | Required for unbounded / full-catalog. Returns `202` + `ProjectionJobAccepted` (`job_id`). |
| Unbounded `inline` | **Rejected** with `413 SYNC_SCOPE_TOO_LARGE` (or `422`) — MUST NOT run full-catalog inside the HTTP request after remediation |

Empty `product_ids`/`article_ids` meaning **full catalog** is preserved only for `mode=enqueue` (or CLI). As-built “empty = sync all inline” is **retired**.

#### Projection jobs (admin)

```http
GET /api/v1/knowledge/projections/jobs/{job_id}
GET /api/v1/knowledge/projections/jobs?status=&skip=&limit=
```

### 3.3 Response schemas (normative shapes)

#### Admin `KnowledgeEdgeResponse` (extend; admin-only)

Retain fields: `id`, `edge_type`, `from_node_type`, `from_node_id`, `to_node_type`, `to_node_id`, `status`, `source_kind`, `source_ref`, `recorded_at`, `recorder`, `confidence`, `attributes`.

Add (Prompt 08+):

| Field | Type | Meaning |
|-------|------|---------|
| `projection_run_id` | string \| null | Last projection job/run that touched the row |
| `first_seen_at` | datetime | First insert time (immutable) |
| `last_verified_at` | datetime | Last successful reconcile/verify |
| `source_artifact` | string \| null | Artifact id/path/version |
| `source_version` | string \| null | Version pin |
| `actor` | string \| null | Steward user id or system actor for last review |
| `review_status` | string \| null | Last review action |
| `reviewed_at` | datetime \| null | |
| `change_reason` | string \| null | Last steward reason |
| `from_label` / `to_label` | string \| null | Resolved node labels for admin UI |

#### Public `PublicProductKnowledgeResponse`

See §8 — no provenance fields.

#### `ProjectionSyncResponse` (remediated counters)

```json
{
  "products_scanned": 0,
  "articles_scanned": 0,
  "created": 0,
  "updated": 0,
  "unchanged": 0,
  "deprecated": 0,
  "invalid_references": 0,
  "failed": 0,
  "job_id": null
}
```

**Compatibility:** `edges_upserted` MAY be emitted during the compatibility window as `created + updated` (documented alias) then removed at T3. New clients MUST use the counters above.

### 3.4 Error behavior

| Code | HTTP | When |
|------|------|------|
| `INVALID_EDGE_TYPE` | 422 | Unknown `edge_type` filter (preserve) |
| `EDGE_NOT_FOUND` | 404 | Review target missing |
| `INVALID_STATUS_TRANSITION` | 409 | Illegal status change |
| `ARTICLE_EDGE_NOT_PUBLISHABLE` | 409 | Publish gates fail |
| `SYNC_SCOPE_TOO_LARGE` | 413 or 422 | Inline sync exceeds scope limits |
| `PROJECTION_JOB_IN_PROGRESS` | 409 | Lock held for overlapping full sync |
| `PRODUCT_NOT_FOUND` | 404 | Public knowledge for non-public product |
| `UNAUTHORIZED` / `FORBIDDEN` | 401 / 403 | AuthZ boundary |

All errors continue to use the platform `api_error` envelope (`error_code`, `message`, `details`).

---

## 4. Orphan, invalid-reference, source-deletion, reconciliation

### 4.1 Orphan policy

An edge is **orphan** when either endpoint node is missing from SoR (`products` / `categories` / `brands` / `articles`).

| Action | Norm |
|--------|------|
| Detection | Reconciliation pass (§4.4) and projection-time checks |
| Treatment | Set `status=deprecated`; increment `invalid_references` if discovered during projection because source pointed at missing id; do **not** hard-delete |
| Public | Orphans never appear |

### 4.2 Invalid-reference policy

| Case | Projection behavior |
|------|---------------------|
| `category_id` points to missing category | Do not create/update published edge; deprecate prior category edge; `invalid_references++` |
| `brand_id` points to missing brand | Same |
| `related_product_ids` contains missing / non-int / non-public-inactive handling | Skip create for that id; deprecate edge if previously existed and id removed from array; `invalid_references++` for missing ids |
| Duplicate ids in `related_product_ids` | Dedupe before upsert (idempotent) |

### 4.3 Source deletion policy

| Source change | Edge effect |
|---------------|-------------|
| Product soft-deleted / deactivated | Category & brand edges → `asserted` (commerce rule) or `deprecated` if product hard-removed; never public |
| `category_id` / `brand_id` cleared or changed | Stale targets deprecated via `_deprecate_stale` semantics (preserve) |
| Article deleted or unpublished | Existing `ARTICLE_EXPLAINS_PRODUCT` edges remain for audit but **MUST** drop from public; steward MAY deprecate; projection SHOULD set `asserted` if was `published` and article no longer publishable |
| Id removed from `related_product_ids` | Corresponding edge deprecated |

**Hard delete of edge rows:** Forbidden in wave remediation except via explicit future Board-approved purge job with backup.

### 4.4 Global reconciliation rule

A **reconcile** pass MUST be runnable from CLI (and optionally enqueueable) and MUST:

1. Scan all `knowledge_edges` of KB-001 freeze types (later: all registered types).
2. Verify endpoint existence and type/direction registry compliance.
3. Align category/brand edges with current `products.category_id` / `brand_id`.
4. Align article edges with current `related_product_ids`.
5. Apply publication demotion when public gates fail for currently `published` article edges.
6. Emit the same counter schema as sync (§6).
7. Be **idempotent**: second reconcile without SoR changes ⇒ `unchanged` dominates; no flip-flop.

Projection sync for a scope **implies** scoped reconciliation for that scope. Full reconcile = full-catalog job.

---

## 5. Projection execution model

### 5.1 Scoped HTTP sync limits

| Parameter | Limit (initial) |
|-----------|-----------------|
| Max `product_ids` in inline sync | **500** |
| Max `article_ids` in inline sync | **200** |
| Max runtime budget inline | **30s** target (§12) |
| Full catalog / null scopes | **enqueue only** |

ADR-012 Category A local enrichment remains binding: sync endpoints MUST NOT target production remote APIs.

### 5.2 Durable PostgreSQL job rows

Introduce `knowledge_projection_jobs` (name normative for Prompt 05):

| Column | Meaning |
|--------|---------|
| `id` | Job id (UUID or BIGSERIAL) |
| `status` | `queued` \| `running` \| `succeeded` \| `failed` \| `cancelled` |
| `scope` | JSON: product_ids/article_ids/null=all |
| `counters` | JSON matching §6 |
| `attempt` | Retry count |
| `locked_by` | Worker id |
| `locked_at` | Lease timestamp |
| `checkpoint` | JSON: last product_id / article_id processed |
| `error` | Last failure message |
| `created_at` / `started_at` / `finished_at` | Timestamps |
| `created_by` | Actor |

### 5.3 CLI worker

- Entry: `python -m app...` or `scripts/knowledge_projection_worker.py` (exact path chosen in Prompt 06; layer: script → service → crud → models).
- Polls `queued` jobs; claims with row lock / `FOR UPDATE SKIP LOCKED`.
- Processes in **batches** (default **100** products, **50** articles).
- Writes **checkpoints** after each batch commit.
- **Retry:** transient DB errors → exponential backoff; max attempts **5**; then `failed`.
- **Locking:** lease TTL **15 minutes**; expired lease reclaimable.
- **Idempotency:** job re-run safe via edge identity unique key (`uq_knowledge_edges_identity`) + counter semantics (§6).

### 5.4 HTTP vs worker responsibilities

| Concern | HTTP API | Worker |
|---------|----------|--------|
| AuthZ | Super-admin | Process identity |
| Scoped inline sync | Yes (within limits) | Optional |
| Full sync | Enqueue only | Execute |
| Long retries | No | Yes |

---

## 6. Upsert behavior & counters

### 6.1 Identity

Upsert key remains:

`(edge_type, from_node_type, from_node_id, to_node_type, to_node_id)`

### 6.2 Real created / updated / unchanged

On projection of a desired edge:

| Outcome | Condition | Counter |
|---------|-----------|---------|
| **created** | No row → insert | `created++` |
| **updated** | Row exists and any governed field changes (status, source_ref, endpoint already same; provenance refresh that changes `last_verified_at` only may count as **unchanged** if policy pins “content equality”; **normative:** content equality = `status` + endpoint identity + `source_ref` + `attributes`; if only `last_verified_at` / `recorded_at` refresh → **unchanged**) | `updated++` or `unchanged++` |
| **deprecated** | Stale active edge closed | `deprecated++` |
| **invalid_references** | Source references missing/invalid node | `invalid_references++` |
| **failed** | Unexpected exception for one entity; job continues when possible | `failed++` |

**Remediation delta:** As-built always returns `True` for updates and folds create+update into `edges_upserted`. That MUST be replaced by the counters above.

### 6.3 Scan counters

- `products_scanned`: products loaded for the run/scope.
- `articles_scanned`: articles loaded for the run/scope.

### 6.4 Idempotency acceptance

Two consecutive identical scoped syncs MUST yield `created=0`, `updated=0`, `deprecated=0` (barring clock-driven publication demotion), with `unchanged ≥ 0` and stable edge counts.

---

## 7. Minimum provenance model

Every knowledge edge (and later Fact) MUST support:

| Field | Required | Notes |
|-------|----------|-------|
| `projection_run_id` | SHOULD | Set on projection touch |
| `first_seen_at` | Yes | Set once on insert |
| `last_verified_at` | Yes | Set on verify/reconcile/projection touch |
| `source_kind` | Yes | Preserve (`projection`, `cms`, `manual`, …) |
| `source_ref` | SHOULD | e.g. `products.category_id` |
| `source_artifact` | MAY | AODS artifact id / checksum |
| `source_version` | MAY | Artifact/version pin |
| `recorder` | Yes | System projector id or user id |
| `actor` | SHOULD on review | Steward who published/rejected |
| `reviewed_at` / `review_status` | SHOULD on review | |
| `change_reason` | Yes on steward mutation | Mandatory on review API |
| `recorded_at` | Yes | Last content write stamp |

Public DTOs **omit** all of the above.

---

## 8. Public Product Knowledge read-model (Storefront)

### 8.1 Endpoint

`GET /api/v1/knowledge/products/{product_id}/knowledge` → `PublicProductKnowledgeResponse`.

### 8.2 Schema

```json
{
  "product_id": 123,
  "category": {
    "id": 1,
    "slug": "…",
    "name": "…",
    "edge_type": "PRODUCT_BELONGS_TO_CATEGORY"
  },
  "brand": {
    "id": 3,
    "slug": "…",
    "name": "…",
    "edge_type": "PRODUCT_BRANDED_AS"
  },
  "articles": [
    {
      "id": 10,
      "slug": "…",
      "title": "…",
      "excerpt": "…",
      "cover_image": "…",
      "published_at": "…",
      "reading_minutes": 5,
      "tags": ["…"],
      "edge_type": "ARTICLE_EXPLAINS_PRODUCT"
    }
  ]
}
```

Rules:

- `category` / `brand` null when no **public** edge.
- `articles` only edges passing §2.4 gates; ordered stably (e.g. `published_at DESC`, then `id`).
- No raw edge ids required on public DTO (MAY include `edge_id` only if product needs deep-link; default **omit**).
- Storefront `ProductKnowledgeRail` MUST migrate from local blog JSON to this API (Prompt 09); empty list ⇒ hide rail (preserve honest-empty UX).

### 8.3 Resolved fields

Resolution joins:

- Category ← `categories` by `to_node_id`
- Brand ← `brands` by `to_node_id`
- Article ← `articles` by `from_node_id`

Missing join at read time ⇒ treat as non-public (omit); admin reconcile SHOULD deprecate.

---

## 9. Admin stewardship requirements

Admin Knowledge UI / APIs MUST provide:

| Capability | Norm |
|------------|------|
| Pagination | `skip`/`limit` with `total` (preserve) |
| Status filters | All four statuses + “active”=`asserted|published` |
| Type filters | KB-001 types; later registry types |
| Resolved node labels | `from_label` / `to_label` (§3.3) |
| Evidence / provenance display | Show §7 fields on detail view |
| Review actions | publish / reject / reopen_asserted / deprecate with `change_reason` |
| History | Append-only `knowledge_edge_events` (Prompt 10): edge_id, at, actor, from_status, to_status, reason, payload |

Read-only Day-5 browser is the baseline; remediation extends it — does not remove FA labels or freeze-type discipline.

---

## 10. Runtime property dictionary, units, Facts, evidence, taxonomy

### 10.1 Scope

Runtime tables are **in-contract** for Prompts 11–13. They remain Postgres overlay tables (ADR-013). Git seeds (`docs/architecture/specs/seeds/…`) stay authoring SoT until import tasks load them.

### 10.2 Property dictionary (runtime)

Tables (logical names): `knowledge_property_definitions`, `knowledge_property_aliases`, `knowledge_spec_templates`, `knowledge_template_properties`.

Fields follow SPEC-property-dictionary-system §3–§4. Status: `draft|active|deprecated`.

### 10.3 Units

Table `knowledge_units`: dimension, canonical code, aliases, conversion table version pin. Facts store canonical units only.

### 10.4 Facts & revisions

| Entity | Norm |
|--------|------|
| `knowledge_facts` | `fact_id`, `entity_id=products.id`, `definition_id`, `value` JSONB, `unit`, `qualifier`, `status` (`asserted|published|disputed|deprecated`), provenance |
| `knowledge_fact_revisions` | Append-only history on value/status changes |
| Publish | Metrology-critical / compliance Facts SHOULD require Evidence (Bible P4 · property SPEC §9) |

### 10.5 Evidence artifacts & links

| Entity | Norm |
|--------|------|
| `knowledge_evidence_artifacts` | document/checksum/source URL; may strangler from `pdf_catalog_url` |
| `knowledge_evidence_links` | Fact↔artifact or edge↔artifact (`FACT_SUPPORTED_BY`) |

### 10.6 Taxonomy nodes & classification assignments

| Entity | Norm |
|--------|------|
| `knowledge_taxonomy_nodes` | Multi-dimension nodes per SPEC-industrial-taxonomy-model; **not** a second commerce Category DAG |
| `knowledge_classification_assignments` | Materialize `PRODUCT_CLASSIFIED_AS` (edge or assignment table + edge projection); closed label set only |

INSIZE mapping tables in Git remain maps until Prompt 13 imports assignments — no silent CLASSIFIED_AS flood.

### 10.7 Explicit no-dual-write rule

Until a **separate** owner/Board-approved migration/import task:

1. `products.specifications` JSONB remains the operational storefront/admin spec SoT.
2. Runtime Facts MAY exist for stewarded pilots.
3. **Forbidden:** writers that update JSONB and Facts in one request path, or projectors that copy JSONB → Facts in bulk, or dropping JSONB.
4. Tests MUST NOT “green” by enabling dual-write.

---

## 11. Migration sequence, rollback, compatibility, matrices, budgets

### 11.1 Migration sequence

| Step | Migration / change | Rollback expectation |
|------|--------------------|----------------------|
| M1 | AuthZ on `/edges`; public visibility fix; public DTO endpoints | Revert app code; DB unchanged |
| M2 | Provenance columns on `knowledge_edges` (`first_seen_at`, `last_verified_at`, …) | Alembic downgrade nullable/drop columns |
| M3 | `knowledge_projection_jobs` | Drop table |
| M4 | `knowledge_edge_events` | Drop table |
| M5 | Property dictionary + units tables | Drop tables; Git seeds remain |
| M6 | Facts + revisions | Drop tables |
| M7 | Evidence artifacts/links | Drop tables |
| M8 | Taxonomy nodes + classification assignments | Drop tables; never drop `categories` |

Each Alembic revision MUST be alone-reviewable; no big-bang.

### 11.2 Compatibility period

- Neighborhood schema change: **30 days** deprecation headers.
- `edges_upserted` alias: same window.
- Admin clients must send auth on `/edges` immediately at M1 (breaking for anonymous — security exception; no grace for anonymous raw listing).

### 11.3 Security matrix

See §1.4. Additional:

| Control | Norm |
|---------|------|
| Publication filter bypass | Forbidden in public services |
| IDOR on admin edge review | `edge_id` must exist; no cross-tenant issues (single-tenant app) |
| Job enqueue flood | Rate-limit / single active full-sync lock |

### 11.4 Test matrix (minimum)

| Area | Required tests |
|------|----------------|
| AuthZ | Anon `/edges` → 401/403; admin OK |
| Publication | Asserted edges absent from public knowledge |
| Article gates | Unpublished / future `published_at` / inactive product omitted |
| Sync limits | Oversize inline → error; enqueue → 202 |
| Counters | create/update/unchanged/deprecate/invalid/failed correctness + idempotency |
| Orphans | Missing category/brand/product → deprecate + counter |
| Rejected freeze | Projection does not clobber `rejected` without reopen |
| No dual-write | Assert no writer couples JSONB↔Facts |
| Layering | Import linter / smoke that endpoints do not touch models bypassing services where required by repo norms |

### 11.5 Observability

Log/metric fields: `job_id`, counters, duration_ms, `failed`, lock contention. Admin job detail view required. No PII beyond steward user ids already used in admin audit.

### 11.6 Performance budgets

| Operation | Budget |
|-----------|--------|
| Public PKE read | p95 ≤ **100 ms** DB time local; ≤ **300 ms** end-to-end staging |
| Inline sync (≤500 products) | ≤ **30 s** |
| Full-catalog job throughput | ≥ **50 products/s** steady-state on staging-class hardware (target; tune in Prompt 14) |
| Admin edge list | p95 ≤ **200 ms** for limit=100 |

---

## 12. Implementation sequence (Prompts 01–14)

This pack’s execution order. Prompt 00 = this contract. Later prompts MUST NOT invent contradictory behavior.

| Prompt | Title | Primary deliverable |
|--------|-------|---------------------|
| **01** | Secure API boundary | Admin-only raw `/edges`; strip public provenance; authZ tests |
| **02** | Publication semantics enforcement | Public queries published-only; article public gates; rejected/deprecated never public |
| **03** | Public & compat endpoint schemas | `GET .../knowledge` DTO; neighborhood deprecation shape; OpenAPI |
| **04** | Orphan & reconciliation policies | Invalid-reference handling; global reconcile service rules + tests |
| **05** | Durable projection jobs | `knowledge_projection_jobs` migration; enqueue API; inline scope limits |
| **06** | Worker runtime | CLI worker, batches, retry, locking, checkpoints, idempotency |
| **07** | Upsert counters | Real created/updated/unchanged/deprecated/invalid_references/failed |
| **08** | Provenance columns | first-seen, last-verified, artifact/version, actor, review metadata, change_reason |
| **09** | Storefront PKE consumption | Wire `ProductKnowledgeRail` to public read-model; honest empty |
| **10** | Admin stewardship | Pagination/status filters, resolved labels, evidence display, review actions, history |
| **11** | Runtime property dictionary + units | Tables + admin read/seed import **without** JSONB dual-write |
| **12** | Facts + revisions | Fact tables, statuses, revision history, publish gates |
| **13** | Evidence + taxonomy + classification | Artifacts/links; taxonomy nodes; CLASSIFIED_AS assignments (no second Category DAG) |
| **14** | Hardening & matrices | Observability, performance budgets verification, security/test matrix closeout, compatibility window checklist |

**Stop condition:** If a prompt requires editing a path outside its allowlist, stop and report — do not expand scope silently.

---

## 13. Requirements traceability (testable)

| ID | Requirement |
|----|-------------|
| **MKB-R1** | Raw edge listing admin-only |
| **MKB-R2** | Public never sees asserted/rejected/deprecated |
| **MKB-R3** | Public never sees recorder/source/audit fields |
| **MKB-R4** | Article public edge requires published article + non-future `published_at` + public target product |
| **MKB-R5** | Inline sync scope-limited; full sync via durable job + worker |
| **MKB-R6** | Counters distinguish created/updated/unchanged/deprecated/invalid_references/failed |
| **MKB-R7** | Provenance minimum fields present on edges |
| **MKB-R8** | Public PKE read-model resolves category/brand/articles |
| **MKB-R9** | Admin stewardship supports filters, labels, review, history |
| **MKB-R10** | Runtime dictionary/Facts/evidence/taxonomy in Postgres overlay |
| **MKB-R11** | No JSONB↔Facts dual-write without separate approved task |
| **MKB-R12** | `products.id` remains PKE identity; no graph DB |
| **MKB-R13** | Layer direction endpoints → services → crud → models preserved |

---

## 14. Document control

| Field | Value |
|-------|-------|
| Status | **Proposed — owner review required** |
| Board acceptance | **Not claimed** |
| Next gate | Owner review → optional Board Accept minute → Prompt 01 allowlist execution |
| Supersedes | None (remediates as-built KB-001 gaps; does not rewrite Accepted ADR-013/014 text) |

---

*End of SPEC-master-knowledge-base-remediation.*
