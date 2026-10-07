# Remediation execution plan (NOT EXECUTED)

```text
STATUS = PLAN_ONLY
CHOWN_OF_17 = FORBIDDEN until Phase A+B complete for PRESERVE_REQUIRED set
```

## Phase A — Preserve required evidence/source (Owner-authorized writes)

Destination (existing): `/opt/karzar/preserve/`

Proposed (Owner must approve names before create):

```text
/opt/karzar/preserve/insize-n4120-20261006/
/opt/karzar/preserve/insize-workbook-20261006/
```

Exact sources to copy (preserve semantics — this plan does not run them):

1. Entire directory tree:

```text
/opt/karzar/Karzar/audit/insize-price-20-n4120/   →  .../preserve/insize-n4120-20261006/audit/
```

2. Alias CSV (live SHA is remaining-19 version):

```text
.../INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv
  → .../preserve/insize-n4120-20261006/INSIZE_SITE_TO_SOURCE_CODE_ALIASES.csv
```

3. Apply scripts (optional if Owner accepts PR #442 retention; recommended anyway):

```text
scripts/ops/insize_n4120_identity_alias_apply.py
scripts/ops/run_insize_n4120_identity_alias_apply.sh
```

4. Workbook:

```text
/_ops/input/موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx
  → .../preserve/insize-workbook-20261006/<same-filename>
```

Write a `PRESERVATION_MANIFEST.csv` at the destination using the schema in `PRESERVATION_REQUIREMENTS.md`.

## Phase B — Verify destination SHA256

For every regular file in Phase A: `sha256(dest) == sha256(source)` from `PRESERVATION_INVENTORY.csv`.

Hard-required before any live deletion:

- `RECOVERY_N4120_20261006T141319Z.json` → `0048f19c9ea5da3319acf54bf7f77cb9dae4afa900f8994492f7aa161f4b07a9`
- `N4120_ROLLBACK.csv` → `be8b4c55de397bed57904aa27e48b714417f58b5bd63c39d2c7df28dfef375c9`
- workbook → `65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a`
- alias CSV → `0449ba50a46233e462b230478c8ca18d2cd4c86e21e521e7137e34afee81f696`

## Phase C — Remove operational artifacts from live checkout

Only after Phase B PASS:

- Remove live `_ops/**` (workbook already preserved).
- Remove live `audit/insize-price-20-n4120/**` **or** leave until deploy deletes after ownership allows unlink — prefer explicit move-away so deploy is not the sole delete mechanism for recovery files.
- Do **not** delete solely by hoping rsync cleans up while root-owned.

## Phase D — Ownership (exact paths only)

After PRESERVE_REQUIRED objects are **gone from live tree** (or intentionally kept as runner-owned tracked content via a future merged PR):

- Do **not** run the original 17-path chown list as a block.
- If any runner-managed path must remain, chown **only that exact remaining path**.
- Never `chown -R /opt/karzar` or `/opt/karzar/Karzar`.
- Do not cosmetic-chown objects whose disposition is delete/relocate.

## Phase E — Preflight

```text
sudo -u github-runner python3 deploy/staging/scripts/deploy_ownership_preflight.py \
  --expected-user github-runner \
  --live-root /opt/karzar/Karzar \
  --frontend-root /opt/karzar/frontend \
  --incoming-base /opt/karzar/incoming \
  --skip-rsync-dry-run
```

## Phase F — Require PASS

```text
status=PASS
unexpected_ownership=0
```

## Phase G — Merge #443

Only after Phase F PASS (or Owner accepts documented residual with updated canary).

## Phase H — Normal Deploy Staging

Prove ownership preflight runs before Sync backend; confirm no unintended loss of preserved SHA256 set.

## Explicitly forbidden now

```text
sudo chown github-runner:github-runner -- <any of the current 17>
```

Reason: 11+ objects are `PRESERVE_REQUIRED` and `WOULD_DELETE` after ownership enables unlink.
