"""Source adapters package."""

from __future__ import annotations

from .base import SourceAdapter
from .insize_tosag import InsizeTosagAdapter

ADAPTERS: dict[str, type[SourceAdapter]] = {
    "insize_tosag": InsizeTosagAdapter,
}


def get_adapter(name: str) -> SourceAdapter:
    try:
        cls = ADAPTERS[name]
    except KeyError as e:
        raise SystemExit(f"Unknown source adapter: {name}. Known: {sorted(ADAPTERS)}") from e
    return cls()
