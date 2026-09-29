KARZAR TAXONOMY PHASE 0B — RESULT
=================================

STATUS
COMPLETE

SAFETY
Production mutation: NO
Transaction mode: READ ONLY
Deployment: NO
Catalog APPLY: NO
Taxonomy mutation: NO
Repository mutation: YES diagnostic-only (audit workflow + artifacts on branch)

IDENTITY
repo SHA: (workflow GITHUB_SHA — see Actions run)
VPS: srv5944957438
database: karzar_staging user=karzar_staging addr=172.18.0.2/32:5432
data plane: APP_ENV=staging KARZAR_DATA_PLANE=None
APP_ENV: staging
Alembic: s2t3u4v5w6x7
transaction_read_only: on
snapshot time: 2026-09-27T10:06:26Z

A. GLOBAL PRODUCT TRUTH
Live: 6536
Deleted: 1
Active: 1585
Available: 3755
Priced: 4552
Imaged: 1464
Visible: 1368
Sellable: 716
Categoryless: 0
Brandless: 295

B. CATEGORY TRUTH
Categories: 138
L1: 15
L2: 81
L3: 42
Leaves: 114
Selectable: 111
Empty: 38
Orphans: []
Cycles: []
Non-leaf assignments: 0
Invalid assignments: 0
Special IDs: {"33": null, "34": null, "165": "اینسرت", "166": "اینسرت › اینسرت تراش CNC", "168": "اینسرت › اینسرت فرز CNC", "186": "فنر هلی کویل", "187": "قلاویز هلی کویل", "188": "کیت کامل هلی کویل"}

C. PRODUCT TYPE
Product Types: 37
Assigned products: 527
Missing Product Type: 6009
Coverage %: 8.063
Active definitions: 37
Zero-product Product Types: 0

D. KNOWLEDGE TAXONOMY
Nodes: 0
Active: 0
Draft: 0
Deprecated: 0
Classified products: 0
Coverage %: 0.0
Broken bridges: commerce=0 pt=0
PT bridge consistency: {'MISSING_BRIDGE': 527}

E. HESABFA
Mapped categories: 0
Unmapped: 138
Duplicate codes: {}

F. MEGAMENU
Groups: 6
L1 represented exactly once: 15/15
Missing: []
Duplicate: []

G. NUMERIC-ID RISK
Missing IDs still referenced (active import/runtime): [33, 34]

H. API ↔ DB RECONCILIATION
| Categories | 138 | 138 | True |
| L1 | 15 | 15 | True |
| L2 | 81 | 81 | True |
| L3 | 42 | 42 | True |
| Leaves | 114 | 114 | True |
| Selectable leaves | 111 | 111 | True |
| Public/storefront-visible products | 1368 | 1368 | True |
| Categoryless public | 0 | 0 | True |
| Available public | 716 | 716 | True |
| Priced public | 1046 | 1046 | True |

I. PHASE 0 FINDINGS REVISED
P0: (none continuous runtime — see findings)
P1: numeric ID semantic deps in ACTIVE_IMPORT (ZCC/INSIZE/Mitutoyo/Azarsanat); missing 33/34 still referenced; commerce stable ID missing; PT coverage near-zero
P2: storefront L1 drift; helicoil depth-1 leaves; Hesabfa mapping sparse/absent; Knowledge taxonomy empty or sparse
P3: semantic property-like commerce leaves

J. PHASE 0 COMPLETION VERDICT
Can Phase 0 be closed? YES (if this report STATUS=COMPLETE and all gates proven)

K. BLOCKERS BEFORE MASTER TAXONOMY V1
1. Introduce commerce Category stable semantic code
2. Migrate ACTIVE_IMPORT paths off bare integer PKs
3. Decide metrology/helicoil L1 presentation vs ontology
4. SEO redirect map for deleted/replaced category IDs/slugs
5. Populate or formally defer Knowledge Taxonomy + PT coverage program

L. SAFE NEXT STEP
Phase 1 READ-ONLY/DESIGN: Master Taxonomy V1 draft + stable-ID scheme. Do not execute.

ARTIFACTS
00-db-identity.txt  SHA256=6f9141560a27c31c4b1a5c5ce2b667ecddc6f1e8f31de2d637d4dd4adc49bec1  bytes=467
01-product-global-counts.json  SHA256=c026ad18968c0584403d9a97704f2e791201bc6a8d1c303828ccd7e1edfddfc8  bytes=3330
02-production-products-category-census.csv  SHA256=fe3eadfbd60114339cd8c21b3ad584fe49768b71bd97a291d117decdece1ec62  bytes=1876598
03-production-category-census.csv  SHA256=d402aa9062d83fd2d2814dfd92e3eb39dbaebe00c1949259f6af969270fc2251  bytes=24649
04-product-type-census.csv  SHA256=d44e4e737b6cfdf0e4bc62a977d5cf5f693e137adc9059dde70df73f0f70f1da  bytes=4052
05-product-type-coverage-by-category.csv  SHA256=26b7eacfba54162f7e3409a9dcd4c00e6f314210c538162f553579e173745c1d  bytes=8379
06-product-type-definitions.csv  SHA256=c73a0e755facd4d8cce653e969120a1f86c3a3de084032cbcd48e0b1db209b67  bytes=10767
07-knowledge-taxonomy-nodes.csv  SHA256=e7ff94c80df6aaae5c21e414006cc1467e1ee9bc2f08bc04eefafcd8430a48ce  bytes=12
08-knowledge-classification-assignments.csv  SHA256=bb02018d412f15813ae5528d602186a62682ee7d35f7ab79cf6aa4464e5e5819  bytes=15
09-megamenu-db-census.csv  SHA256=c6053ad46bace3403bb11e571627d42af0ec2b55eecce5f434ebcd52f45bd4f6  bytes=832
10-hesabfa-category-map.csv  SHA256=72355951a01a43cc5a3e32c78db5215347de61c3b4ce3c5fff494a2fbbf30598  bytes=10439
11-hardcoded-id-live-resolution.csv  SHA256=b5891329470a4b6e99b8a34f8780f0b44421d34bf4efbce0ca2f06d3c4ced445  bytes=4800
12-api-vs-db-reconciliation.csv  SHA256=169e395652825efc3f4377734f314be19e068075a8ed5192e5351d54b7ef724f  bytes=305
13-phase0b-findings.md  SHA256=d4ddc7e79265c0471ddec111edb6bbc7a1d582b6e9fb0d575148bbb50d087aba  bytes=983
SUMMARY.json  SHA256=c865c77d859e8f24a98947f7994a6122f9767716c99f8a25ce4b0724ccee90ae  bytes=5439
IDENTITY_PROBE.json  SHA256=1c096d7ff1812d097f1b2d22c4bcfa8a8226f783e7eee549b85fedce7f3c437d  bytes=811
14-phase0b-final-report.md  SHA256=1fb6077ce45f8e0ce65f82f5b01b719efd3831bb25945b2578a20fae33dba7f7  bytes=4939
