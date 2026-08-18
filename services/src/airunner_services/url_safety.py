"""URL safety helpers for outbound HTTP fetches.

These guardrails reduce SSRF risk when tooling is allowed to fetch
arbitrary URLs.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class SSRFBlocked(ValueError):
    """Raised when one URL violates the SSRF safety policy."""

    reason: str

    def __str__(self) -> str:  # pragma: no cover
        return self.reason


# NAT64 prefixes that embed an IPv4 address in the low 32 bits (RFC 6052
# well-known prefix and RFC 8215 local-use prefix). ``ipaddress.is_global``
# reports True for these prefixes because they are globally routed, even when
# the embedded IPv4 is loopback/private -- so the embedded address must be
# checked explicitly or ``http://[64:ff9b::7f00:1]/`` becomes a loopback
# SSRF vector on NAT64 networks (issue #2029).
_NAT64_EMBEDDING_PREFIXES = (
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
)

# Deprecated 6to4 relay anycast (RFC 7526). Legacy routers may still forward
# these; treat the range as disallowed for outbound fetches.
_6TO4_RELAY_ANYCAST = ipaddress.ip_network("192.88.99.0/24")


def _is_ip_disallowed(ip: ipaddress._BaseAddress) -> bool:
    """Return True when one IP should be blocked for outbound fetches."""
    if not ip.is_global:
        return True
    # Multicast addresses are not routable fetch targets even though some
    # multicast ranges report ``is_global`` True.
    if ip.is_multicast:
        return True
    if isinstance(ip, ipaddress.IPv6Address) and any(
        ip in prefix for prefix in _NAT64_EMBEDDING_PREFIXES
    ):
        embedded_ipv4 = ipaddress.ip_address(int(ip) & 0xFFFFFFFF)
        return _is_ip_disallowed(embedded_ipv4)
    if isinstance(ip, ipaddress.IPv4Address) and ip in _6TO4_RELAY_ANYCAST:
        return True
    return False


def _allowed_host_set() -> frozenset[str]:
    """Return the env-configured SSRF host/IP allow-list.

    Operators may set ``AIRUNNER_SSRF_ALLOWED_HOSTS`` to a comma-separated
    list of hostnames and/or IP literals (for example legitimate intranet
    mirrors) that are exempt from the private/link-local IP rejection rules.
    """
    raw = os.environ.get("AIRUNNER_SSRF_ALLOWED_HOSTS", "").strip()
    return frozenset(host.strip().lower() for host in raw.split(",") if host.strip())


def _host_is_allowed(
    hostname: str,
    ips: set[ipaddress._BaseAddress],
) -> bool:
    """Return True when one hostname or any of its IPs is allow-listed."""
    allowed = _allowed_host_set()
    if not allowed:
        return False
    if hostname.strip().lower() in allowed:
        return True
    return any(str(ip) in allowed for ip in ips)


def _resolve_host_ips(
    hostname: str,
    port: int,
) -> set[ipaddress._BaseAddress]:
    """Resolve one hostname to all candidate IP addresses."""
    ips: set[ipaddress._BaseAddress] = set()
    for family, _type, _proto, _canonname, sockaddr in socket.getaddrinfo(
        hostname,
        port,
    ):
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue

        ip_str = sockaddr[0]
        try:
            ips.add(ipaddress.ip_address(ip_str))
        except ValueError:
            continue

    return ips


def validate_url_for_fetch(url: str) -> None:
    """Validate one URL against the AIRunner fetch safety policy."""
    raw = (url or "").strip()
    if not raw:
        raise SSRFBlocked("missing url")

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise SSRFBlocked("unsupported url scheme")

    if parsed.username or parsed.password:
        raise SSRFBlocked("userinfo not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlocked("missing hostname")

    if hostname.strip().lower() == "localhost":
        raise SSRFBlocked("localhost not allowed")

    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise SSRFBlocked("invalid port") from exc

    port = parsed_port or (443 if scheme == "https" else 80)

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip is not None:
        if _host_is_allowed(hostname, {ip}):
            return
        if _is_ip_disallowed(ip):
            raise SSRFBlocked("ip address not allowed")
        return

    try:
        ips = _resolve_host_ips(hostname, port)
    except socket.gaierror as exc:
        raise SSRFBlocked("hostname could not be resolved") from exc

    if not ips:
        raise SSRFBlocked("hostname could not be resolved")

    if _host_is_allowed(hostname, ips):
        return

    if any(_is_ip_disallowed(ip_address) for ip_address in ips):
        raise SSRFBlocked("hostname resolves to disallowed ip")


def safe_fetch_url(
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout_seconds: Optional[float] = None,
    max_redirects: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> str:
    """Fetch one URL with SSRF guardrails and return decoded text."""
    body, encoding = _fetch_body_and_encoding(
        url,
        headers=headers,
        timeout_seconds=timeout_seconds,
        max_redirects=max_redirects,
        max_bytes=max_bytes,
    )
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def safe_fetch_bytes(
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout_seconds: Optional[float] = None,
    max_redirects: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> bytes:
    """Fetch one URL with SSRF guardrails and return raw bytes."""
    body, _encoding = _fetch_body_and_encoding(
        url,
        headers=headers,
        timeout_seconds=timeout_seconds,
        max_redirects=max_redirects,
        max_bytes=max_bytes,
    )
    return body


def _fetch_body_and_encoding(
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout_seconds: Optional[float] = None,
    max_redirects: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> tuple[bytes, str]:
    """Fetch one URL and return its body plus response encoding."""
    timeout_seconds, max_redirects, max_bytes = _request_limits(
        timeout_seconds,
        max_redirects,
        max_bytes,
    )
    current = url
    redirects_followed = 0

    with requests.Session() as session:
        while True:
            validate_url_for_fetch(current)
            with session.get(
                current,
                headers=headers,
                timeout=timeout_seconds,
                allow_redirects=False,
                stream=True,
            ) as response:
                redirect = response.headers.get("location")
                if (
                    response.status_code in {301, 302, 303, 307, 308}
                    and redirect
                ):
                    redirects_followed += 1
                    if redirects_followed > max_redirects:
                        raise SSRFBlocked("too many redirects")
                    current = urljoin(current, redirect)
                    continue

                body = _read_response_body(response, max_bytes)
                return body, response.encoding or "utf-8"


def _request_limits(
    timeout_seconds: Optional[float],
    max_redirects: Optional[int],
    max_bytes: Optional[int],
) -> tuple[float, int, int]:
    """Resolve one fetch limit set from optional overrides or env."""
    if timeout_seconds is None:
        timeout_seconds = float(
            os.environ.get("AIRUNNER_SCRAPER_TIMEOUT_SECONDS", "8")
        )

    if max_redirects is None:
        max_redirects = int(
            os.environ.get("AIRUNNER_SCRAPER_MAX_REDIRECTS", "3")
        )

    if max_bytes is None:
        max_bytes = int(
            os.environ.get("AIRUNNER_SCRAPER_MAX_BYTES", "2000000")
        )

    return timeout_seconds, max_redirects, max_bytes


def _read_response_body(
    response: requests.Response,
    max_bytes: int,
) -> bytes:
    """Read one streamed response with a hard response-size cap."""
    total = 0
    chunks: list[bytes] = []
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise SSRFBlocked("response too large")
        chunks.append(chunk)
    return b"".join(chunks)


__all__ = [
    "SSRFBlocked",
    "safe_fetch_bytes",
    "safe_fetch_url",
    "validate_url_for_fetch",
]