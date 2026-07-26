"""Validation helpers for product image URL endpoints."""

import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.core.config import settings
from app.core.constants import ALLOWED_IMAGE_URL_EXTENSIONS, MAX_PRODUCT_IMAGES

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
        "kubernetes.default.svc",
    }
)

_PRIVATE_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _hostname_is_blocked(hostname: str) -> bool:
    lowered = hostname.strip().lower().rstrip(".")
    if not lowered:
        return True
    if lowered in _BLOCKED_HOSTNAMES:
        return True
    if lowered.endswith(".localhost") or lowered.endswith(".local"):
        return True

    # Literal IPv4 / IPv6 in hostname.
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", lowered):
            return True
        return False

    return any(address in network for network in _PRIVATE_NETWORKS)


def _resolve_and_block_private(hostname: str) -> None:
    """Resolve hostname and reject if any A/AAAA lands in a private/special network."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("image_url hostname could not be resolved") from exc

    if not infos:
        raise ValueError("image_url hostname could not be resolved")

    for info in infos:
        sockaddr = info[4]
        ip_text = sockaddr[0]
        try:
            address = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if any(address in network for network in _PRIVATE_NETWORKS):
            raise ValueError("image_url must not target internal or private hosts")


def validate_product_image_url(image_url: str, *, resolve_dns: bool = True) -> str:
    """Ensure the image URL looks like a supported, non-internal image resource."""
    normalized = image_url.strip()
    if not normalized:
        raise ValueError("image_url cannot be empty")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("image_url must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("image_url must not include credentials")
    if not parsed.hostname:
        raise ValueError("image_url must include a hostname")
    if _hostname_is_blocked(parsed.hostname):
        raise ValueError("image_url must not target internal or private hosts")

    path_lower = parsed.path.lower()
    if not any(path_lower.endswith(ext) for ext in ALLOWED_IMAGE_URL_EXTENSIONS):
        allowed = ", ".join(sorted(ALLOWED_IMAGE_URL_EXTENSIONS))
        raise ValueError(f"image_url must point to an image file ({allowed})")

    if len(normalized) > 500:
        raise ValueError("image_url exceeds maximum length of 500 characters")

    # Resolve-time SSRF guard (DNS rebinding): block if resolved IPs are private.
    if resolve_dns and not _hostname_is_literal_ip(parsed.hostname):
        try:
            _resolve_and_block_private(parsed.hostname)
        except ValueError as exc:
            # Production: fail closed. DEBUG: allow unresolved fixture hosts (example.com).
            if settings.DEBUG and "could not be resolved" in str(exc):
                pass
            else:
                raise

    return normalized


def _hostname_is_literal_ip(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname.strip().lower().rstrip("."))
        return True
    except ValueError:
        return False


def ensure_image_count_within_limit(current_count: int) -> None:
    if current_count >= MAX_PRODUCT_IMAGES:
        raise ValueError(f"A product may have at most {MAX_PRODUCT_IMAGES} images")
