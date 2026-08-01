# Knowledge architecture seeds

**Status:** Draft / REFERENCE (not Canon Lock rows by themselves)  
**Parents:** Accepted `SPEC-property-dictionary-system.md` · Day-2 UD-03 A (metrology first)

## Property Dictionary v0 — metrology

| File | Role |
|------|------|
| [`property-dictionary-v0-metrology.json`](./property-dictionary-v0-metrology.json) | Definitions + `caliper` template + aliases + legacy key map |

### Rules

1. **Git-first** — this seed is the living dictionary until a Board-gated DB ADR/RFC.  
2. **No dual-write** — do not write Facts into Postgres from this seed; JSONB remains operational.  
3. **Metrology only** — caliper family; insert/end-mill/etc. stay out of v0.  
4. **Canonical keys** are English snake_case; FA appears in `label_fa` + `aliases` only.  
5. Empty/honest values beat invented OEM numbers (playbook + Bible P4).

### Operator checklist (KB-001 residual from Day-3)

On a local Category A stack (ADR-012):

```bash
alembic upgrade head
# admin JWT
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/projections/sync \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
curl "http://127.0.0.1:8000/api/v1/knowledge/edges?edge_type=PRODUCT_BELONGS_TO_CATEGORY&limit=5"
```

### Validation

`tests/test_property_dictionary_v0.py` loads the JSON and checks SPEC-required fields.
