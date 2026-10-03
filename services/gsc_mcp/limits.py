from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from services.gsc_mcp.errors import ErrorCode, GscMcpError


@dataclass
class InspectionRateLimiter:
    daily_soft_limit: int
    _day_key: str = field(default="")
    _count: int = 0
    _lock: Lock = field(default_factory=Lock)

    def _current_day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def acquire(self) -> None:
        with self._lock:
            day = self._current_day()
            if day != self._day_key:
                self._day_key = day
                self._count = 0
            if self._count >= self.daily_soft_limit:
                raise GscMcpError(
                    ErrorCode.RATE_LIMITED,
                    f"URL inspection daily soft limit ({self.daily_soft_limit}) reached",
                )
            self._count += 1


@dataclass
class InMemoryRateLimiter:
    """Lightweight per-key rate limiter (process-local)."""

    max_per_minute: int
    _events: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _lock: Lock = field(default_factory=Lock)

    def acquire(self, key: str) -> None:
        now = time.monotonic()
        window = 60.0
        with self._lock:
            events = [t for t in self._events[key] if now - t < window]
            if len(events) >= self.max_per_minute:
                raise GscMcpError(ErrorCode.RATE_LIMITED, f"Rate limit exceeded for {key}")
            events.append(now)
            self._events[key] = events
