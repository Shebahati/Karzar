# HISTORICAL RECONCILIATION

Fresh snapshot **2026-10-07T10:16:05Z** vs historical Wave 0 / Wave 1A anchors.

Reference anchors only — current audit is independently calculated.

## Headline deltas

| Metric | Historical | Current | Delta |
|--------|----------:|--------:|------:|
| live | 6536 (Wave 0) | 6536 | 0 |
| sellable | 716 → later verified **717** (Wave 1A) | **717** | 0 vs verified |
| CURRENT_ONLY_AVAILABILITY | Wave 0 READY_EXCEPT_AVAILABILITY **330** | **580** | +250 (new cohort, not same membership) |

## Metric comparison (where historical artifacts allow)

| Metric | Wave 0 / 1A | Current |
|--------|------------:|--------:|
| sellable | 717 (verified) | 717 |
| live | 6536 | 6536 |

Other Wave 0 column-level census values were not re-forced; fresh active/available/priced/imaged are computed from current Production only:

| Metric | Current |
|--------|--------:|
| active | 1585 |
| available | 3756 |
| priced (`base_price > 0`) | 4926 |
| imaged | 1464 |
| visible | 1368 |

## Historical cohort 330 (`READY_EXCEPT_AVAILABILITY`)

Membership frozen from Wave 0 `READY_EXCEPT_AVAILABILITY.csv` (330 product_ids). **Not redefined.**

| Outcome | Count |
|---------|------:|
| still live | 330 |
| now sellable | **1** |
| still only availability blocked | **329** |
| new blockers appeared | 0 |
| membership preserved | YES |

Artifact: `HISTORICAL_330_RECONCILIATION.csv`.

Interpretation: the historical “ready except availability” pool remains almost entirely availability-blocked. One product became sellable since that freeze (availability flipped with other gates still satisfied). The **current** only-availability pool is larger (580) because additional products became active+priced+imaged while still `is_available=false`.

## Known causal notes (evidence-supported, incomplete)

| Event | Effect on sellability census |
|-------|------------------------------|
| Wave 1A / 1A.1 stock-authority work | Did **not** APPLY availability; sellable stayed ~717 |
| Product 1789 brand integrity/repair | Identity/brand integrity; not a mass sellability unlock |
| INSIZE price operations (historical) | Reflected in priced/active state where already applied; not re-audited as APPLY here |
| Soft-delete | 1 soft-deleted row outside LIVE universe |

No forced matching of current counts to historical counts beyond documenting identity of the 330 membership set.

## CURRENT vs HISTORICAL only-availability

```text
HISTORICAL_330  ≠  CURRENT_ONLY_AVAILABILITY (580)
```

| Brand (current ONLY_AVAILABILITY) | Count |
|-----------------------------------|------:|
| INSIZE | 476 |
| ASTPOWER | 53 |
| SAN OU | 24 |
| Dasqua | 22 |
| TERMA | 4 |
| Mitutoyo | 1 |
| **Total** | **580** |
