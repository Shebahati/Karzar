"""CREATE HOLD recovery planning by product family."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _family_from_source(source_document: str) -> str:
    doc = source_document or ""
    if "داسکوا" in doc:
        return "DASQUA_MEASURING"
    if "قلاویز ET" in doc:
        return "ET_TAPS"
    if "فرز انگشتی" in doc:
        return "END_MILLS"
    if "چام پاور" in doc:
        return "CHUMPOWER_INSERTS"
    if "قلاویز" in doc:
        return "TAP_FAMILY_OTHER"
    if "سه نظام" in doc:
        return "CHUCKS_AND_HOLDING"
    if "دریل مگنت" in doc or "گردبر" in doc or "کردریل" in doc:
        return "MAGNET_DRILL_AND_ANNULAR"
    return "OTHER_AST_FAMILY"


def write_create_hold_recovery_plan(
    *,
    audit_dir: Path,
    sanitized_dir: Path,
    holds: list[dict[str, Any]],
) -> Path:
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    create_hold_rows = [
        h
        for h in holds
        if (h.get("hold_reason") or "")
        in {
            "HOLD_MANUFACTURER_IDENTITY_UNVERIFIED",
            "HOLD_VISUAL_PDF_QA_REQUIRED",
            "HOLD_CATEGORY_MAPPING",
            "HOLD_ET_TAP_VARIANT",
            "HOLD_DRILL_CHUCK_IDENTITY",
            "dasqua:missing_keyword",
        }
        or str(h.get("hold_reason") or "").startswith("HOLD_")
    ]
    by_reason = Counter(str(h.get("hold_reason") or "") for h in holds)
    by_family: Counter = Counter()
    family_reason: dict[str, Counter] = defaultdict(Counter)
    for h in holds:
        fam = _family_from_source(str(h.get("source_document") or ""))
        reason = str(h.get("hold_reason") or "")
        by_family[fam] += 1
        family_reason[fam][reason] += 1

    batches = [
        {
            "batch_id": "CREATE-BATCH-01_DASQUA_MEASURING",
            "family": "DASQUA_MEASURING",
            "row_count": by_family.get("DASQUA_MEASURING", 0),
            "resolution_steps": [
                "Attach PDF visual QA per SKU (visual_pdf_qa_verified=YES).",
                "Map measuring subfamily from code_nearby keywords.",
                "Set manufacturer=DASQUA with evidence; regenerate partial CREATE manifest.",
            ],
        },
        {
            "batch_id": "CREATE-BATCH-02_ET_TAPS",
            "family": "ET_TAPS",
            "row_count": by_family.get("ET_TAPS", 0),
            "resolution_steps": [
                "Confirm straight vs spiral from PDF row text.",
                "Verify ET brand identity; assign leaf 48/49.",
            ],
        },
        {
            "batch_id": "CREATE-BATCH-03_END_MILLS",
            "family": "END_MILLS",
            "row_count": by_family.get("END_MILLS", 0),
            "resolution_steps": [
                "Distinguish HSS/HSSCO vs carbide from supplier text.",
                "Reject carbide labels for HSSCO rows.",
            ],
        },
        {
            "batch_id": "CREATE-BATCH-04_AST_MANUFACTURER",
            "family": "AST_MANUFACTURER_REVIEW",
            "row_count": by_reason.get("HOLD_MANUFACTURER_IDENTITY_UNVERIFIED", 0),
            "resolution_steps": [
                "Establish manufacturer identity independent of ASTPOWER supplier label.",
                "Do not infer manufacturer from distributor identity alone.",
            ],
        },
    ]

    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "total_hold_rows": len(holds),
        "create_recovery_target_rows": len(create_hold_rows),
        "hold_reason_counts": dict(by_reason),
        "hold_by_product_family": dict(by_family),
        "family_reason_matrix": {k: dict(v) for k, v in family_reason.items()},
        "controlled_batches": batches,
        "policy": "HOLD is not rejection; resolved rows graduate to reviewed CREATE manifests per family.",
    }
    out_json = sanitized_dir / "CREATE_HOLD_RECOVERY_PLAN.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# CREATE HOLD recovery plan",
        "",
        f"- Total HOLD rows: **{len(holds)}**",
        f"- Recovery objective rows: **{len(create_hold_rows)}**",
        "",
        "## Hold reasons",
        "",
    ]
    for reason, count in by_reason.most_common():
        lines.append(f"- `{reason}`: **{count}**")
    lines.extend(["", "## Controlled batches", ""])
    for batch in batches:
        lines.append(f"### {batch['batch_id']} ({batch['row_count']} rows)")
        for step in batch["resolution_steps"]:
            lines.append(f"- {step}")
        lines.append("")
    (sanitized_dir / "CREATE_HOLD_RECOVERY_PLAN.md").write_text("\n".join(lines), encoding="utf-8")
    return out_json
