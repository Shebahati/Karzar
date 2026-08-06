"""Robots classification helpers (fixture-friendly; no silent crawl)."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from . import MultisourceError


def classify_robots_text(
    robots_txt: str,
    *,
    user_agent: str,
    url: str,
) -> dict[str, str]:
    parser = RobotFileParser()
    parser.parse((robots_txt or "").splitlines())
    allowed = parser.can_fetch(user_agent, url)
    return {
        "robots_status": "allow" if allowed else "disallow",
        "user_agent": user_agent,
        "url": url,
        "crawl_permitted": "true" if allowed else "false",
    }


def classify_robots_from_url(
    robots_url: str,
    *,
    user_agent: str,
    target_url: str,
    fetch_text,
) -> dict[str, str]:
    """fetch_text(url) -> str; injected for fixtures / offline tests."""
    host = urlparse(robots_url).hostname
    if not host:
        raise MultisourceError("robots", f"invalid robots url: {robots_url}")
    text = fetch_text(robots_url)
    result = classify_robots_text(text, user_agent=user_agent, url=target_url)
    result["robots_url"] = robots_url
    return result
