# External Standards Alignment

**Status:** Proposed design (Phase 1A)  
**Licensing:** No bulk ECLASS/ETIM/ISO/OEM datasets copied. Public structural principles + Karzar interpretation only.

---

## 1. Claim posture (D13)

| Scheme | Karzar claim | Notes |
|--------|--------------|-------|
| ECLASS Release 16.0 (published 2025-11-28) | **ECLASS-INSPIRED** | Class vs Application Class vs Property vs Value vs Keyword/Synonym vs IRDI stability |
| ETIM Classification Model | **ETIM-INSPIRED** | Product Class ≈ Product Type; Feature/Value/Unit; language-independent IDs; synonyms for search |
| ISO 13399 family | **ISO-ALIGNED** (cutting domain) | Cutting item / tool item / adaptive item vocabulary & property thinking — **not** “ISO-COMPLIANT” |
| IEC CDD / ISO 13584 | Deferred reference | Possible future crosswalk |
| UNSPSC / GS1 GPC | Related-only | Too coarse for engineering PT |
| Manufacturer sites | OEM-BACKED when technical docs; **not** authority when merchandising trees |

---

## 2. Principles adopted

From **ECLASS** public model (STANDARD-BACKED principles):

- Classification groups similar products.
- Properties describe characteristics; values instantiate them.
- Stable identifiers independent of language labels.
- Keywords/synonyms aid findability without changing identity.

From **ETIM** public model:

- Similar products → same Product Class.
- Technical differences → Features/Values.
- Multilingual labels hang off stable codes.

From **ISO 13399** (cutting tools):

- Distinguish cutting items, tool items, adaptive items, assemblies.
- Connection systems and reference dictionaries inform Properties/Compatibility — not Commerce L1 inventiveness.

---

## 3. Crosswalk model

See identity contract §6. Relations: `EXACT | NARROWER_THAN | BROADER_THAN | RELATED | CANDIDATE`.

**Default for unreviewed mappings:** `CANDIDATE` only.

Do not claim `EXACT` without steward verification + evidence_source.

---

## 4. Authority resolution examples

| Dispute | Prefer |
|---------|--------|
| Insert identity vs generic ECLASS label | ISO 13399-aligned cutting-item split (Turning vs Milling Insert as PTs) |
| Digital caliper as class vs feature | ETIM Feature principle + ADR-015 → Property |
| BT as product class vs interface | Interface Property; holder principle as PT |
| HELICOIL as class name | Scientific Wire Thread Insert; trade synonym |

---

## 5. TCR-1 — Taxonomy Conflict Resolution

1. State contested concept + options.  
2. Cite authorities with evidence class.  
3. Apply domain-sensitive hierarchy (Constitution §5).  
4. Record decision packet: decision · rationale · authority · evidence · reviewer · date.  
5. If Production impact: Migration Reviewer + SEO Reviewer sign-off before APPLY (future phases).
