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
DECISION_ID_FLUIDS_156_PUBLICATION = "FLUIDS-156-PUBLICATION"
DECISION_ID_MACHINE_ACCESSORIES_163_164 = "MACHINE-ACCESSORIES-163-164"
DECISION_ID_TX_OWNER_SCOPE_157_160 = "TX-OWNER-SCOPE-157-160"
DECISION_ID_MIXED_CHUCKS_116_118 = "MIXED-CHUCKS-116-118"
DECISION_ID_HELICOIL_55_THREAD_REPAIR = "HELICOIL-55-THREAD-REPAIR"
DECISION_ID_MEGAMENU_186_187_188 = "MEGAMENU-186-187-188"
B2_PENDING_MEGAMENU_HELICOIL_NAV = DECISION_ID_MEGAMENU_186_187_188
GATE_IR_MARKET_NAMING_SEO = "IR-MARKET-NAMING-SEO"

OWNER_DECIDED_B2_GROUP_IDS = frozenset(
    {
        DECISION_ID_ARCH_7_L1,
        DECISION_ID_METROLOGY_L2,
        DECISION_ID_ACCESSORIES_154,
        DECISION_ID_FLUIDS_155,
        DECISION_ID_FLUIDS_156_PUBLICATION,
        DECISION_ID_MACHINE_ACCESSORIES_163_164,
        DECISION_ID_TX_OWNER_SCOPE_157_160,
        DECISION_ID_MIXED_CHUCKS_116_118,
        DECISION_ID_HELICOIL_55_THREAD_REPAIR,
        DECISION_ID_MEGAMENU_186_187_188,
    }
)

B2_TOTAL_DECISION_GROUPS = 10
BASELINE_LIVE_PRODUCT_ROWS = 6536
BASELINE_PRODUCT_LEVEL_REQUIRED = 718
BASELINE_APPROVED_EXECUTABLE_TARGET_CODES = 0
B2_PENDING_GROUP_COUNT = B2_TOTAL_DECISION_GROUPS - len(OWNER_DECIDED_B2_GROUP_IDS)

JOURNAL_ENTRY_SPECS: tuple[tuple[str, str, str], ...] = (
    ("OWNER-ARCH-DECISION-001", DECISION_ID_ARCH_7_L1, "CONDITIONAL_ARCHITECTURE_ACCEPTANCE"),
    ("OWNER-ARCH-DECISION-002", DECISION_ID_METROLOGY_L2, "STRUCTURAL_ARCHITECTURE_APPROVAL"),
    ("OWNER-ARCH-DECISION-003", DECISION_ID_ACCESSORIES_154, "CONDITIONAL_STRUCTURAL_APPROVAL"),
    ("OWNER-ARCH-DECISION-004", DECISION_ID_FLUIDS_155, "STRUCTURAL_ARCHITECTURE_APPROVAL"),
    ("OWNER-ARCH-DECISION-005", DECISION_ID_FLUIDS_156_PUBLICATION, "CONDITIONAL_STRUCTURAL_APPROVAL"),
    (
        "OWNER-ARCH-DECISION-006",
        DECISION_ID_MACHINE_ACCESSORIES_163_164,
        "CONDITIONAL_STRUCTURAL_APPROVAL",
    ),
    ("OWNER-ARCH-DECISION-007", DECISION_ID_TX_OWNER_SCOPE_157_160, "STRUCTURAL_ARCHITECTURE_APPROVAL"),
    ("OWNER-ARCH-DECISION-008", DECISION_ID_MIXED_CHUCKS_116_118, "CONDITIONAL_STRUCTURAL_APPROVAL"),
    ("OWNER-ARCH-DECISION-009", DECISION_ID_HELICOIL_55_THREAD_REPAIR, "STRUCTURAL_ARCHITECTURE_APPROVAL"),
    ("OWNER-ARCH-DECISION-010", DECISION_ID_MEGAMENU_186_187_188, "EXECUTION_DESIGN_DIRECTION_APPROVAL"),
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

LEGACY_CATEGORY_163_ID = "163"
LEGACY_CATEGORY_164_ID = "164"
LEGACY_CATEGORY_164_PRODUCT_COUNT = 80
LEGACY_CATEGORY_163_STAGING_CODE = "KZ.CAT.TRANSITIONAL_MACHINE_ACCESSORIES_HUB_163"
MACHINES_COMMERCE_ROOT_CODE = "KZ.CAT.BUYER_MACHINES"

TX_OWNER_001_PACKAGE_DIR = "audit/taxonomy-phase1b-tx-owner-001-owner-decision-package"
TX_OWNER_SCOPE_CATEGORY_IDS = ("157", "158", "159", "160")
TX_OWNER_001_COHORT_PRODUCT_COUNT = 262
TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT = 151
TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT = 111
TX_OWNER_DEPRECATED_TARGET_CODES = (
    "KZ.CAT.DEPRECATED_TX_OWNER_HAND_TOOLS_157",
    "KZ.CAT.DEPRECATED_TX_OWNER_HAND_TOOLS_158",
    "KZ.CAT.DEPRECATED_TX_OWNER_WOODWORKING_159",
    "KZ.CAT.DEPRECATED_TX_OWNER_WOODWORKING_160",
)

MIXED_CHUCK_CATEGORY_IDS = ("116", "117", "118")
MIXED_CHUCK_PLR_COUNT_BY_CATEGORY = {"116": 571, "117": 40, "118": 0}
MIXED_CHUCK_PLR_TOTAL = 611
MIXED_CHUCK_STAGING_CODES = (
    "KZ.CAT.STAGING_LATHE_CHUCK_MIXED_116",
    "KZ.CAT.STAGING_FOUR_JAW_MIXED_117",
    "KZ.CAT.STAGING_TWO_JAW_MIXED_118",
)
WORKHOLDING_COMMERCE_ROOT_CODE = "KZ.CAT.BUYER_WORKHOLDING"

LEGACY_CATEGORY_55_ID = "55"
HELICOIL_LIVE_PRODUCT_COUNT = 29
THREAD_REPAIR_SCIENTIFIC_DOMAIN = "KZ.DOM.THREAD_REPAIR"
HELICOIL_COMMERCE_IDENTITY_CODE = "KZ.CAT.THREAD_REPAIR_HELICOIL_KITS"
THREAD_REPAIR_COMMERCE_ROOT_CODE = "KZ.CAT.BUYER_THREAD_REPAIR"
DEPRECATED_HELICOIL_HISTORIC_CATEGORY_IDS = ("186", "187", "188")
DEPRECATED_HELICOIL_HISTORIC_CODES = (
    "KZ.CAT.DEPRECATED_HELICOIL_L1_SPRING_INSERT_ROOT",
    "KZ.CAT.DEPRECATED_HELICOIL_L1_TAP_RANGE_ROOT",
    "KZ.CAT.DEPRECATED_HELICOIL_L1_INSTALL_TOOL_ROOT",
)
B2_SENSITIVE_CATEGORY_DOSSIER = (
    "audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18/"
    "E-SENSITIVE-CATEGORY-DOSSIER.csv"
)

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
    def decision_md_fluids_156(self) -> Path:
        return self.root / "08-DECISION-FLUIDS-156-PUBLICATION-2026-10-18.md"

    @property
    def decision_md_machine_accessories_163_164(self) -> Path:
        return self.root / "09-DECISION-MACHINE-ACCESSORIES-163-164-2026-10-18.md"

    @property
    def decision_md_tx_owner_scope_157_160(self) -> Path:
        return self.root / "10-DECISION-TX-OWNER-SCOPE-157-160-2026-10-18.md"

    @property
    def decision_md_mixed_chucks_116_118(self) -> Path:
        return self.root / "11-DECISION-MIXED-CHUCKS-116-118-2026-10-18.md"

    @property
    def decision_md_helicoil_55(self) -> Path:
        return self.root / "12-DECISION-HELICOIL-55-THREAD-REPAIR-2026-10-18.md"

    @property
    def decision_md_megamenu_186_187_188(self) -> Path:
        return self.root / "13-DECISION-MEGAMENU-186-187-188-2026-10-18.md"

    @property
    def effective_state_json(self) -> Path:
        return self.root / "14-EFFECTIVE-DECISION-STATE-SUMMARY.json"

    @property
    def execution_gates_json(self) -> Path:
        return self.root / "15-EXECUTION-GATES-REGISTER.json"

    @property
    def hold_reconciliation_csv(self) -> Path:
        return self.root / "16-HOLD-CATEGORY-TO-DECISION-RECONCILIATION.csv"

    @property
    def owner_closeout_md(self) -> Path:
        return self.root / "K-OWNER-ARCHITECTURE-CLOSEOUT-REPORT.md"

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
            f"{DECISION_ID_FLUIDS_156_PUBLICATION} not implied approved."
        ),
    }


def build_journal_entry_005() -> dict[str, str]:
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-005",
        "decision_id": DECISION_ID_FLUIDS_156_PUBLICATION,
        "decision_date": "2026-10-18",
        "decision_type": "CONDITIONAL_STRUCTURAL_APPROVAL",
        "b2_decision_group_id": DECISION_ID_FLUIDS_156_PUBLICATION,
        "owner_statement_fa": (
            "«جایگاه ساختاری دسته ۱۵۶ (روغن صنعتی) تحت ریشه FLUIDS را می‌پذیرم؛ "
            "۲۷ محصول و هویت KZ.CAT.FLUIDS_INDUSTRIAL_OIL؛ جداسازی از ۱۵۵؛ "
            "انتشار واقعی، نام فارسی، سئو، URL و APPLY هنوز مجاز نیست.»"
        ),
        "owner_architecture_decision_status": "CONDITIONAL_STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Structural placement of category {LEGACY_CATEGORY_156_ID} under "
            f"{FLUIDS_COMMERCE_ROOT_CODE} with {FLUIDS_INDUSTRIAL_OIL_CODE}; "
            f"{LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT} protected product IDs; "
            "separation from legacy 155; cohort protected from blanket removal/reassignment. "
            "B2 group name says PUBLICATION but Owner approves architecture ONLY — "
            "runtime publication, naming/SEO/URL, APPLY, and deploy remain NO."
        ),
    }


def build_journal_entry_006() -> dict[str, str]:
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-006",
        "decision_id": DECISION_ID_MACHINE_ACCESSORIES_163_164,
        "decision_date": "2026-10-18",
        "decision_type": "CONDITIONAL_STRUCTURAL_APPROVAL",
        "b2_decision_group_id": DECISION_ID_MACHINE_ACCESSORIES_163_164,
        "owner_statement_fa": (
            "«تجزیهٔ ساختاری کنترل‌شدهٔ دسته‌های ۱۶۳ و ۱۶۴ را تأیید می‌کنم: "
            "۱۶۳ انتقالی؛ ۸۰ محصول ۱۶۴؛ مقصد برگ تخصصی در MACHINES بر اساس مدرک فنی؛ "
            "بدون دستهٔ عمومی جایگزین؛ PRODUCT_LEVEL_REQUIRED هنوز مسدود.»"
        ),
        "owner_architecture_decision_status": "CONDITIONAL_STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Controlled decomposition of categories {LEGACY_CATEGORY_163_ID} and "
            f"{LEGACY_CATEGORY_164_ID}; keep {LEGACY_CATEGORY_163_ID} TRANSITIONAL "
            f"({LEGACY_CATEGORY_163_STAGING_CODE}); preserve all "
            f"{LEGACY_CATEGORY_164_PRODUCT_COUNT} products under {LEGACY_CATEGORY_164_ID}; "
            f"specialized leaves under {MACHINES_COMMERCE_ROOT_CODE} from per-product evidence; "
            "no generic catch-all substitute; 80 PRODUCT_LEVEL_REQUIRED records blocked."
        ),
    }


def build_journal_entry_007() -> dict[str, str]:
    scope_ids = "|".join(TX_OWNER_SCOPE_CATEGORY_IDS)
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-007",
        "decision_id": DECISION_ID_TX_OWNER_SCOPE_157_160,
        "decision_date": "2026-10-18",
        "decision_type": "STRUCTURAL_ARCHITECTURE_APPROVAL",
        "b2_decision_group_id": DECISION_ID_TX_OWNER_SCOPE_157_160,
        "owner_statement_fa": (
            "«دسته‌های ۱۵۷–۱۶۰ را از معماری هفت‌ریشهٔ تخصصی خارج می‌کنم؛ "
            "DEPRECATED فقط در طراحی هدف؛ TX-OWNER-001 (۱۵۱ خروج سندی، ۱۱۱ مدرک باز، "
            "۲۶۲ محصول) بدون تغییر؛ بدون حذف دسته‌ای، تخصیص خودکار یا APPLY.»"
        ),
        "owner_architecture_decision_status": "STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Exclude legacy categories {scope_ids} from future seven-root commerce; "
            "DEPRECATED in target design only. Preserve immutable TX-OWNER-001 journals: "
            f"{TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT} APPROVE_CATALOG_EXIT (documentary, not APPLY); "
            f"{TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT} REQUEST_MORE_EVIDENCE (open); "
            f"{TX_OWNER_001_COHORT_PRODUCT_COUNT} product IDs total. No blanket deletion, "
            "auto retirement, reassignment, redirect, or 410; production requires separate "
            "per-product evidence and Owner execution authorization."
        ),
    }


def build_journal_entry_008() -> dict[str, str]:
    scope_ids = "|".join(MIXED_CHUCK_CATEGORY_IDS)
    plr_breakdown = (
        f"116={MIXED_CHUCK_PLR_COUNT_BY_CATEGORY['116']}; "
        f"117={MIXED_CHUCK_PLR_COUNT_BY_CATEGORY['117']}; "
        f"118={MIXED_CHUCK_PLR_COUNT_BY_CATEGORY['118']}"
    )
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-008",
        "decision_id": DECISION_ID_MIXED_CHUCKS_116_118,
        "decision_date": "2026-10-18",
        "decision_type": "CONDITIONAL_STRUCTURAL_APPROVAL",
        "b2_decision_group_id": DECISION_ID_MIXED_CHUCKS_116_118,
        "owner_statement_fa": (
            "«تجزیهٔ کنترل‌شدهٔ نظام‌های ۱۱۶–۱۱۸ را تأیید می‌کنم: تفکیک نظام از لوازم "
            "بر اساس هویت فنی؛ ۶۱۱ PRODUCT_LEVEL_REQUIRED (۵۷۱/۴۰/۰)؛ STAGING/HOLD تا "
            "پیش‌نیازهای مهاجرت؛ حذف ۱۱۸ به‌خاطر صفر ممنوع؛ بدون catch-all عمومی.»"
        ),
        "owner_architecture_decision_status": "CONDITIONAL_STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Controlled decomposition of categories {scope_ids}; separate chucks from "
            "accessories by technical identity; preserve "
            f"{MIXED_CHUCK_PLR_TOTAL} PRODUCT_LEVEL_REQUIRED ({plr_breakdown}); "
            "STAGING/HOLD until validated migration prerequisites; per-product evidence "
            "and destination review; do not delete category 118 for zero cohort; no generic "
            f"mixed catch-all under {WORKHOLDING_COMMERCE_ROOT_CODE}. Structural approval only."
        ),
    }


def build_journal_entry_009() -> dict[str, str]:
    historic_ids = "|".join(DEPRECATED_HELICOIL_HISTORIC_CATEGORY_IDS)
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-009",
        "decision_id": DECISION_ID_HELICOIL_55_THREAD_REPAIR,
        "decision_date": "2026-10-18",
        "decision_type": "STRUCTURAL_ARCHITECTURE_APPROVAL",
        "b2_decision_group_id": DECISION_ID_HELICOIL_55_THREAD_REPAIR,
        "owner_statement_fa": (
            "«دسته ۵۵ (هلی‌کویل) را تحت دامنه THREAD_REPAIR و "
            "KZ.CAT.THREAD_REPAIR_HELICOIL_KITS می‌پذیرم؛ ۲۹ محصول از دوسیه B2؛ "
            "جداسازی از CUTTING؛ لینک زمینه‌ای از قلاویز بدون تخصیص دستهٔ تکراری؛ "
            f"۱۸۶/۱۸۷/۱۸۸ فقط سابقه؛ {B2_PENDING_MEGAMENU_HELICOIL_NAV} جداست.»"
        ),
        "owner_architecture_decision_status": "STRUCTURAL_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Category {LEGACY_CATEGORY_55_ID} under {THREAD_REPAIR_SCIENTIFIC_DOMAIN} with "
            f"{HELICOIL_COMMERCE_IDENTITY_CODE} ({THREAD_REPAIR_COMMERCE_ROOT_CODE}); "
            f"preserve {HELICOIL_LIVE_PRODUCT_COUNT} live product IDs per immutable "
            f"{B2_SENSITIVE_CATEGORY_DOSSIER}; separate from CUTTING; contextual tapping links "
            f"without duplicate assignments; historic {historic_ids} deprecated, do not recreate; "
            f"{B2_PENDING_MEGAMENU_HELICOIL_NAV} remains separate pending decision."
        ),
    }


def build_journal_entry_010() -> dict[str, str]:
    historic = "|".join(DEPRECATED_HELICOIL_HISTORIC_CATEGORY_IDS)
    return {
        "journal_entry_id": "OWNER-ARCH-DECISION-010",
        "decision_id": DECISION_ID_MEGAMENU_186_187_188,
        "decision_date": "2026-10-18",
        "decision_type": "EXECUTION_DESIGN_DIRECTION_APPROVAL",
        "b2_decision_group_id": DECISION_ID_MEGAMENU_186_187_188,
        "owner_statement_fa": (
            "«جهت طراحی حذف ارجاع مگامنو به ۱۸۶/۱۸۷/۱۸۸ را تأیید می‌کنم؛ "
            f"جایگزینی بر اساس دسته ۵۵ و {HELICOIL_COMMERCE_IDENTITY_CODE}؛ "
            "بدون بازسازی ریشه‌های تاریخی؛ پیاده‌سازی ناوبری و URL در فاز اجرا.»"
        ),
        "owner_architecture_decision_status": "EXECUTION_DESIGN_ACCEPTED",
        "linked_prerequisite_gate_ids": GATE_IR_MARKET_NAMING_SEO,
        "category_apply_authorization": "NO",
        "product_reassignment_authorization": "NO",
        "seo_deployment_authorization": "NO",
        "production_mutation_authorization": "NO",
        "b2_review_snapshot_preserved": "YES",
        "notes_en": (
            f"Design direction to eliminate megamenu refs to removed categories {historic}; "
            f"replacement navigation basis: category {LEGACY_CATEGORY_55_ID} / "
            f"{HELICOIL_COMMERCE_IDENTITY_CODE} subject to final validation; do not recreate "
            "historical roots; nav implementation and URL/redirect treatment deferred to execution "
            "design. Tier D: EXECUTION RELEASE dependency — does NOT block structural architecture "
            "freeze. No megamenu deploy or SEO deployment authorized."
        ),
    }


def build_gate_ir_market_naming_seo() -> dict[str, Any]:
    metrology_l2 = ", ".join(METROLOGY_L2_FAMILY_CODES)
    return {
        "gate_id": GATE_IR_MARKET_NAMING_SEO,
        "status": "PENDING_OWNER_REVIEW",
        "blocks_naming_and_seo_freeze": True,
        "blocks_category_apply": True,
        "blocks_seo_deployment": True,
        "required_evidence": [
            "Iranian-market terminology and search intent",
            "Karzar Search Console evidence where accessible",
            "Competitor taxonomy and keyword research",
            "All seven L1 display names (FA/EN proposals — not final until Owner freeze)",
            f"Three Metrology L2 display names ({metrology_l2})",
            "Impacted descendant landing pages",
            "Proposed SEO titles and H1",
            "URL preservation, slug changes, canonical and redirect implications",
            "Explicit separate Owner approval before naming/SEO freeze",
        ],
        "provisional_b1_b2_labels_are_not_final": True,
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


def build_hold_category_reconciliation() -> list[dict[str, str]]:
    hold_map = _read_csv(B2_DIR / "C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv")
    journal_by_group = {spec[1]: spec[0] for spec in JOURNAL_ENTRY_SPECS}
    rows: list[dict[str, str]] = []
    for row in hold_map:
        gid = row["decision_group_id"]
        rows.append(
            {
                "hold_category_id": row["hold_category_id"],
                "decision_group_id": gid,
                "b2_snapshot_owner_status": row["owner_architecture_decision_status"],
                "journal_entry_id": journal_by_group.get(gid, ""),
                "journal_authoritative": "YES",
                "note": "B2 HOLD map unchanged; Owner record in journal",
            }
        )
    return rows


def build_execution_gates_register() -> dict[str, Any]:
    return {
        "authorization_layers": [
            "historical_census_evidence",
            "b1_b2_architecture_recommendations",
            "owner_architecture_decisions_journal",
            "pending_market_naming_seo_gate",
            "pending_product_level_evidence",
            "future_execution_authorization",
        ],
        "owner_decisions_do_not_imply_execution": True,
        "gates": [
            {
                "gate_id": GATE_IR_MARKET_NAMING_SEO,
                "status": "PENDING_OWNER_REVIEW",
                "blocks_structural_architecture_freeze": False,
                "blocks_naming_seo_freeze": True,
            },
            {
                "gate_id": "PRODUCT-LEVEL-EVIDENCE-AND-MAPPING",
                "status": "PENDING",
                "record_count": BASELINE_PRODUCT_LEVEL_REQUIRED,
                "blocks_execution": True,
            },
            {
                "gate_id": "TX-OWNER-001-EVIDENCE-QUEUE",
                "status": "OPEN",
                "request_more_evidence_count": TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT,
                "blocks_execution": True,
            },
            {
                "gate_id": "TX-OWNER-001-DOCUMENTARY-EXIT",
                "status": "DOCUMENTARY_ONLY",
                "approve_catalog_exit_count": TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT,
                "apply_authorized": False,
            },
            {
                "gate_id": "MEGAMENU-NAV-IMPLEMENTATION",
                "status": "PENDING_EXECUTION_DESIGN",
                "journal_entry": "OWNER-ARCH-DECISION-010",
                "blocks_execution_release": True,
                "blocks_structural_architecture_freeze": False,
            },
            {
                "gate_id": "CATEGORY-APPLY",
                "status": "NO",
            },
            {
                "gate_id": "SEO-DEPLOYMENT",
                "status": "NO",
            },
            {
                "gate_id": "PRODUCTION-MUTATION",
                "status": "NO",
            },
        ],
    }


def build_effective_decision_state_summary() -> dict[str, Any]:
    return {
        "closeout_status": "TEN_OF_TEN_OWNER_DECISIONS_RECORDED",
        "b2_merge_sha": PR534_MERGE_SHA,
        "decision_count": len(JOURNAL_ENTRY_SPECS),
        "decisions": [
            {
                "journal_entry_id": spec[0],
                "decision_id": spec[1],
                "decision_type": spec[2],
            }
            for spec in JOURNAL_ENTRY_SPECS
        ],
        "baseline_invariants": {
            "live_product_rows": BASELINE_LIVE_PRODUCT_ROWS,
            "product_level_required": BASELINE_PRODUCT_LEVEL_REQUIRED,
            "tx_owner_approve_catalog_exit_documentary": TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT,
            "tx_owner_request_more_evidence_open": TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT,
            "protected_oil_product_ids_category_156": LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT,
            "helicoil_live_product_ids_category_55": HELICOIL_LIVE_PRODUCT_COUNT,
            "approved_executable_target_codes": BASELINE_APPROVED_EXECUTABLE_TARGET_CODES,
            "hold_category_ids_count": 11,
        },
        "safety": {
            "DESIGN_ONLY": "YES",
            "CATEGORY_APPLY": "NO",
            "PRODUCT_REASSIGNMENT": "NO",
            "SEO_DEPLOYMENT": "NO",
            "PRODUCTION_MUTATION": "NO",
        },
    }


def build_owner_architecture_closeout_report(validation: dict[str, Any]) -> str:
    decision_table = "\n".join(
        f"| {spec[0]} | `{spec[1]}` | `{spec[2]}` |"
        for spec in JOURNAL_ENTRY_SPECS
    )
    return "\n".join(
        [
            "# Owner Architecture Decision Closeout (10/10)",
            "",
            f"**Validation:** `{validation['status']}`",
            "",
            f"B2 merge reference: `{PR534_MERGE_SHA}` (PR #534)",
            "",
            "## Ten Owner decisions (journal authoritative)",
            "",
            "| Journal entry | DECISION_ID | Type |",
            "|---------------|-------------|------|",
            decision_table,
            "",
            "## Closeout checks",
            "",
            "- Ten distinct B2 decision groups recorded in journal (B2 CSV remains historical PENDING).",
            "- Decision 001: conditional acceptance; naming/SEO/URL/APPLY excluded.",
            "- Decision 005: structural only — runtime publication NOT authorized.",
            "- Decision 010: execution design direction — blocks execution release, not architecture freeze.",
            f"- {BASELINE_LIVE_PRODUCT_ROWS} live product baseline preserved (B2 reconciliation).",
            f"- {BASELINE_PRODUCT_LEVEL_REQUIRED} PRODUCT_LEVEL_REQUIRED preserved.",
            f"- TX-OWNER-001: {TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT} documentary exit / "
            f"{TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT} evidence pending.",
            f"- Protected cohorts: {LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT} oils / "
            f"{HELICOIL_LIVE_PRODUCT_COUNT} Helicoil.",
            f"- Executable target codes: {BASELINE_APPROVED_EXECUTABLE_TARGET_CODES}.",
            "- Eleven HOLD category IDs traceable via `16-HOLD-CATEGORY-TO-DECISION-RECONCILIATION.csv`.",
            "",
            "## Remaining open gates",
            "",
            "See `15-EXECUTION-GATES-REGISTER.json` and `02-GATE-IR-MARKET-NAMING-SEO.json`.",
            "",
            "## Authorization separation",
            "",
            "Owner architecture approval does **not** authorize catalog APPLY, product reassignment, "
            "SEO deploy, or production mutation.",
        ]
    )


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
        "owner_decision_closeout": "TEN_OF_TEN_COMPLETE",
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
            f"- **`{DECISION_ID_FLUIDS_156_PUBLICATION}`** — publication of category 156 is a separate pending Owner decision.",
            "- Display names, SEO titles, H1, URLs, slugs (`IR-MARKET-NAMING-SEO`).",
            "- Production mutation, product reassignment, redirects, `CATEGORY_APPLY`.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `FLUIDS-155-FACET-NAV`; this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_fluids_156() -> str:
    return "\n".join(
        [
            "# Owner Architecture Decision — FLUIDS-156-PUBLICATION",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-005` |",
            "| **DECISION_ID** | `FLUIDS-156-PUBLICATION` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |",
            f"| **Legacy category** | `{LEGACY_CATEGORY_156_ID}` — Industrial Oil |",
            f"| **Proposed commerce identity** | `{FLUIDS_INDUSTRIAL_OIL_CODE}` under `{FLUIDS_COMMERCE_ROOT_CODE}` |",
            f"| **Protected product IDs** | {LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT} |",
            "| **B2 link** | group `FLUIDS-156-PUBLICATION` (name ≠ publication authorization) |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |",
            "",
            "## Approved (structural only)",
            "",
            f"- Preserve `{FLUIDS_INDUSTRIAL_OIL_CODE}` as the proposed specialized commerce identity.",
            f"- Preserve all **{LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT}** existing industrial-oil product IDs.",
            f"- Maintain architecture separation between legacy category **{LEGACY_CATEGORY_155_ID}** and proposed category **{LEGACY_CATEGORY_156_ID}**.",
            "- Protect the cohort from blanket removal or unintended reassignment.",
            "",
            "## Explicitly NOT approved",
            "",
            "- **Actual publication** of the category (runtime go-live).",
            "- Final Persian display name.",
            "- SEO title, H1, slug, URL, or redirects.",
            "- Product-level `APPLY` or category migration.",
            "- Any production deployment.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `FLUIDS-156-PUBLICATION`; "
            "this journal entry is authoritative for conditional structural acceptance only.",
        ]
    )


def build_decision_markdown_machine_accessories_163_164() -> str:
    return "\n".join(
        [
            "# Owner Architecture Decision — MACHINE-ACCESSORIES-163-164",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-006` |",
            "| **DECISION_ID** | `MACHINE-ACCESSORIES-163-164` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |",
            f"| **Legacy categories** | `{LEGACY_CATEGORY_163_ID}` (hub) · `{LEGACY_CATEGORY_164_ID}` (tapping accessories) |",
            f"| **Staging hub** | `{LEGACY_CATEGORY_163_STAGING_CODE}` |",
            f"| **Category 164 products** | {LEGACY_CATEGORY_164_PRODUCT_COUNT} (PRODUCT_LEVEL_REQUIRED — execution blocked) |",
            f"| **MACHINES root** | `{MACHINES_COMMERCE_ROOT_CODE}` |",
            "| **B2 link** | group `MACHINE-ACCESSORIES-163-164` |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (mandatory) |",
            "",
            "## Approved direction",
            "",
            f"- Keep category **{LEGACY_CATEGORY_163_ID}** as **TRANSITIONAL** during migration planning.",
            f"- Preserve all **{LEGACY_CATEGORY_164_PRODUCT_COUNT}** existing products under category **{LEGACY_CATEGORY_164_ID}**.",
            "- Require exact per-product technical evidence before determining final destination.",
            f"- Design specialized destination leaves within the **MACHINES** architecture (`{MACHINES_COMMERCE_ROOT_CODE}`), based on actual product identity.",
            "- Do **not** create another generic catch-all category as a substitute for decomposition.",
            "",
            "## Execution block",
            "",
            f"- The **{LEGACY_CATEGORY_164_PRODUCT_COUNT}** `PRODUCT_LEVEL_REQUIRED` records remain blocked from execution.",
            "",
            "## Explicitly NOT approved",
            "",
            "- `CATEGORY_APPLY`, product reassignment, SEO deploy, production mutation.",
            "- Approval of other pending B2 decision groups.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `MACHINE-ACCESSORIES-163-164`; "
            "this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_tx_owner_scope_157_160() -> str:
    cat_list = " · ".join(f"**{cid}**" for cid in TX_OWNER_SCOPE_CATEGORY_IDS)
    codes = "\n".join(f"- `{code}`" for code in TX_OWNER_DEPRECATED_TARGET_CODES)
    return "\n".join(
        [
            "# Owner Architecture Decision — TX-OWNER-SCOPE-157-160",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-007` |",
            "| **DECISION_ID** | `TX-OWNER-SCOPE-157-160` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |",
            f"| **Legacy categories** | {cat_list} (hand tools / woodworking) |",
            f"| **TX-OWNER-001 cohort** | {TX_OWNER_001_COHORT_PRODUCT_COUNT} product IDs |",
            "| **B2 link** | group `TX-OWNER-SCOPE-157-160` |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |",
            "",
            "## Approved structural direction",
            "",
            "- Exclude categories **157, 158, 159, 160** from the future seven-root specialized commerce architecture.",
            "- Record these identities as **DEPRECATED** in **target design only** (not production mutation).",
            "Target design codes:",
            codes,
            "",
            "## TX-OWNER-001 preservation (immutable prior journals)",
            "",
            f"- **`{TX_OWNER_001_PACKAGE_DIR}/`** — do not modify prior Owner authorization batches.",
            f"- **{TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT}** `APPROVE_CATALOG_EXIT` — documentary authorization only, **not** APPLY.",
            f"- **{TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT}** `REQUEST_MORE_EVIDENCE` — still open and protected.",
            f"- **Total scope:** exactly **{TX_OWNER_001_COHORT_PRODUCT_COUNT}** product IDs.",
            "- Do **not** change any individual product authorization.",
            "",
            "## Explicitly NOT approved",
            "",
            "- Blanket deletion, automatic category retirement, product deletion.",
            "- Product reassignment, redirect deployment, or HTTP 410.",
            "- `CATEGORY_APPLY`, SEO deploy, production deployment.",
            "- Approval of other pending B2 decision groups.",
            "",
            "## Future production",
            "",
            "Any production action requires separate exact-product evidence, prerequisite validation, "
            "and explicit Owner execution authorization.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `TX-OWNER-SCOPE-157-160`; "
            "this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_mixed_chucks_116_118() -> str:
    cats = " · ".join(f"**{cid}**" for cid in MIXED_CHUCK_CATEGORY_IDS)
    staging = "\n".join(f"- `{code}`" for code in MIXED_CHUCK_STAGING_CODES)
    plr_lines = "\n".join(
        f"- Category **{cid}**: {MIXED_CHUCK_PLR_COUNT_BY_CATEGORY[cid]}"
        for cid in MIXED_CHUCK_CATEGORY_IDS
    )
    return "\n".join(
        [
            "# Owner Architecture Decision — MIXED-CHUCKS-116-118",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-008` |",
            "| **DECISION_ID** | `MIXED-CHUCKS-116-118` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `CONDITIONAL_STRUCTURAL_APPROVAL` |",
            f"| **Legacy categories** | {cats} |",
            f"| **PRODUCT_LEVEL_REQUIRED total** | {MIXED_CHUCK_PLR_TOTAL} |",
            f"| **Workholding root** | `{WORKHOLDING_COMMERCE_ROOT_CODE}` |",
            "| **B2 link** | group `MIXED-CHUCKS-116-118` |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (mandatory for display/landing/URL) |",
            "",
            "## Approved direction (structural only)",
            "",
            "- Separate **chucks** from **chuck accessories** based on actual technical product identity.",
            f"- Preserve **{MIXED_CHUCK_PLR_TOTAL}** `PRODUCT_LEVEL_REQUIRED` records:",
            plr_lines,
            "- Keep legacy categories in **STAGING/HOLD** until validated migration prerequisites are satisfied.",
            "- Require per-product evidence and explicit destination review.",
            "- Do **not** delete category **118** merely because its decomposition cohort is zero.",
            "- Do **not** introduce another generic mixed catch-all destination.",
            "",
            "Staging identities (target design):",
            staging,
            "",
            "## Explicitly NOT approved",
            "",
            "- Product reassignment, category mutation, deletion.",
            "- SEO deployment, `CATEGORY_APPLY`, production deployment.",
            "- Approval of other pending B2 decision groups.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `MIXED-CHUCKS-116-118`; "
            "this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_helicoil_55() -> str:
    historic = " · ".join(f"**{cid}**" for cid in DEPRECATED_HELICOIL_HISTORIC_CATEGORY_IDS)
    dep_codes = "\n".join(f"- `{code}`" for code in DEPRECATED_HELICOIL_HISTORIC_CODES)
    return "\n".join(
        [
            "# Owner Architecture Decision — HELICOIL-55-THREAD-REPAIR",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-009` |",
            "| **DECISION_ID** | `HELICOIL-55-THREAD-REPAIR` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `STRUCTURAL_ARCHITECTURE_APPROVAL` |",
            f"| **Legacy category** | `{LEGACY_CATEGORY_55_ID}` — Helicoil |",
            f"| **Scientific domain** | `{THREAD_REPAIR_SCIENTIFIC_DOMAIN}` |",
            f"| **Proposed commerce identity** | `{HELICOIL_COMMERCE_IDENTITY_CODE}` under `{THREAD_REPAIR_COMMERCE_ROOT_CODE}` |",
            f"| **Live product IDs** | {HELICOIL_LIVE_PRODUCT_COUNT} (immutable B2 sensitive dossier) |",
            f"| **Evidence** | `{B2_SENSITIVE_CATEGORY_DOSSIER}` |",
            "| **B2 link** | group `HELICOIL-55-THREAD-REPAIR` |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |",
            "",
            "## Approved (structural)",
            "",
            f"- Place category **{LEGACY_CATEGORY_55_ID}** under independent **THREAD_REPAIR** domain architecture.",
            f"- Adopt proposed commerce identity `{HELICOIL_COMMERCE_IDENTITY_CODE}`.",
            f"- Preserve all **{HELICOIL_LIVE_PRODUCT_COUNT}** exact live product IDs from the frozen B2 dossier.",
            "- Keep Helicoil structurally **separate from CUTTING**.",
            "- Allow contextual navigation links from relevant tapping pages **without** duplicate category assignments.",
            f"- Preserve historic categories {historic} as deprecated records; **do not recreate** them.",
            "",
            "Deprecated historic target codes (do not recreate):",
            dep_codes,
            "",
            "## Explicitly NOT approved",
            "",
            "- Final display labels, SEO titles, URL, slug, redirects, or megamenu deployment.",
            "- Product reassignment or production mutation.",
            f"- **`{B2_PENDING_MEGAMENU_HELICOIL_NAV}`** — separate pending Owner decision.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `HELICOIL-55-THREAD-REPAIR`; "
            "this journal entry is authoritative.",
        ]
    )


def build_decision_markdown_megamenu_186_187_188() -> str:
    historic = " · ".join(f"**{cid}**" for cid in DEPRECATED_HELICOIL_HISTORIC_CATEGORY_IDS)
    return "\n".join(
        [
            "# Owner Architecture Decision — MEGAMENU-186-187-188",
            "",
            "| Field | Value |",
            "|-------|-------|",
            "| **Journal entry** | `OWNER-ARCH-DECISION-010` |",
            "| **DECISION_ID** | `MEGAMENU-186-187-188` |",
            "| **DECISION_DATE** | 2026-10-18 |",
            "| **DECISION_TYPE** | `EXECUTION_DESIGN_DIRECTION_APPROVAL` |",
            f"| **Removed nav targets** | {historic} (deprecated — do not recreate) |",
            f"| **Replacement basis** | Category **{LEGACY_CATEGORY_55_ID}** / `{HELICOIL_COMMERCE_IDENTITY_CODE}` |",
            "| **B2 tier** | D — execution release dependency |",
            "| **Gate** | `IR-MARKET-NAMING-SEO` (`PENDING_OWNER_REVIEW`) |",
            "",
            "## Approved design direction",
            "",
            "- Eliminate legacy megamenu references to removed category IDs **186, 187, 188**.",
            f"- Use valid category **{LEGACY_CATEGORY_55_ID}** and proposed semantic commerce identity "
            f"`{HELICOIL_COMMERCE_IDENTITY_CODE}` as the basis for replacement navigation (subject to final validation).",
            "- Do **not** recreate historical Helicoil L1 roots.",
            "- Determine actual navigation implementation and per-URL/redirect treatment in later execution design.",
            "",
            "## Architecture vs execution",
            "",
            "- This decision is an **EXECUTION RELEASE** dependency.",
            "- It does **not** block freezing the **structural** architecture (Decisions 001–009).",
            "",
            "## Explicitly NOT approved",
            "",
            "- Megamenu deployment, SEO deploy, redirects, or production mutation.",
            "- Product reassignment or duplicate CUTTING category assignments.",
            "",
            "## B2 snapshot policy",
            "",
            "Frozen B2 register still shows `PENDING` for `MEGAMENU-186-187-188`; "
            "this journal entry is authoritative for design direction only.",
        ]
    )


def _validate_closeout_invariants(errors: list[str], journal_rows: list[dict[str, str]]) -> None:
    decision_ids = [r["decision_id"] for r in journal_rows]
    if len(decision_ids) != len(set(decision_ids)):
        errors.append("duplicate_decision_ids")
    if len(decision_ids) != B2_TOTAL_DECISION_GROUPS:
        errors.append(f"decision_id_count_{len(decision_ids)}_not_{B2_TOTAL_DECISION_GROUPS}")

    arch7 = next(r for r in journal_rows if r["decision_id"] == DECISION_ID_ARCH_7_L1)
    if arch7.get("decision_type") != "CONDITIONAL_ARCHITECTURE_ACCEPTANCE":
        errors.append("decision_001_not_conditional")

    fluids156 = next(r for r in journal_rows if r["decision_id"] == DECISION_ID_FLUIDS_156_PUBLICATION)
    notes = fluids156.get("notes_en", "")
    if "publication" not in notes.lower() or "architecture only" not in notes.lower():
        if "not implied" not in notes.lower() and "runtime publication" not in notes.lower():
            errors.append("decision_005_publication_guard_missing")
    if fluids156.get("category_apply_authorization") != "NO":
        errors.append("decision_005_apply_not_no")

    megamenu = next((r for r in journal_rows if r["decision_id"] == DECISION_ID_MEGAMENU_186_187_188), None)
    if not megamenu:
        errors.append("missing_decision_010")
    elif "EXECUTION" not in megamenu.get("notes_en", ""):
        errors.append("decision_010_execution_scope_missing")

    recon = json.loads((B2_DIR / "I-B2-RECONCILIATION-REPORT.json").read_text(encoding="utf-8"))
    inv = recon.get("invariants_recalculated", {})
    if inv.get("live_product_rows") != BASELINE_LIVE_PRODUCT_ROWS:
        errors.append("baseline_live_product_rows_mismatch")
    if inv.get("product_level_decomposition_required") != BASELINE_PRODUCT_LEVEL_REQUIRED:
        errors.append("baseline_plr_mismatch")
    if inv.get("approved_executable_target_codes") != BASELINE_APPROVED_EXECUTABLE_TARGET_CODES:
        errors.append("executable_targets_not_zero")
    if inv.get("owner_journal_exits") != TX_OWNER_001_APPROVE_CATALOG_EXIT_COUNT:
        errors.append("tx_owner_exit_count_mismatch")
    if inv.get("owner_journal_evidence") != TX_OWNER_001_REQUEST_MORE_EVIDENCE_COUNT:
        errors.append("tx_owner_evidence_count_mismatch")
    if inv.get("category_156_product_rows") != LEGACY_CATEGORY_156_PROTECTED_PRODUCT_COUNT:
        errors.append("oil_27_mismatch")

    hold_rows = _read_csv(B2_DIR / "C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv")
    if len(hold_rows) != 11:
        errors.append(f"hold_category_count_{len(hold_rows)}_not_11")


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

    _validate_closeout_invariants(errors, rows)

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
    paths.decision_md_fluids_156.write_text(build_decision_markdown_fluids_156(), encoding="utf-8")
    paths.decision_md_machine_accessories_163_164.write_text(
        build_decision_markdown_machine_accessories_163_164(), encoding="utf-8"
    )
    paths.decision_md_tx_owner_scope_157_160.write_text(
        build_decision_markdown_tx_owner_scope_157_160(), encoding="utf-8"
    )
    paths.decision_md_mixed_chucks_116_118.write_text(
        build_decision_markdown_mixed_chucks_116_118(), encoding="utf-8"
    )
    paths.decision_md_helicoil_55.write_text(build_decision_markdown_helicoil_55(), encoding="utf-8")
    paths.decision_md_megamenu_186_187_188.write_text(
        build_decision_markdown_megamenu_186_187_188(), encoding="utf-8"
    )

    with paths.journal_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=JOURNAL_CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(build_journal_entry_001())
        writer.writerow(build_journal_entry_002())
        writer.writerow(build_journal_entry_003())
        writer.writerow(build_journal_entry_004())
        writer.writerow(build_journal_entry_005())
        writer.writerow(build_journal_entry_006())
        writer.writerow(build_journal_entry_007())
        writer.writerow(build_journal_entry_008())
        writer.writerow(build_journal_entry_009())
        writer.writerow(build_journal_entry_010())

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

    paths.effective_state_json.write_text(
        json.dumps(build_effective_decision_state_summary(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    paths.execution_gates_json.write_text(
        json.dumps(build_execution_gates_register(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    hold_rows = build_hold_category_reconciliation()
    with paths.hold_reconciliation_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "hold_category_id",
                "decision_group_id",
                "b2_snapshot_owner_status",
                "journal_entry_id",
                "journal_authoritative",
                "note",
            ],
        )
        writer.writeheader()
        writer.writerows(hold_rows)

    validation = validate_journal_package(paths)
    closeout = [
        "# Owner Architecture Decision Journal — validation closeout",
        "",
        f"**{validation['status']}**",
        "",
        json.dumps(validation, indent=2),
    ]
    (out_dir / "J-VALIDATION-CLOSEOUT-REPORT.md").write_text("\n".join(closeout), encoding="utf-8")
    paths.owner_closeout_md.write_text(
        build_owner_architecture_closeout_report(validation), encoding="utf-8"
    )

    artifacts = [
        "00-JOURNAL-IDENTITY.json",
        "01-OWNER-ARCHITECTURE-DECISION-JOURNAL.csv",
        "02-GATE-IR-MARKET-NAMING-SEO.json",
        "03-DECISION-ARCH-7-L1-ROOTS-2026-10-18.md",
        "05-DECISION-METROLOGY-L2-FAMILIES-2026-10-18.md",
        "06-DECISION-ACCESSORIES-154-DECOMPOSE-2026-10-18.md",
        "07-DECISION-FLUIDS-155-FACET-NAV-2026-10-18.md",
        "08-DECISION-FLUIDS-156-PUBLICATION-2026-10-18.md",
        "09-DECISION-MACHINE-ACCESSORIES-163-164-2026-10-18.md",
        "10-DECISION-TX-OWNER-SCOPE-157-160-2026-10-18.md",
        "11-DECISION-MIXED-CHUCKS-116-118-2026-10-18.md",
        "12-DECISION-HELICOIL-55-THREAD-REPAIR-2026-10-18.md",
        "13-DECISION-MEGAMENU-186-187-188-2026-10-18.md",
        "14-EFFECTIVE-DECISION-STATE-SUMMARY.json",
        "15-EXECUTION-GATES-REGISTER.json",
        "16-HOLD-CATEGORY-TO-DECISION-RECONCILIATION.csv",
        "04-B2-REMAINING-PENDING-DECISION-GROUPS.csv",
        "README.md",
        "J-VALIDATION-CLOSEOUT-REPORT.md",
        "K-OWNER-ARCHITECTURE-CLOSEOUT-REPORT.md",
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
            build_journal_entry_005(),
            build_journal_entry_006(),
            build_journal_entry_007(),
            build_journal_entry_008(),
            build_journal_entry_009(),
            build_journal_entry_010(),
        ],
    }
