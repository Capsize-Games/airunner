"""URL safety helpers for outbound HTTP fetches.

These guardrails are intended to reduce SSRF risk when tools are allowed to fetch
arbitrary URLs (e.g., research/crawling tooling).

Policy (default):
- Only allow http/https URLs.
- Disallow userinfo.
- Disallow private/loopback/link-local/etc destinations (IPv4 + IPv6), including
  hostnames that resolve to such addresses.
- Enforce a conservative redirect limit and re-validate every hop.
- Enforce a conservative max response size.

This is not a complete SSRF solution (e.g., DNS rebinding), but it provides
meaningful baseline protections.
"""

from __future__ import annotations

import os
import socket
import ipaddress
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urljoin

import requests


@dataclass(frozen=True)
class SSRFBlocked(ValueError):
    reason: str

    def __str__(self) -> str:  # pragma: no cover
        return self.reason


def _is_ip_disallowed(ip: ipaddress._BaseAddress) -> bool:
    # Prefer an allow-by-default posture: only globally-routable IPs are allowed.
    # This blocks RFC1918, loopback, link-local (incl. metadata), multicast, etc.
    return not bool(ip.is_global)


def _resolve_host_ips(hostname: str, port: int) -> set[ipaddress._BaseAddress]:
    ips: set[ipaddress._BaseAddress] = set()
    for family, _type, _proto, _canonname, sockaddr in socket.getaddrinfo(
        hostname, port
    ):
        if family == socket.AF_INET:
            ip_str = sockaddr[0]
        elif family == socket.AF_INET6:
            ip_str = sockaddr[0]
        else:
            continue

        try:
            ips.add(ipaddress.ip_address(ip_str))
        except ValueError:
            continue

    return ips


def validate_url_for_fetch(url: str) -> None:
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

    host_lower = hostname.strip().lower()
    if host_lower == "localhost":
        raise SSRFBlocked("localhost not allowed")

    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise SSRFBlocked("invalid port") from exc

    port = parsed_port or (443 if scheme == "https" else 80)

    # Block IP literals directly.
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_ip_disallowed(ip):
            raise SSRFBlocked("ip address not allowed")
        return
    except ValueError:
        pass

    # Resolve DNS and reject if it resolves to disallowed IPs.
    try:
        ips = _resolve_host_ips(hostname, port)
    except socket.gaierror as exc:
        raise SSRFBlocked("hostname could not be resolved") from exc

    if not ips:
        raise SSRFBlocked("hostname could not be resolved")

    if any(_is_ip_disallowed(ip) for ip in ips):
        raise SSRFBlocked("hostname resolves to disallowed ip")


def safe_fetch_url(
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout_seconds: Optional[float] = None,
    max_redirects: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> str:
    """Fetch a URL with SSRF guardrails and conservative limits.

    Returns the response body as text (best-effort decoding).
    """

    if timeout_seconds is None:
        timeout_seconds = float(os.environ.get("AIRUNNER_SCRAPER_TIMEOUT_SECONDS", "8"))

    if max_redirects is None:
        max_redirects = int(os.environ.get("AIRUNNER_SCRAPER_MAX_REDIRECTS", "3"))

    if max_bytes is None:
        max_bytes = int(os.environ.get("AIRUNNER_SCRAPER_MAX_BYTES", "2000000"))

    session = requests.Session()

    current = url
    redirects_followed = 0

    while True:
        validate_url_for_fetch(current)

        resp = session.get(
            current,
            headers=headers,
            timeout=timeout_seconds,
            allow_redirects=False,
            stream=True,
        )

        if resp.status_code in {301, 302, 303, 307, 308} and resp.headers.get("location"):
            redirects_followed += 1
            if redirects_followed > max_redirects:
                raise SSRFBlocked("too many redirects")
            current = urljoin(current, resp.headers["location"])
            continue

        total = 0
        chunks: list[bytes] = []
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise SSRFBlocked("response too large")
            chunks.append(chunk)

        body = b"".join(chunks)

        encoding = resp.encoding or "utf-8"
        try:
            return body.decode(encoding, errors="replace")
        except LookupError:
            return body.decode("utf-8", errors="replace")
