"""READ-ONLY zcc.ir Phase 2 import planning. No APPLY path; no catalog mutation."""

from __future__ import annotations

PHASE2_VERSION = "zcc_ir_phase2/1.0.0"
FORBIDDEN_FLAGS = ("--apply", "--write", "--write-db", "--mutate", "--production-apply")
