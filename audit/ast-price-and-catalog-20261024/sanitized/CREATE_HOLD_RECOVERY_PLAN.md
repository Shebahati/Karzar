# CREATE HOLD recovery plan

- Total HOLD rows: **1205**
- Recovery objective rows: **1173**

## Hold reasons

- `HOLD_VISUAL_PDF_QA_REQUIRED`: **1168**
- `QA_MANUFACTURER_IDENTITY_REVIEW`: **20**
- `QA_LARGE_PRICE_SWING`: **12**
- `HOLD_ET_TAP_VARIANT`: **2**
- `HOLD_CATEGORY_MAPPING`: **2**
- `HOLD_MANUFACTURER_IDENTITY_UNVERIFIED`: **1**

## Controlled batches

### CREATE-BATCH-01_DASQUA_MEASURING (11 rows)
- Attach PDF visual QA per SKU (visual_pdf_qa_verified=YES).
- Map measuring subfamily from code_nearby keywords.
- Set manufacturer=DASQUA with evidence; regenerate partial CREATE manifest.

### CREATE-BATCH-02_ET_TAPS (0 rows)
- Confirm straight vs spiral from PDF row text.
- Verify ET brand identity; assign leaf 48/49.

### CREATE-BATCH-03_END_MILLS (0 rows)
- Distinguish HSS/HSSCO vs carbide from supplier text.
- Reject carbide labels for HSSCO rows.

### CREATE-BATCH-04_AST_MANUFACTURER (1 rows)
- Establish manufacturer identity independent of ASTPOWER supplier label.
- Do not infer manufacturer from distributor identity alone.
