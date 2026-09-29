"""PR3-B.1 — Wave lifecycle foundation (status map + deny-by-default)."""

from __future__ import annotations

import pytest
from app.services.knowledge_wave_lifecycle import (
    ALLOWED_TRANSITIONS,
    WAVE_STATUS_ABORTED,
    WAVE_STATUS_ARCHIVED,
    WAVE_STATUS_ASSERTED,
    WAVE_STATUS_DRAFT,
    WAVE_STATUS_EVIDENCE_VALIDATED,
    WAVE_STATUS_EXECUTING,
    WAVE_STATUS_FAILED,
    WAVE_STATUS_PUBLISHED,
    WAVE_STATUS_PUBLISHING,
    WAVE_STATUS_REVIEWED,
    WAVE_STATUS_SEALED,
    WAVE_STATUS_SUPERSEDED,
    WAVE_STATUSES,
    assert_mutable_pre_seal,
    assert_transition,
    can_transition,
    is_post_seal,
)
from fastapi import HTTPException


def test_pr3b_status_vocabulary_complete() -> None:
    expected = {
        "Draft",
        "Reviewed",
        "Sealed",
        "Executing",
        "Asserted",
        "EvidenceValidated",
        "Publishing",
        "Published",
        "Failed",
        "Aborted",
        "Superseded",
        "Archived",
    }
    assert WAVE_STATUSES == expected
    assert set(ALLOWED_TRANSITIONS) == expected


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (WAVE_STATUS_ASSERTED, WAVE_STATUS_EVIDENCE_VALIDATED),
        (WAVE_STATUS_EVIDENCE_VALIDATED, WAVE_STATUS_PUBLISHING),
        (WAVE_STATUS_PUBLISHING, WAVE_STATUS_PUBLISHED),
        (WAVE_STATUS_DRAFT, WAVE_STATUS_REVIEWED),
        (WAVE_STATUS_REVIEWED, WAVE_STATUS_SEALED),
        (WAVE_STATUS_SEALED, WAVE_STATUS_EXECUTING),
        (WAVE_STATUS_EXECUTING, WAVE_STATUS_ASSERTED),
        (WAVE_STATUS_EXECUTING, WAVE_STATUS_FAILED),
        (WAVE_STATUS_ASSERTED, WAVE_STATUS_FAILED),
        (WAVE_STATUS_FAILED, WAVE_STATUS_SEALED),
        (WAVE_STATUS_FAILED, WAVE_STATUS_PUBLISHING),
        (WAVE_STATUS_FAILED, WAVE_STATUS_SUPERSEDED),
        (WAVE_STATUS_FAILED, WAVE_STATUS_ARCHIVED),
        (WAVE_STATUS_PUBLISHED, WAVE_STATUS_ARCHIVED),
        (WAVE_STATUS_ABORTED, WAVE_STATUS_ARCHIVED),
        (WAVE_STATUS_EVIDENCE_VALIDATED, WAVE_STATUS_ARCHIVED),
        (WAVE_STATUS_PUBLISHING, WAVE_STATUS_FAILED),
    ],
)
def test_allowed_transitions(current: str, target: str) -> None:
    assert can_transition(current, target) is True
    assert_transition(current, target)  # no raise


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (WAVE_STATUS_DRAFT, WAVE_STATUS_SEALED),
        (WAVE_STATUS_DRAFT, WAVE_STATUS_EXECUTING),
        (WAVE_STATUS_REVIEWED, WAVE_STATUS_EXECUTING),
        (WAVE_STATUS_SEALED, WAVE_STATUS_PUBLISHED),
        (WAVE_STATUS_ASSERTED, WAVE_STATUS_PUBLISHED),
        (WAVE_STATUS_SEALED, WAVE_STATUS_PUBLISHING),
        (WAVE_STATUS_PUBLISHED, WAVE_STATUS_EXECUTING),
        (WAVE_STATUS_PUBLISHED, WAVE_STATUS_DRAFT),
        (WAVE_STATUS_SEALED, WAVE_STATUS_ASSERTED),
        (WAVE_STATUS_DRAFT, WAVE_STATUS_PUBLISHED),
        (WAVE_STATUS_ARCHIVED, WAVE_STATUS_DRAFT),
        (WAVE_STATUS_FAILED, WAVE_STATUS_EVIDENCE_VALIDATED),
    ],
)
def test_forbidden_transitions(current: str, target: str) -> None:
    assert can_transition(current, target) is False
    with pytest.raises(HTTPException) as exc:
        assert_transition(current, target)
    assert exc.value.status_code == 409


def test_post_seal_immutability_helper() -> None:
    assert is_post_seal(WAVE_STATUS_SEALED)
    assert is_post_seal(WAVE_STATUS_ASSERTED)
    assert is_post_seal(WAVE_STATUS_EVIDENCE_VALIDATED)
    assert is_post_seal(WAVE_STATUS_PUBLISHED)
    assert not is_post_seal(WAVE_STATUS_DRAFT)
    assert not is_post_seal(WAVE_STATUS_REVIEWED)

    assert_mutable_pre_seal(WAVE_STATUS_DRAFT)  # no raise
    with pytest.raises(HTTPException) as exc:
        assert_mutable_pre_seal(WAVE_STATUS_SEALED)
    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert "immutable" in str(detail.get("message", "")).lower()


def test_identity_transition_allowed() -> None:
    """Same-status is a no-op edge (review refresh, etc.)."""
    assert can_transition(WAVE_STATUS_REVIEWED, WAVE_STATUS_REVIEWED) is True
    assert_transition(WAVE_STATUS_ASSERTED, WAVE_STATUS_ASSERTED)
