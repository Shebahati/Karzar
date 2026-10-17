# Owner decision options (not pre-approved)

Evidence-only package for **Product 2915** (SKU **2064**) and **Product 3238** (SKU **4457**).

Batches **001** and **002** owner authorization journals are **unchanged**.

## Product 2915 — Groz blade (تیغچه رنده تراشکاری)

| Option | Meaning |
|--------|---------|
| `APPROVE_INDUSTRIAL_EXCEPTION_KZ.DOM.CUTTING` | Keep in catalog under explicit Cutting Tools industrial exception (no category APPLY in this PR). |
| `REJECT_INDUSTRIAL_EXCEPTION_APPROVE_CATALOG_EXIT` | Confirm TX-OWNER-001 catalog exit (workshop/woodworking scope). |
| `REQUEST_MORE_EVIDENCE` | Require dimensions, Groz article, or photo before decision. |
| `DEFER_DECISION` | Hold pending procurement/OEM confirmation. |

## Product 3238 — Groz jack (جک ماشینکاری)

| Option | Meaning |
|--------|---------|
| `APPROVE_INDUSTRIAL_EXCEPTION_KZ.DOM.WORKHOLDING` | Treat as machinist setup/workholding exception (if physical unit matches setup jack class). |
| `APPROVE_CATALOG_EXIT` | Confirm catalog exit as general workshop/hand tool. |
| `REQUEST_MORE_EVIDENCE` | Require photo, load rating, Groz article (e.g. MJ/01) before decision. |
| `DEFER_DECISION` | Hold pending verification. |

All `owner_decision` fields remain **blank**; `authorization_status` **PENDING**.
