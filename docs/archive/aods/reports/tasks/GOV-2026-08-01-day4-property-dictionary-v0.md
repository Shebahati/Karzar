# Day 4 — Property Dictionary v0 (metrology)

| Field | Value |
|-------|-------|
| **Date** | 2026-08-01 |
| **Session** | Day-4 practical week — Topic 1 |
| **Attendees** | Mohammad Shebahati · Cursor |
| **Owner order** | Day-3 close → Day-4 start with **۱** |
| **Interpretation** | After KB-001 wave-1 close, **۱** = next architecture node: Property Dictionary v0 metrology (readiness §5 step 4 · UD-03 A). Operator Alembic checklist remains Day-3 residual. |

## Binding parents

- `docs/architecture/specs/SPEC-property-dictionary-system.md` (Accepted)
- Day-2 ballot **UD-03 A** — metrology first
- Canon Lock §1c · dual-write **still Deferred**
- SPEC §10: Dictionary lives **Git-first** until tables via separate ADR/RFC

## Scope

**In:**
- Git JSON seed: metrology Property Definitions + `caliper` template + FA/EN/legacy aliases
- Seed README + structural validation test
- PMO touch

**Out:**
- Facts table / dual-write
- DB dictionary tables
- Non-metrology L1 domains (insert, end_mill, …)
- AI inventing values
- Changing `spec_template_service` runtime (strangler later)

## Deliverable path

`docs/architecture/specs/seeds/property-dictionary-v0-metrology.json`
