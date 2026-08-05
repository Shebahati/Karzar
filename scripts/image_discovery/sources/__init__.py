"""Source adapters package."""

from __future__ import annotations

from .base import SourceAdapter
from .dasqua_official import DasquaOfficialAdapter
from .insize_tosag import InsizeTosagAdapter
from .sanou_official import SanouOfficialAdapter

ADAPTERS: dict[str, type[SourceAdapter]] = {
    "dasqua_official": DasquaOfficialAdapter,
    "insize_tosag": InsizeTosagAdapter,
    "sanou_official": SanouOfficialAdapter,
}


def get_adapter(name: str) -> SourceAdapter:
    try:
        cls = ADAPTERS[name]
    except KeyError as e:
        raise SystemExit(f"Unknown source adapter: {name}. Known: {sorted(ADAPTERS)}") from e
    return cls()
