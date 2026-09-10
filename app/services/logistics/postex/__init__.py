"""Postex provider package."""

from app.services.logistics.postex.client import PostexClient
from app.services.logistics.postex.provider import PostexProvider

__all__ = ["PostexClient", "PostexProvider"]
