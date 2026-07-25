"""In-process background job heartbeats for readiness/metrics (ARCH / OPS)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

_lock = Lock()
_heartbeats: dict[str, datetime] = {}


@dataclass(frozen=True)
class JobHeartbeatSnapshot:
    job: str
    last_run_at: datetime | None


def record_job_heartbeat(job: str, *, when: datetime | None = None) -> None:
    stamp = when or datetime.now(UTC)
    with _lock:
        _heartbeats[job] = stamp


def get_job_heartbeat(job: str) -> datetime | None:
    with _lock:
        return _heartbeats.get(job)


def all_job_heartbeats() -> list[JobHeartbeatSnapshot]:
    with _lock:
        return [
            JobHeartbeatSnapshot(job=name, last_run_at=stamp)
            for name, stamp in sorted(_heartbeats.items())
        ]
