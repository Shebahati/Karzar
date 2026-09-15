"""READ-ONLY zcc.ir catalog discovery and Karzar reconciliation (Phase 1).

This package never writes to Karzar, production, or zcc.ir. There is no APPLY path.
Parser/script version is independent of Karzar catalog authority: zcc.ir values are
observed provenance only unless a later Accepted decision says otherwise.
"""

from __future__ import annotations

PARSER_VERSION = "zcc_ir_catalog/1.0.0"
SOURCE_SITE = "zcc.ir"
SOURCE_ORIGIN = "https://zcc.ir"
USER_AGENT = (
    "KarzarCatalogResearch/1.0 "
    "(+https://www.karzartools.com; read-only catalog discovery; Phase 1 inventory)"
)

FORBIDDEN_FLAGS = ("--apply", "--write", "--write-db", "--mutate", "--production-apply")
