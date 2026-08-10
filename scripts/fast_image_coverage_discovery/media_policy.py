"""Safe media/CDN host policy for product-page image URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def classify_media_host(page_url: str, image_url: str) -> tuple[bool, str, str, str]:
    """Return (allowed, page_host, media_host, relation)."""
    page = urlparse(page_url)
    img = urlparse(image_url)
    page_host = (page.hostname or "").lower()
    media_host = (img.hostname or "").lower()
    if img.scheme != "https":
        return False, page_host, media_host, "rejected_scheme"
    if not media_host or media_host in {"localhost", "127.0.0.1", "::1"}:
        return False, page_host, media_host, "rejected_localhost"
    # IP literal rejection
    try:
        ipaddress.ip_address(media_host)
        return False, page_host, media_host, "rejected_ip_literal"
    except ValueError:
        pass
    if img.username or img.password:
        return False, page_host, media_host, "rejected_credentials"
    if img.port not in (None, 443):
        return False, page_host, media_host, "rejected_port"
    try:
        infos = socket.getaddrinfo(media_host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, page_host, media_host, "rejected_dns"
    for info in infos:
        ip = info[4][0]
        if _is_private_ip(ip):
            return False, page_host, media_host, "rejected_private_dns"

    if media_host == page_host:
        relation = "same_host"
    elif media_host.endswith("." + page_host) or page_host.endswith("." + media_host):
        relation = "subdomain"
    else:
        relation = "external_cdn"
    return True, page_host, media_host, relation
