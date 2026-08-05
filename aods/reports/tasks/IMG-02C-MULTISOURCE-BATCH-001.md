# TASK-RECORD · IMG-02C

## Identity

| Field | Value |
|---|---|
| Task ID | IMG-02C |
| Title | Multisource Image Discovery Expansion |
| Node | IMG-02C-01-R1-REAL-SOURCE-ONBOARDING-BULK |
| Status | in_progress |
| Progress | 60 |
| Phase | R1 real-source onboarding + bulk discovery Artifact |
| Bulk discovery | complete (eligible universe exhausted) |
| Replacements applied | 0 |

## Relation to IMG-02B

Preserve unchanged:

```text
IMG-02B = in_progress / 40
IMG-02B-05 = not started
Dasqua = calibration_failed
INSIZE = partial
SAN OU = calibration_failed
```

IMG-02B-R2 seed (immutable inputs):

```text
stable product-image relations = 28
physical packaged images = 18
source-drift rows = 7
governed review rows = 46
```

## Eligibility (derived, not hardcoded)

```text
total_governed_work_items = 1204
already_sourced = 28
source_drift = 7
manual_or_ineligible = 47
remaining_eligible = 1129
```

## R1 source research (≥9 investigated)

Investigated (ledger): dasqua_official, sanou_official, insize_official_web,
insize_eu261_pdf, insize_tosag, willrich_insize, phase2plus_insize,
abzarham_sitemap, abzarmarket_brand_catalog, abzarreza_search,
example_unknown_disabled.

Enabled after PDP/PDF calibration (false_match=0, parser_success≥80%):

```text
insize_eu261_pdf (S2) — TOSAG-hosted INSIZE EU261 catalogue PDF
abzarham_sitemap (S5) — product-sitemap exact SKU (robots disallow /?s=*)
abzarmarket_brand_catalog (S5) — /brand/{dasqua,insize} exact SKU PDPs
```

Enabled classes: S2 + S5 (≥2). Disabled others remain fail-closed (homepage/search-only,
unknown auth, HTTP 500, no PDP mapping, or not selected).

## Bulk discovery outcomes

```text
products_attempted = 1129
products_with_candidates = 202
candidate_relations = 202
stable_candidates = 3
retailer_review_candidates = 140
manual_review_candidates = 59
rejected_candidates = 0
unique_image_candidates = 138
stop_reason = eligible_universe_exhausted
```

Operational target 200–400 relations met at the floor (202). Unique images 138 is
honest under the 150–250 target after identity-preserving stop (sources exhausted).

## Outputs (external only)

```text
working: /var/tmp/karzar-image-multisource/r1
review:  /home/moahmmad/Projects/Karzar-image-discovery/IMG-02C-01-R1
zip:     /home/moahmmad/Projects/Karzar-image-discovery/IMG-02C-01-R1.zip
```

## Safety

```text
database_accessed = false
ProductImage_modified = false
application_storage_mutations = 0
images_applied = 0
replacement_execution = false
rights_cleared = 0
rights_status = review_required
apply_status = not_started
seed_assets_skipped = 18
```
