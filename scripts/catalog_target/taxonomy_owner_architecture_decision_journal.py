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
DECISION_ID_METROLOGY_L2 = "METROLOGY-L2-FAMILIES"
DECISION_ID_ACCESSORIES_154 = "ACCESSORIES-154-DECOMPOSE"
DECISION_ID_FLUIDS_155 = "FLUIDS-155-FACET-NAV"
GATE_IR_MARKET_NAMING_SEO = "IR-MARKET-NAMING-SEO"

OWNER_DECIDED_B2_GROUP_IDS = frozenset(
    {
        DECISION_ID_ARCH_7_L1,
        DECISION_ID_METROLOGY_L2,
        DECISION_ID_ACCESSORIES_154,
        DECISION_ID_FLUIDS_155,
    }
)

B2_TOTAL_DECISION_GROUPS = 10
B2_PENDING_GROUP_COUNT = B2_TOTAL_DECISION_GROUPS - len(OWNER_DECIDED_B2_GROUP_IDS)

JOURNAL_ENTRY_SPECS: tuple[tuple[str, str, str], ...] = (
    ("OWNER-ARCH-DECISION-001", DECISION_ID_ARCH_7_L1, "CONDITIONAL_ARCHITECTURE_ACCEPTANCE"),
    ("OWNER-ARCH-DECISION-002", DECISION_ID_METROLOGY_L2, "STRUCTURAL_ARCHITECTURE_APPROVAL"),
    ("OWNER-ARCH-DECISION-003", DECISION_ID_ACCESSORIES_154, "CONDITIONAL_STRUCTURAL_APPROVAL"),
    ("OWNER-ARCH-DECISION-004", DECISION_ID_FLUIDS_155, "STRUCTURAL_ARCHITECTURE_APPROVAL"),
)

LEGACY_CATEGORY_154_ID = "154"
LEGACY_CATEGORY_154_DESCENDANT_PRODUCT_COUNT = 289
LEGACY_CATEGORY_154_STAGING_CODE = "KZ.CAT.TRANSITIONAL_INDUSTRIAL_ACCESSORIES_HUB_154"

LEGACY_CATEGORY_155_ID = "155"
LEGACY_CATEGORY_156_ID = "156"
LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT = 27
LEGACY_CATEGORY_155_FACET_CODE = "KZ.CAT.TRANSITIONAL_LUBRICANTS_FACET_155"
FLUIDS_INDUSTRIAL_OIL_CODE = "KZ.CAT.FLUIDS_INDUSTRIAL_OIL"
FLUIDS_COMMERCE_ROOT_CODE = "KZ.CAT.BUYER_FLUIDS"
B2_PENDING_FLUIDS_156_PUBLICATION = "FLUIDS-156-PUBLICATION"

OWNER_STATEMENT_FA = (
    "«به‌عنوان مالک، هفت ریشهٔ معماری پیشنهادی را به‌صورت مشروط می‌پذیرم، "
    "اما نام‌های نمایشی، عناوین سئو و URLها را هنوز تأیید نمی‌کنم. "
    "تحقیق نام‌گذاری بازار ایران را به‌عنوان یک گیت مستقل ثبت کنیم؛ "
    "هیچ APPLY یا Deploy مجاز نیست.»"
)

OWNER_STATEMENT_METROLOGY_L2_FA = "«با همین سه تا موافقم.»"

METROLOGY_L2_FAMILY_CODES = (
    "KZ.CAT.METROLOGY_FAMILY_PRECISION",
    "KZ.CAT.METROLOGY_FAMILY_CNC",
    "KZ.CAT.METROLOGY_FAMILY_LABORATORY",
)
METROLOGY_L2_PARENT_CODE = "KZ.CAT.BUYER_METROLOGY"

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
    def decision_md_arch7(self) -> Path:
        return self.root / "03-DECISION-ARCH-7-L1-ROOTS-2026-10-18.md"

    @property
    def decision_md_metrology_l2(self) -> Path:
        return self.root / "05-DECISION-METROLOGY-L2-FAMILIES-2026-10-18.md"

    @property
    def decision_md_accessories_154(self) -> Path:
        return self.root / "06-DECISION-ACCESSORIES-154-DECOMPOSE-2026-10-18.md"

    @property
    def decision_md_fluids_155(self) -> Path:
        return self.root / "07-DECISION-FLUIDS-155-FACET-NAV-2026-10-18.md"

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


def build_journal_entry_002() -> dict[str, str]:
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-002",
        "decision_id": DECISION_ID_METROLOGY_L2,
        "decision_date": "2026-10-18",
        "decision_type": "STRUCTURAL_ARCHITECTURE_APPROVAL",
        "b2_decision_group_id": DECISION_ID_METROLOGY_L2,
        "owner_statement_fa": OWNER_STATEMENT_METROLOGY_L2_FA,
        "owner_architecture_decision_status": "STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            "Three Metrology L2 families approved with B1 KZ.CAT.* identities under "
            "BUYER_METROLOGY; display/SEO/URL naming gated by IR-MARKET-NAMING-SEO; "
            "no product-level mapping approval."
        ),
    }


def build_journal_entry_003() -> dict[str, str]:
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-003",
        "decision_id": DECISION_ID_ACCESSORIES_154,
        "decision_date": "2026-10-18",
        "decision_type": "CONDITIONAL_STRUCTURAL_APPROVAL",
        "b2_decision_group_id": DECISION_ID_ACCESSORIES_154,
        "owner_statement_fa": (
            "«تجزیهٔ کنترل‌شدهٔ لوازم جانبی صنعتی (دسته ۱۵۴) را تأیید می‌کنم: "
            "حفظ هویت انتقالی، پوشش ۲۸۹ محصول، مقصد دامنه‌محور بر اساس مدرک، "
            "بدون حذف دسته‌ای یا تخصیص خودکار؛ اجرا و APPLY جداگانه.»"
        ),
        "owner_architecture_decision_status": "CONDITIONAL_STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Controlled decomposition of legacy category {LEGACY_CATEGORY_154_ID} "
            f"({LEGACY_CATEGORY_154_DESCENDANT_PRODUCT_COUNT} descendant product IDs); "
            f"preserve {LEGACY_CATEGORY_154_STAGING_CODE} as TRANSITIONAL; protect oils "
            "cohort; retire legacy nav only after validated migration, SEO review, and "
            "separate Owner execution approval."
        ),
    }


def build_journal_entry_004() -> dict[str, str]:
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-004",
        "decision_id": DECISION_ID_FLUIDS_155,
        "decision_date": "2026-10-18",
        "decision_type": "STRUCTURAL_ARCHITECTURE_APPROVAL",
        "b2_decision_group_id": DECISION_ID_FLUIDS_155,
        "owner_statement_fa": (
            "«خروج دسته ۱۵۵ از ناوبری خریدار مستقل را تأیید می‌کنم: روغن‌های صنعتی "
            "تحت ریشه FLUIDS؛ ۱۵۶ برگ تخصصی؛ ۲۷ محصول محافظت‌شده؛ هویت عددی تا اجرای "
            "جداگانه؛ انتشار ۱۵۶ هنوز تصمیم جداست.»"
        ),
        "owner_architecture_decision_status": "STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Retire legacy category {LEGACY_CATEGORY_155_ID} as independent buyer-facing "
            f"commerce node; oils under {FLUIDS_COMMERCE_ROOT_CODE}; "
            f"{LEGACY_CATEGORY_156_ID} remains proposed leaf {FLUIDS_INDUSTRIAL_OIL_CODE} "
            f"({LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT} protected product IDs); "
            f"preserve numeric {LEGACY_CATEGORY_155_ID} for importer compatibility; "
            f"{B2_PENDING_FLUIDS_156_PUBLICATION} not implied approved."
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
        "linked_decision_journal_entries": [spec[0] for spec in JOURNAL_ENTRY_SPECS],
        "linked_b2_decision_groups": sorted(OWNER_DECIDED_B2_GROUP_IDS),
    }


def build_pending_b2_groups() -> list[dict[str, str]]:
    register = _read_csv(B2_DIR / "C-GROUPED-OWNER-DECISION-REGISTER.csv")
    rows: list[dict[str, str]] = []
    for row in register:
        gid = row["decision_group_id"]
        if gid in OWNER_DECIDED_B2_GROUP_IDS:
            continue
        rows.append(
            {
                "decision_group_id": gid,
                "owner_architecture_decision_status": "PENDING",
                "source_artifact": "audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/C-GROUPED-OWNER-DECISION-REGISTER.csv",
                "note": "Unchanged B2 historical snapshot; Owner record in journal when decided",
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
        "journal_entry_count": len(JOURNAL_ENTRY_SPECS),
        "owner_decided_b2_groups": sorted(OWNER_DECIDED_B2_GROUP_IDS),
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


def build_decision_markdown_arch7() -> str:
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
            "Remaining B2 groups — see `04-B2-REMAINING-PENDING-DECISION-GROUPS.csv`.",
        ]
    )


def build_decision_markdown_metrology_l2() -> str:
    families = "\n".join(
        f"- `{code}` (parent `{METROLOGY_L2_PARENT_CODE}`)" for code in METROLOGY_L2_FAMILY_CODES
    )
    return "\n".join(
        [
            "# Owner Architecture Decision — METROLOGY-L2-FAMILIES",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-002` |",
            "| **DECISION_ID** | `METROLOGY-L2-FAMILIES` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |",
            "| **B2 link** | `audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/` → group `METROLOGY-L2-FAMILIES` |",
            "| **Naming gate** | `IR-MARKET-NAMING-SEO` (display/SEO/URL not approved) |",
            "",
            "## Owner statement (FA)",
            "",
            OWNER_STATEMENT_METROLOGY_L2_FA,
            "",
            "## Approved scope (structural)",
            "",
            "Exactly three L2 families under the Metrology commerce root, preserving B1 identities:",
            families,
            "",
            "## Explicitly NOT approved",
            "",
            "- Final display names, SEO titles, H1, URLs, slugs (IR-MARKET-NAMING-SEO).",
            "- Product-level category mapping or reassignment.",
            "- `CATEGORY_APPLY`, production deploy, SEO deploy.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `METROLOGY-L2-FAMILIES`; this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_accessories_154() -> str:
    return "\n".join(
        [
            "# Owner Architecture Decision — ACCESSORIES-154-DECOMPOSE",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-003` |",
            "| **DECISION_ID** | `ACCESSORIES-154-DECOMPOSE` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |",
            f"| **Legacy category** | `{LEGACY_CATEGORY_154_ID}` — Industrial Accessories |",
            f"| **Staging code** | `{LEGACY_CATEGORY_154_STAGING_CODE}` |",
            f"| **Descendant product IDs** | {LEGACY_CATEGORY_154_DESCENDANT_PRODUCT_COUNT} (census graph) |",
            "| **B2 link** | group `ACCESSORIES-154-DECOMPOSE` |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (mandatory) |",
            "",
            "## Approved architecture",
            "",
            "- Preserve category **154** as **TRANSITIONAL** during migration planning.",
            f"- Account for all **{LEGACY_CATEGORY_154_DESCENDANT_PRODUCT_COUNT}** descendant live product IDs.",
            "- Design domain-specific destinations from technical identity and evidence.",
            "- Preserve protected subtrees/cohorts (including industrial oils under FLUIDS).",
            "- No blanket deletion or automatic product reassignment.",
            "- Retire legacy navigation only after validated migration, SEO review, and separate Owner execution approval.",
            "",
            "## Explicitly NOT approved",
            "",
            "- Production mutation, category deletion, product reassignment, redirects, `CATEGORY_APPLY`.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `ACCESSORIES-154-DECOMPOSE`; this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_fluids_155() -> str:
    return "\n".join(
        [
            "# Owner Architecture Decision — FLUIDS-155-FACET-NAV",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-004` |",
            "| **DECISION_ID** | `FLUIDS-155-FACET-NAV` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |",
            f"| **Legacy category 155** | Lubricants facet — `{LEGACY_CATEGORY_155_FACET_CODE}` |",
            f"| **Proposed leaf 156** | `{FLUIDS_INDUSTRIAL_OIL_CODE}` under `{FLUIDS_COMMERCE_ROOT_CODE}` |",
            f"| **Protected product IDs** | {LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT} (category {LEGACY_CATEGORY_156_ID} cohort) |",
            "| **B2 link** | group `FLUIDS-155-FACET-NAV` |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |",
            "",
            "## Approved structural direction",
            "",
            f"- Industrial oils belong under the **FLUIDS** commerce root (`{FLUIDS_COMMERCE_ROOT_CODE}`).",
            f"- Category **{LEGACY_CATEGORY_156_ID}** remains the proposed specialized industrial-oil leaf (`{FLUIDS_INDUSTRIAL_OIL_CODE}`).",
            f"- Preserve all **{LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT}** protected product IDs.",
            f"- Category **{LEGACY_CATEGORY_155_ID}** must **not** become an independently selectable commerce landing page in the target design.",
            f"- Preserve existing numeric category **{LEGACY_CATEGORY_155_ID}** identity and importer compatibility until separate Owner execution approval.",
            "",
            "## Explicitly NOT approved / not implied",
            "",
            f"- **`{B2_PENDING_FLUIDS_156_PUBLICATION}`** — publication of category 156 is a separate pending Owner decision.",
            "- Display names, SEO titles, H1, URLs, slugs (`IR-MARKET-NAMING-SEO`).",
            "- Production mutation, product reassignment, redirects, `CATEGORY_APPLY`.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `FLUIDS-155-FACET-NAV`; this journal entry is authoritative.",
        ]
    )


def _validate_journal_entry(row: dict[str, str], errors: list[str]) -> None:
    for auth_field in (
        "category_apply_authorization",
        "product_reassignment_authorization",
        "seo_deployment_authorization",
        "production_mutation_authorization",
    ):
        if row.get(auth_field) != "NO":
            errors.append(f"{row.get('journal_entry_id')}_{auth_field}_not_no")


def validate_journal_package(paths: JournalPaths) -> dict[str, Any]:
    errors: list[str] = []
    if not paths.journal_csv.is_file():
        errors.append("missing_journal_csv")
        return {"status": "FAIL", "errors": errors}

    rows = _read_csv(paths.journal_csv)
    if len(rows) != len(JOURNAL_ENTRY_SPECS):
        errors.append(f"journal_entry_count_{len(rows)}_not_{len(JOURNAL_ENTRY_SPECS)}")

    by_id = {r["journal_entry_id"]: r for r in rows}
    for journal_id, decision_id, decision_type in JOURNAL_ENTRY_SPECS:
        entry = by_id.get(journal_id)
        if not entry or entry.get("decision_id") != decision_id:
            errors.append(f"{journal_id}_decision_id_mismatch")
        elif entry.get("decision_type") != decision_type:
            errors.append(f"{journal_id}_type_mismatch")
    for row in rows:
        _validate_journal_entry(row, errors)

    b2_rows = _read_csv(B2_DIR / "C-GROUPED-OWNER-DECISION-REGISTER.csv")
    for gid in OWNER_DECIDED_B2_GROUP_IDS:
        b2_row = next((r for r in b2_rows if r["decision_group_id"] == gid), None)
        if not b2_row:
            errors.append(f"b2_missing_{gid}")
        elif b2_row.get("owner_architecture_decision_status") != "PENDING":
            errors.append(f"b2_{gid}_snapshot_must_remain_pending")

    pending = _read_csv(paths.pending_groups_csv) if paths.pending_groups_csv.is_file() else []
    if len(pending) != B2_PENDING_GROUP_COUNT:
        errors.append(f"pending_groups_count_{len(pending)}_not_{B2_PENDING_GROUP_COUNT}")

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
    paths.decision_md_arch7.write_text(build_decision_markdown_arch7(), encoding="utf-8")
    paths.decision_md_metrology_l2.write_text(build_decision_markdown_metrology_l2(), encoding="utf-8")
    paths.decision_md_accessories_154.write_text(
        build_decision_markdown_accessories_154(), encoding="utf-8"
    )
    paths.decision_md_fluids_155.write_text(build_decision_markdown_fluids_155(), encoding="utf-8")

    with paths.journal_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=JOURNAL_CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(build_journal_entry_001())
        writer.writerow(build_journal_entry_002())
        writer.writerow(build_journal_entry_003())
        writer.writerow(build_journal_entry_004())

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
        "05-DECISION-METROLOGY-L2-FAMILIES-2026-10-18.md",
        "06-DECISION-ACCESSORIES-154-DECOMPOSE-2026-10-18.md",
        "07-DECISION-FLUIDS-155-FACET-NAV-2026-10-18.md",
        "04-B2-REMAINING-PENDING-DECISION-GROUPS.csv",
        "README.md",
        "J-VALIDATION-CLOSEOUT-REPORT.md",
    ]
    write_sha256sums(out_dir, artifacts)

    if validation["status"] != "PASS":
        raise RuntimeError("JOURNAL_VALIDATION_FAILED: " + "; ".join(validation["errors"]))
    return {
        "validation": validation,
        "journal_entries": [
            build_journal_entry_001(),
            build_journal_entry_002(),
            build_journal_entry_003(),
            build_journal_entry_004(),
        ],
    }
