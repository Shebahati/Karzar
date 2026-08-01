# Knowledge architecture seeds

**Status:** Draft / REFERENCE (not Canon Lock rows by themselves)  
**Parents:** Accepted `SPEC-property-dictionary-system.md` · Accepted `SPEC-industrial-taxonomy-model.md` · Day-2 UD-03 A (metrology first)

## Property Dictionary v0 — metrology

| File | Role |
|------|------|
| [`property-dictionary-v0-metrology.json`](./property-dictionary-v0-metrology.json) | Definitions + `caliper` template + aliases + legacy key map |

## Taxonomy v0 — metrology

| File | Role |
|------|------|
| [`taxonomy-v0-metrology.json`](./taxonomy-v0-metrology.json) | Domain/Family/Type + Application/Industry slice + commerce L1 bridge (56/81/87) |

## Classification map — INSIZE (one brand)

| File | Role |
|------|------|
| [`classification-map-insize-v0-metrology.json`](./classification-map-insize-v0-metrology.json) | AODS `MAPPING-TABLE` / taxonomy classify rules → closed `concept_id` set for brand_id=3 |

### Rules

1. **Git-first** — seeds are living until Board-gated DB ADR/RFC.  
2. **No dual-write** — do not write Facts into Postgres from dictionary seed; JSONB remains operational.  
3. **Metrology only** — Measurement domain + caliper/micrometer families; cutting/toolholding out of v0.  
4. **No second Category DAG** — commerce `categories` stay SoR for merchandising (CF-SPEC-01). Bridge is assignment-only.  
5. **No indexable knowledge hubs** until UD-04.  
6. Canonical concept_ids / slugs are English; FA in `name_fa` + synonyms.  
7. Empty/honest values beat invented OEM numbers (playbook + Bible P4).  
8. **Classification maps** — Git rules only; no `PRODUCT_CLASSIFIED_AS` projection until Board reopens beyond KB-001 three-edge freeze; unknown → `unclassified_pending_taxonomy` (no invented nodes).

### Operator checklist (KB-001 residual from Day-3)

On a local Category A stack (ADR-012):

```bash
alembic upgrade head
# admin JWT
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/projections/sync \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
curl "http://127.0.0.1:8000/api/v1/knowledge/edges?edge_type=PRODUCT_BELONGS_TO_CATEGORY&limit=5"
```

Admin read-only UI (after sync): `/knowledge` edges browser · product edit → «گراف دانش».

### Validation

- `tests/test_property_dictionary_v0.py` — dictionary seed fields  
- `tests/test_taxonomy_v0_metrology.py` — taxonomy seed + bridge + no second DAG  
- `tests/test_classification_map_insize_v0.py` — INSIZE classify map + offline sample coverage
