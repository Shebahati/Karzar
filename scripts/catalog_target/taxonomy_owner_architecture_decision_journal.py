"""Owner Architecture Decision Journal — append-only documentation (no catalog APPLY)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import sha256_file, write_sha256sums

ROOT = Path(__file__).resolve().parents[2]
JOURNAL_DIR_NAME = "audit/taxonomy-phase1b-owner-architecture-decision-journal-2026-10-18"
B2_DIR = ROOT / "audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18"
PR534_MERGE_SHA = "25a2497c11b6a740fa606292af1e791d41335ba9"

DECISION_ID_ARCH_7_L1 = "ARCH-7-L1-ROOTS"
GATE_IR_MARKET_NAMING_SEO = "IR-MARKET-NAMING-SEO"

OWNER_STATEMENT_FA = (
    "«به‌عنوان مالک، هفت ریشهٔ معماری پیشنهادی را به‌صورت مشروط می‌پذیرم، "
    "اما نام‌های نمایشی، عناوین سئو و URLها را هنوز تأیید نمی‌کنم. "
    "تحقیق نام‌گذاری بازار ایران را به‌عنوان یک گیت مستقل ثبت کنیم؛ "
    "هیچ APPLY یا Deploy مجاز نیست.»"
)

SEVEN_L1_COMMERCE_CODES = (
    "KZ.CAT.BUYER_CUTTING_TOOLS",
    "KZ.CAT.BUYER_FLUIDS",
    "KZ.CAT.BUYER_MACHINES",
    "KZ.CAT.BUYER_METROLOGY",
    "KZ.CAT.BUYER_THREAD_REPAIR",
    "KZ.CAT.BUYER_TOOLHOLDING",
    "KZ.CAT.BUYER_WORKHOLDING",
)

JOURNAL_CSV_COLUMNS = [
    "journal_entry_id",
    "decision_id",
    "decision_date",
    "decision_type",
    "b2_decision_group_id",
    "owner_statement_fa",
    "owner_architecture_decision_status",
    "linked_prerequisite_gate_ids",
    "category_apply_authorization",
    "product_reassignment_authorization",
    "seo_deployment_authorization",
    "production_mutation_authorization",
    "b2_review_snapshot_preserved",
    "notes_en",
]


@dataclass(frozen=True)
class JournalPaths:
    root: Path

    @property
    def journal_csv(self) -> Path:
        return self.root / "01-OWNER-ARCHITECTURE-DECISION-JOURNAL.csv"

    @property
    def identity_json(self) -> Path:
        return self.root / "00-JOURNAL-IDENTITY.json"

    @property
    def gate_json(self) -> Path:
        return self.root / "02-GATE-IR-MARKET-NAMING-SEO.json"

    @property
    def decision_md(self) -> Path:
        return self.root / "03-DECISION-ARCH-7-L1-ROOTS-2026-10-18.md"

    @property
    def pending_groups_csv(self) -> Path:
        return self.root / "04-B2-REMAINING-PENDING-DECISION-GROUPS.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_journal_entry_001() -> dict[str, str]:
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-001",
        "decision_id": DECISION_ID_ARCH_7_L1,
        "decision_date": "2026-10-18",
        "decision_type": "CONDITIONAL_ARCHITECTURE_ACCEPTANCE",
        "b2_decision_group_id": DECISION_ID_ARCH_7_L1,
        "owner_statement_fa": OWNER_STATEMENT_FA,
        "owner_architecture_decision_status": "CONDITIONAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            "Structural seven-root buyer architecture accepted; naming/SEO/URL/APPLY "
            "explicitly excluded. B2 CSV snapshot not rewritten."
        ),
    }


def build_gate_ir_market_naming_seo() -> dict[str, Any]:
    return {
        "gate_id": GATE_IR_MARKET_NAMING_SEO,
        "status": "PENDING_OWNER_REVIEW",
        "blocks_naming_and_seo_freeze": True,
        "blocks_category_apply": True,
        "blocks_seo_deployment": True,
        "required_evidence": [
            "Karzar Search Console query/page evidence where available",
            "Iranian-market terminology and competitor taxonomy research",
            "Search intent and keyword candidates for L1 and key descendants",
            "Proposed L1 display labels and SEO titles (FA/EN)",
            "Descendant landing-page naming implications",
            "URL/SEO preservation and migration risk assessment",
            "Explicit Owner approval before naming and SEO freeze",
        ],
        "linked_decision_journal_entry": "OWNER-ARCH-DECISION-001",
        "linked_b2_decision_group": DECISION_ID_ARCH_7_L1,
    }


def build_pending_b2_groups() -> list[dict[str, str]]:
    register = _read_csv(B2_DIR / "C-GROUPED-OWNER-DECISION-REGISTER.csv")
    rows: list[dict[str, str]] = []
    for row in register:
        gid = row["decision_group_id"]
        if gid == DECISION_ID_ARCH_7_L1:
            continue
        rows.append(
            {
                "decision_group_id": gid,
                "owner_architecture_decision_status": "PENDING",
                "source_artifact": "audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/C-GROUPED-OWNER-DECISION-REGISTER.csv",
                "note": "Unchanged B2 historical snapshot; not superseded by OWNER-ARCH-DECISION-001",
            }
        )
    return rows


def build_identity(generator_git_sha: str) -> dict[str, Any]:
    b2_register = B2_DIR / "C-GROUPED-OWNER-DECISION-REGISTER.csv"
    b2_recon = B2_DIR / "I-B2-RECONCILIATION-REPORT.json"
    return {
        "journal_policy": "APPEND_ONLY",
        "pr534_merge_sha": PR534_MERGE_SHA,
        "frozen_b2_review_dir": str(B2_DIR.relative_to(ROOT)),
        "frozen_b2_register_sha256": sha256_file(b2_register),
        "frozen_b2_reconciliation_sha256": sha256_file(b2_recon),
        "generator_run_git_sha": generator_git_sha,
        "interpretation": (
            "This journal records Owner architecture decisions. It does not mutate the "
            "frozen B2 review CSV statuses. Conditional acceptance is not APPLY, deploy, "
            "or SEO authorization."
        ),
        "safety": {
            "DESIGN_ONLY": "YES",
            "CATEGORY_APPLY": "NO",
            "PRODUCT_REASSIGNMENT": "NO",
            "SEO_DEPLOYMENT": "NO",
            "PRODUCTION_MUTATION": "NO",
        },
    }


def build_decision_markdown() -> str:
    l1_list = "\n".join(f"- `{code}`" for code in SEVEN_L1_COMMERCE_CODES)
    return "\n".join(
        [
            "# Owner Architecture Decision — ARCH-7-L1-ROOTS",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-001` |",
            "| **DECISION_ID** | `ARCH-7-L1-ROOTS` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `CONDITIONAL_ARCHITECTURE_ACCEPTANCE` |",
            "| **B2 link** | `audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/` → group `ARCH-7-L1-ROOTS` |",
            "| **Prerequisite gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |",
            "",
            "## Owner statement (FA)",
            "",
            OWNER_STATEMENT_FA,
            "",
            "## Approved scope (structural)",
            "",
            "- Seven buyer-facing L1 commerce roots (distinct from seven scientific domains).",
            "- Codes:",
            l1_list,
            "",
            "## Explicitly NOT approved",
            "",
            "- Final Persian/English display names, menu labels, H1, metadata/SEO copy.",
            "- Slugs, URLs, canonical/redirect decisions.",
            "- Product category reassignment, runtime category create/delete.",
            "- `CATEGORY_APPLY`, production deploy, SEO deploy.",
            "",
            "## B2 snapshot policy",
            "",
            "Merged B2 remains an immutable historical review artifact. "
            "`C-GROUPED-OWNER-DECISION-REGISTER.csv` still shows `PENDING` for this group; "
            "this journal entry is the authoritative Owner record for conditional acceptance.",
            "",
            "## Other B2 groups",
            "",
            "Nine decision groups remain `PENDING` — see `04-B2-REMAINING-PENDING-DECISION-GROUPS.csv`.",
        ]
    )


def validate_journal_package(paths: JournalPaths) -> dict[str, Any]:
    errors: list[str] = []
    if not paths.journal_csv.is_file():
        errors.append("missing_journal_csv")
        return {"status": "FAIL", "errors": errors}

    rows = _read_csv(paths.journal_csv)
    if len(rows) != 1:
        errors.append("journal_must_have_single_entry_v001")

    entry = rows[0] if rows else {}
    if entry.get("decision_id") != DECISION_ID_ARCH_7_L1:
        errors.append("decision_id_mismatch")
    if entry.get("decision_type") != "CONDITIONAL_ARCHITECTURE_ACCEPTANCE":
        errors.append("decision_type_mismatch")
    for auth_field in (
        "category_apply_authorization",
        "product_reassignment_authorization",
        "seo_deployment_authorization",
        "production_mutation_authorization",
    ):
        if entry.get(auth_field) != "NO":
            errors.append(f"{auth_field}_not_no")

    b2_rows = _read_csv(B2_DIR / "C-GROUPED-OWNER-DECISION-REGISTER.csv")
    arch7 = next((r for r in b2_rows if r["decision_group_id"] == DECISION_ID_ARCH_7_L1), None)
    if not arch7:
        errors.append("b2_missing_arch7_group")
    elif arch7.get("owner_architecture_decision_status") != "PENDING":
        errors.append("b2_arch7_snapshot_must_remain_pending")

    pending = _read_csv(paths.pending_groups_csv) if paths.pending_groups_csv.is_file() else []
    if len(pending) != 9:
        errors.append(f"pending_groups_count_{len(pending)}_not_9")

    gate = json.loads(paths.gate_json.read_text(encoding="utf-8"))
    if gate.get("status") != "PENDING_OWNER_REVIEW":
        errors.append("gate_not_pending")
    if gate.get("gate_id") != GATE_IR_MARKET_NAMING_SEO:
        errors.append("gate_id_mismatch")

    identity = json.loads(paths.identity_json.read_text(encoding="utf-8"))
    if identity.get("safety", {}).get("CATEGORY_APPLY") != "NO":
        errors.append("identity_safety_apply")

    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def write_journal_package(out_dir: Path, *, generator_git_sha: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = JournalPaths(out_dir)

    paths.identity_json.write_text(
        json.dumps(build_identity(generator_git_sha), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths.gate_json.write_text(
        json.dumps(build_gate_ir_market_naming_seo(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths.decision_md.write_text(build_decision_markdown(), encoding="utf-8")

    with paths.journal_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=JOURNAL_CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(build_journal_entry_001())

    pending = build_pending_b2_groups()
    with paths.pending_groups_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["decision_group_id", "owner_architecture_decision_status", "source_artifact", "note"],
        )
        writer.writeheader()
        writer.writerows(pending)

    readme = "\n".join(
        [
            "# Owner Architecture Decision Journal (Phase 1B)",
            "",
            "Append-only Owner architecture decisions. Does **not** modify frozen B2 artifacts.",
            "",
            "```bash",
            "python3 scripts/audit_taxonomy_owner_architecture_decision_journal.py",
            "```",
            "",
            f"PR #534 merge: `{PR534_MERGE_SHA}`",
        ]
    )
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    validation = validate_journal_package(paths)
    closeout = [
        "# Owner Architecture Decision Journal — validation closeout",
        "",
        f"**{validation['status']}**",
        "",
        json.dumps(validation, indent=2),
    ]
    (out_dir / "J-VALIDATION-CLOSEOUT-REPORT.md").write_text("\n".join(closeout), encoding="utf-8")

    artifacts = [
        "00-JOURNAL-IDENTITY.json",
        "01-OWNER-ARCHITECTURE-DECISION-JOURNAL.csv",
        "02-GATE-IR-MARKET-NAMING-SEO.json",
        "03-DECISION-ARCH-7-L1-ROOTS-2026-10-18.md",
        "04-B2-REMAINING-PENDING-DECISION-GROUPS.csv",
        "README.md",
        "J-VALIDATION-CLOSEOUT-REPORT.md",
    ]
    write_sha256sums(out_dir, artifacts)

    if validation["status"] != "PASS":
        raise RuntimeError("JOURNAL_VALIDATION_FAILED: " + "; ".join(validation["errors"]))
    return {"validation": validation, "journal_entry": build_journal_entry_001()}
