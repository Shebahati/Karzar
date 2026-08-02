---
id: SPEC-master-knowledge-base-remediation
version: 0.4.1
status: Proposed
date: 2026-08-02
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/architecture/adr/ADR-013-knowledge-edge-fact-storage.md
  - docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md
  - docs/architecture/adr/ADR-015-product-type-engineering-classification.md
  - docs/architecture/specs/SPEC-canonical-product-type-model.md
  - docs/architecture/specs/SPEC-knowledge-graph-model.md
  - docs/architecture/specs/SPEC-knowledge-graph-registry.md
  - docs/architecture/specs/SPEC-product-knowledge-entity-model.md
  - docs/architecture/specs/SPEC-property-dictionary-system.md
  - docs/architecture/specs/SPEC-industrial-taxonomy-model.md
owner: Platform Architect + Knowledge Architect (author) · Owner implementation approval recorded 2026-08-02 · Product Type architecture amendment KB-PT-00 · Final owner-review corrections KB-PT-00A
task_id: KB-PT-00A
pack: docs/architecture/specs/README.md
amends: KB-PT-00 (v0.4.0) — final owner-review corrections (11A sequencing, Board gate); not Board Accept
owner_implementation_approval: Approved for Prompts 01-14 subject to Product Type gates in §12.1
owner_implementation_approval_date: "2026-08-02"
owner_implementation_approver: Mohammad Shebahati
architecture_board_acceptance: not_granted
canonical_authority: not_accepted_canon
---

# SPEC — Master Knowledge Base Remediation Architecture Contract

**Status:** **Proposed** (document lifecycle) — **owner implementation approval recorded** for Prompts 01–14, **subject to the Product Type gate in §12.1**
**Document type:** Implementation contract (Plane B)
**Authority:** This document does **not** claim Architecture Board acceptance and is **not** Accepted Canon. AODS registry classification remains **PROPOSED**. Path is present on `main` as of PR #192 (`on_main=true`); **v0.4.x branch amendments (KB-PT-00 / KB-PT-00A) are not yet merged**. Owner implementation approval authorizes Prompts 01–14 execution **except** where §12.1 gates apply — it does **not** upgrade Canon.
**Non-goals of this SPEC file:** Code · Alembic · tests · frontend · editing Accepted ADRs · dual-write authorization · graph database introduction · inventing a parallel public product ID · claiming Board acceptance of Product Type.

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
2. **PostgreSQL remains commerce + knowledge storage.** No graph database / engine (ADR-013 Decision 1–2).
3. **`products.id` is the Wave-1 Product Knowledge Entity identity.** No parallel public product ID namespace (ADR-014 Decision 1–2).
4. **Never weaken** authentication, authorization, publication-state filtering, provenance, auditability, or DB integrity to make tests pass.
5. **No dual-write** of `products.specifications` JSONB ↔ Facts until a **separate** Board-approved migration/import task (Bible P5–P6 · ADR-013 Decision 4 · SPEC-property-dictionary PD-R7).
6. **Product Type (owner direction, Proposed):** engineering classification source of truth is Product Type (ADR-015 Proposed · SPEC-canonical-product-type-model), not Category. Category remains commerce navigation. See §0.4 historical decision log and §12.1 gate.

---

## 0.4 Historical decision log — Product Type architecture amendment (KB-PT-00 / v0.4.0)

Preserves prior 00 / 00A / 00B / 00C history (task reports). New normative decisions recorded here:

| # | Decision |
|---|----------|
| 1 | Product Type becomes first-class engineering classification. |
| 2 | Category remains commerce navigation. |
| 3 | `products.id` remains PKE identity (ADR-014). |
| 4 | `products.product_type_id` is initially nullable. |
| 5 | Readout (digital/dial/vernier) is orthogonal to Product Type. |
| 6 | Product Type Definition is versioned (`draft` / `active` / `retired`). |
| 7 | Attribute membership uses `required` / `optional` / `conditional` / `forbidden`. |
| 8 | No bulk legacy JSONB migration is authorized by this remediation pack. |
| 9 | No JSONB↔Facts dual-write is authorized. |
| 10 | Prompt sequencing is changed before Property/Facts implementation (§12.1). |

Authoritative detail: `docs/architecture/specs/SPEC-canonical-product-type-model.md` · `docs/architecture/adr/ADR-015-product-type-engineering-classification.md`.

### 0.5 Final owner-review corrections (KB-PT-00A / v0.4.1)

Preserves §0.4. Additional normative corrections:

| # | Correction |
|---|------------|
| 1 | Prompt **11A** = Property Definitions + aliases + Units only; **before** PT-W2 Attribute Membership |
| 2 | Prompt 11A **MUST NOT** create `knowledge_spec_templates` / `knowledge_template_properties` |
| 3 | Prompt 12/13 remain blocked until PT-W2 Definition/membership ownership is implemented and approved |
| 4 | Architecture Board clarification of Hybrid vs `PRODUCT_CLASSIFIED_AS` is **mandatory** before KB-PT-01 runtime |
| 5 | PT-W1 has no readout persistence, no Product Type catalogue seed, no assignment backfill |

---

## 1. Public versus admin API boundary

### 1.1 Surface classes

| Class | Audience | AuthN/AuthZ | May expose |
|-------|----------|-------------|------------|
| **Public knowledge** | Storefront / anonymous / customer | None or session; no admin role required | Published knowledge read-models only (§1.3, §8) |
| **Admin stewardship** | Admin panel / operators | Authenticated **super-admin** (same gate as today’s sync: `get_current_super_admin`) unless a later Accepted ADR introduces a narrower Knowledge Steward role | Raw edges, all statuses, provenance, audit, review actions, jobs |
| **Projection control** | Operators / CLI | Super-admin for HTTP; CLI worker uses ops credentials / process identity (§5) | Sync requests, job status, counters |

### 1.2 Raw edge listing is admin-only (Prompt 01)

| Endpoint (target) | Rule |
|-------------------|------|
| `GET /api/v1/knowledge/edges` | **MUST** require super-admin. |
| Future `GET /api/v1/knowledge/edges/{edge_id}` | Admin-only if introduced. |
| Any endpoint returning `KnowledgeEdgeResponse` (full row) | Admin-only. |

**Prompt sequencing (normative — resolves Prompt 01 vs Prompt 03):**

| Prompt | Obligation |
|--------|------------|
| **01** | Close anonymous / non-super-admin access to raw `GET /edges` (and any full-row edge listing). **MUST NOT** wait for Prompt 03. |
| **03** | Introduce the public resolved Product Knowledge DTO (`GET .../knowledge`) and neighborhood deprecation shape. |

Prompt 01 and Prompt 03 **MUST NOT** be required in the same commit. Closing raw-edge access is a security defect fix and is independently mergeable. Until Prompt 03 lands, Storefront continues to use its as-built rail (local blog JSON); that temporary gap is **accepted** and documented — it is not permission to leave raw `/edges` public.

A compatibility shim that continues to return full rows to anonymous clients is **forbidden**.

### 1.3 Exact authentication behavior (normative)

For every admin-only knowledge endpoint (raw edges, review, sync, jobs), AuthN/AuthZ **MUST** match existing `get_current_user` / `get_current_super_admin` semantics (`app/api/deps.py`):

| Caller state | HTTP | Error code |
|--------------|------|------------|
| Missing Authorization/cookie, malformed token, expired token, revoked token (`token_version` mismatch), unknown subject | **401** | `UNAUTHORIZED` |
| Authenticated active user whose role is **not** super-admin | **403** | `FORBIDDEN` |
| Authenticated inactive user | **403** | `FORBIDDEN` |
| Authenticated super-admin | **Allowed** (proceed) | — |

Implementations MUST NOT collapse 401 and 403 into a single status. Tests MUST cover all three rows.

### 1.4 Public responses — publication & field redaction

Public knowledge responses **MUST**:

1. Include only knowledge with public-eligible publication state (§2).
2. **Never** expose internal recorder / source / audit fields, including at minimum: `recorder`, `source_kind`, `source_ref`, `recorded_at` (as audit stamp), `confidence` (internal), `notes`, projection-run IDs, steward user ids, change reasons, review metadata.
3. Use **resolved public DTOs** (§8), not ORM-shaped `KnowledgeEdgeResponse`.

Admin responses **MAY** expose the full edge row plus provenance extensions (§7).

### 1.5 Security matrix (normative)

| Operation | Anon | Customer | Super-admin |
|-----------|------|----------|-------------|
| `GET .../products/{product_id}/knowledge` (public PKE read-model) | Yes (published only) | Yes | Yes |
| `GET .../edges` (raw) | No (401) | No (403) | Yes |
| `GET .../edges` with `status=asserted\|published\|rejected\|deprecated` | No | No | Yes |
| Review / publish / reject edge | No | No | Yes |
| `POST .../projections/sync` (scoped) | No | No | Yes |
| Enqueue full-catalog projection job | No | No | Yes |
| `GET` projection job status | No | No | Yes |
| Property dictionary / Facts admin CRUD | No | No | Yes (when tables exist) |
| Public Facts (customer-facing) | Published Facts only | Published Facts only | Yes |

---

## 2. Publication semantics

Statuses remain the Accepted vocabulary: **`asserted` \| `published` \| `rejected` \| `deprecated`** (SPEC-knowledge-graph-model §7 · `EDGE_STATUSES`).

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
| Steward publish | Super-admin Review API (Prompt **08**) MAY set `published` only when **all** public gates hold at transition time. Projector and reconciliation **MUST NEVER** auto-publish. |
| **Public article edge gates** (all required) | (1) edge `status=published`; (2) article `is_published=true`; (3) article `published_at` is not in the future (server clock UTC); (4) target product is a **public target product** (§2.5) |
| If any gate fails at read time | Omit from public response (do not error the whole PDP knowledge payload) |
| If steward attempts publish while gates fail | `409` with error code `ARTICLE_EDGE_NOT_PUBLISHABLE` and details naming failed gates |

#### 2.4.1 Article edge lifecycle: demotion vs deprecation (MUST)

Exact missing-node versus non-public-node rules for `ARTICLE_EXPLAINS_PRODUCT`:

| Condition | Required edge effect | `invalid_references` |
|-----------|----------------------|----------------------|
| Article **exists**, `is_published=false`, edge was `published` | → `asserted` | no |
| Article **exists**, `published_at` in the future, edge was `published` | → `asserted` | no |
| Target product **exists** but inactive or soft-deleted, edge was `published` | → `asserted` | no |
| Article source row **missing/deleted** | → `deprecated` (MUST NOT remain `asserted` or `published`) | +1 per distinct missing article id (after dedupe) |
| Target product row **missing/deleted** | → `deprecated` (MUST NOT remain `asserted` or `published`) | +1 per distinct missing product id |
| `related_product_ids` no longer contains the target | → `deprecated` | no (stale relation, not invalid id) |

Projector and reconciliation apply these rules. Read-time omission (§2.4) remains defense-in-depth.

**Event logging:** From Prompt **08** onward (when `knowledge_edge_events` exists), every such status change **MUST** append an event (§7.2). Prompt **02** applies the status rules without requiring the events table.

### 2.5 Public target product — single reusable eligibility policy

A product is a **public target product** iff it would be visible on the existing public PDP read path for a non-admin caller:

1. Row exists in `products`.
2. `deleted_at IS NULL` (same as `crud_product.get_product_by_id` / `get_product_by_slug`).
3. `is_active = true` (same as `_guard_inactive_product` for non-admin callers — `app/api/endpoints/product_common.py:20-27`).

**Normative reuse:** Public Product Knowledge queries (§8) **and** projector / reconciliation publication gates **MUST** call **one** shared service or query predicate that encodes the above (extract/reuse the PDP eligibility rule). Duplicating a weaker filter (e.g. ignoring `is_active`, or treating soft-deleted as public) is **forbidden**.

Inactive-but-present products are **non-public**, not invalid references (§4.2).

### 2.6 Normative edge status transition matrix (type-specific)

Actors: **S** = steward via Review API (Prompt **08+**); **P** = projector; **R** = reconciliation; **M** = migration/backfill that changes status.

Steward mutations (**S** columns) are unavailable until Prompt 08. Before Prompt 08, only **P** / **R** / **M** transitions apply.

#### 2.6.1 Shared transitions (all freeze types)

| From → To | S | P | R | M | Notes |
|-----------|---|---|---|---|-------|
| `asserted` → `rejected` | Yes | No | No | No | Steward only; `change_reason` required. |
| `asserted` → `deprecated` | Yes | Yes | Yes | Yes | Stale source, orphan/missing node, or steward deprecate. |
| `published` → `rejected` | Yes | No | No | No | Steward only. |
| `published` → `deprecated` | Yes | Yes | Yes | Yes | Source relation gone / missing node / steward deprecate. |
| `rejected` → `asserted` | Yes (`reopen_asserted`) | **No** | **No** | No | **Rejected freeze.** |
| `rejected` → `published` | No (reopen then publish) | No | No | No | Two-step. |
| `rejected` → `deprecated` | Yes | No | No | No | Steward only; P/R must not. |
| `deprecated` → `rejected` | Yes | No | No | No | Steward only. |

#### 2.6.2 `PRODUCT_BELONGS_TO_CATEGORY` / `PRODUCT_BRANDED_AS`

| From → To | S | P | R | M | Notes |
|-----------|---|---|---|---|-------|
| `asserted` → `published` | Yes (if §2.5 passes) | **Yes iff §2.5 public-product eligibility passes** | **Yes iff §2.5 passes** | No | Commerce auto-publish is P/R-driven when the product is public. |
| `published` → `asserted` | Yes | **Yes — required** when product remains present but becomes non-public (§2.5 fails) | **Yes — required** (same) | Yes | Present inactive/soft-deleted product is demotion, not deprecation. |
| `deprecated` → `asserted` | Yes (`reopen_asserted`) | Yes | Yes | Yes | Revival when source relation returns but product is non-public. |
| `deprecated` → `published` | No (unless steward publish after reopen path) | **Yes** when source relationship exists **and** commerce publication rule / §2.5 passes | **Yes** (same) | No | Direct revival to `published` allowed for category/brand only under those conditions. |

#### 2.6.3 `ARTICLE_EXPLAINS_PRODUCT`

| From → To | S | P | R | M | Notes |
|-----------|---|---|---|---|-------|
| `asserted` → `published` | **Yes only** via Review API when all §2.4 gates pass; else `409 ARTICLE_EDGE_NOT_PUBLISHABLE` | **No** | **No** | No | P/R **MUST NEVER** auto-publish. |
| `published` → `asserted` | Yes | **Yes** per §2.4.1 non-public cases (unpublished / future / inactive target) | **Yes** (same) | Yes | Not used for missing rows — those deprecate. |
| `deprecated` → `asserted` | Yes (`reopen_asserted`) | Yes | Yes | Yes | Revival when id reappears in `related_product_ids`; always `asserted` (never auto-publish). |
| `deprecated` → `published` | No (must revive/assert then steward publish) | **No** | **No** | No | Articles never auto-publish from P/R. |

Any transition not listed is **`409 INVALID_STATUS_TRANSITION`**. From Prompt **08** onward, every successful transition **MUST** append a `knowledge_edge_events` row (§7.2).

### 2.7 Rejected & deprecated (summary)

- `rejected`: steward decision; retained for audit; never public; projection and reconciliation MUST NOT overwrite without steward `reopen_asserted`.
- `deprecated`: reconciliation/lifecycle; never public; soft state — rows are not hard-deleted by projection.

---

## 3. Endpoint plan, schemas, deprecation, errors

### 3.1 Backward-compatible plan

| Phase | Behavior |
|-------|----------|
| **T0 (as-built)** | `GET /edges`, `GET /products/{id}/neighborhood`, `POST /projections/sync` |
| **T1a (Prompt 01)** | Lock raw `/edges` to super-admin; strip anonymous full-row access. Public PKE DTO **not** required in this commit. |
| **T1b (Prompt 02)** | Public query paths published-only; type-specific publication gates; deterministic demotion/deprecation (§2.4.1); rejected-edge protection. **No** steward Review API. |
| **T1c (Prompt 03)** | Add public PKE read-model; keep neighborhood path but change its **response schema and visibility**. |
| **T2 (compatibility window)** | Documented period (default **30 days** after T1c merge to `main`, or until owner shortens) during which clients MUST migrate |
| **T3** | Remove legacy public field shapes only after Storefront + Admin consumers updated |

### 3.2 Endpoint inventory (target)

#### Admin — raw edges

```http
GET /api/v1/knowledge/edges
```

Query (preserve + extend): `edge_type`, `from_type`, `from_id`, `to_type`, `to_id`, `status` (`asserted` \| `published` \| `rejected` \| `deprecated`), `skip`, `limit` (1–500).
Response: `KnowledgeEdgeListResponse` (full rows + later provenance extensions).
Auth: super-admin (§1.3).

#### Admin — review actions (backend: Prompt **08**; Admin UI: Prompt **10**)

```http
POST /api/v1/knowledge/edges/{edge_id}/review
```

**Timing (normative — resolves Review / provenance / events contradiction):**

| Surface | Prompt | Notes |
|---------|--------|-------|
| Publication visibility, gates, demotion, rejected freeze | **02** | Status rules only. **No** steward mutations. **No** Review API. |
| Edge provenance/review columns + `knowledge_edge_events` + backend Review API + status-transition service + audit/event tests | **08** | First moment steward publish/reject/reopen/deprecate is supported. |
| Admin stewardship UI, resolved labels, filters, event-history presentation | **10** | UI only; consumes Prompt 08 APIs/tables. |

Between Prompt 02 and Prompt 08, stewards have **no** supported mutation API — only projector/reconcile system transitions. That limitation is **documented and intentional**. After Prompt 08 and before Prompt 10, review is **API-only**.

Body:

```json
{
  "action": "publish" | "reject" | "reopen_asserted" | "deprecate",
  "change_reason": "string (required, min 3 chars)"
}
```

Effects: status transition per §2.6; write review metadata (§7); append event (§7.2).
Errors: `404 EDGE_NOT_FOUND`, `409 INVALID_STATUS_TRANSITION`, `409 ARTICLE_EDGE_NOT_PUBLISHABLE`, `422` validation.

#### Public — Product Knowledge read-model (Prompt 03; preferred Storefront contract)

```http
GET /api/v1/knowledge/products/{product_id}/knowledge
```

Auth: public.
`product_id` = commerce `products.id` (ADR-014).
Response: `PublicProductKnowledgeResponse` (§8).
If product is not a public target product: `404 PRODUCT_NOT_FOUND` (align with products public GET / `_guard_inactive_product`).

#### Legacy neighborhood (compat — Prompt 03)

```http
GET /api/v1/knowledge/products/{product_id}/neighborhood
```

| Rule | Norm |
|------|------|
| Auth | Remains public |
| Visibility | **Published-only** (no `asserted`, no `rejected`, no `deprecated`) |
| Schema | **MUST NOT** return admin fields (`recorder`, `source_*`, etc.) |
| Shape | Prefer embedding the same resolved objects as §8 (`category`, `brand`, `articles`) rather than raw edge rows |
| Deprecation | Response header `Deprecation: true` + `Link` to `/knowledge` successor; OpenAPI mark deprecated; remove after compatibility window |

Breaking change note: removing `asserted` articles from neighborhood **is intentional**. Tests that expected asserted articles on public neighborhood MUST be rewritten to admin or publish-path tests.

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

#### Projection jobs (admin)

```http
GET /api/v1/knowledge/projections/jobs/{job_id}
GET /api/v1/knowledge/projections/jobs?status=&skip=&limit=
POST /api/v1/knowledge/projections/jobs/{job_id}/cancel
```

Cancel semantics: §5.3.1. Auth: super-admin (§1.3). `job_id` is UUID (§5.2).
### 3.3 Sync scope semantics (normative — no ambiguity)

Definitions:

- **Null** = JSON `null` / omitted-as-null for that field.
- **Empty array** = `[]` (zero-length list). Empty arrays **MUST NEVER** mean full catalog.

#### 3.3.1 Full catalog

Full catalog is represented **only** by:

```text
mode=enqueue, product_ids=null, article_ids=null
```

Any other combination is **not** full catalog.

#### 3.3.2 Decision table

| `mode` | `product_ids` | `article_ids` | Result |
|--------|---------------|---------------|--------|
| `enqueue` | `null` | `null` | **Full catalog** job; `202` + `job_id` |
| `inline` | `null` | `null` | **`413` `SYNC_SCOPE_TOO_LARGE`** — MUST NOT run full catalog inline |
| `inline` or `enqueue` | `[]` | any | **`422` `EMPTY_SYNC_SCOPE`** |
| `inline` or `enqueue` | any | `[]` | **`422` `EMPTY_SYNC_SCOPE`** |
| `inline` or `enqueue` | `[]` | `[]` | **`422` `EMPTY_SYNC_SCOPE`** |
| `inline` | non-empty list (≤500) | `null` | **Product-scoped inline:** project category/brand edges for those products only; **do not** scan all articles |
| `inline` | `null` | non-empty list (≤200) | **Article-scoped inline:** project `ARTICLE_EXPLAINS_PRODUCT` for those articles only |
| `inline` | non-empty (≤500) | non-empty (≤200) | **Union scope:** both product commerce edges and listed articles |
| `enqueue` | non-empty | `null` | Enqueue product-scoped job (same scan rules as inline product-scoped) |
| `enqueue` | `null` | non-empty | Enqueue article-scoped job |
| `enqueue` | non-empty | non-empty | Enqueue union-scoped job |
| `inline` | list length > 500 products or > 200 articles | — | **`413` `SYNC_SCOPE_TOO_LARGE`** |

**Chosen empty-array behavior:** `422 EMPTY_SYNC_SCOPE` (deterministic rejection). A silent no-op is **forbidden**.

**Mixed-scope note:** `product_ids=[1], article_ids=null` does **not** imply scanning every article that mentions product 1. Article edges for product 1 are updated only when those articles are included via `article_ids`, via full-catalog, or via reconciliation that walks existing `ARTICLE_EXPLAINS_PRODUCT` edges for demotion/orphan checks in scope.

As-built “empty / null = sync all inline” is **retired**.

### 3.4 Response schemas (normative shapes)

#### Admin `KnowledgeEdgeResponse` (extend; admin-only)

Retain fields: `id`, `edge_type`, `from_node_type`, `from_node_id`, `to_node_type`, `to_node_id`, `status`, `source_kind`, `source_ref`, `recorded_at`, `recorder`, `confidence`, `attributes`.

Add (Prompt **08** provenance + Review API wave):

| Field | Type | Meaning |
|-------|------|---------|
| `projection_run_id` | UUID string \| null | Nullable FK → `knowledge_projection_jobs.id` (`ON DELETE SET NULL`). Admin may serialize as string. Public DTOs **never** expose it. |
| `first_seen_at` | datetime | First insert time (immutable after backfill) |
| `last_verified_at` | datetime | Last successful reconcile/verify |
| `source_artifact` | string \| null | Artifact id/path/version |
| `source_version` | string \| null | Version pin |
| `reviewed_by` | string \| null | Steward user id of last review action; null if never reviewed by a human |
| `last_actor` | string | Last actor that changed status or governed content: steward user id **or** system actor id (§7.2) |
| `last_review_action` | string \| null | Last steward review **action** (`publish` \| `reject` \| `reopen_asserted` \| `deprecate`); **not** a duplicate of `edge.status` |
| `reviewed_at` | datetime \| null | Timestamp of last steward review action |
| `change_reason` | string \| null | Last steward reason |
| `from_label` / `to_label` | string \| null | Resolved node labels for admin UI |

**Naming ban:** A generic field named `actor` or `review_status` that could be confused with `edge.status` MUST NOT be introduced. Use `reviewed_by`, `last_actor`, and `last_review_action` as above.

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

### 3.5 Error behavior

| Code | HTTP | When |
|------|------|------|
| `INVALID_EDGE_TYPE` | 422 | Unknown `edge_type` filter (preserve) |
| `EDGE_NOT_FOUND` | 404 | Review target missing |
| `INVALID_STATUS_TRANSITION` | 409 | Illegal status change (§2.6) |
| `ARTICLE_EDGE_NOT_PUBLISHABLE` | 409 | Publish gates fail |
| `SYNC_SCOPE_TOO_LARGE` | 413 | Inline sync is unbounded (`null`/`null`) or exceeds numeric limits |
| `EMPTY_SYNC_SCOPE` | 422 | One or both scope arrays are `[]` |
| `PROJECTION_JOB_IN_PROGRESS` | 409 | Active full-catalog job already queued/running (§5.5) |
| `INVALID_JOB_TRANSITION` | 409 | Cancel (or other job mutation) illegal for current job status (§5.3.1) |
| `PRODUCT_NOT_FOUND` | 404 | Public knowledge for non-public product |
| `UNAUTHORIZED` | 401 | Missing / invalid / expired / revoked credentials |
| `FORBIDDEN` | 403 | Authenticated non-super-admin (or inactive user) |

All errors continue to use the platform `api_error` envelope (`error_code`, `message`, `details`) — `docs/API_CONTRACT.md` error envelope.

---

## 4. Orphan, invalid-reference, source-deletion, reconciliation

### 4.1 Orphan policy

An edge is **orphan** when either endpoint node is **missing** from SoR (`products` / `categories` / `brands` / `articles`).

| Action | Norm |
|--------|------|
| Detection | Reconciliation pass (§4.4) and projection-time checks |
| Treatment | Set `status=deprecated` (MUST NOT leave the edge `asserted` or `published`); increment `invalid_references` per §4.2; do **not** hard-delete |
| Public | Orphans never appear |

Present-but-non-public nodes (inactive / unpublished / future-dated) are **not** orphans — see §2.4.1 and §4.2.

### 4.2 Invalid-reference policy (exact)

| Case | Classification | Projection / counter behavior |
|------|----------------|-------------------------------|
| Source or target **row missing/deleted** | **Invalid reference** | Deprecate edge; MUST NOT remain `asserted`/`published`; `invalid_references += 1` **per distinct missing id after dedupe** |
| Product row **present** but inactive or soft-deleted | **Non-public** (not invalid) | Do not count `invalid_references`; demote `published` → `asserted` for affected edges (§2.4.1 / §2.6.2) |
| Article row **present** but unpublished or future-dated | **Non-public article** (not invalid) | Do not count `invalid_references`; demote `published` → `asserted` (§2.4.1) |
| `related_product_ids` value is **non-integer** (wrong JSON type / non-coercible) | **Invalid reference** | Skip that entry; `invalid_references += 1` per distinct bad value after dedupe |
| Duplicate IDs in `related_product_ids` (or duplicate invalid values) | Deduplicate first | Duplicates are **not** multiple invalid references; count once |
| `category_id` / `brand_id` points to missing category/brand | **Invalid reference** | Deprecate prior edge; `invalid_references += 1` |
| Id removed from `related_product_ids` while both rows still exist | Stale relation (not invalid id) | Deprecate corresponding edge; do **not** increment `invalid_references` |

**Counter exactness:** `invalid_references` counts distinct invalid reference tokens encountered in the run/scope after dedupe within that entity’s source list — not per duplicate occurrence, and not for inactive/unpublished-but-present nodes.

### 4.3 Source deletion policy

| Source change | Edge effect |
|---------------|-------------|
| Product soft-deleted / deactivated (row still present) | Category & brand: `published` → `asserted` (§2.6.2); article edges targeting it: `published` → `asserted` (§2.4.1); never public |
| Product hard-removed / row missing | All edges referencing it → `deprecated` + `invalid_references` per §4.2 |
| `category_id` / `brand_id` cleared or changed | Stale targets deprecated via `_deprecate_stale` semantics (preserve) |
| Article unpublished or future-dated (row present) | If `published` → `asserted` (§2.4.1) |
| Article deleted / missing | → `deprecated` + `invalid_references` (§2.4.1); MUST NOT remain `asserted` |
| Id removed from `related_product_ids` | Corresponding edge → `deprecated` |

**Hard delete of edge rows:** Forbidden in wave remediation except via explicit future Board-approved purge job with backup.

### 4.4 Global reconciliation rule

A **reconcile** pass MUST be runnable from CLI (and optionally enqueueable) and MUST:

1. Scan all `knowledge_edges` of KB-001 freeze types (later: all registered types).
2. Verify endpoint existence and type/direction registry compliance.
3. Align category/brand edges with current `products.category_id` / `brand_id`.
4. Align article edges with current `related_product_ids`.
5. Apply §2.4.1 / §2.6 demotion and deprecation rules (missing → deprecated; non-public present → asserted).
6. Emit the same counter schema as sync (§6).
7. Be **idempotent**: second reconcile without SoR changes ⇒ `unchanged` dominates; no flip-flop.
8. From Prompt **08** onward, append `knowledge_edge_events` for every status change (§7.2). Prompt **04** may ship reconcile logic that changes status before the events table exists; Prompt **08** adds mandatory event emission to that path.

Projection sync for a scope **implies** scoped reconciliation for that scope. Full reconcile = full-catalog job.

---

## 5. Projection execution model

### 5.1 Scoped HTTP sync limits

| Parameter | Limit (initial) |
|-----------|-----------------|
| Max `product_ids` in inline sync | **500** |
| Max `article_ids` in inline sync | **200** |
| Max runtime budget inline | **30s** target (§11.6 — non-blocking) |
| Full catalog / null scopes | **enqueue only** (`mode=enqueue`, both null) |

ADR-012 Category A local enrichment remains binding: sync endpoints MUST NOT target production remote APIs.

### 5.2 Durable PostgreSQL job rows

Introduce `knowledge_projection_jobs` (name normative for Prompt 05 / Alembic **A1**):

| Column | Meaning |
|--------|---------|
| `id` | **UUID primary key** (not BIGSERIAL) |
| `status` | `queued` \| `running` \| `succeeded` \| `succeeded_with_errors` \| `failed` \| `cancelled` |
| `scope` | JSONB: `{ "product_ids": <list\|null>, "article_ids": <list\|null> }` |
| `is_full_catalog` | Boolean **integrity-protected** (§5.5.1): true **iff** both scope id lists are null |
| `cancel_requested_at` | timestamptz \| null — set when cancel accepted on a `running` job |
| `counters` | JSON matching §6 |
| `attempt` | Retry count |
| `locked_by` | Worker id |
| `locked_at` | Lease timestamp |
| `checkpoint` | JSON: last product_id / article_id processed |
| `error` | Last failure message |
| `created_at` / `started_at` / `finished_at` | Timestamps |
| `created_by` | Actor (steward user id or system) |

**`knowledge_edges.projection_run_id`:** nullable UUID column, **FOREIGN KEY** → `knowledge_projection_jobs.id` with **`ON DELETE SET NULL`**. Public DTOs never expose it. Admin schemas MAY serialize the UUID as a string.

### 5.3 Job completion semantics (terminal statuses)

| Terminal status | When | Client `GET .../jobs/{id}` receives |
|-----------------|------|-------------------------------------|
| `succeeded` | Worker finished entire scope; `failed == 0` | Final counters; `finished_at`; `error=null`; `cancel_requested_at` ignored/null |
| `succeeded_with_errors` | Worker finished entire scope; `failed > 0` | Final counters including `failed`; `finished_at`; optional summary in `error` |
| `failed` | Retry exhausted (§5.4) **or** unrecoverable abort before scope completion | Counters reflecting partial progress; `checkpoint` preserved; `error` set |
| `cancelled` | Cancel completed for a formerly `queued`/`running` job (§5.3.1) | Counters/checkpoint at cancel time; `finished_at` set |

**Normative choice:** `failed > 0` after a **complete** scan does **not** force `failed`; it yields **`succeeded_with_errors`**. Status `failed` is reserved for jobs that did not finish the scope (or exhausted retries while still incomplete).

#### 5.3.1 Job cancellation (Wave-1 — `cancelled` is live)

```http
POST /api/v1/knowledge/projections/jobs/{job_id}/cancel
```

| Rule | Norm |
|------|------|
| Auth | Super-admin only (§1.3) |
| `queued` | Transition immediately to `cancelled`; set `finished_at`; clear lease fields; worker MUST NOT claim it |
| `running` | Set `cancel_requested_at = now()`; leave status `running` until worker stops; worker MUST check the flag at each **batch boundary**, then transition to `cancelled`, persist counters/checkpoint, set `finished_at` |
| `succeeded` / `succeeded_with_errors` / `failed` / `cancelled` | **`409 INVALID_JOB_TRANSITION`** — cancel is illegal |
| Client polling | After accepting cancel on `running`, clients continue `GET .../jobs/{id}` until terminal `cancelled` (or another terminal if the job finished the last batch first — if the worker completes the scope in the same batch where cancel was noticed after work, prefer `cancelled` only if cancel was observed before committing the final batch; if final batch already committed as success, return `409` on a late cancel) |
| Late race | If the job reaches `succeeded` / `succeeded_with_errors` / `failed` between cancel request and worker observation, cancel API returns **`409 INVALID_JOB_TRANSITION`** |

### 5.4 CLI worker — retry, checkpoint, reclaim

- Entry: `python -m app...` or `scripts/knowledge_projection_worker.py` (exact path chosen in Prompt 06; layer: script → service → crud → models).
- Polls `queued` jobs; claims with row lock / `FOR UPDATE SKIP LOCKED`.
- Processes in **batches** (default **100** products, **50** articles).
- At each batch boundary, if `cancel_requested_at IS NOT NULL`, stop and finalize as `cancelled` (§5.3.1).
- Writes **checkpoints** after each batch commit. On crash/retry, resume **after** the checkpoint (do not re-count already committed entities as new creates; idempotent upsert + counter rules §6).
- **Retry:** transient DB errors → exponential backoff; max attempts **5**; then terminal `failed` with checkpoint retained for diagnosis / manual re-enqueue.
- **Locking:** lease TTL **15 minutes**; expired lease reclaimable (status may return to `queued` with `attempt++`, or another worker may take over). Reclaim MUST preserve `cancel_requested_at` if set.
- **Idempotency:** job re-run safe via edge identity unique key (`uq_knowledge_edges_identity`) + counter semantics (§6).

### 5.5 Full-sync concurrency mechanism (concrete)

#### 5.5.1 `is_full_catalog` integrity

**Chosen form:** ordinary Boolean column plus CHECK constraint (generated stored column is an acceptable equivalent if the database edition supports it):

```text
CHECK (
  (is_full_catalog = true  AND scope->>'product_ids' IS NULL AND scope->>'article_ids' IS NULL)
  OR
  (is_full_catalog = false AND NOT (
      scope->>'product_ids' IS NULL AND scope->>'article_ids' IS NULL
  ))
)
```

Writers (enqueue API / worker) MUST set `is_full_catalog` consistently with scope. The CHECK makes illegal combinations impossible. The partial unique index **MUST** use this integrity-protected column (not an unconstrained expression that can drift).

#### 5.5.2 Partial unique index

```text
UNIQUE INDEX uq_knowledge_projection_jobs_active_full
  ON knowledge_projection_jobs (is_full_catalog)
  WHERE is_full_catalog = true
    AND status IN ('queued', 'running')
```

| Scenario | Behavior |
|----------|----------|
| Second full-catalog enqueue while one is `queued`/`running` | DB unique violation → API **`409 PROJECTION_JOB_IN_PROGRESS`** |
| Overlapping **scoped** jobs (non-full) | **Allowed** concurrently with each other |
| Scoped job while full-catalog runs | **Allowed**; edge upserts rely on row identity + transactions. Operators SHOULD prefer waiting for full sync when practical; the contract does not block scoped jobs. |
| Stale `running` full-catalog (dead worker) | Lease reclaim (§5.4) must move the job to `failed` or re-queue before a new full-catalog enqueue can succeed |

Advisory locks are **not** the primary exclusivity mechanism (optional belt-and-suspenders inside the worker only; the partial unique index is authoritative for HTTP enqueue).

### 5.6 HTTP vs worker responsibilities

| Concern | HTTP API | Worker |
|---------|----------|--------|
| AuthZ | Super-admin (§1.3) | Process identity |
| Scoped inline sync | Yes (within limits) | Optional |
| Full sync | Enqueue only | Execute |
| Cancel | Accept cancel / set `cancel_requested_at` | Honor at batch boundary |
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
| **invalid_references** | Source references missing/invalid node (§4.2) | `invalid_references++` |
| **failed** | Unexpected exception for one entity; job continues when possible | `failed++` |

**Remediation delta:** As-built always returns `True` for updates and folds create+update into `edges_upserted`. That MUST be replaced by the counters above.

### 6.3 Scan counters

- `products_scanned`: products loaded for the run/scope.
- `articles_scanned`: articles loaded for the run/scope.

### 6.4 Idempotency acceptance

Two consecutive identical scoped syncs MUST yield `created=0`, `updated=0`, `deprecated=0` (barring clock-driven publication demotion), with `unchanged ≥ 0` and stable edge counts.

---

## 7. Minimum provenance model & event log

### 7.1 Edge provenance columns

Every knowledge edge (and later Fact) MUST support:

| Field | Required | Notes |
|-------|----------|-------|
| `projection_run_id` | nullable UUID FK | Set on projection touch when a job id exists; FK → `knowledge_projection_jobs.id` ON DELETE SET NULL; see §11.2 |
| `first_seen_at` | Yes after backfill + NOT NULL | Set once on insert / backfill |
| `last_verified_at` | Yes after backfill + NOT NULL | Set on verify/reconcile/projection touch |
| `source_kind` | Yes | Preserve (`projection`, `cms`, `manual`, …) |
| `source_ref` | SHOULD | e.g. `products.category_id` |
| `source_artifact` | MAY | AODS artifact id / checksum |
| `source_version` | MAY | Artifact/version pin |
| `recorder` | Yes | System projector id or user id of original write |
| `reviewed_by` | null until steward review | Human steward user id only |
| `last_actor` | Yes after first post-migration write | Steward user id **or** system actor (§7.2) |
| `last_review_action` | null until steward review | Action enum — **not** `edge.status` |
| `reviewed_at` | null until steward review | |
| `change_reason` | Yes on steward mutation | Mandatory on review API |
| `recorded_at` | Yes | Last content write stamp |

Public DTOs **omit** all of the above.

### 7.2 `knowledge_edge_events` — mandatory on every status transition (from Prompt 08)

Table (Prompt **08** / Alembic **A2**, same wave as provenance columns + Review API): append-only history.

| Column | Meaning |
|--------|---------|
| `id` | Event id |
| `edge_id` | FK to `knowledge_edges.id` |
| `at` | Timestamp |
| `actor_kind` | `human` \| `system` |
| `actor_id` | Steward user id **or** system actor id |
| `from_status` | Prior status (`asserted` \| `published` \| `rejected` \| `deprecated`) |
| `to_status` | New status (`asserted` \| `published` \| `rejected` \| `deprecated`) |
| `reason` | Steward `change_reason` or system reason code |
| `payload` | JSON optional (job_id, gates failed, migration id, …) |

**MUST log** (once the table exists — Prompt 08+) transitions made by:

1. Stewards (Review API),
2. Projector,
3. Reconciliation,
4. Migrations/backfills **when they change `status`**.

Prompt **02** / **04** status changes that land before Prompt 08 do not require historical backfill of events unless a later approved task demands it.
#### System actor representation

| Actor | `actor_kind` | `actor_id` (normative strings) |
|-------|--------------|--------------------------------|
| HTTP projection inline | `system` | `system:projector:http` |
| CLI/worker projection | `system` | `system:projector:worker` |
| Reconciliation | `system` | `system:reconcile` |
| Migration/backfill | `system` | `system:migration:<revision_id>` |
| Steward | `human` | string form of user id |

Human identity MUST NOT be written into `actor_id` for system actions. Conversely, system actor ids MUST NOT be stored in `reviewed_by` (humans only).

---

## 8. Public Product Knowledge read-model (Storefront)

### 8.1 Endpoint

`GET /api/v1/knowledge/products/{product_id}/knowledge` → `PublicProductKnowledgeResponse` (Prompt 03).

Eligibility: §2.5 shared predicate. Non-public ⇒ `404 PRODUCT_NOT_FOUND`.

### 8.2 Schema — verified against current models

Runtime sources (do not invent columns):

| DTO field | Source model | Column / note |
|-----------|--------------|---------------|
| `product_id` | `Product` | `products.id` (ADR-014) |
| `category.id` | `Category` | `categories.id` |
| `category.slug` | `Category` | `categories.slug` |
| `category.name` | `Category` | `categories.name` |
| `brand.id` | `Brand` | `brands.id` |
| `brand.slug` | `Brand` | `brands.slug` |
| `brand.name` | `Brand` | `brands.name` |
| `articles[].id` | `Article` | `articles.id` |
| `articles[].slug` | `Article` | `articles.slug` |
| `articles[].title` | `Article` | `articles.title` |
| `articles[].excerpt` | `Article` | `articles.excerpt` |
| `articles[].cover_image` | `Article` | `articles.cover_image` (**nullable**) |
| `articles[].published_at` | `Article` | `articles.published_at` |
| `articles[].reading_minutes` | `Article` | `articles.reading_minutes` |
| `articles[].tags` | `Article` | `articles.tags` (JSONB list) |
| `*.edge_type` | edge row | constant per relation |

All fields above exist on current models (`app/db/models/content.py:31-45`, `app/db/models/product.py:72-124`). No deferred invented columns in this DTO. Fields absent from models (e.g. article `author` on the public rail) are **omitted** from the public knowledge contract unless a later approved task adds them.

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
- `articles` only edges passing §2.4 gates; ordered stably (`published_at DESC`, then `id`).
- No raw edge ids required on public DTO (default **omit**).
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

| Capability | Norm | Prompt |
|------------|------|--------|
| Pagination | `skip`/`limit` with `total` (preserve) | 01/10 |
| Status filters | All four: `asserted` \| `published` \| `rejected` \| `deprecated` + “active”=`asserted\|published` | 10 |
| Type filters | KB-001 types; later registry types | 01/10 |
| Resolved node labels | `from_label` / `to_label` (§3.4) | 10 |
| Evidence / provenance display | Show §7 fields on detail view | 10 |
| Review actions (API) | publish / reject / reopen_asserted / deprecate with `change_reason` | **08** |
| Review actions (Admin UI) | Same actions in browser | **10** |
| Event history presentation | Read `knowledge_edge_events` in Admin UI | **10** |
| `knowledge_edge_events` table + emission | Append-only log on every status transition | **08** |

Read-only Day-5 browser is the baseline; remediation extends it — does not remove FA labels or freeze-type discipline.

---

## 10. Runtime property dictionary, units, Facts, evidence, taxonomy

### 10.0 Product Type precondition (normative — KB-PT-00 / 00A)

Runtime Property Dictionary / Facts work in this section **MUST NOT** introduce Category-owned future templates as the permanent applicability owner. Applicability, requiredness, and validation ownership ultimately derive from **Product Type Definition** (`SPEC-canonical-product-type-model.md`) after PT-W2.

Corrected insertion order (§12.1 / SPEC-canonical §15):

1. Board clarification minute (hard gate before KB-PT-01)
2. PT-W1 Product Type core + nullable FK
3. **Prompt 11A** Property Definitions + aliases + Units
4. **PT-W2** Product Type Definitions + Attribute Memberships
5. Prompts 12–13 (Facts; Evidence + taxonomy)

### 10.1 Scope

Runtime tables for Prompt **11A** and later remain Postgres overlay tables (ADR-013). Git seeds (`docs/architecture/specs/seeds/…`) stay authoring SoT until import tasks load them.

### 10.2 Property dictionary (runtime) — Prompt 11A scope

**Prompt 11A MUST create only:**

| Table | In 11A? |
|-------|---------|
| `knowledge_property_definitions` | **Yes** |
| `knowledge_property_aliases` | **Yes** |
| `knowledge_units` | **Yes** (see §10.3) |
| `knowledge_spec_templates` | **No** — forbidden as Prompt 11A / Category-owned permanent deliverable |
| `knowledge_template_properties` | **No** — forbidden as Prompt 11A / Category-owned permanent deliverable |

Fields for definitions/aliases follow SPEC-property-dictionary-system §3–§4. Status: `draft|active|deprecated`.

Product Type Definition and Attribute Membership tables belong to **PT-W2** after Property Definitions exist — not to Prompt 11A.

### 10.3 Units

Table `knowledge_units`: dimension, canonical code, aliases, conversion table version pin. Facts store canonical units only.

### 10.4 Facts & revisions

| Entity | Norm |
|--------|------|
| `knowledge_facts` | `fact_id`, `entity_id=products.id`, `definition_id`, `value` JSONB, `unit`, `qualifier`, `status` (`asserted` \| `published` \| `rejected` \| `deprecated`), provenance |
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

## 11. Migration sequence, backfill, compatibility, matrices, budgets

### 11.1 Implementation waves vs Alembic migrations

Do **not** number code-only steps as Alembic migrations. Two label spaces:

**Implementation waves (W)** — prompt delivery order (code and/or DDL):

| Wave | Prompt(s) | Deliverable |
|------|-----------|-------------|
| W1 | 01 | AuthZ on `/edges` |
| W2 | 02 | Publication visibility, gates, demotion/deprecation, rejected freeze (**no** Review API) |
| W3 | 03 | Public PKE DTO + neighborhood deprecation shape |
| W4 | 04 | Orphan/reconcile service rules (status changes; events deferred to A2) |
| W5 | 05 | Jobs enqueue API + **Alembic A1** |
| W6 | 06–07 | Worker runtime + counters (code only) |
| W7 | 08 | Provenance columns + `knowledge_edge_events` + Review API + transition service + tests — **Alembic A2** |
| W8 | 09 | Storefront PKE consumption |
| W9 | 10 | Admin stewardship UI only (labels, filters, review UI, event history presentation) |
| **Board clarification** | — | Architecture Board minute (or equivalent Canon amendment) for Hybrid primary FK vs `PRODUCT_CLASSIFIED_AS` — **hard gate before KB-PT-01** |
| **PT-W1** | **KB-PT-01** | Product Type core table + nullable `products.product_type_id` only (no seed, no readout, no membership) |
| **W10 / 11A** | **11A** | Property definitions + aliases + units — **Alembic A3** — **no** `knowledge_spec_templates` / `knowledge_template_properties` |
| **PT-W2** | **KB-PT-02** (name indicative) | Product Type Definitions + Attribute Memberships (requires 11A) |
| **PT-W3…PT-W4** | KB-PT follow-ons | Assignment/ambiguity; read-only JSONB validation |
| W11 | 12 | Facts + revisions — **Alembic A4** — blocked until PT-W2 ownership approved (§12.1) |
| W12 | 13 | Evidence + taxonomy + classification — **Alembic A5** — blocked until PT-W2 ownership approved; Product Type primary; CLASSIFIED_AS secondary |
| W13 | 14 | Hardening / evidence pack |

**Alembic revisions (A)** — DDL only, in this exact order:

| Alembic | Prompt | Change | Rollback |
|---------|--------|--------|----------|
| **A1** | 05 | `knowledge_projection_jobs` (UUID PK, `is_full_catalog` CHECK, partial unique active-full index, `cancel_requested_at`) | Drop table / index |
| **A2** | 08 | Provenance columns on `knowledge_edges` (§11.2) + FK `projection_run_id` → jobs + `knowledge_edge_events` | Downgrade per §11.2; drop events |
| **A3** | **11A** | Property definitions + aliases + units tables **only** (after PT-W1 merged + §12.1 Prompt 11A gate) | Drop those tables; Git seeds remain |
| **A4** | 12 | Facts + revisions (after PT-W2 Definition/membership ownership approved) | Drop tables |
| **A5** | 13 | Evidence artifacts/links; taxonomy nodes + classification assignments | Drop tables; never drop `categories` |

**Product Type Alembic (PT):** PT-W1 (`product_types` + nullable FK) MUST land **before** A3. PT-W2 (Definition/membership) MUST land **after** A3 / 11A and **before** A4. Exact PT revision IDs are owned by KB-PT implementation prompts — not invented here.

**Ordering reason:** Jobs (**A1**) before provenance FK (**A2**). Review API, provenance columns, and events land together in Prompt **08** / **A2**. Admin UI (Prompt 10) has no DDL. **Board clarification → PT-W1 → 11A (A3) → PT-W2 → 12 (A4) → 13 (A5)** so membership never precedes Property Definitions and templates are not Category-owned by default.

Each Alembic revision MUST be alone-reviewable; no big-bang.

### 11.2 Provenance backfill policy (existing `knowledge_edges`)

| Phase | Rule |
|-------|------|
| **Add columns** | Add as **nullable** first (`projection_run_id` UUID FK → `knowledge_projection_jobs.id` ON DELETE SET NULL, `first_seen_at`, `last_verified_at`, `source_artifact`, `source_version`, `reviewed_by`, `last_actor`, `last_review_action`, `reviewed_at`, `change_reason`). Requires **A1** already applied. |
| **`first_seen_at` backfill** | `UPDATE knowledge_edges SET first_seen_at = recorded_at WHERE first_seen_at IS NULL` (deterministic). |
| **`last_verified_at` backfill** | `UPDATE knowledge_edges SET last_verified_at = recorded_at WHERE last_verified_at IS NULL` (deterministic). |
| **`projection_run_id` legacy** | Leave **NULL** for pre-job rows. Do **not** invent synthetic UUIDs. Next projection/reconcile touch sets a real job id. |
| **`last_actor` backfill** | Set `last_actor = recorder` where null (system or historical recorder string). |
| **Review fields** | Leave `reviewed_by`, `last_review_action`, `reviewed_at`, `change_reason` NULL until a steward review occurs. |
| **NOT NULL** | Apply `NOT NULL` on `first_seen_at` and `last_verified_at` only **after** backfill completes in the same or immediately subsequent revision, with a verified row count check. Other new provenance columns remain nullable. |
| **Status-changing backfill** | If a migration changes `status`, it MUST insert `knowledge_edge_events` rows with `actor_kind=system` and `actor_id=system:migration:<revision_id>` (A2+). Prefer not to change status in the provenance migration. |
| **Downgrade** | Downgrade drops the new columns/constraints/tables added by that revision. Data in dropped columns is lost (acceptable for overlay provenance). Downgrade MUST NOT delete commerce SoR rows. |

### 11.3 Compatibility period

- Neighborhood schema change: **30 days** deprecation headers (starts at Prompt 03 merge).
- `edges_upserted` alias: same window.
- Admin clients must send auth on `/edges` immediately at Prompt 01 (breaking for anonymous — security exception; no grace for anonymous raw listing).

### 11.4 Security matrix

See §1.5. Additional:

| Control | Norm |
|---------|------|
| Publication filter bypass | Forbidden in public services |
| IDOR on admin edge review | `edge_id` must exist; no cross-tenant issues (single-tenant app) |
| Job enqueue flood | Rate-limit / single active full-sync via §5.5 |

### 11.5 Test matrix (minimum)

| Area | Required tests |
|------|----------------|
| AuthZ | Missing/invalid → 401; authenticated non-admin → 403; super-admin OK |
| Publication | Asserted/rejected/deprecated edges absent from public knowledge |
| Article gates | Unpublished / future `published_at` / inactive product → demote to asserted; missing article/product → deprecate + invalid_references |
| Sync limits | Inline null/null → `SYNC_SCOPE_TOO_LARGE`; `[]` → `EMPTY_SYNC_SCOPE`; enqueue null/null → 202 |
| Counters | create/update/unchanged/deprecate/invalid/failed correctness + idempotency; inactive ≠ invalid |
| Orphans | Missing category/brand/product/article → deprecate + invalid_references; MUST NOT remain asserted |
| Rejected freeze | Projection does not clobber `rejected` without reopen |
| Job terminals | `succeeded` / `succeeded_with_errors` / `failed` / `cancelled` / checkpoint resume |
| Job cancel | queued → cancelled; running → cancel_requested_at then cancelled; terminal → 409 `INVALID_JOB_TRANSITION` |
| Full-sync exclusivity | Second full enqueue → 409 |
| Review API timing | Prompt 08 introduces Review API; Prompt 02 must not expose steward mutations |
| No dual-write | Assert no writer couples JSONB↔Facts |
| Layering | endpoints → services → crud → models |
| Shared eligibility | Public knowledge uses same predicate as PDP |

### 11.6 Observability

Log/metric fields: `job_id`, counters, duration_ms, `failed`, lock contention. Admin job detail view required. No PII beyond steward user ids already used in admin audit.

### 11.7 Performance values (targets / observations — not merge gates)

| Operation | Target / observation |
|-----------|----------------------|
| Public PKE read | p95 ≤ **100 ms** DB time local; ≤ **300 ms** end-to-end staging |
| Inline sync (≤500 products) | ≤ **30 s** |
| Full-catalog job throughput | ≥ **50 products/s** steady-state on staging-class hardware |
| Admin edge list | p95 ≤ **200 ms** for limit=100 |

**Reclassification (normative):** Until a staging hardware profile, dataset size, warm/cold cache policy, and benchmark command are recorded (Prompt 14 evidence pack), these numbers are **targets and observations only**. They are **not** merge-blocking acceptance gates. Prompt 14 may promote specific numbers to gates only after that evidence exists.

### 11.8 Minimum index plan

| Index | Purpose |
|-------|---------|
| Existing `uq_knowledge_edges_identity` | Upsert identity |
| Existing `ix_knowledge_edges_from` / `_to` / `_type_status` / `_active_from` | Edge filters by endpoints/type/status |
| `ix_knowledge_edges_status_type_from` (if not covered): `(status, edge_type, from_node_type, from_node_id)` | Admin status/type/from filters |
| `ix_knowledge_edges_public_product` partial: `(to_node_id)` WHERE `edge_type='ARTICLE_EXPLAINS_PRODUCT' AND status='published'` plus product-side `(from_node_id)` WHERE `edge_type IN ('PRODUCT_BELONGS_TO_CATEGORY','PRODUCT_BRANDED_AS') AND status='published'` | Public product knowledge lookups |
| `ix_knowledge_projection_jobs_claim`: `(status, created_at)` WHERE `status='queued'` | Queued job claiming |
| `uq_knowledge_projection_jobs_active_full` (§5.5) | Active full-sync exclusivity |
| `ix_knowledge_edge_events_edge_at`: `(edge_id, at DESC)` | Event history by edge + time |

Exact DDL names may vary; the access patterns above are mandatory.

---

## 12. Implementation sequence (Prompts 01–14)

This pack’s execution order. Prompt 00 / 00A / 00B / 00C = this contract through owner approval. **KB-PT-00 / KB-PT-00A** amend sequencing for Product Type. Later prompts MUST NOT invent contradictory behavior. Waves **W*** and Alembic **A*** (§11.1) share this order. Prompt numbers **01–14 are not renumbered**; Product Type work is inserted as **KB-PT-*** / **PT-W*** waves. Prompt **11** is scoped as **11A** below without renumbering the pack.

| Prompt | Title | Primary deliverable | Alembic |
|--------|-------|---------------------|---------|
| **01** | Secure API boundary | Admin-only raw `/edges`; 401/403 matrix; authZ tests. **Does not** require public PKE DTO. | — |
| **02** | Publication semantics enforcement | Public queries published-only; type-specific gates; MUST demotion/deprecation (§2.4.1); rejected freeze. **No** Review API / steward mutations. | — |
| **03** | Public & compat endpoint schemas | `GET .../knowledge` DTO; neighborhood deprecation shape; OpenAPI | — |
| **04** | Orphan & reconciliation policies | Invalid-reference / missing vs non-public handling; global reconcile (events deferred to 08) | — |
| **05** | Durable projection jobs | `knowledge_projection_jobs` UUID PK; enqueue; cancel endpoint; inline scope limits; `is_full_catalog` CHECK + unique index | **A1** |
| **06** | Worker runtime | CLI worker, batches, retry, locking, checkpoints, cancel honor, terminal statuses | — |
| **07** | Upsert counters | Real created/updated/unchanged/deprecated/invalid_references/failed | — |
| **08** | Provenance + events + Review API | Provenance columns; `knowledge_edge_events`; backend `POST .../review`; status-transition service; audit/event tests; backfill §11.2 | **A2** |
| **09** | Storefront PKE consumption | Wire `ProductKnowledgeRail` to public read-model; honest empty | — |
| **10** | Admin stewardship UI | Pagination/status filters, resolved labels, evidence display, review UI, event-history presentation (**no** new DDL) | — |
| **Board clarification** | Hybrid vs CLASSIFIED_AS | Architecture Board minute / Canon amendment — **before KB-PT-01** | — |
| **KB-PT-01** | PT-W1 Product Type core | `product_types` + nullable `products.product_type_id` only | **PT-W1** |
| **11A** | Runtime property definitions + aliases + units | Tables + admin read/seed import **without** JSONB dual-write; **no** `knowledge_spec_templates` / `knowledge_template_properties` — **§12.1 Prompt 11A gate** | **A3** |
| **KB-PT-02…** | PT-W2+ | Definitions + Attribute Memberships; then assignment/ambiguity; read-only JSONB validation | **PT-W2…** |
| **12** | Facts + revisions | Fact tables, statuses, revision history, publish gates — **§12.1 Prompt 12/13 gate** | **A4** |
| **13** | Evidence + taxonomy + classification | Artifacts/links; taxonomy nodes; CLASSIFIED_AS (no second Category DAG); Product Type remains primary class (ADR-015 Hybrid) — inherits Prompt 12/13 gate | **A5** |
| **14** | Hardening & matrices | Observability; evidence pack; optional perf gates; security/test matrix closeout | — |

### 12.1 Product Type gates (normative — KB-PT-00A)

Prompts **01–10** MAY remain executable when they do not depend on Product Type and MUST NOT silently introduce Category-owned **future** templates as the permanent engineering applicability owner.

#### Prompt 11A gate

**Prompt 11A** (Property Definitions + aliases + Units) may start only after **all** of:

1. Canonical Product Type SPEC is **owner-reviewed**;
2. ADR-015 is **owner-reviewed**;
3. **PT-W1** runtime model is **merged**;
4. Property ownership boundaries are **approved**.

Prompt 11A **does not** require PT-W2 membership tables to exist.

Prompt 11A **MUST NOT** create permanent Category-owned `knowledge_spec_templates` or `knowledge_template_properties`.

#### Prompt 12 / 13 gate

Prompts **12** and **13** remain **blocked** until PT-W2 Definition/membership ownership is **implemented and approved**.

#### KB-PT-01 governance block

Before KB-PT-01 changes runtime schema, an Architecture Board minute (or equivalent repository-approved Canon amendment) **MUST** clarify the Hybrid model per ADR-015. Owner implementation direction alone is insufficient to supersede Accepted Canon. Until that minute exists, **KB-PT-01 is governance-blocked**.

This gate does **not** renumber Prompts 01–14. Insertion prompts/waves are **KB-PT-*** / **PT-W***; Prompt 11 is referred to as **11A** for narrowed scope.

**Stop condition:** If a prompt requires editing a path outside its allowlist, stop and report — do not expand scope silently.

---

## 13. Requirements traceability (testable)

| ID | Requirement |
|----|-------------|
| **MKB-R1** | Raw edge listing admin-only (Prompt 01; independent of Prompt 03) |
| **MKB-R1a** | Auth: missing/invalid/expired → 401; authenticated non-super-admin → 403 |
| **MKB-R2** | Public never sees asserted/rejected/deprecated |
| **MKB-R3** | Public never sees recorder/source/audit fields |
| **MKB-R4** | Article public edge requires published article + non-future `published_at` + public target product |
| **MKB-R4a** | Non-public present article/product → demote published→asserted; missing rows → deprecated |
| **MKB-R5** | Inline sync scope-limited; full sync = enqueue + both null only |
| **MKB-R5a** | Empty arrays → 422 `EMPTY_SYNC_SCOPE`; never full catalog |
| **MKB-R5b** | Full-catalog exclusivity via integrity-protected `is_full_catalog` + partial unique index |
| **MKB-R5c** | Job cancel endpoint; `cancelled` terminal; UUID job ids |
| **MKB-R6** | Counters distinguish created/updated/unchanged/deprecated/invalid_references/failed |
| **MKB-R6a** | Missing row / non-int = invalid; inactive/unpublished present = non-public; duplicates deduped |
| **MKB-R7** | Provenance minimum fields; `reviewed_by` / `last_actor` / `last_review_action` naming |
| **MKB-R7a** | From Prompt 08: every status transition appends `knowledge_edge_events` |
| **MKB-R8** | Public PKE read-model resolves category/brand/articles from real model columns only |
| **MKB-R8a** | Shared public-product eligibility predicate with PDP |
| **MKB-R9** | Review API + events + provenance in Prompt **08**; Admin UI in Prompt **10**; Prompt **02** has no steward mutations |
| **MKB-R10** | Runtime dictionary/Facts/evidence/taxonomy in Postgres overlay |
| **MKB-R11** | No JSONB↔Facts dual-write without separate approved task |
| **MKB-R12** | `products.id` remains PKE identity; no graph DB |
| **MKB-R13** | Layer direction endpoints → services → crud → models preserved |
| **MKB-R14** | Job terminals include `succeeded_with_errors` and `cancelled`; checkpoint/retry documented |
| **MKB-R15** | Performance numbers are targets until Prompt 14 evidence pack |
| **MKB-R16** | Category/brand: P/R may asserted→published iff §2.5; articles: never P/R auto-publish |
| **MKB-R17** | Product Type is engineering classification SoT (Proposed ADR-015); Category remains commerce-only |
| **MKB-R18** | Prompt 11A creates definitions/aliases/units only; forbids Category-owned `knowledge_spec_templates` / `knowledge_template_properties` |
| **MKB-R19** | Prompt 11A may start after SPEC+ADR owner review, PT-W1 merged, property ownership approved — does **not** require PT-W2 |
| **MKB-R20** | Prompts 12–13 blocked until PT-W2 Definition/membership ownership implemented and approved |
| **MKB-R21** | KB-PT-01 governance-blocked until Architecture Board Hybrid clarification minute exists |

### 13.1 Acceptance criteria (falsifiable)

1. Given an anonymous caller, when `GET /api/v1/knowledge/edges` is requested after Prompt 01, then the response is HTTP 401 (and Prompt 03 has not been required to merge).
2. Given an authenticated non-super-admin, when any admin knowledge endpoint is called, then the response is HTTP 403.
3. Given `mode=inline` with `product_ids=null` and `article_ids=null`, when sync is posted, then the API returns HTTP 413 with `SYNC_SCOPE_TOO_LARGE`.
4. Given `product_ids=[]` (or `article_ids=[]`), when sync is posted, then the API returns HTTP 422 with `EMPTY_SYNC_SCOPE` and does not scan the catalog.
5. Given `mode=enqueue` with both scopes null, when sync is posted, then a full-catalog job is accepted with HTTP 202 and a UUID `job_id`.
6. Given an active full-catalog job (`queued` or `running`), when a second full-catalog enqueue is attempted, then the API returns HTTP 409 with `PROJECTION_JOB_IN_PROGRESS`.
7. Given a `published` `ARTICLE_EXPLAINS_PRODUCT` edge whose article becomes unpublished (row still present), when projection or reconciliation runs, then the edge status becomes `asserted`.
8. Given a `published` `ARTICLE_EXPLAINS_PRODUCT` edge whose article row is missing, when projection or reconciliation runs, then the edge status becomes `deprecated` and `invalid_references` increments once for that distinct id.
9. Given a `rejected` edge, when the projector runs for the same identity, then the status remains `rejected` unless a steward `reopen_asserted` occurred (Prompt 08+).
10. Given `related_product_ids` containing duplicate missing ids, when projection runs, then `invalid_references` increments once per distinct missing id after dedupe.
11. Given a present inactive product id in `related_product_ids`, when projection runs, then `invalid_references` does not increment for that id and a previously `published` article edge demotes to `asserted`.
12. Given a projection job that finishes its full scope with `failed > 0`, when the job is read, then terminal status is `succeeded_with_errors`.
13. Given a public knowledge request for a soft-deleted or inactive product, when `GET .../knowledge` is called as a non-admin, then the response is HTTP 404 using the same eligibility predicate as the public PDP.
14. Given Prompt 02 is merged and Prompt 08 is not, when a client calls `POST .../edges/{id}/review`, then the route is absent or not part of the Prompt 02 deliverable (no steward mutation API yet).
15. Given a `queued` job, when `POST .../jobs/{id}/cancel` is called by a super-admin, then status becomes `cancelled`.
16. Given a terminal job (`succeeded` / `succeeded_with_errors` / `failed` / `cancelled`), when cancel is posted, then the API returns HTTP 409 with `INVALID_JOB_TRANSITION`.
17. Given a category/brand edge and a public product, when projector runs, then `asserted` → `published` is allowed; given an article edge, when projector runs, then `asserted` → `published` never occurs.
18. Given §12.1 Prompt 11A gate unmet, when Prompt 11A implementation is attempted, then work MUST halt rather than create Category-owned permanent property-template ownership.
19. Given Product Type architecture, when PKE identity is inspected, then `products.id` remains the Wave-1 join key and is not replaced by Product Type.
20. Given Prompt 11A completes, when schema is inspected, then `knowledge_spec_templates` and `knowledge_template_properties` are absent from Prompt 11A deliverables.
21. Given no Architecture Board Hybrid clarification minute, when KB-PT-01 runtime schema work is attempted, then work is governance-blocked.
22. Given PT-W2 Definition/membership ownership is not yet implemented and approved, when Prompt 12 or 13 is attempted, then work MUST halt.

---

## 14. Document control

| Field | Value |
|-------|-------|
| Document lifecycle status | **Proposed** |
| Version | **0.4.1** |
| Owner implementation approval | **Approved for Prompts 01–14** (2026-08-02) — subject to Product Type gates §12.1 — approver: Mohammad Shebahati |
| Product Type architecture amendment | **KB-PT-00** (v0.4.0) + **KB-PT-00A** (v0.4.1 final owner-review corrections) |
| Architecture Board acceptance | **Not granted** |
| Canonical authority | **Not Accepted Canon** — MUST NOT be treated as binding Canon until a Board minute + Canon Lock row |
| AODS registry class/status | **PROPOSED** / `proposed` (`SPEC-MASTER-KB-REMEDIATION`) |
| Registry `on_main` | **true** (path on `main` via PR #192); **v0.4.x branch changes not yet merged** |
| Next gate | Owner review → Architecture Board Hybrid clarification → KB-PT-01 (PT-W1) → Prompt 11A → PT-W2 → Prompts 12–13 |
| Supersedes | None for Canon. Supersedes SPEC v0.4.0 contradictory sequencing via KB-PT-00A; preserves 00/00A/00B/00C and KB-PT-00 history. |

---

*End of SPEC-master-knowledge-base-remediation.*
