---
id: FOUNDATION-ARCHITECTURE-REVIEW
version: 0.1.0
status: Proposed
date: 2026-07-30
owner: Principal Architect
task_id: KB-001
pack: docs/architecture/specs/README.md
---

# Foundation Architecture Review

**Status:** Proposed  
**Subjects:** Knowledge Foundation Specs Pack (`docs/architecture/specs/README.md` + four SPECs)  
**Method:** Consistency with repository evidence + Master Architecture / Canon Lock / Phase 2 — **not** a blind rewrite

---

## 1. Verdict

The Foundation Pack is **directionally correct and aligned** with Bible principles (P3–P7), Phase 2 overlay decisions, ADR-012, and KB-001 constraints when interpreted via CF-SPEC-01.

It is **not yet implementation-ready** alone:

| Strength | Gap |
|----------|-----|
| Clear Commerce ≠ Knowledge split | No unified ER across all entities |
| Multi-dim taxonomy without second Category DAG | No concrete seed nodes / FA-EN labels |
| Graph overlay + provenance principles | No normative Relation Type Registry table |
| Import stages + AI allow/deny | No mapping/transform architecture detail (units, jobs, rollback matrices) |
| Spec Definitions concept | No Property Dictionary system (datatypes, versioning, FA/EN governance) |
| EPIC-1 URL deference | Does not describe how PDP composes commerce+knowledge at target |

**This completion phase fills those gaps** without replacing the four foundation SPECs.

---

## 2. Document-by-document review

### 2.1 Pack README (`README.md`)

| Check | Result |
|-------|--------|
| Repo analysis cites models/IA/ingestion | Pass — matches `product.py` / IA / ADR-012 |
| CF-SPEC-01…05 surfaced | Pass |
| UD-01…08 listed | Pass — still open |
| Dependency diagram | Pass — still valid |
| Assumes Brand Hub / slug PDP absent | **Partial fail** — prose inherits older “CURRENT”; Storefront has shipped hubs/slug (FULL audit §5). Prefer CF-SPEC-05 |

**Action:** Keep README; completion docs supersede stale route assumptions for *runtime* description.

### 2.2 SPEC-product-knowledge-entity-model

| Check | Result |
|-------|--------|
| Matches as-built Product/Brand fields | Pass |
| Manufacturer ≠ Brand | Pass — conflicts with as-built (expected); UD-01 |
| JSONB strangler | Pass — Bible P6 |
| Content modules | Pass — missing vs `description` blob |
| 1:N PKE:SKU | Correctly Board-gated |
| Spec templates vs `spec_template_service.py` | **Gap** — does not map existing keys (`measurement`, `insert`, …) to future Definition IDs |

**Missing concepts to add in Domain/Property SPECs:** Evidence Source, Fact status machine detail, link from `pdf_catalog_url` → Document node, Series/Family as nodes vs attributes.

### 2.3 SPEC-industrial-taxonomy-model

| Check | Result |
|-------|--------|
| CF-SPEC-01 interpretation | Pass — compatible with KB-001 AC |
| Dimensions complete | Pass |
| Bridge to commerce Category | Pass conceptually |
| Concrete seed + L1 Persian map | **Gap** → master seed SPEC |
| SEO hub gating UD-04 | Pass |

**Hidden contradiction risk:** Calling knowledge nodes “Product Category” vs commerce `categories` — naming collision. **Mitigation in Domain/Seed:** use `knowledge_category` / `tool_class` labels in APIs; never overload `categories` table.

### 2.4 SPEC-knowledge-graph-model

| Check | Result |
|-------|--------|
| Overlay not SoR replacement | Pass — Phase 2 |
| Edge inventory covers mission set | Pass |
| Style A Facts default | Pass — needs Property SPEC to operationalize |
| Soft-link migration plan | Pass for KB-001 start |
| Official registry with evidence rules per edge | **Gap** → registry SPEC |
| Storage choice UD-05 | Still open — readiness must gate DDL |

### 2.5 SPEC-product-import-enrichment-playbook

| Check | Result |
|-------|--------|
| Aligns ADR-012 / ingestion policy | Pass |
| AI deny list | Pass — Bible P4 |
| Review tiers | Pass |
| Maps to existing scripts | Pass (pattern-level) |
| Detailed transform (unit parse, mapping tables, job IDs) | **Gap** → data transformation SPEC |
| Enforcement hooks in app | Out of scope for SPEC; readiness notes “policy only today” |

---

## 3. Consistency with repository

| Foundation claim | Repo evidence | Status |
|------------------|---------------|--------|
| Commerce SoR = products/brands/categories/articles | Models present | Consistent |
| No knowledge package | `app/` has no `knowledge/` | Consistent |
| Megamenu ≠ taxonomy | `MegamenuNavGroup` + D1 | Consistent |
| Specs JSONB operational | Column + GIN + templates | Consistent |
| Category ≠ Tool Class | Bible + taxonomy SPEC | Consistent |
| Identity before intelligence | SKU unique partial index | Consistent |
| EPIC 1 without Facts | ADR-010 Decision 7; hubs shipped | Consistent |
| “Brand hub absent” if implied | Storefront `/brands/[slug]` exists | **Stale foundation prose** |

---

## 4. Hidden contradictions (explicit)

1. **Naming:** “Product Category” (knowledge) vs `categories` (commerce) — resolve via distinct types (`TaxonomyNode.dimension=family` / `node_type=knowledge_category`).  
2. **Template keys:** as-built `measurement`/`insert`/… vs future Property Templates — need strangler map, not dual registries forever.  
3. **KB-001 AC “Graph links queryable”** vs no edge tables — foundation correctly defers IMPL; readiness must say “SPECs ≠ schema Accepted”.  
4. **Similar vs Alternative edges** — foundation defines both; registry must disambiguate publish rules to avoid SEO thin-content duplicates.  
5. **1 PKE : N SKU** allowed conceptually but as-built Product is the only identity — provisional `products.id` link is mandatory until UD-02.

---

## 5. What NOT to rewrite

Do **not** replace the four foundation SPECs. Treat them as parent vocabulary. Completion docs **cite and extend**.

Amend foundation only if Board requires — out of scope for this node except README index update.

---

## 6. Traceability matrix (foundation → completion)

| Foundation need | Completion doc |
|-----------------|----------------|
| Full entity ER | `SPEC-domain-model.md` |
| Governed specs | `SPEC-property-dictionary-system.md` |
| Concrete taxonomy | `SPEC-industrial-taxonomy-master-seed.md` |
| Edge registry | `SPEC-knowledge-graph-registry.md` |
| Pipeline mechanics | `SPEC-data-transformation-architecture.md` |
| PDP composition story | `KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md` |
| “Can we build yet?” | `FOUNDATION_IMPLEMENTATION_READINESS.md` |
| Repo ground truth | `FULL_PLATFORM_ARCHITECTURE_AUDIT.md` |

---

## 7. Review outcome

| Decision | Choice |
|----------|--------|
| Keep foundation SPECs | Yes |
| Status | Remain Proposed until Board Accept (UD-06) |
| Blocking gaps for engineering planning | Closed by completion pack (logical design) |
| Blocking gaps for coding | Remain: Board Accept, storage ADR (UD-05), UD-01/02/03, dual-write gate |

---

## 8. Deliberately not fixed in foundation files

- Stale route “CURRENT” wording inside older audits / ADR context blocks  
- Measurement bias in `get_default_specifications()` (code — forbidden this phase)  
- Soft `related_product_ids` migration (IMPL)
