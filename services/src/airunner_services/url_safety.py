"""URL safety helpers for outbound HTTP fetches.

These guardrails reduce SSRF risk when tooling is allowed to fetch
arbitrary URLs.
"""

from __future__ import annotations

import contextlib
import ipaddress
import os
import socket
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests

from airunner_common import settings as _airunner_settings


@dataclass
class SSRFBlocked(ValueError):
    """Raised when one URL violates the SSRF safety policy.

    Deliberately not ``frozen``: CPython's exception machinery assigns
    ``__traceback__``/``__cause__``/``__context__`` onto a raised
    exception as it propagates, and a nested generator-based context
    manager's re-raise path (``contextlib``'s ``__exit__``) does this
    explicitly. A frozen dataclass blocks that assignment and crashes
    with ``FrozenInstanceError`` instead of propagating the original
    error — found while adding ``OfflineModeBlocked`` below (release
    issue O01), which hit this every time it propagated uncaught
    through ``_fetch_body_and_encoding``'s nested ``with`` blocks.
    """

    reason: str

    def __str__(self) -> str:  # pragma: no cover
        return self.reason


@dataclass
class OfflineModeBlocked(ValueError):
    """Raised when an outbound fetch is attempted while offline mode is on.

    Distinct from ``SSRFBlocked`` so a caller/test can tell "denied because
    offline" apart from "denied because the target itself is unsafe"
    (release issue O01). Not frozen, for the same reason as ``SSRFBlocked``.
    """

    reason: str

    def __str__(self) -> str:  # pragma: no cover
        return self.reason


def is_offline_mode() -> bool:
    """Return whether external (non-loopback) network egress is denied.

    Reads ``airunner_common.settings.AIRUNNER_OFFLINE_MODE`` by attribute
    lookup on every call (not a value captured at import time) so tests
    and any future settings bridge can flip it without reimporting this
    module.
    """
    return bool(_airunner_settings.AIRUNNER_OFFLINE_MODE)


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


@dataclass(frozen=True)
class ResolvedFetchTarget:
    """One URL validated for fetching, with its DNS resolution pinned.

    ``ip`` is the single validated address the connection must use. It is
    chosen from the addresses returned by the one DNS resolution performed
    during validation, so connecting to it -- instead of resolving the
    hostname again at connect time -- closes the validate-then-connect
    DNS-rebinding window (issue #2490): an attacker hostname that resolves
    to a public address for validation and a private address a moment
    later still connects to the validated address.
    """

    url: str
    scheme: str
    hostname: str
    port: int
    ip: str


def _parse_fetch_url(url: str) -> tuple[str, str, int]:
    """Return one URL's scheme, hostname and effective port after checks."""
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
    return scheme, hostname, port


def resolve_url_for_fetch(url: str) -> ResolvedFetchTarget:
    """Validate one URL and resolve its host exactly once.

    Returns the validated target with the single IP the connection must
    use. Every redirect hop must be resolved separately through this
    function so each hop is validated and pinned before connecting.
    """
    if is_offline_mode():
        raise OfflineModeBlocked(
            "external network access is disabled while offline mode is on"
        )

    scheme, hostname, port = _parse_fetch_url(url)

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip is not None:
        if _host_is_allowed(hostname, {ip}):
            return ResolvedFetchTarget(
                url=url, scheme=scheme, hostname=hostname, port=port,
                ip=str(ip),
            )
        if _is_ip_disallowed(ip):
            raise SSRFBlocked("ip address not allowed")
        return ResolvedFetchTarget(
            url=url, scheme=scheme, hostname=hostname, port=port,
            ip=str(ip),
        )

    try:
        ips = _resolve_host_ips(hostname, port)
    except socket.gaierror as exc:
        raise SSRFBlocked("hostname could not be resolved") from exc

    if not ips:
        raise SSRFBlocked("hostname could not be resolved")

    if not _host_is_allowed(hostname, ips):
        if any(_is_ip_disallowed(ip_address) for ip_address in ips):
            raise SSRFBlocked("hostname resolves to disallowed ip")

    # Pin one validated address deterministically so repeated fetches of
    # the same hostname do not flap between its addresses.
    pinned = min(str(ip_address) for ip_address in ips)
    return ResolvedFetchTarget(
        url=url, scheme=scheme, hostname=hostname, port=port, ip=pinned
    )


def validate_url_for_fetch(url: str) -> Optional[ResolvedFetchTarget]:
    """Validate one URL against the AIRunner fetch safety policy.

    Returns the resolved target carrying the single validated IP the
    connection must use; see :func:`resolve_url_for_fetch`. Returning the
    target (instead of nothing) lets callers pin their connection to the
    exact address that was validated.
    """
    return resolve_url_for_fetch(url)


_pin_lock = threading.Lock()
_pin_installs = 0
_real_getaddrinfo = None
_thread_dns_pins = threading.local()
_absent_pin: object = object()


def _pinned_host_key(hostname: str) -> str:
    """Return one normalized DNS-pin lookup key for a hostname."""
    return hostname.lower().rstrip(".")


def _pinned_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Honor thread-local validated DNS pins, delegating everything else."""
    pinned_ip = None
    if isinstance(host, str):
        pins = getattr(_thread_dns_pins, "pins", None) or {}
        pinned_ip = pins.get(_pinned_host_key(host))
    resolver = _real_getaddrinfo
    if pinned_ip is None:
        return resolver(host, port, family, type, proto, flags)
    # Resolve the pinned IP literal through the real resolver so the
    # returned sockaddr tuples keep the correct family-specific shape.
    return resolver(pinned_ip, port, family, type, proto, flags)


@contextlib.contextmanager
def pinned_dns(
    target: Optional[ResolvedFetchTarget],
) -> Iterator[Optional[ResolvedFetchTarget]]:
    """Pin one validated hostname to its validated IP for one connection.

    While active, ``socket.getaddrinfo`` calls from this thread for the
    target hostname return only the validated IP, so the HTTP stack
    connects to the address validation approved even if the hostname's
    DNS record changed (rebound) after validation. Other hostnames, other
    threads, and non-string hosts are delegated to the real resolver
    untouched. ``None`` (returned by test doubles that stub out URL
    validation) disables pinning and yields ``None``.
    """
    global _pin_installs, _real_getaddrinfo
    if target is None:
        yield None
        return
    key = _pinned_host_key(target.hostname)
    pins = getattr(_thread_dns_pins, "pins", None)
    if pins is None:
        pins = {}
        _thread_dns_pins.pins = pins
    previous = pins.get(key, _absent_pin)
    pins[key] = target.ip
    with _pin_lock:
        if _pin_installs == 0:
            _real_getaddrinfo = socket.getaddrinfo
            socket.getaddrinfo = _pinned_getaddrinfo
        _pin_installs += 1
    try:
        yield target
    finally:
        if previous is _absent_pin:
            pins.pop(key, None)
        else:
            pins[key] = previous
        with _pin_lock:
            _pin_installs -= 1
            if _pin_installs == 0:
                socket.getaddrinfo = _real_getaddrinfo
                _real_getaddrinfo = None


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
            # Resolve once per hop and pin the connection to the validated
            # IP, then re-validate every redirect target before following
            # it, so neither DNS rebinding nor redirect chains can steer
            # the connection onto an unvalidated address.
            target = validate_url_for_fetch(current)
            with pinned_dns(target):
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
    "OfflineModeBlocked",
    "ResolvedFetchTarget",
    "SSRFBlocked",
    "is_offline_mode",
    "pinned_dns",
    "resolve_url_for_fetch",
    "safe_fetch_bytes",
    "safe_fetch_url",
    "validate_url_for_fetch",
]