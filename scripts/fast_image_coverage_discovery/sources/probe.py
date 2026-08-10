"""TLS/DNS probe diagnostics without disabling certificate verification."""

from __future__ import annotations

import socket
import ssl
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .base import ProbeResult


def _resolve(host: str) -> tuple[list[str], list[str], str]:
    ipv4: list[str] = []
    ipv6: list[str] = []
    try:
        for fam, _type, _proto, _canon, sockaddr in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
            if fam == socket.AF_INET:
                ipv4.append(sockaddr[0])
            elif fam == socket.AF_INET6:
                ipv6.append(sockaddr[0])
    except socket.gaierror as exc:
        return [], [], f"dns_failure:{exc}"
    return list(dict.fromkeys(ipv4)), list(dict.fromkeys(ipv6)), ""


def _tls_handshake(host: str, *, prefer_ipv4: bool = True, timeout: float = 15.0) -> tuple[bool, str]:
    ipv4, ipv6, dns_err = _resolve(host)
    if dns_err:
        return False, dns_err
    targets: list[tuple[str, int]] = []
    if prefer_ipv4 and ipv4:
        targets.extend((ip, socket.AF_INET) for ip in ipv4[:2])
    if ipv6:
        targets.extend((ip, socket.AF_INET6) for ip in ipv6[:1])
    if not prefer_ipv4 and ipv4:
        targets.extend((ip, socket.AF_INET) for ip in ipv4[:1])
    if not targets:
        return False, "dns_failure:no_addresses"
    ctx = ssl.create_default_context()
    last = "tls_handshake_timeout"
    for ip, fam in targets:
        try:
            sock = socket.socket(fam, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, 443) if fam == socket.AF_INET else (ip, 443, 0, 0))
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                ssock.do_handshake()
                return True, ""
        except TimeoutError:
            last = "tls_handshake_timeout"
        except ssl.SSLCertVerificationError as exc:
            return False, f"certificate_error:{exc}"
        except ssl.SSLError as exc:
            last = f"certificate_error:{exc}"
        except OSError as exc:
            last = f"connect_timeout:{exc}"
        finally:
            try:
                sock.close()
            except Exception:
                pass
    return False, last


def probe_url(source_id: str, url: str, *, attempts: int = 2, timeout: float = 15.0) -> ProbeResult:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    result = ProbeResult(source_id=source_id, domain=host, attempt_count=0)
    if not host:
        result.failure_class = "dns_failure"
        result.notes = "empty_host"
        return result

    ipv4, ipv6, dns_err = _resolve(host)
    result.dns_ok = not dns_err and bool(ipv4 or ipv6)
    result.ipv4_ok = bool(ipv4)
    result.ipv6_ok = bool(ipv6)
    if dns_err:
        result.failure_class = "dns_failure"
        result.notes = dns_err
        return result

    last_fail = ""
    for i in range(1, attempts + 1):
        result.attempt_count = i
        tls_ok, tls_err = _tls_handshake(host, prefer_ipv4=True, timeout=timeout)
        result.tls_ok = tls_ok
        if not tls_ok:
            last_fail = tls_err or "tls_handshake_timeout"
            continue
        try:
            req = Request(url, headers={"User-Agent": "KarzarFastCoverage/1.1", "Accept": "*/*"})
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — explicit probe of configured sources
                result.http_status = int(getattr(resp, "status", None) or resp.getcode())
            if result.http_status == 403:
                result.failure_class = "http_403"
            elif result.http_status == 429:
                result.failure_class = "http_429"
            elif result.http_status and result.http_status >= 500:
                result.failure_class = "http_5xx"
            elif result.http_status and 200 <= result.http_status < 400:
                result.failure_class = ""
                return result
            else:
                result.failure_class = f"http_{result.http_status}"
        except TimeoutError:
            last_fail = "connect_timeout"
            result.failure_class = "connect_timeout"
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if "certificate" in msg or "ssl" in msg:
                result.failure_class = "certificate_error"
            else:
                result.failure_class = "connect_timeout"
            last_fail = str(exc)
    if not result.failure_class:
        result.failure_class = last_fail or "connect_timeout"
    result.notes = last_fail
    return result
