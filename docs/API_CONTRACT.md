# API contract

Machine source of truth: [`../openapi/v1.json`](../openapi/v1.json). This file records only rules that OpenAPI does not.

Changelog: [`API_CHANGELOG.md`](API_CHANGELOG.md). Domain rules: [`COMMERCE.md`](COMMERCE.md).

## OpenAPI

| Env | `ENABLE_API_DOCS` | URLs |
|-----|-------------------|------|
| Local | `true` (default) | `/api/docs`, `/api/redoc`, `/api/openapi.json` |
| Staging | `true` recommended | Same paths |
| Production | `false` recommended | Use the committed snapshot; do not rely on live docs |

Regenerate after any shape change:

```bash
python -c "import json; from app.main import app; json.dump(app.openapi(), open('openapi/v1.json','w'), indent=2, ensure_ascii=False)"
python3 aods/tools/aods_validate.py --gate openapi
```

Path inventory is the snapshot, not a prose table. Known residual: regenerate in the same PR if `app.openapi()` and the file diverge (`CR-012`).

## Error envelope

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Human-readable summary",
  "details": [{ "field": "sku", "message": "already exists" }]
}
```

## Rules OpenAPI does not own

- Site availability is `is_available`, not warehouse quantity (`COMMERCE.md`).
- Optional auth: cart (`X-Cart-Token` and/or JWT), checkout, payment init, public product GETs.
- List envelopes vary (`{data, meta}` vs `{data}` vs raw array) — trust the snapshot + contract tests (`tests/test_p5_contract.py`, `tests/test_p1_contract.py`).
- Breaking field changes need `/api/v2` or a documented deprecation window (`API_CHANGELOG.md`).

## Sync checklist

1. Change code/schemas.
2. Update `API_CHANGELOG.md` when contract-affecting.
3. Regenerate and commit `openapi/v1.json`.
4. Run pytest contract tests + `--gate openapi`.
