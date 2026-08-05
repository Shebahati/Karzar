"""HTTP helpers for candidate discovery (reuse image_discovery transport)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from image_discovery.contracts import DiscoveryError  # noqa: E402
from image_discovery.transport import (  # noqa: E402
    HostThrottledFetcher,
    host_allowed,
    host_of,
)

__all__ = ["DiscoveryError", "HostThrottledFetcher", "host_allowed", "host_of"]
