"""Postex provider package."""

from __future__ import annotations

from typing import Any

from app.services.logistics.postex.client import PostexClient

__all__ = ["PostexClient", "PostexProvider"]


def __getattr__(name: str) -> Any:
    if name == "PostexProvider":
        from app.services.logistics.postex.provider import PostexProvider

        return PostexProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
