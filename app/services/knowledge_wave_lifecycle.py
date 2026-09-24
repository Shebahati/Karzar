"""Knowledge Wave status vocabulary + deny-by-default transitions (PR3-B.1).

Single source of truth for allowed wave lifecycle edges. Existing review /
seal / execute services call ``assert_transition``; PR3-B.2/B.3 endpoints
will reuse the same map without duplicating rules.
"""

from __future__ import annotations

from fastapi import status

from app.core.errors import ErrorCode, api_error

# --- Status constants (exact DB strings) ---

WAVE_STATUS_DRAFT = "Draft"
WAVE_STATUS_REVIEWED = "Reviewed"
WAVE_STATUS_SEALED = "Sealed"
WAVE_STATUS_EXECUTING = "Executing"
WAVE_STATUS_ASSERTED = "Asserted"
WAVE_STATUS_EVIDENCE_VALIDATED = "EvidenceValidated"
WAVE_STATUS_PUBLISHING = "Publishing"
WAVE_STATUS_PUBLISHED = "Published"
WAVE_STATUS_FAILED = "Failed"
WAVE_STATUS_ABORTED = "Aborted"
WAVE_STATUS_SUPERSEDED = "Superseded"
WAVE_STATUS_ARCHIVED = "Archived"

WAVE_STATUSES: frozenset[str] = frozenset(
    {
        WAVE_STATUS_DRAFT,
        WAVE_STATUS_REVIEWED,
        WAVE_STATUS_SEALED,
        WAVE_STATUS_EXECUTING,
        WAVE_STATUS_ASSERTED,
        WAVE_STATUS_EVIDENCE_VALIDATED,
        WAVE_STATUS_PUBLISHING,
        WAVE_STATUS_PUBLISHED,
        WAVE_STATUS_FAILED,
        WAVE_STATUS_ABORTED,
        WAVE_STATUS_SUPERSEDED,
        WAVE_STATUS_ARCHIVED,
    }
)

# Deny-by-default: only listed edges are legal.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    WAVE_STATUS_DRAFT: frozenset({WAVE_STATUS_REVIEWED}),
    WAVE_STATUS_REVIEWED: frozenset({WAVE_STATUS_DRAFT, WAVE_STATUS_SEALED}),
    WAVE_STATUS_SEALED: frozenset({WAVE_STATUS_EXECUTING}),
    WAVE_STATUS_EXECUTING: frozenset({WAVE_STATUS_ASSERTED, WAVE_STATUS_FAILED}),
    WAVE_STATUS_ASSERTED: frozenset(
        {WAVE_STATUS_EVIDENCE_VALIDATED, WAVE_STATUS_FAILED}
    ),
    WAVE_STATUS_EVIDENCE_VALIDATED: frozenset(
        {WAVE_STATUS_PUBLISHING, WAVE_STATUS_ARCHIVED}
    ),
    WAVE_STATUS_PUBLISHING: frozenset(
        {WAVE_STATUS_PUBLISHED, WAVE_STATUS_FAILED}
    ),
    WAVE_STATUS_PUBLISHED: frozenset({WAVE_STATUS_ARCHIVED}),
    WAVE_STATUS_FAILED: frozenset(
        {
            WAVE_STATUS_SEALED,  # PR3-A assert resume re-approve
            WAVE_STATUS_PUBLISHING,  # PR3-B.3 publish resume
            WAVE_STATUS_SUPERSEDED,
            WAVE_STATUS_ARCHIVED,
        }
    ),
    WAVE_STATUS_ABORTED: frozenset({WAVE_STATUS_ARCHIVED}),
    WAVE_STATUS_SUPERSEDED: frozenset(),
    WAVE_STATUS_ARCHIVED: frozenset(),
}

# Statuses at/after Seal: policy + manifest_sha256 immutable.
POST_SEAL_STATUSES: frozenset[str] = frozenset(
    {
        WAVE_STATUS_SEALED,
        WAVE_STATUS_EXECUTING,
        WAVE_STATUS_ASSERTED,
        WAVE_STATUS_EVIDENCE_VALIDATED,
        WAVE_STATUS_PUBLISHING,
        WAVE_STATUS_PUBLISHED,
        WAVE_STATUS_FAILED,
        WAVE_STATUS_ABORTED,
        WAVE_STATUS_SUPERSEDED,
        WAVE_STATUS_ARCHIVED,
    }
)


def can_transition(current: str, target: str) -> bool:
    """Return True iff ``current → target`` is an allowed edge."""
    if current == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def allowed_targets(current: str) -> frozenset[str]:
    return ALLOWED_TRANSITIONS.get(current, frozenset())


def is_post_seal(status_value: str) -> bool:
    return status_value in POST_SEAL_STATUSES


def assert_transition(current: str, target: str) -> None:
    """Raise 409 CONFLICT when the edge is not allowed (deny-by-default)."""
    cur = (current or "").strip()
    tgt = (target or "").strip()
    if cur not in WAVE_STATUSES:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=f"Unknown wave status '{cur}'",
            details=[{"field": "status", "message": cur}],
        )
    if tgt not in WAVE_STATUSES:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=f"Unknown target wave status '{tgt}'",
            details=[{"field": "to_status", "message": tgt}],
        )
    if not can_transition(cur, tgt):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=f"Illegal wave transition {cur} → {tgt}",
            details=[
                {"field": "status", "message": cur},
                {"field": "to_status", "message": tgt},
            ],
        )


def assert_mutable_pre_seal(status_value: str) -> None:
    """Reject Draft-field / policy mutation once Seal (or later) is reached."""
    if is_post_seal(status_value):
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Sealed waves are immutable",
            details=[{"field": "status", "message": status_value}],
        )
