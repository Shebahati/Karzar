"""Wave Evidence Artifact allowlist contract (Prompt 141).

Wave Evidence source authorization is sealed in ``policy_json.evidence_artifacts``
and therefore part of the canonical Wave manifest SHA. Each pin is identified by
``artifact_pk`` + stable ``artifact_id`` + ``checksum_sha256`` — all three must
agree with the ``knowledge_evidence_artifacts`` row.

Invariant (execute / resume / Evidence Validate):
A Wave may only assert Evidence from an Artifact whose identity and checksum
were included in the Wave's sealed manifest policy (or the historical sealed
Wave compatibility fallback for Artifact pk=1 / 108A).

Historical already-sealed Waves without ``evidence_artifacts`` resolve to the
legacy Artifact-1 pin. New Waves being sealed with ``require_evidence=true``
must pin sources explicitly (no silent fallback at pre-seal).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import KnowledgeEvidenceArtifact
from app.services.knowledge_wave_fact_contract import wave_require_evidence_from_policy

# Historical sealed Waves (001–052 era) omitted evidence_artifacts; fallback only.
LEGACY_WAVE_EVIDENCE_ARTIFACT_PK = 1
LEGACY_WAVE_EVIDENCE_ARTIFACT_ID = "insize-108a-catalogue-v1"
LEGACY_WAVE_EVIDENCE_ARTIFACT_CHECKSUM = (
    "4b251dbbd6b662e64dcc1703dd373886f8e3df8e3363a5406bc706c8aa85123b"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class WaveEvidenceArtifactPin:
    """One sealed Evidence Artifact authorization pin."""

    artifact_pk: int
    artifact_id: str
    checksum_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_pk": self.artifact_pk,
            "artifact_id": self.artifact_id,
            "checksum_sha256": self.checksum_sha256,
        }


LEGACY_WAVE_EVIDENCE_ARTIFACT_PIN = WaveEvidenceArtifactPin(
    artifact_pk=LEGACY_WAVE_EVIDENCE_ARTIFACT_PK,
    artifact_id=LEGACY_WAVE_EVIDENCE_ARTIFACT_ID,
    checksum_sha256=LEGACY_WAVE_EVIDENCE_ARTIFACT_CHECKSUM,
)


class EvidenceArtifactContractError(ValueError):
    """Malformed or missing Wave Evidence Artifact pin contract."""

    def __init__(
        self,
        message: str,
        *,
        field: str = "policy_json.evidence_artifacts",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


def _validation(message: str, *, field: str) -> None:
    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code=ErrorCode.VALIDATION_FAILED,
        message=message,
        details=[{"field": field, "message": message}],
    )


def _conflict(message: str, *, field: str) -> None:
    raise api_error(
        status.HTTP_409_CONFLICT,
        error_code=ErrorCode.CONFLICT,
        message=message,
        details=[{"field": field, "message": message}],
    )


def pin_lookup_by_pk(
    pins: tuple[WaveEvidenceArtifactPin, ...] | list[WaveEvidenceArtifactPin],
) -> dict[int, WaveEvidenceArtifactPin]:
    return {p.artifact_pk: p for p in pins}


def allowed_artifact_pks(
    pins: tuple[WaveEvidenceArtifactPin, ...] | list[WaveEvidenceArtifactPin],
) -> frozenset[int]:
    return frozenset(p.artifact_pk for p in pins)


def parse_evidence_artifact_pins(raw: Any) -> tuple[WaveEvidenceArtifactPin, ...]:
    """Parse and validate ``evidence_artifacts`` list shape (no DB I/O)."""
    if not isinstance(raw, list) or not raw:
        raise EvidenceArtifactContractError(
            "evidence_artifacts must be a non-empty list"
        )

    pins: list[WaveEvidenceArtifactPin] = []
    seen_pk: set[int] = set()
    seen_id: set[str] = set()
    for idx, item in enumerate(raw):
        field = f"policy_json.evidence_artifacts[{idx}]"
        if not isinstance(item, dict):
            raise EvidenceArtifactContractError(
                "each evidence_artifacts entry must be an object",
                field=field,
            )
        pk_raw = item.get("artifact_pk")
        if not isinstance(pk_raw, int) or isinstance(pk_raw, bool) or pk_raw < 1:
            raise EvidenceArtifactContractError(
                "artifact_pk must be a positive integer",
                field=f"{field}.artifact_pk",
            )
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            raise EvidenceArtifactContractError(
                "artifact_id must be a non-empty string",
                field=f"{field}.artifact_id",
            )
        artifact_id = artifact_id.strip()
        checksum_raw = item.get("checksum_sha256")
        if not isinstance(checksum_raw, str) or not checksum_raw.strip():
            raise EvidenceArtifactContractError(
                "checksum_sha256 must be a non-empty string",
                field=f"{field}.checksum_sha256",
            )
        checksum = checksum_raw.strip().lower()
        if not _SHA256_RE.fullmatch(checksum):
            raise EvidenceArtifactContractError(
                "checksum_sha256 must be 64 lowercase hex characters",
                field=f"{field}.checksum_sha256",
            )
        if pk_raw in seen_pk:
            raise EvidenceArtifactContractError(
                f"duplicate artifact_pk={pk_raw}",
                field=f"{field}.artifact_pk",
            )
        if artifact_id in seen_id:
            raise EvidenceArtifactContractError(
                f"duplicate artifact_id={artifact_id!r}",
                field=f"{field}.artifact_id",
            )
        seen_pk.add(pk_raw)
        seen_id.add(artifact_id)
        pins.append(
            WaveEvidenceArtifactPin(
                artifact_pk=pk_raw,
                artifact_id=artifact_id,
                checksum_sha256=checksum,
            )
        )
    return tuple(pins)


def resolve_wave_evidence_artifact_contract(
    policy_json: dict[str, Any] | None,
    *,
    allow_legacy_fallback: bool,
) -> tuple[WaveEvidenceArtifactPin, ...]:
    """Return deterministic allowed Artifact pins for a Wave policy.

    When ``evidence_artifacts`` is absent/null and ``allow_legacy_fallback`` is
    True (sealed historical Waves), return the Artifact-1 / 108A pin.
    When absent and fallback is disallowed (new-wave pre-seal), raise.
    """
    policy: dict[str, Any] = policy_json if isinstance(policy_json, dict) else {}
    if "evidence_artifacts" not in policy or policy.get("evidence_artifacts") is None:
        if allow_legacy_fallback:
            return (LEGACY_WAVE_EVIDENCE_ARTIFACT_PIN,)
        raise EvidenceArtifactContractError(
            "evidence_artifacts is required for new Waves when Evidence sources "
            "must be pinned (require_evidence=true)"
        )
    return parse_evidence_artifact_pins(policy.get("evidence_artifacts"))


async def assert_db_matches_evidence_artifact_pins(
    db: AsyncSession,
    pins: tuple[WaveEvidenceArtifactPin, ...] | list[WaveEvidenceArtifactPin],
) -> None:
    """Fail closed unless every pin matches the live Artifact row on all three axes."""
    for pin in pins:
        row = await db.get(KnowledgeEvidenceArtifact, pin.artifact_pk)
        if row is None:
            _conflict(
                f"Evidence Artifact pk={pin.artifact_pk} not found",
                field="evidence_artifacts.artifact_pk",
            )
        if (row.artifact_id or "") != pin.artifact_id:
            _conflict(
                f"Evidence Artifact pk={pin.artifact_pk} artifact_id mismatch "
                f"(pinned={pin.artifact_id!r}, db={row.artifact_id!r})",
                field="evidence_artifacts.artifact_id",
            )
        db_checksum = (row.checksum_sha256 or "").lower()
        if db_checksum != pin.checksum_sha256:
            _conflict(
                f"Evidence Artifact pk={pin.artifact_pk} checksum mismatch vs sealed pin",
                field="evidence_artifacts.checksum_sha256",
            )


def raise_contract_as_validation(exc: EvidenceArtifactContractError) -> None:
    _validation(exc.message, field=exc.field)


async def collect_wave_evidence_artifact_preseal_issues(
    db: AsyncSession,
    policy_json: Any,
) -> list[dict[str, str]]:
    """Pre-seal checks for ``evidence_artifacts`` (issues with severity=error)."""
    issues: list[dict[str, str]] = []
    policy: dict[str, Any] = policy_json if isinstance(policy_json, dict) else {}
    require_evidence = wave_require_evidence_from_policy(policy)
    missing = (
        "evidence_artifacts" not in policy or policy.get("evidence_artifacts") is None
    )

    if missing:
        if require_evidence:
            issues.append(
                {
                    "field": "policy_json.evidence_artifacts",
                    "message": (
                        "required when require_evidence=true; "
                        "pin each authorized Artifact by artifact_pk, "
                        "artifact_id, and checksum_sha256"
                    ),
                    "severity": "error",
                }
            )
        return issues

    try:
        pins = parse_evidence_artifact_pins(policy.get("evidence_artifacts"))
    except EvidenceArtifactContractError as exc:
        issues.append(
            {
                "field": exc.field,
                "message": exc.message,
                "severity": "error",
            }
        )
        return issues

    for pin in pins:
        row = await db.get(KnowledgeEvidenceArtifact, pin.artifact_pk)
        if row is None:
            issues.append(
                {
                    "field": "policy_json.evidence_artifacts",
                    "message": f"artifact_pk={pin.artifact_pk} not found",
                    "severity": "error",
                }
            )
            continue
        if (row.artifact_id or "") != pin.artifact_id:
            issues.append(
                {
                    "field": "policy_json.evidence_artifacts",
                    "message": (
                        f"artifact_pk={pin.artifact_pk} artifact_id mismatch "
                        f"(pinned={pin.artifact_id!r}, db={row.artifact_id!r})"
                    ),
                    "severity": "error",
                }
            )
        db_checksum = (row.checksum_sha256 or "").lower()
        if db_checksum != pin.checksum_sha256:
            issues.append(
                {
                    "field": "policy_json.evidence_artifacts",
                    "message": (
                        f"artifact_pk={pin.artifact_pk} checksum_sha256 mismatch "
                        "vs DB row"
                    ),
                    "severity": "error",
                }
            )
    return issues
