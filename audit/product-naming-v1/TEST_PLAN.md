# Test plan — Product Naming Standard v1

## Unit (implemented)

```bash
python3 -m pytest tests/test_product_naming_v1.py -q --noconftest
```

Covers: INSIZE caliper, ZCC insert, SAN OU chuck, code preservation, units, prohibited terms, HOLDs, determinism, Arabic ye/kaf, EXACT match, thread repair, solid tool diameter, micrometer range, generic omit-noise.

## Audit dry-run

```bash
python3 scripts/audit_product_naming_v1.py
python3 scripts/audit_product_naming_v1.py --apply   # must exit 2
```

## Future (Phase 2+)

| Class | Cases |
|-------|-------|
| Regression fixtures | Real catalog rows: INSIZE, Mitutoyo, DASQUA, TERMA, ZCC.CT, SAN OU, ASTPOWER, thread repair |
| Property | same input → same name; OEM code substring unchanged; no marketing injection; no invented facts |
| API lint | ProductCreate/Update warning phase without breaking clients |
| Admin preview | Canonical name preview matches engine for fixtures |

## Soft length policy

- Soft UX target: **120** characters  
- Hard DB limit: **255** (`products.name`)  
- Never truncate manufacturer code; HOLD if over hard limit
